"""In-process, privacy-minimized state shared with an approved collector."""
from collections import Counter, deque
import math
from datetime import datetime, timezone
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit


def safe_path(url):
    """Never expose arbitrary path segments, usernames, or query strings."""
    path = urlsplit(url).path
    if path.startswith('/discussion/topic/'):
        return '/discussion/topic/[redacted]'
    if path in ('/', '/discussion', '/discussion/', '/robots.txt'):
        return path
    return '/[redacted]'


def directory_bytes(root):
    total = 0
    if root.is_symlink() or not root.is_dir():
        return 0
    for item in root.iterdir():
        try:
            if item.is_symlink():
                continue
            if item.is_dir():
                total += directory_bytes(item)
            elif item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


class DashboardState:
    """A cooperative worker must use checkpoints and monitored_get()."""

    def __init__(self, data_root=Path('data'), *, demo=False):
        self.root = Path(data_root)
        self.demo = demo
        self.lock = threading.Condition()
        self.status = 'stopped'
        self.attached = False
        self.pause_requested = False
        self.stop_requested = False
        self.monitor = None
        self.permission_check = None
        self.reason = None
        self.counts = dict(requests=0, success=0, failed=0, pages=0,
                           topics_identified=0, topics_examined=0, topics_saved=0,
                           messages_identified=0, messages_saved=0, active=0)
        self.response_times = Counter()
        self.events = deque(maxlen=100)
        self.timeline = deque(maxlen=50)
        self.last_request = None
        self.last_started = None
        self._counted_topics = {name: set() for name in ('topics_identified', 'topics_examined', 'topics_saved')}

    def attach(self, monitor, permission_check):
        """Called by trusted collector code, never by the dashboard API."""
        with self.lock:
            if self.attached or not permission_check() or monitor.stop_reason:
                raise PermissionError('Collector cannot be attached')
            self.monitor, self.permission_check = monitor, permission_check
            self.stop_requested = False
            self.attached, self.status, self.reason = True, 'running', None

    def checkpoint(self):
        """Stop before the next operation until explicitly resumed or detached."""
        with self.lock:
            if not self.attached or self.stop_requested:
                return False
            if self.monitor.stop_reason:
                self.status, self.reason = 'error', self._safe_stop_reason()
                return False
            while self.pause_requested and self.attached and not self.stop_requested:
                self.status = 'paused'
                self.lock.wait()
            if not self.attached or self.stop_requested:
                return False
            if self.monitor.stop_reason or not self.permission_check():
                self.status, self.reason = 'error', 'safety_or_permission'
                return False
            self.status = 'running'
            return True

    def pause(self):
        with self.lock:
            if not self.attached or self.status != 'running':
                return False
            self.pause_requested = True
            self.status = 'pausing'
            self.reason = 'user_pause'
            self.lock.notify_all()
            return True

    def wait_for_next_cycle(self, seconds):
        """Wait without network activity; wake promptly on pause or stop."""
        end = time.monotonic() + seconds
        with self.lock:
            while self.attached and not self.stop_requested:
                if self.pause_requested and not self.checkpoint():
                    return False
                remaining = end - time.monotonic()
                if remaining <= 0:
                    return self.checkpoint()
                self.lock.wait(timeout=remaining)
            return False

    def resume(self):
        with self.lock:
            if not self.attached or self.status != 'paused' or self.monitor.stop_reason or not self.permission_check():
                return False
            self.pause_requested, self.reason, self.status = False, None, 'running'
            self.lock.notify_all()
            return True

    def stop(self):
        with self.lock:
            if not self.attached or self.stop_requested:
                return False
            self.stop_requested, self.pause_requested = True, False
            self.status, self.reason = 'stopping', 'user_stop'
            self.lock.notify_all()
            return True

    def detach(self):
        with self.lock:
            self.attached, self.pause_requested, self.status = False, False, 'stopped'
            self.lock.notify_all()

    def finish(self, error=None):
        with self.lock:
            self.attached, self.pause_requested = False, False
            self.status = 'error' if error else 'stopped'
            self.reason = error or ('user_stop' if self.stop_requested else 'completed')
            self.lock.notify_all()

    def count(self, **changes):
        """Trusted collector reports separate lifecycle milestones, not content."""
        allowed = {'pages', 'topics_identified', 'topics_examined', 'topics_saved', 'messages_identified', 'messages_saved'}
        if any(key not in allowed or type(value) is not int or value < 0 for key, value in changes.items()):
            raise ValueError('Invalid counter update')
        with self.lock:
            for key, value in changes.items():
                self.counts[key] += value

    def count_topic_once(self, stage, topic_key):
        """Count the same topic once per stage in this dashboard session."""
        if stage not in self._counted_topics:
            raise ValueError('Invalid topic stage')
        with self.lock:
            if topic_key not in self._counted_topics[stage]:
                self._counted_topics[stage].add(topic_key)
                self.counts[stage] += 1

    def monitored_get(self, url, *, retry=0):
        """All collector GETs must pass through this method and the shared monitor."""
        if type(retry) is not int or retry < 0:
            raise ValueError('Invalid retry count')
        if not self.checkpoint():
            raise RuntimeError('Collector stopped')
        timing = {}
        response = None
        try:
            def guard():
                if not self.checkpoint():
                    raise RuntimeError('Collector stopped')
                start = time.monotonic()
                with self.lock:
                    self.counts['active'] += 1
                    self.counts['requests'] += 1
                    timing['start'] = start
                    timing['interval'] = None if self.last_started is None else round(start - self.last_started, 2)
                    self.last_started = start
            response = self.monitor.get(url, before_request=guard)
            return response
        finally:
            if 'start' in timing:
                duration = round((time.monotonic() - timing['start']) * 1000)
                status = response.status_code if response is not None else None
                if status is None and self.monitor.stop_reason in ('http_429', 'http_403'):
                    status = int(self.monitor.stop_reason[-3:])
                size = len(response.content) if response is not None else None
                ok = status is not None and 200 <= status < 300
                with self.lock:
                    self.counts['active'] -= 1
                    result = 'success' if ok else 'redirected' if status == 301 else 'gone' if status == 410 else 'failed'
                    if result in ('success', 'failed'):
                        self.counts[result] += 1
                    if status is not None:
                        self.response_times[duration] += 1
                    if self.monitor.stop_reason:
                        self.status, self.reason = 'error', self._safe_stop_reason()
                    self.last_request = dict(time=datetime.now(timezone.utc).isoformat(), path=safe_path(url),
                                             status=status, duration_ms=duration, size_bytes=size, interval_s=timing['interval'], retries=retry)
                    self.events.append(dict(self.last_request, operation='request', result=result))

    def _safe_stop_reason(self):
        reason = self.monitor.stop_reason
        return reason if reason in ('http_429', 'http_403', 'captcha', 'repeated_server_errors_or_timeouts') else 'safety_stop'

    def snapshot(self):
        raw = directory_bytes(self.root / 'raw')
        processed = directory_bytes(self.root / 'processed')
        with self.lock:
            item = dict(time=datetime.now(timezone.utc).isoformat(), requests=self.counts['requests'],
                        messages_saved=self.counts['messages_saved'], bytes=raw + processed,
                        duration_ms=self.last_request['duration_ms'] if self.last_request else None)
            self.timeline.append(item)
            samples = sum(self.response_times.values())
            ordered = sorted(self.response_times.items())
            def percentile(rank):
                seen = 0
                for value, count in ordered:
                    seen += count
                    if seen >= rank:
                        return value
                return None
            metrics = {'count': samples, 'mean_ms': sum(v * n for v, n in ordered) / samples if samples else None,
                       'median_ms': (percentile((samples + 1) // 2) + percentile((samples + 2) // 2)) / 2 if samples else None,
                       'p95_ms': percentile(math.ceil(samples * .95)) if samples else None}
            return dict(response_time_stats=metrics, mode='demo' if self.demo else 'live', status=self.status, attached=self.attached,
                        reason=self.reason, counts=self.counts.copy(), last_request=self.last_request,
                        safety={'state': ('not_attached' if self.monitor is None else ('stopped' if self.monitor.stop_reason else 'ready')),
                                'delay_s': self.monitor.delay_seconds if self.monitor else None},
                        controls={'pause': self.attached and self.status == 'running',
                                  'stop': self.attached and not self.stop_requested,
                                  'resume': self.attached and self.status == 'paused' and not self.monitor.stop_reason and bool(self.permission_check())},
                        size={'raw_bytes': raw, 'processed_bytes': processed, 'total_bytes': raw + processed},
                        events=list(self.events), timeline=list(self.timeline))
