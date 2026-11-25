import json
import threading
import time
from pathlib import Path

import httpx

from market_tool.dashboard_state import DashboardState
from market_tool.load_safety_monitor import CollectionStopped
from market_tool.ninisite_pilot import NiniSitePilot, REVIEWED, save_numbered_topic


def wait_finished(state):
    for _ in range(300):
        if not state.attached:
            return
        time.sleep(.005)
    raise AssertionError('pilot did not finish')


def test_default_monitor_uses_ten_second_delay(tmp_path):
    pilot = NiniSitePilot(DashboardState(tmp_path))
    monitor = pilot.monitor_factory()
    try:
        assert monitor.delay_seconds == 10
    finally:
        monitor.close()


def test_pilot_runs_with_mocked_requests_and_saves_only_reviewed(tmp_path):
    state = DashboardState(tmp_path)
    calls = []
    class FakeMonitor:
        delay_seconds = 12
        stop_reason = None
        def get(self, url, *, before_request):
            before_request()
            calls.append(url)
            req = httpx.Request('GET', url)
            if url.endswith('/robots.txt'):
                return httpx.Response(200, headers={'Content-Type': 'text/plain'}, text='User-agent: *\nAllow: /', request=req)
            html = '<h1>عنوان</h1>' + ''.join(f'<p class="post-message topic-post__message">{x}</p>' for x in REVIEWED) + '<p class="post-message topic-post__message">private-unreviewed</p>'
            return httpx.Response(200, headers={'Content-Type': 'text/html; charset=utf-8'}, content=html.encode('utf-8'), request=req)
        def close(self): pass
    pilot = NiniSitePilot(state, monitor_factory=FakeMonitor)
    assert pilot.start()
    wait_finished(state)
    output = list((tmp_path / 'processed' / 'topic').glob('P*/*.jsonl'))
    assert len(output) == 1
    rows = [json.loads(line) for line in output[0].read_text(encoding='utf-8').splitlines()]
    assert {r['text'] for r in rows} == REVIEWED and len(calls) == 2
    assert state.counts['messages_identified'] == 4 and state.counts['messages_saved'] == 3
    assert state.status == 'stopped' and state.reason == 'completed'


def test_numbered_topic_files_preserve_existing_content(tmp_path):
    first = save_numbered_topic(tmp_path, [{'text': 'فارسی'}])
    second = save_numbered_topic(tmp_path, [{'text': 'دوم'}])
    assert first.name == '1.jsonl' and second.name == '2.jsonl'
    assert json.loads(first.read_text(encoding='utf-8').strip()) == {'text': 'فارسی'}
    assert json.loads(second.read_text(encoding='utf-8').strip()) == {'text': 'دوم'}


def test_permission_guard_rejects_changed_topic(tmp_path):
    state = DashboardState(tmp_path)
    pilot = NiniSitePilot(state)
    pilot.topic_url = 'https://example.test/'
    assert not pilot.start() and not state.attached


def test_safety_stop_disables_new_start(tmp_path):
    state = DashboardState(tmp_path)
    class StoppedMonitor:
        delay_seconds = 12
        stop_reason = None
        def get(self, url, *, before_request):
            before_request()
            self.stop_reason = 'http_429'
            raise CollectionStopped('stopped')
        def close(self): pass
    pilot = NiniSitePilot(state, monitor_factory=StoppedMonitor)
    assert pilot.start()
    wait_finished(state)
    assert state.status == 'error' and state.reason == 'http_429'
    assert not pilot.start()


def test_stop_during_request_prevents_topic_fetch_and_output(tmp_path):
    state = DashboardState(tmp_path)
    entered, release = threading.Event(), threading.Event()
    calls = []
    class BlockingMonitor:
        delay_seconds = 12
        stop_reason = None
        def get(self, url, *, before_request):
            before_request()
            calls.append(url)
            entered.set()
            assert release.wait(2)
            return httpx.Response(200, headers={'Content-Type': 'text/plain'}, text='User-agent: *\nAllow: /', request=httpx.Request('GET', url))
        def close(self): pass
    pilot = NiniSitePilot(state, monitor_factory=BlockingMonitor)
    assert pilot.start() and entered.wait(2)
    assert state.stop()
    release.set()
    wait_finished(state)
    assert state.status == 'stopped' and state.reason == 'user_stop'
    assert len(calls) == 1 and not list(tmp_path.rglob('*.jsonl'))
