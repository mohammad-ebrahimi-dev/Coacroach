"""Continuous first-page topic collection with best-effort text minimization."""
from datetime import datetime, timezone
from email.message import Message
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import json
import hashlib
import logging
import re
import threading
import time

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from .load_safety_monitor import LoadSafetyMonitor
from .ninisite_pilot import save_numbered_topic
from .persian_html import parse_topic
from .text_safety import clean_message
from .connectors import check_ninisite_continuous_permission
from .policy_cache import PolicyCache

ORIGIN = 'https://www.ninisite.com'
ROBOTS = ORIGIN + '/robots.txt'
LISTING = ORIGIN + '/discussion'
TOPIC_PATH = re.compile(r'^/discussion/topic/([0-9]+)(?:/[^?#]*)?$')
logger = logging.getLogger('market_tool.ninisite')


class TopicSummary(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: str = 'topic_summary'
    topic_id: str = Field(pattern=r'^[0-9]+$')
    complete: bool = False
    messages_on_first_page: int = Field(ge=1)
    retrieved_at: str


def topic_link(url):
    try:
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.hostname != 'www.ninisite.com' or parts.port not in (None, 443):
            return None
    except ValueError:
        return None
    if parts.username or parts.password or parts.query or parts.fragment:
        return None
    match = TOPIC_PATH.fullmatch(parts.path)
    return match.group(1) if match else None


class ContinuousNiniSiteCollector:
    """Read permitted topic pages and save filtered first-page messages.

    Author fields, URL slugs and raw HTML are not stored or logged. Automated
    filtering cannot guarantee that names or sensitive content are absent.
    """
    permission_status = 'User-authorized filtered first-page'

    def __init__(self, state, monitor_factory=None, cycle_wait=60):
        self.state = state
        self.monitor_factory = monitor_factory or (lambda: LoadSafetyMonitor(delay_seconds=10))
        self.cycle_wait = cycle_wait
        self._start_lock = threading.Lock()
        self._safety_latched = False
        self._policy_cache = PolicyCache()
        self._gone_path = self.state.root / 'gone-url-sha256.txt'
        self._gone = None

    def permitted(self):
        try:
            check_ninisite_continuous_permission(self)
            return not self._safety_latched
        except PermissionError:
            return False

    def start(self):
        with self._start_lock:
            if self.state.attached or not self.permitted():
                return False
            monitor = self.monitor_factory()
            try:
                self.state.attach(monitor, self.permitted)
            except Exception:
                monitor.close()
                raise
            threading.Thread(target=self._supervise, args=(monitor,), daemon=True).start()
            return True

    def _existing_ids(self):
        seen = set()
        folder = self.state.root / 'processed' / 'topic'
        if not folder.exists():
            return seen
        for path in list(folder.glob('*.jsonl')) + list(folder.glob('P[0-9]*/*.jsonl')):
            try:
                with path.open(encoding='utf-8') as file:
                    row = json.loads(file.readline())
                if row.get('kind') == 'topic_first_page' and str(row.get('topic_id', '')).isdigit():
                    seen.add(str(row['topic_id']))
            except (OSError, ValueError, AttributeError):
                continue
        return seen

    def _gone_urls(self):
        if self._gone is None:
            try:
                self._gone = set(self._gone_path.read_text(encoding='ascii').splitlines())
            except FileNotFoundError:
                self._gone = set()
        return self._gone

    def _url_key(self, url):
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def _request(self, url):
        key = self._url_key(url)
        if key in self._gone_urls():
            raise ValueError('url_gone')
        # 429/403/CAPTCHA and the second consecutive timeout/5xx latch in the monitor.
        for attempt in range(2):
            try:
                response = self.state.monitored_get(url, retry=attempt)
            except httpx.TimeoutException:
                logger.warning('network_timeout retry=%d', attempt)
                continue
            if 500 <= response.status_code <= 599:
                logger.warning('server_error status=%d retry=%d', response.status_code, attempt)
                continue
            if response.status_code == 410:
                self._gone_path.parent.mkdir(parents=True, exist_ok=True)
                with self._gone_path.open('a', encoding='ascii') as file:
                    file.write(key + '\n')
                    file.flush()
                self._gone.add(key)
                return response
            if response.status_code == 301:
                return response
            if response.status_code != 200:
                raise ValueError('access_denied_or_unavailable')
            return response
        raise ValueError('repeated_network_failure')

    def _supervise(self, monitor):
        # Reuse the monitor so the interval and safety latch survive recovery.
        try:
            while True:
                if not self._run(monitor):
                    return
                with self.state.lock:
                    self.state.reason = 'connection_retry_in_60_seconds'
                if not self.state.wait_for_next_cycle(60):
                    return
                with self.state.lock:
                    self.state.reason = None
        finally:
            if self.state.attached:
                self.state.finish()
            monitor.close()

    def _run(self, monitor):
        try:
            def read_policy():
                policy_text = self._policy_cache.get(ROBOTS)
                if policy_text is None:
                    robots = self._request(ROBOTS)
                    if robots.status_code != 200 or 'text/plain' not in robots.headers.get('content-type', '').lower():
                        raise ValueError('robots_unavailable')
                    policy_text = robots.text
                    self._policy_cache.put(ROBOTS, robots)
                current = RobotFileParser()
                current.parse(policy_text.splitlines())
                if not current.can_fetch('IranMarketResearch', LISTING):
                    raise ValueError('robots_denied')
                crawl_delay = current.crawl_delay('IranMarketResearch')
                if crawl_delay and crawl_delay > 10:
                    raise ValueError('stricter_crawl_delay')
                return current

            policy = read_policy()
            policy_checked = time.monotonic()
            seen = self._existing_ids()
            while self.state.checkpoint():
                if time.monotonic() - policy_checked >= 3600:
                    policy = read_policy()
                    policy_checked = time.monotonic()
                listing = self._request(LISTING)
                if listing.status_code != 200 or 'html' not in listing.headers.get('content-type', '').lower():
                    raise ValueError('unexpected_content')
                soup = BeautifulSoup(listing.content, 'html.parser')
                queue = []
                queued = set()
                for link in soup.select('a[href]'):
                    url = urljoin(LISTING, link.get('href', ''))
                    topic_id = topic_link(url)
                    if topic_id and topic_id not in seen and topic_id not in queued and self._url_key(url) not in self._gone_urls() and policy.can_fetch('IranMarketResearch', url):
                        queued.add(topic_id)
                        queue.append((topic_id, url))
                        self.state.count_topic_once('topics_identified', topic_id)
                self.state.count(pages=1)
                for topic_id, url in queue:
                    if not self.state.checkpoint():
                        return
                    if time.monotonic() - policy_checked >= 3600:
                        policy = read_policy()
                        policy_checked = time.monotonic()
                    if not policy.can_fetch('IranMarketResearch', url):
                        continue
                    response = self._request(url)
                    if response.status_code in (301, 410):
                        continue
                    if 'html' not in response.headers.get('content-type', '').lower():
                        raise ValueError('unexpected_content')
                    title, messages = parse_topic(response)
                    content_type = Message()
                    content_type['content-type'] = response.headers.get('content-type', '')
                    charset = content_type.get_content_charset()
                    html = response.content.decode(charset, errors='strict') if charset else response.content
                    soup = BeautifulSoup(html, 'html.parser')
                    author_names = [node.get_text(' ', strip=True) for node in soup.select('.nickname')]
                    self.state.count(pages=1, messages_identified=len(messages))
                    self.state.count_topic_once('topics_examined', topic_id)
                    if not self.state.checkpoint():
                        return
                    # A first-page count is not a complete topic or full pagination.
                    header = TopicSummary(topic_id=topic_id, messages_on_first_page=len(messages),
                                          retrieved_at=datetime.now(timezone.utc).isoformat()).model_dump()
                    header['kind'] = 'topic_first_page'
                    title = clean_message(title, author_names)
                    if title:
                        header['title'] = title
                    records = [header]
                    for index, text in enumerate(messages):
                        cleaned = clean_message(text, author_names)
                        if cleaned:
                            records.append({'kind': 'post' if index == 0 else 'reply', 'text': cleaned})
                    save_numbered_topic(self.state.root, records)
                    self.state.count(messages_saved=len(records)-1)
                    seen.add(topic_id)
                # New topics may appear later. Sleep without an HTTP request and
                # keep pause/end responsive via the shared condition.
                if not self.state.wait_for_next_cycle(self.cycle_wait):
                    return
        except httpx.ConnectError:
            logger.warning('connection_error automatic_retry')
            return True
        except Exception as exc:
            logger.warning('collection_stopped error_type=%s', type(exc).__name__)
            if monitor.stop_reason:
                self._safety_latched = True
                self.state.finish(error=self.state._safe_stop_reason())
            elif self.state.stop_requested:
                self.state.finish()
            else:
                self.state.finish(error='collector_error')
