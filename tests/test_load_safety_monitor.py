import threading

import httpx
import pytest

from market_tool.load_safety_monitor import CollectionStopped, LoadSafetyMonitor


class FakeClock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_spacing_and_no_automatic_retries():
    clock = FakeClock()
    times = []
    def handler(request):
        times.append(clock.now)
        clock.now += 3
        return httpx.Response(200)
    with LoadSafetyMonitor(delay_seconds=10, clock=clock.monotonic, sleep=clock.sleep,
                           transport=httpx.MockTransport(handler)) as monitor:
        monitor.get('https://example.test/one')
        monitor.get('https://example.test/two')
    assert times == [0, 13] and clock.sleeps == [10]


@pytest.mark.parametrize('value', [0, 9, 16, True])
def test_invalid_delay_is_rejected(value):
    with pytest.raises(ValueError):
        LoadSafetyMonitor(delay_seconds=value)


@pytest.mark.parametrize('response,reason', [
    (httpx.Response(429), 'http_429'),
    (httpx.Response(403), 'http_403'),
    (httpx.Response(200, headers={'Content-Type': 'text/html'}, text='<form action="/captcha"></form>'), 'captcha'),
    (httpx.Response(302, headers={'Location': '/captcha'}), 'captcha'),
])
def test_immediate_stop_is_latched(response, reason):
    calls = []
    def handler(request):
        calls.append(request)
        return response
    with LoadSafetyMonitor(transport=httpx.MockTransport(handler)) as monitor:
        with pytest.raises(CollectionStopped, match=reason):
            monitor.get('https://example.test/')
        with pytest.raises(CollectionStopped, match=reason):
            monitor.get('https://example.test/')
    assert len(calls) == 1


def test_consecutive_server_errors_and_timeouts_stop():
    clock = FakeClock()
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        raise httpx.ReadTimeout('timeout', request=request)
    with LoadSafetyMonitor(transport=httpx.MockTransport(handler), clock=clock.monotonic, sleep=clock.sleep) as monitor:
        assert monitor.get('https://example.test/').status_code == 503
        with pytest.raises(CollectionStopped, match='repeated_server_errors_or_timeouts'):
            monitor.get('https://example.test/')
        with pytest.raises(CollectionStopped):
            monitor.get('https://example.test/')
    assert len(calls) == 2 and clock.sleeps == [12]


def test_success_resets_failure_count():
    clock = FakeClock()
    responses = iter([503, 200, 503])
    with LoadSafetyMonitor(transport=httpx.MockTransport(lambda request: httpx.Response(next(responses))),
                           clock=clock.monotonic, sleep=clock.sleep) as monitor:
        assert [monitor.get('https://example.test/').status_code for _ in range(3)] == [503, 200, 503]
        assert monitor.stop_reason is None


def test_two_callers_cannot_overlap():
    clock = FakeClock()
    started, release = threading.Event(), threading.Event()
    active, peak = 0, 0
    def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        started.set()
        assert release.wait(2)
        active -= 1
        return httpx.Response(200)
    with LoadSafetyMonitor(transport=httpx.MockTransport(handler), clock=clock.monotonic, sleep=clock.sleep) as monitor:
        threads = [threading.Thread(target=monitor.get, args=('https://example.test/',)) for _ in range(2)]
        threads[0].start()
        assert started.wait(2)
        threads[1].start()
        release.set()
        for thread in threads:
            thread.join(2)
            assert not thread.is_alive()
    assert peak == 1
