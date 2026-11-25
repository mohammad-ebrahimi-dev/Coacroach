"""Build an offline, content-free duplicate index from existing JSONL files."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import unicodedata
from urllib.parse import urlsplit, urlunsplit


def text_key(value):
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = ' '.join(unicodedata.normalize('NFKC', value).split()).casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def url_key(value):
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        host = parts.hostname.lower()
        port = parts.port
        if port is not None and (parts.scheme.lower(), port) not in (('http', 80), ('https', 443)):
            host += ':' + str(port)
        safe = urlunsplit((parts.scheme.lower(), host, parts.path or '/', '', ''))
        return hashlib.sha256(safe.encode('utf-8')).hexdigest()
    except ValueError:
        return None


def scan(data_root):
    """Scan raw and processed JSONL without storing original text or URLs."""
    root = Path(data_root)
    text_hashes, title_hashes, url_hashes, topic_ids = set(), set(), set(), set()
    counts = Counter()
    for area in ('raw', 'processed'):
        for directory, _, files in os.walk(root / area, followlinks=False):
            for name in sorted(files):
                path = Path(directory) / name
                if not name.lower().endswith('.jsonl') or path.is_symlink():
                    continue
                counts['files'] += 1
                try:
                    with path.open(encoding='utf-8-sig') as source:
                        for line in source:
                            if not line.strip():
                                continue
                            counts['lines'] += 1
                            try:
                                row = json.loads(line)
                            except (ValueError, TypeError):
                                counts['invalid_lines'] += 1
                                continue
                            if not isinstance(row, dict):
                                counts['non_object_lines'] += 1
                                continue
                            if isinstance(row.get('record'), dict):
                                row = row['record']
                            if row.get('synthetic') is True:
                                counts['synthetic_lines_excluded'] += 1
                                continue
                            title_hash = text_key(row.get('title'))
                            if title_hash:
                                title_hashes.add(title_hash)
                            ident = row.get('topic_id')
                            if isinstance(ident, (str, int)) and not isinstance(ident, bool) and str(ident).isdigit():
                                topic_ids.add(str(ident))
                            url = row.get('source_url')
                            key = url_key(url)
                            if key:
                                url_hashes.add(key)
                                try:
                                    parts = urlsplit(url)
                                    segments = parts.path.strip('/').split('/')
                                    if parts.hostname and parts.hostname.lower() == 'www.ninisite.com' and len(segments) >= 3 and segments[:2] == ['discussion','topic'] and segments[2].isdigit():
                                        topic_ids.add(segments[2])
                                except ValueError:
                                    pass
                            if row.get('kind') in ('topic_summary','topic_first_page','public_homepage_heading','source_observation'):
                                counts['metadata_lines_excluded'] += 1
                                continue
                            text = row.get('original_text', row.get('text'))
                            fingerprint = text_key(text)
                            if fingerprint is None:
                                counts['no_text_lines'] += 1
                            elif fingerprint in text_hashes:
                                counts['duplicate_text_lines'] += 1
                            else:
                                text_hashes.add(fingerprint)
                                counts['unique_text_lines'] += 1
                except (OSError, UnicodeError):
                    counts['unreadable_files'] += 1
    return {'counts':dict(counts), 'content_sha256':sorted(text_hashes),
            'url_sha256':sorted(url_hashes), 'title_sha256':sorted(title_hashes),
            'ninisite_topic_ids':sorted(topic_ids)}


def compare_topic(index, topic_id, source_url, title, original_post):
    """Classify a topic against old and new records without assuming old IDs.

    Title or text alone cannot establish the same topic; they require review.
    A 'new' decision is conditional on readable indexed records and does not
    prove that a previously unrecorded topic was never collected.
    """
    if not isinstance(topic_id, str) or not topic_id.isdigit() or not url_key(source_url):
        return 'requires_manual_review', 'missing_topic_identity'
    if not text_key(title) or not text_key(original_post):
        return 'extraction_failed', 'missing_title_or_post'
    counts = index.get('counts', {})
    if counts.get('unreadable_files', 0) or counts.get('invalid_lines', 0):
        return 'requires_manual_review', 'incomplete_existing_index'
    if topic_id in index.get('ninisite_topic_ids', []) or url_key(source_url) in index.get('url_sha256', []):
        return 'duplicate', 'known_topic_id_or_url'
    if text_key(title) in index.get('title_sha256', []):
        return 'requires_manual_review', 'matching_legacy_title'
    if text_key(original_post) in index.get('content_sha256', []):
        return 'requires_manual_review', 'matching_legacy_content'
    return 'new_unique_topic', 'no_identity_title_or_content_match'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data_root',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=scan(args.data_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8',newline='\n') as out:
        json.dump(result,out,ensure_ascii=False,indent=2); out.write('\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
