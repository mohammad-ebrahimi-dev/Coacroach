"""A deliberately narrow, privacy-reviewed single-topic pilot."""
from urllib.robotparser import RobotFileParser
import threading

from .load_safety_monitor import LoadSafetyMonitor
from .persian_html import parse_topic, write_jsonl_new
from .connectors import check_ninisite_pilot_permission

TOPIC = 'https://www.ninisite.com/discussion/topic/19134672/%DB%8C%D9%87-%D8%AC%D8%A7%DB%8C-%D8%AE%D9%88%D8%A8-%D9%85%D8%B9%D8%B1%D9%81%DB%8C-%DA%A9%D9%86%DB%8C%D8%AF'
ROBOTS = 'https://www.ninisite.com/robots.txt'
# These exact messages were individually reviewed during the previous pilot.
REVIEWED = frozenset({
    'کدوم منطقه یا کدوم سمت تهران هستید؟',
    'تهران به این بزرگی کدوم سمتی خواهر',
    'تهران که پر سالن خوبه ولی خب پیدا کردن جای مطمئن سخته',
})


def save_numbered_topic(output_root, records):
    """Create the first available numbered JSONL without replacing any file."""
    folder = output_root / 'processed' / 'topic'
    folder.mkdir(parents=True, exist_ok=True)
    used = {int(path.stem) for path in folder.glob('*.jsonl') if path.stem.isdigit()}
    for group in folder.glob('P*'):
        if group.is_dir() and group.name[1:].isdigit():
            used.update(int(path.stem) for path in group.glob('*.jsonl') if path.stem.isdigit())
    number = 1
    while number in used:
        number += 1
    group_number = 1
    while True:
        group = folder / f'P{group_number}'
        if group.is_dir() and len(list(group.glob('*.jsonl'))) >= 60:
            group_number += 1
            continue
        path = group / f'{number}.jsonl'
        try:
            write_jsonl_new(path, records)
            return path
        except FileExistsError:
            number += 1
            while number in used:
                number += 1



class NiniSitePilot:
    """Runs only the explicitly requested previously examined public topic."""
    permission_status = 'User-authorized one-topic inspection'
    topic_url = TOPIC
    robots_url = ROBOTS
    def __init__(self, state, monitor_factory=None):
        self.state = state
        self.monitor_factory = monitor_factory or (lambda: LoadSafetyMonitor(delay_seconds=10))
        self._start_lock = threading.Lock()
        self._safety_latched = False

    def permitted(self):
        try:
            check_ninisite_pilot_permission(self)
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
            threading.Thread(target=self._run, args=(monitor,), daemon=True).start()
            return True

    def _run(self, monitor):
        try:
            robots = self.state.monitored_get(self.robots_url)
            if robots.status_code != 200 or 'text/plain' not in robots.headers.get('content-type', '').lower():
                raise ValueError('robots_unavailable')
            policy = RobotFileParser()
            policy.parse(robots.text.splitlines())
            if not policy.can_fetch('IranMarketResearch', self.topic_url):
                raise ValueError('robots_denied')
            self.state.count_topic_once('topics_identified', self.topic_url)
            page = self.state.monitored_get(self.topic_url)
            if page.status_code != 200:
                raise ValueError('topic_unavailable')
            _, messages = parse_topic(page)
            self.state.count_topic_once('topics_examined', self.topic_url)
            self.state.count(pages=1, messages_identified=len(messages))
            selected = [text for text in messages if text in REVIEWED]
            if not selected:
                raise ValueError('no_reviewed_messages')
            if not self.state.checkpoint():
                return
            save_numbered_topic(self.state.root, [{'text': text} for text in selected])
            self.state.count_topic_once('topics_saved', self.topic_url)
            self.state.count(messages_saved=len(selected))
        except Exception:
            if monitor.stop_reason:
                self._safety_latched = True
                self.state.finish(error=self.state._safe_stop_reason())
            elif self.state.stop_requested:
                self.state.finish()
            else:
                self.state.finish(error='pilot_error')
        else:
            self.state.finish()
        finally:
            if self.state.attached and self.state.stop_requested:
                self.state.finish()
            monitor.close()
