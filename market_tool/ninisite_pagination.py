"""Read only observed, permitted NiniSite continuation links sequentially."""
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from urllib.parse import urljoin, urlsplit, parse_qs
from urllib.robotparser import RobotFileParser
import json
import httpx
from bs4 import BeautifulSoup
from .dedup_index import text_key
from .connectors import check_ninisite_continuous_permission
from .load_safety_monitor import CollectionStopped
from .ninisite_continuous import ROBOTS, topic_link
from .persian_html import parse_topic, write_jsonl_new
from .text_safety import clean_message
from .market_signal_pipeline import classify_records


def page_link(base, href):
    try:
        original = urlsplit(base)
        candidate = urlsplit(urljoin(base, href))
        if (topic_link(base) is None or candidate.scheme != 'https' or candidate.hostname != 'www.ninisite.com'
                or candidate.port not in (None, 443) or candidate.username or candidate.password or candidate.fragment
                or candidate.path != original.path):
            return None
        params = parse_qs(candidate.query, keep_blank_values=True)
        if set(params) != {'page'} or len(params['page']) != 1:
            return None
        number = params['page'][0]
        if not number.isascii() or not number.isdigit() or not 2 <= int(number) <= 1000:
            return None
        return candidate.geturl(), int(number)
    except (ValueError, TypeError):
        return None


def html_soup(response):
    header = Message()
    header['content-type'] = response.headers.get('content-type', '')
    charset = header.get_content_charset()
    html = response.content.decode(charset, errors='strict') if charset else response.content
    return BeautifulSoup(html, 'html.parser')


def existing_pages(directory):
    pages = set()
    if not directory.is_dir() or directory.is_symlink():
        return pages
    groups = [directory]
    if directory.name.startswith('P') and directory.name[1:].isdigit():
        groups = [p for p in directory.parent.glob('P[0-9]*') if p.is_dir() and not p.is_symlink() and p.name[1:].isdigit()]
    for path in (path for group in groups for path in group.glob('*.jsonl')):
        if path.is_symlink():
            continue
        try:
            with path.open(encoding='utf-8-sig') as f:
                row = json.loads(f.readline())
            if row.get('kind') == 'topic_additional_page' and str(row.get('topic_id', '')).isdigit() and type(row.get('page_number')) is int:
                pages.add((str(row['topic_id']), row['page_number']))
        except (OSError, ValueError, AttributeError):
            continue
    return pages


def collect_pages(seeds, topic_bases, hashes, monitor, directory, max_requests=20, *, collector, policy=None):
    """Process only actual observed links; return counts, never user text."""
    check_ninisite_continuous_permission(collector)
    if not collector.permitted():
        raise PermissionError('Source is not approved')
    directory = Path(directory)
    result = {'requests':0, 'received':0, 'new':0, 'duplicates':0, 'rejected':0,
              'files':[], 'pages':[], 'complete':False, 'stop_reason':None}
    if policy is None:
        robot = monitor.get(ROBOTS)
        if robot.status_code != 200 or 'text/plain' not in robot.headers.get('content-type', '').lower():
            result['stop_reason'] = 'robots_unavailable'; return result
        policy = RobotFileParser(); policy.parse(robot.text.splitlines())
    if (policy.crawl_delay('IranMarketResearch') or 0) > 10:
        result['stop_reason'] = 'stricter_crawl_delay'; return result
    queue = list(seeds); visited = set(); known = existing_pages(directory)
    while queue and result['requests'] < max_requests:
        item = queue.pop(0)
        topic_id = str(item.get('topic_id', ''))
        base = topic_bases.get(topic_id)
        parsed = page_link(base, item.get('url')) if base else None
        if not parsed or topic_link(base) != topic_id:
            result['rejected'] += 1; continue
        url, number = parsed
        key = (topic_id, number)
        if key in visited or key in known:
            continue
        visited.add(key)
        if not policy.can_fetch('IranMarketResearch', url):
            result['stop_reason'] = 'robots_denied'; break
        try:
            result['requests'] += 1
            response = monitor.get(url)
            if response.status_code != 200 or 'html' not in response.headers.get('content-type', '').lower():
                result['stop_reason'] = 'http_' + str(response.status_code); break
            _, messages = parse_topic(response)
            soup = html_soup(response)
            names = [x.get_text(' ', strip=True) for x in soup.select('.nickname')]
            fresh = []
            result['received'] += len(messages)
            for text in messages:
                original_hash = text_key(text)
                cleaned = clean_message(text, names)
                if not cleaned:
                    result['rejected'] += 1; continue
                key_hash = text_key(cleaned)
                if original_hash in hashes or key_hash in hashes:
                    result['duplicates'] += 1; continue
                hashes.add(original_hash); hashes.add(key_hash)
                fresh.append(cleaned)
            result['pages'].append({'topic_id':topic_id, 'page':number, 'received':len(messages), 'new':len(fresh)})
            if fresh:
                directory.mkdir(parents=True, exist_ok=True)
                if directory.name.startswith('P') and directory.name[1:].isdigit():
                    group = int(directory.name[1:])
                    while len(list(directory.glob('*.jsonl'))) >= 60:
                        group += 1
                        directory = directory.parent / f'P{group}'
                        directory.mkdir(parents=True, exist_ok=True)
                elif len(list(directory.glob('*.jsonl'))) >= 60:
                    result['stop_reason'] = 'output_full'; break
                stamp = datetime.now(timezone.utc).isoformat()
                records = [{'kind':'topic_additional_page','source':'ninisite','source_url':url,
                            'topic_id':topic_id,'page_number':number,'retrieved_at':stamp,
                            'complete':False,'privacy':'best_effort_filtered'}]
                candidates = [{'record_id':f'ninisite:{topic_id}:{number}:{i}', 'source':'ninisite',
                               'source_url':url, 'content_type':'Discussion', 'text':text}
                              for i, text in enumerate(fresh)]
                decisions = classify_records(candidates)
                records.extend({'kind':'reply', 'text':d['record']['text'], 'parent_topic_id':topic_id,
                                'source':'ninisite', 'source_url':url, 'retrieved_at':stamp,
                                'quality_decision':d['decision'], 'quality_reason':d['reason']} for d in decisions)
                groups = [directory]
                if directory.name.startswith('P') and directory.name[1:].isdigit():
                    groups = [g for g in directory.parent.glob('P[0-9]*') if g.is_dir() and not g.is_symlink() and g.name[1:].isdigit()]
                used = {int(p.stem) for group in groups for p in group.glob('*.jsonl') if p.stem.isdigit()}
                for n in range(1,100000):
                    if n in used:
                        continue
                    target = directory / f'{n}.jsonl'
                    try:
                        write_jsonl_new(target, records); break
                    except FileExistsError:
                        continue
                else: raise OSError('no output slot')
                result['files'].append(directory.name + '/' + target.name if directory.name.startswith('P') and directory.name[1:].isdigit() and directory.name != 'P1' else target.name); result['new'] += len(fresh)
            for a in soup.select('.pagination-box a[href]'):
                link = page_link(base, a.get('href'))
                if link and (topic_id, link[1]) not in visited and (topic_id, link[1]) not in known:
                    queue.append({'topic_id':topic_id,'url':link[0]})
        except CollectionStopped:
            result['stop_reason'] = monitor.stop_reason or 'safety_stop'; break
        except (httpx.HTTPError, ValueError, UnicodeError, OSError) as exc:
            result['stop_reason'] = type(exc).__name__; break
    result['complete'] = not queue and result['stop_reason'] is None
    return result
