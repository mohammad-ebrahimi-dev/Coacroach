"""Offline, review-gated transformation of previously stored JSONL records."""
from collections import Counter
import json
from pathlib import Path

from .market_signals import Candidate, ContentType, SIGNAL_TYPES, assess

# These are collector output types, never market signals.
METADATA_KINDS = {'public_homepage_heading', 'topic_summary', 'topic_first_page', 'source_observation'}


def classify_records(records, reviewed_ids=()):
    """Preserve each input record verbatim; reviews are provided separately."""
    reviewed_ids, seen = set(reviewed_ids), set()
    id_counts = Counter(r.get('record_id') for r in records if isinstance(r, dict) and isinstance(r.get('record_id'), str))
    decisions = []
    for position, raw in enumerate(records, 1):
        if not isinstance(raw, dict):
            decisions.append({'record': raw, 'position': position, 'decision': 'rejected', 'reason': 'invalid_record'})
            continue
        kind = raw.get('kind')
        raw_type = raw.get('content_type')
        text = raw.get('original_text', raw.get('text'))
        try:
            content_type = ContentType(raw_type)
        except (ValueError, TypeError):
            content_type = ContentType.HOMEPAGE_METADATA if kind in METADATA_KINDS else ContentType.OTHER
        candidate = Candidate(raw.get('source'), raw.get('source_url'), content_type, text,
                              isinstance(raw.get('record_id'), str) and id_counts[raw['record_id']] == 1 and raw['record_id'] in reviewed_ids)
        if kind in METADATA_KINDS or content_type in (ContentType.HOMEPAGE_METADATA, ContentType.MARKETING, ContentType.NAVIGATION):
            decision, reason = 'rejected', 'non_signal_content_type'
        elif not isinstance(text, str) or not text.strip():
            decision, reason = 'rejected', 'empty_content'
        elif content_type is ContentType.OTHER:
            decision, reason = 'manual_review', 'ambiguous_content_type'
        else:
            accepted, reason = assess(candidate, seen)
            decision = 'accepted' if accepted else ('manual_review' if reason == 'requires_evidence_review' else 'rejected')
        decisions.append({'record': raw, 'position': position, 'decision': decision, 'reason': reason})
    return decisions


def read_jsonl(path):
    with Path(path).open(encoding='utf-8-sig') as source:
        return [json.loads(line) for line in source if line.strip()]


def process_file(input_path, output_dir, reviewed_ids=()):
    """Write a new output directory; never modify input or pre-existing output."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    records = read_jsonl(input_path)
    decisions = classify_records(records, reviewed_ids)
    for entry in decisions:
        entry['input_provenance'] = {'input_file': str(input_path), 'record_index': entry['position']}
    # A new directory is created exclusively; never replace any prior outputs.
    output_dir.mkdir(parents=True, exist_ok=False)
    for label in ('accepted', 'rejected', 'manual_review'):
        with (output_dir / (label + '.jsonl')).open('x', encoding='utf-8', newline='\n') as out:
            for entry in decisions:
                if entry['decision'] == label:
                    out.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + '\n')
    counts = Counter(entry['decision'] for entry in decisions)
    reasons = Counter(entry['reason'] for entry in decisions if entry['decision'] == 'rejected')
    summary = {'total': len(decisions), 'accepted': counts['accepted'], 'rejected': counts['rejected'],
               'manual_review': counts['manual_review'], 'rejection_reasons': dict(reasons)}
    with (output_dir / 'summary.json').open('x', encoding='utf-8', newline='\n') as out:
        json.dump(summary, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')
    return summary
