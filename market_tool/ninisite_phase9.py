"""One-pass NiniSite topic inspection and optional filtered local output."""
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import httpx

from .dedup_index import compare_topic, text_key, url_key
from .load_safety_monitor import CollectionStopped
from .ninisite_continuous import ROBOTS, topic_link
from .persian_html import parse_topic, write_jsonl_new
from .text_safety import clean_message


def inspect_topics(topics, index, monitor, *, output_dir=None):
    """Probe each candidate once. Stop globally on a safety restriction."""
    entries = []
    robots = monitor.get(ROBOTS)
    if robots.status_code != 200 or 'text/plain' not in robots.headers.get('content-type', '').lower():
        return [{'topic_id': str(x.get('topic_id', '')), 'url': x.get('url'), 'status': 'requires_manual_review', 'reason': 'robots_unavailable'} for x in topics]
    policy = RobotFileParser()
    policy.parse(robots.text.splitlines())
    delay = policy.crawl_delay('IranMarketResearch') or 0
    stopped = None
    visited = set()
    for item in topics:
        url = item.get('url')
        ident = topic_link(url) if isinstance(url, str) else None
        entry = {'topic_id': str(item.get('topic_id', '')), 'url': url, 'status': None, 'reason': None}
        if stopped:
            entry.update(status='requires_manual_review', reason='safety_stop_' + stopped)
        elif not ident or ident != entry['topic_id']:
            entry.update(status='extraction_failed', reason='invalid_candidate_url')
        elif ident in visited or ident in index.get('ninisite_topic_ids', []):
            entry.update(status='duplicate', reason='known_or_repeated_topic_id')
        elif delay > 10 or not policy.can_fetch('IranMarketResearch', url):
            entry.update(status='requires_manual_review', reason='robots_denied_or_stricter_delay')
        else:
            visited.add(ident)
            try:
                response = monitor.get(url)
                entry['http_status'] = response.status_code
                if response.status_code in (301, 302, 303, 307, 308):
                    entry.update(status='requires_manual_review', reason='redirect_' + str(response.status_code))
                elif response.status_code != 200:
                    entry.update(status='inaccessible', reason='http_' + str(response.status_code))
                elif 'html' not in response.headers.get('content-type', '').lower():
                    entry.update(status='extraction_failed', reason='unexpected_content_type')
                else:
                    title, messages = parse_topic(response)
                    if not messages[0].strip():
                        entry.update(status='extraction_failed', reason='empty_original_post')
                    else:
                        status, reason = compare_topic(index, ident, url, title, messages[0])
                        entry['available_replies_first_page'] = max(0, len(messages)-1)
                        if status == 'new_unique_topic':
                            if output_dir is None:
                                status, reason = 'requires_manual_review', 'privacy_review_required_after_dedup'
                            else:
                                saved = save_filtered_topic(response, ident, url, title, messages, output_dir)
                                if saved is None:
                                    status, reason = 'requires_manual_review', 'post_or_title_excluded_by_filter'
                                else:
                                    path, saved_replies, excluded = saved
                                    entry['saved_file'] = path.name
                                    entry['saved_replies'] = saved_replies
                                    entry['excluded_messages'] = excluded
                                    index.setdefault('ninisite_topic_ids', []).append(ident)
                                    index.setdefault('url_sha256', []).append(url_key(url))
                                    index.setdefault('title_sha256', []).append(text_key(title))
                                    index.setdefault('content_sha256', []).append(text_key(messages[0]))
                                    status, reason = 'new_unique_topic', 'saved_filtered_first_page'
                        entry.update(status=status, reason=reason)
            except CollectionStopped:
                stopped = monitor.stop_reason or 'safety_stop'
                entry.update(status='inaccessible', reason='safety_stop_' + stopped)
            except httpx.HTTPError as exc:
                entry.update(status='inaccessible', reason=type(exc).__name__)
            except OSError:
                entry.update(status='requires_manual_review', reason='output_write_failed')
                stopped = 'output_write_failed'
            except (ValueError, UnicodeError) as exc:
                entry.update(status='extraction_failed', reason=type(exc).__name__)
        entries.append(entry)
    return entries


def save_filtered_topic(response, topic_id, url, title, messages, output_dir):
    """Save first-page text after best-effort filtering, never claiming anonymity."""
    header = Message()
    header['content-type'] = response.headers.get('content-type', '')
    charset = header.get_content_charset()
    html = response.content.decode(charset, errors='strict') if charset else response.content
    soup = BeautifulSoup(html, 'html.parser')
    names = [node.get_text(' ', strip=True) for node in soup.select('.nickname')]
    safe_title = clean_message(title, names)
    safe_post = clean_message(messages[0], names)
    if not safe_title or not safe_post:
        return None
    timestamp = datetime.now(timezone.utc).isoformat()
    records = [{'kind':'topic_first_page', 'source':'ninisite', 'source_url':url,
                'topic_id':topic_id, 'retrieved_at':timestamp, 'title':safe_title,
                'complete':False, 'privacy':'best_effort_filtered',
                'notice':'Only first page; links and quotations excluded; privacy review required.'}]
    for i, text in enumerate(messages):
        cleaned = safe_post if i == 0 else clean_message(text, names)
        if cleaned:
            records.append({'kind':'post' if i == 0 else 'reply', 'text':cleaned})
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if len(list(directory.glob('*.jsonl'))) >= 60:
        raise OSError('P1 full')
    for number in range(1, 100000):
        path = directory / f'{number}.jsonl'
        try:
            write_jsonl_new(path, records)
            return path, sum(r['kind'] == 'reply' for r in records), len(messages) - (len(records)-1)
        except FileExistsError:
            continue
    raise OSError('No output file available')
