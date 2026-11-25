# NiniSite structure research

Inspection date: 2026-11-25 (Asia/Tehran).

## Observations and limits

A Python `requests` GET of `https://www.ninisite.com/robots.txt` with user agent `NiniSiteResearch/1.0` and a 20-second timeout failed during the HTTPS handshake through the configured proxy with `requests.exceptions.ReadTimeout`. No HTTP response, status, headers, redirect, or robots policy was obtained. A separate web-tool attempt also reported the robots URL inaccessible. Public web searches for NiniSite discussion URLs returned no results. These failures do not establish that the site itself is down or that any URL is allowed or forbidden.

The homepage, category and subforum pages, topic listings, topics, reply pagination, and their HTML were not retrieved. Consequently their structure, URL patterns, rendering mode, and HTTP behavior remain **unverified**. No site HTML or personal data was saved. Browser automation was not used. No further site pages were requested because the robots policy could not be evaluated.

## Connectivity diagnostic (2026-11-25)

DNS resolved `www.ninisite.com` to one IPv4 address in this environment. The usual uppercase and lowercase HTTP, HTTPS, ALL and NO proxy environment variables were unset. Python detected system proxy entries for HTTP, HTTPS and FTP, selected an HTTPS proxy for the site, and reported no proxy bypass for the hostname. Proxy addresses and credentials were not recorded.

Separate `requests` GETs of the homepage and robots.txt, each with 6-second connect and read timeouts, ended in `ReadTimeout` without an HTTP response. This run did not establish the exact timeout phase. Separate default `curl.exe` checks returned HTTP 200 for each URL and exit code 0, with response bodies discarded. The effective curl proxy route was not established, so these results do not isolate the cause of the Python failures. The 200 for robots.txt does not establish its contents or permissions. Neither result proves that the website is generally unavailable. See [the connectivity report](../reports/connectivity-report.md) for details and limitations.

## robots.txt inspection (2026-11-25)

A single curl request using the system-configured HTTPS proxy returned HTTP 200 and `text/plain` for `https://www.ninisite.com/robots.txt`; the response body is preserved at [samples/robots.txt](../samples/robots.txt). The connection trace showed a proxy tunnel. The file has a `User-agent: *` group, valid `Allow` and `Disallow` lines, no `Crawl-delay` or `Sitemap` directive, and a malformed `Allow /sitemap` line without a colon. Its intended meaning is uncertain; do not silently turn it into an allow rule or a sitemap declaration. The 200 response is not blanket permission to crawl. See [the robots inspection](../reports/robots-inspection.md) for exact rules and limits.

The earlier Python requests timed out with the system proxy; this curl request succeeded with that proxy explicitly supplied to the process. These observations do not establish why Python timed out, nor do they establish the route of the earlier default curl tests. No forum page was requested during the robots inspection.

## Follow-up inspection

From an environment with ordinary authorized access, request robots.txt first with an identifiable user agent and a timeout. Evaluate the applicable rules and any advertised crawl delay before visiting allowed paths. Stop for authentication, CAPTCHA, access denial, or rate limiting; do not attempt to circumvent them. Make sequential requests with a conservative delay and avoid automatic aggressive retries. Inspect the homepage and follow actual public forum links, recording response status, redirects, content type, and evidence for each selector and URL pattern. Compare the raw response HTML with visible content before concluding whether JavaScript is needed. Inspect a multi-page topic and verify next-page links and termination. Avoid retaining identifiers or raw content in research artifacts.

## Candidate architecture (design, not an observed site model)

Separate robots-aware discovery, a sequential HTTP fetcher, site-specific parsers, pagination and deduplication, and local storage. Enforce host and robots rules on every discovered URL, including redirects; use timeouts, backoff and a global request interval. Stop on access-control challenges, respect 429/Retry-After, and do not retry persistently. Store only necessary discussion text and dates, with explicit exclusion and redaction of usernames, profile links, phone numbers and other personal identifiers; validate redaction before persistence. Treat dates and content as potentially sensitive and define retention and deletion policies. Test parsers against sanitized, representative fixtures after live HTML has been lawfully obtained. URL patterns and extraction logic must be based on observed pages rather than assumptions.
