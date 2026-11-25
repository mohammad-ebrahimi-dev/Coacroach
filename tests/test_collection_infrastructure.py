import httpx
import pytest
from pydantic import ValidationError

from market_tool.load_safety_monitor import LoadSafetyMonitor
from market_tool.ninisite_continuous import ContinuousNiniSiteCollector, TopicSummary
from market_tool.dashboard_state import DashboardState
from market_tool.offline_browser import inspect_offline_html
from market_tool.policy_cache import PolicyCache

ROBOTS = 'https://www.ninisite.com/robots.txt'


def test_policy_cache_honors_expiry_and_never_caches_user_pages():
    now = [0]
    cache = PolicyCache(ttl_seconds=300, clock=lambda: now[0])
    response = httpx.Response(200, headers={'Cache-Control': 'public, max-age=10', 'Age': '2'}, text='User-agent: *')
    cache.put('https://www.ninisite.com/discussion', response)
    assert cache.get('https://www.ninisite.com/discussion') is None
    cache.put(ROBOTS, response)
    assert cache.get(ROBOTS) == 'User-agent: *'
    now[0] = 8
    assert cache.get(ROBOTS) is None


@pytest.mark.parametrize('headers', [
    {'Cache-Control': 'no-store, max-age=20'},
    {'Cache-Control': 'private, max-age=20'},
    {'Cache-Control': 'public, max-age=20', 'Set-Cookie': 'secret=x'},
    {'Cache-Control': 'public, max-age=20', 'Vary': 'Cookie'},
    {},
])
def test_policy_cache_refuses_private_or_unspecified_responses(headers):
    cache = PolicyCache()
    cache.put(ROBOTS, httpx.Response(200, headers=headers, text='value'))
    assert cache.get(ROBOTS) is None


def test_http_session_keeps_cookie_in_memory_and_uses_identifiable_headers():
    calls = []
    class Clock:
        now = 0
        def time(self): return self.now
        def sleep(self, seconds): self.now += seconds
    clock = Clock()
    def handler(request):
        calls.append(request)
        return httpx.Response(200, headers={'Set-Cookie': 'session=synthetic; Path=/'} if len(calls) == 1 else {})
    with LoadSafetyMonitor(delay_seconds=10, transport=httpx.MockTransport(handler),
                           clock=clock.time, sleep=clock.sleep) as monitor:
        monitor.get('https://example.test/first')
        monitor.get('https://example.test/second')
    assert calls[1].headers['cookie'] == 'session=synthetic'
    assert 'IranMarketResearch' in calls[0].headers['user-agent']
    assert 'fa' in calls[0].headers['accept-language']
    assert clock.now == 10


def test_summary_validation_rejects_invalid_ids_and_counts():
    with pytest.raises(ValidationError):
        TopicSummary(topic_id='not-a-number', messages_on_first_page=1, retrieved_at='test')
    with pytest.raises(ValidationError):
        TopicSummary(topic_id='123', messages_on_first_page=True, retrieved_at='test')


def test_retries_reported_in_dashboard_without_exposing_exception(tmp_path):
    state = DashboardState(tmp_path)
    class FakeMonitor:
        delay_seconds = 10
        stop_reason = None
        calls = 0
        def get(self, url, *, before_request):
            before_request()
            self.calls += 1
            if self.calls == 1:
                raise httpx.ReadTimeout('secret', request=httpx.Request('GET', url))
            return httpx.Response(200, request=httpx.Request('GET', url))
    monitor = FakeMonitor()
    state.attach(monitor, lambda: True)
    collector = ContinuousNiniSiteCollector(state)
    collector._request('https://www.ninisite.com/discussion')
    snapshot = state.snapshot()
    assert snapshot['counts']['requests'] == 2
    assert snapshot['events'][-1]['retries'] == 1
    assert 'secret' not in str(snapshot)
    state.detach()


def test_offline_browser_blocks_network_and_closes_context():
    calls = []
    class Page:
        def set_default_timeout(self, value): calls.append(('timeout', value))
        def set_content(self, html, **kwargs): calls.append(('content', html))
        def locator(self, selector):
            class Locator:
                def count(self): return 2
            return Locator()
    class Context:
        def route(self, pattern, callback): calls.append(('route', pattern))
        def new_page(self): return Page()
        def close(self): calls.append(('context_closed',))
    class Browser:
        def new_context(self, **kwargs):
            calls.append(('options', kwargs))
            return Context()
        def close(self): calls.append(('browser_closed',))
    class Chromium:
        def launch(self): return Browser()
    class Playwright:
        chromium = Chromium()
        def __enter__(self): return self
        def __exit__(self, *args): pass
    assert inspect_offline_html('<p>sample</p>', 'p', playwright_factory=Playwright) == 2
    assert ('options', {'java_script_enabled': False, 'service_workers': 'block'}) in calls
    assert ('route', '**/*') in calls
    assert ('context_closed',) in calls and ('browser_closed',) in calls
