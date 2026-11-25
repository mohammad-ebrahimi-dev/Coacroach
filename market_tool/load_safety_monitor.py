"""Sequential, fail-closed HTTP monitor for future approved collection."""

import threading
import time

import httpx
from bs4 import BeautifulSoup


class CollectionStopped(RuntimeError):
    """The circuit breaker has stopped this collection session."""


def has_captcha(response):
    """Recognize common challenge markup, without logging response content."""
    if 'captcha' in response.headers.get('location', '').lower():
        return True
    if 'html' not in response.headers.get('content-type', '').lower():
        return False
    soup = BeautifulSoup(response.content, 'html.parser')
    return bool(soup.select(
        'form[action*="captcha" i], input[name*="captcha" i], '
        'iframe[src*="captcha" i], [class~="g-recaptcha"], '
        '[class~="h-captcha"], [class~="cf-turnstile"]'
    ))


class LoadSafetyMonitor:
    """One in-flight GET, with a pause after completion and a latched breaker.

    One monitor must be shared by all threads collecting from a site. It does
    not coordinate independent processes or requests made outside this object.
    """

    def __init__(self, delay_seconds=12, failure_threshold=2, *, timeout=15,
                 transport=None, clock=time.monotonic, sleep=time.sleep):
        if isinstance(delay_seconds, bool) or not 10 <= delay_seconds <= 15:
            raise ValueError('delay_seconds must be between 10 and 15')
        if isinstance(failure_threshold, bool) or not isinstance(failure_threshold, int) or failure_threshold < 2:
            raise ValueError('failure_threshold must be an integer of at least 2')
        self.delay_seconds = delay_seconds
        self.failure_threshold = failure_threshold
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=timeout, verify=True, follow_redirects=False,
                                    transport=transport, headers={'User-Agent': 'IranMarketResearch/0.1',
                                                                  'Accept': 'text/html, text/plain;q=0.9, */*;q=0.1',
                                                                  'Accept-Language': 'fa, en;q=0.8'})
        self._last_finished = None
        self._failures = 0
        self._reason = None
        self._closed = False

    @property
    def stop_reason(self):
        return self._reason

    def _stop(self, reason):
        self._reason = reason
        raise CollectionStopped(f'Collection stopped: {reason}')

    def get(self, url, *, before_request=None):
        with self._lock:
            if self._closed:
                raise CollectionStopped('Collection stopped: monitor closed')
            if self._reason:
                raise CollectionStopped(f'Collection stopped: {self._reason}')
            if self._last_finished is not None:
                # Recheck the clock after sleeping in case the sleep ends early.
                while (remaining := self.delay_seconds - (self._clock() - self._last_finished)) > 0:
                    self._sleep(remaining)
            if before_request is not None:
                before_request()
            try:
                response = self._client.get(url)
                if response.status_code == 429:
                    self._stop('http_429')
                if response.status_code == 403:
                    self._stop('http_403')
                if has_captcha(response):
                    self._stop('captcha')
                if 500 <= response.status_code <= 599:
                    self._failures += 1
                    if self._failures >= self.failure_threshold:
                        self._stop('repeated_server_errors_or_timeouts')
                else:
                    self._failures = 0
                return response
            except httpx.TimeoutException:
                self._failures += 1
                if self._failures >= self.failure_threshold:
                    self._stop('repeated_server_errors_or_timeouts')
                raise
            finally:
                self._last_finished = self._clock()

    def close(self):
        with self._lock:
            self._closed = True
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
