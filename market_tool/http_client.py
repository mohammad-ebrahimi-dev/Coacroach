import logging
import ssl
import time
from urllib.parse import urlsplit

import httpx


class FetchError(Exception):
    def __init__(self, category, status=None, retries=0):
        self.category, self.status, self.retries = category, status, retries
        super().__init__(f'{category}; status={status}; retries={retries}')


class HttpClient:
    def __init__(self, settings, transport=None, sleep=time.sleep):
        self.settings, self.sleep = settings, sleep
        t = settings.http_timeout
        self.timeout = httpx.Timeout(connect=settings.connect_timeout or t, read=settings.read_timeout or t,
                                     write=settings.write_timeout or t, pool=settings.pool_timeout or t)
        self.transport = transport
        self.log = logging.getLogger('market_tool.http')

    def get(self, url, source):
        scheme = urlsplit(url).scheme
        configured = bool(self.settings.http_proxy or self.settings.https_proxy)
        proxy = self.settings.https_proxy if scheme == 'https' else self.settings.http_proxy
        if configured and not proxy:
            raise FetchError('proxy_missing_for_scheme')
        kwargs = dict(timeout=self.timeout, follow_redirects=False, verify=True, trust_env=not configured)
        if proxy:
            kwargs['proxy'] = proxy
        if self.transport is not None:
            kwargs['transport'] = self.transport
        hostname = urlsplit(url).hostname or 'unknown'
        with httpx.Client(**kwargs) as client:
            for attempt in range(self.settings.max_retries + 1):
                start = time.monotonic()
                try:
                    response = client.get(url, headers={'User-Agent': 'IranMarketResearch/0.1'})
                    elapsed = time.monotonic() - start
                    category = 'rate_limited' if response.status_code == 429 else ('http_error' if response.status_code >= 300 else 'none')
                    self.log.info('source=%s host=%s status=%s duration=%.3f error=%s retry=%d', source, hostname, response.status_code, elapsed, category, attempt)
                    # The source policy requires stopping on rate limits.
                    if response.status_code == 429:
                        raise FetchError('rate_limited_retry_after_present' if response.headers.get('Retry-After') else 'rate_limited', 429, attempt)
                    if 500 <= response.status_code <= 599 and attempt < self.settings.max_retries:
                        self.sleep(min(2 ** attempt, 8))
                        continue
                    if not 200 <= response.status_code < 300:
                        raise FetchError('http_error', response.status_code, attempt)
                    return response
                except httpx.TransportError as exc:
                    category = type(exc).__name__
                    self.log.warning('source=%s host=%s status=none duration=%.3f error=%s retry=%d', source, hostname, time.monotonic() - start, category, attempt)
                    cause = exc
                    tls_failure = False
                    while cause is not None:
                        if isinstance(cause, ssl.SSLError):
                            tls_failure = True
                            break
                        cause = cause.__cause__ or cause.__context__
                    if tls_failure or attempt == self.settings.max_retries:
                        raise FetchError(category, retries=attempt) from None
                    self.sleep(min(2 ** attempt, 8))
