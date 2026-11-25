"""Read a bounded view of local, already filtered user-content JSONL files."""
import json
from pathlib import Path
from .dedup_index import text_key
from .text_safety import clean_message


def local_records(data_root, limit=25, offset=0):
    """Expose whitelisted fields only; never access raw files or other folders."""
    result = {'counts': {'sources_with_records': 0, 'posts': 0, 'replies': 0,
                         'duplicates': 0, 'rejected': None}, 'latest': None, 'last_batch': None, 'offset': offset, 'has_more': False, 'records': []}
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('invalid page')
    records, hashes, sources = [], set(), set()
    base = Path(data_root) / 'processed'
    if base.is_symlink():
        return result
    for source in ('ninisite', 'parscoders'):
        directory = base / source
        if directory.is_symlink() or not directory.is_dir():
            continue
        for group in sorted(directory.glob('P[0-9]*'), key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0):
            if group.is_symlink() or not group.is_dir() or not group.name[1:].isdigit():
                continue
            for path in sorted(group.glob('*.jsonl'), key=lambda p: int(p.stem) if p.stem.isdigit() else 0):
                if path.is_symlink() or not path.is_file():
                    continue
                metadata = {}
                try:
                    if path.stat().st_size > 2_000_000:
                        continue
                    with path.open(encoding='utf-8-sig') as source_file:
                        for line in source_file:
                            try:
                                row = json.loads(line)
                            except (ValueError, TypeError):
                                continue
                            if not isinstance(row, dict):
                                continue
                            kind = row.get('kind')
                            if kind in ('topic_first_page', 'topic_additional_page'):
                                metadata = {'retrieved_at': row.get('retrieved_at')}
                                continue
                            if kind not in ('post', 'reply') and row.get('content_type') not in ('ProjectListing','ProjectDescription'):
                                continue
                            text = row.get('text')
                            safe = clean_message(text)
                            if not safe:
                                continue
                            fingerprint = text_key(safe)
                            if fingerprint in hashes:
                                result['counts']['duplicates'] += 1
                                continue
                            hashes.add(fingerprint)
                            sources.add(source)
                            category = 'reply' if kind == 'reply' else 'post'
                            result['counts']['replies' if category == 'reply' else 'posts'] += 1
                            stamp = row.get('retrieved_at') or metadata.get('retrieved_at')
                            if isinstance(stamp, str) and len(stamp) <= 40 and (result['latest'] is None or stamp > result['latest']):
                                result['latest'] = stamp
                            ordinal = result['counts']['posts'] + result['counts']['replies'] - 1
                            if offset <= ordinal < offset + limit:
                                records.append({'source': source, 'kind': category, 'text': safe,
                                                'retrieved_at': stamp if isinstance(stamp, str) and len(stamp) <= 40 else None})
                except (OSError, UnicodeError):
                    continue
    batch_dir = base / 'phase-12'
    batch_file = batch_dir / 'continuation-result.json'
    if not batch_dir.is_symlink() and not batch_file.is_symlink():
        try:
            if batch_file.is_file() and batch_file.stat().st_size <= 100_000:
                with batch_file.open(encoding='utf-8') as batch_input:
                    batch = json.load(batch_input)
                if isinstance(batch, dict) and all(type(batch.get(k)) is int and batch[k] >= 0 for k in ('new','duplicates','rejected')):
                    result['last_batch'] = {k: batch[k] for k in ('new','duplicates','rejected')}
        except (OSError, ValueError, TypeError, UnicodeError):
            pass
    result['counts']['sources_with_records'] = len(sources)
    result['has_more'] = result['counts']['posts'] + result['counts']['replies'] > offset + limit
    result['records'] = records
    return result
