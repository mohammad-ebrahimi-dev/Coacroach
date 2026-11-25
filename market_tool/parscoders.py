"""ParsCoders project-list parsing; remote collection remains disabled."""
from datetime import datetime, timezone
from email.message import Message
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlsplit
import re

from bs4 import BeautifulSoup
from .text_safety import clean_message
from .market_signal_pipeline import classify_records

ORIGIN = 'https://parscoders.com'
LISTING = ORIGIN + '/project'
# Changed only after source-specific access and reuse approval is verified.
# Not supplied by environment, a user request, or other untrusted runtime data.
_APPROVED_SCOPE = None
PROJECT_PATH = re.compile(r'^/project/([0-9]+)(?:/[^/?#]+)?/?$')


def project_url(href):
    if not isinstance(href, str):
        return None
    try:
        value = urljoin(LISTING, href)
        parts = urlsplit(value)
        if (parts.scheme != 'https' or parts.hostname != 'parscoders.com' or parts.port not in (None, 443)
                or parts.username or parts.password or parts.query or parts.fragment):
            return None
        match = PROJECT_PATH.fullmatch(parts.path)
        return (value, match.group(1)) if match else None
    except ValueError:
        return None


def parse_project_listing(response):
    """Parse public listing excerpts, retaining no author or profile fields.

    The returned text is a best-effort filtered preview, not a privacy-reviewed
    record. The listing contains private placeholders: require a public link
    and visible description. Never interpret a stated budget as a payment.
    """
    response.raise_for_status()
    if 'html' not in response.headers.get('content-type', '').lower():
        raise ValueError('unexpected content type')
    header = Message()
    header['content-type'] = response.headers.get('content-type', '')
    charset = header.get_content_charset()
    html = response.content.decode(charset, errors='strict') if charset else response.content
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('div.project-list-item')
    if not cards:
        raise ValueError('project listing structure not found')
    result, seen = [], set()
    for card in cards:
        anchor = card.select_one('.project-title h6 a.project--link[href]')
        description = card.select_one('div.project-text')
        parsed = project_url(anchor.get('href')) if anchor else None
        if not parsed or not description:
            continue
        url, ident = parsed
        for node in description.select('a, script, style, img, blockquote'):
            node.decompose()
        title = clean_message(anchor.get_text(' ', strip=True))
        text = clean_message(description.get_text(' ', strip=True))
        if not title or not text or ident in seen:
            continue
        seen.add(ident)
        result.append({'source': 'parscoders', 'source_url': url, 'project_id': ident,
                       'content_type': 'ProjectListing', 'title': title, 'text': text,
                       'privacy': 'best_effort_filtered', 'review_required': True})
    return result


def fetch_projects(monitor):
    """Use a shared safety monitor only after a code-reviewed scope approval."""
    if _APPROVED_SCOPE != ('parscoders', LISTING, 'market-research'):
        raise PermissionError('ParsCoders automated collection is not approved')
    robots = monitor.get(ORIGIN + '/robots.txt')
    if robots.status_code != 200 or 'text/plain' not in robots.headers.get('content-type', '').lower():
        raise ValueError('robots unavailable')
    policy = RobotFileParser(); policy.parse(robots.text.splitlines())
    if not policy.can_fetch('IranMarketResearch', LISTING) or (policy.crawl_delay('IranMarketResearch') or 0) > monitor.delay_seconds:
        raise PermissionError('robots restriction')
    response = monitor.get(LISTING)
    if response.status_code != 200:
        raise ValueError('listing unavailable')
    timestamp = datetime.now(timezone.utc).isoformat()
    records = parse_project_listing(response)
    for record in records:
        record['record_id'] = 'parscoders:' + record['project_id']
        record['retrieved_at'] = timestamp
    # No supplied reviews: every candidate remains in manual review.
    return classify_records(records)
