"""One-pass NiniSite topic inspection; no scraped text is persisted."""
from urllib.robotparser import RobotFileParser
import httpx

from .dedup_index import compare_topic
from .load_safety_monitor import CollectionStopped
from .ninisite_continuous import ROBOTS, topic_link
from .persian_html import parse_topic


def inspect_topics(topics, index, monitor):
    """Probe each candidate once. Stop globally on a safety restriction."""
    entries = []
    robots = monitor.get(ROBOTS)
    if robots.status_code != 200 or 'text/plain' not in robots.headers.get('content-type', '').lower():
        return [{'topic_id': str(x.get('topic_id', '')), 'url': x.get('url'), 'status': 'requires_manual_review', 'reason': 'robots_unavailable'} for x in topics]
    policy = RobotFileParser()
    policy.parse(robots.text.splitlines())
    delay = policy.crawl_delay('IranMarketResearch') or 0
    stopped = None
    visited = set()
    for item in topics:
        url = item.get('url')
        ident = topic_link(url) if isinstance(url, str) else None
        entry = {'topic_id': str(item.get('topic_id', '')), 'url': url, 'status': None, 'reason': None}
        if stopped:
            entry.update(status='requires_manual_review', reason='safety_stop_' + stopped)
        elif not ident or ident != entry['topic_id']:
            entry.update(status='extraction_failed', reason='invalid_candidate_url')
        elif ident in visited or ident in index.get('ninisite_topic_ids', []):
            entry.update(status='duplicate', reason='known_or_repeated_topic_id')
        elif delay > 10 or not policy.can_fetch('IranMarketResearch', url):
            entry.update(status='requires_manual_review', reason='robots_denied_or_stricter_delay')
        else:
            visited.add(ident)
            try:
                response = monitor.get(url)
                entry['http_status'] = response.status_code
                if response.status_code in (301, 302, 303, 307, 308):
                    entry.update(status='requires_manual_review', reason='redirect_' + str(response.status_code))
                elif response.status_code != 200:
                    entry.update(status='inaccessible', reason='http_' + str(response.status_code))
                elif 'html' not in response.headers.get('content-type', '').lower():
                    entry.update(status='extraction_failed', reason='unexpected_content_type')
                else:
                    title, messages = parse_topic(response)
                    if not messages[0].strip():
                        entry.update(status='extraction_failed', reason='empty_original_post')
                    else:
                        status, reason = compare_topic(index, ident, url, title, messages[0])
                        entry['available_replies_first_page'] = max(0, len(messages)-1)
                        if status == 'new_unique_topic':
                            # Automatic regex redaction cannot verify the absence of
                            # names or sensitive disclosures in arbitrary free text.
                            status, reason = 'requires_manual_review', 'privacy_review_required_after_dedup'
                        entry.update(status=status, reason=reason)
            except CollectionStopped:
                stopped = monitor.stop_reason or 'safety_stop'
                entry.update(status='inaccessible', reason='safety_stop_' + stopped)
            except httpx.HTTPError as exc:
                entry.update(status='inaccessible', reason=type(exc).__name__)
            except (ValueError, UnicodeError) as exc:
                entry.update(status='extraction_failed', reason=type(exc).__name__)
        entries.append(entry)
    return entries
