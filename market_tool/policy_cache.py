"""Bounded in-memory cache only for explicitly public robots policy bodies."""
from collections import OrderedDict
import re
import time


class PolicyCache:
    def __init__(self, ttl_seconds=300, max_entries=8, clock=time.monotonic):
        if ttl_seconds <= 0 or max_entries < 1:
            raise ValueError('Invalid cache limits')
        self.ttl, self.max_entries, self.clock = ttl_seconds, max_entries, clock
        self._entries = OrderedDict()

    def get(self, url):
        item = self._entries.get(url)
        if item is None:
            return None
        expires, value = item
        if self.clock() >= expires:
            del self._entries[url]
            return None
        self._entries.move_to_end(url)
        return value

    def put(self, url, response):
        controls = response.headers.get('cache-control', '').lower()
        max_age = re.search(r'(?:^|,)\s*max-age\s*=\s*(\d+)', controls)
        if (url != 'https://www.ninisite.com/robots.txt' or response.status_code != 200
                or not max_age or 'no-store' in controls or 'no-cache' in controls
                or 'private' in controls or 'set-cookie' in response.headers
                or 'vary' in response.headers):
            return
        try:
            age = max(0, int(response.headers.get('age', '0')))
        except ValueError:
            return
        lifetime = min(self.ttl, max(0, int(max_age.group(1)) - age))
        if not lifetime:
            return
        self._entries[url] = (self.clock() + lifetime, response.text)
        self._entries.move_to_end(url)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
