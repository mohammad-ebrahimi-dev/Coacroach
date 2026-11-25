import json
from pathlib import Path
import socket
import pytest
from market_tool.market_signal_pipeline import process_file

FIXTURE = Path('tests/fixtures/market-signals-synthetic.jsonl')
REVIEWS = Path('tests/fixtures/market-signals-synthetic-reviews.json')


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def test_offline_end_to_end_preserves_source_and_reviews(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: pytest.fail('network prohibited'))
    before = FIXTURE.read_bytes()
    reviewed = [k for k, v in json.loads(REVIEWS.read_text(encoding='utf-8-sig')).items() if v]
    output = tmp_path / 'new-run'
    result = process_file(FIXTURE, output, reviewed)
    assert result == {'total': 7, 'accepted': 1, 'rejected': 5, 'manual_review': 1,
                      'rejection_reasons': {'non_signal_content_type': 3, 'empty_content': 1, 'duplicate': 1}}
    original = rows(FIXTURE)
    decisions = sum((rows(output / (name + '.jsonl')) for name in ('accepted', 'rejected', 'manual_review')), [])
    assert sorted((d['position'], d['record']) for d in decisions) == list(enumerate(original, 1))
    assert all(d['reason'] and d['input_provenance']['input_file'] == str(FIXTURE) for d in decisions)
    candidate = rows(output / 'accepted.jsonl')[0]
    assert candidate['record']['record_id'] == 'request' and 'pain_point' not in candidate
    assert FIXTURE.read_bytes() == before
    with pytest.raises(FileExistsError): process_file(FIXTURE, output, reviewed)


def test_unreviewed_and_untrusted_record_cannot_self_approve(tmp_path):
    fixture = tmp_path / 'old.jsonl'
    data = {'record_id':'x','source':'s','source_url':'https://example.test/project/1',
            'content_type':'UserRequest','text':'Need a tool', 'evidence_reviewed':True}
    fixture.write_text(json.dumps(data) + '\n', encoding='utf-8')
    result = process_file(fixture, tmp_path / 'out')
    assert result['manual_review'] == 1 and result['accepted'] == 0
    assert rows(tmp_path / 'out' / 'manual_review.jsonl')[0]['record'] == data


def test_existing_collector_output_is_metadata_not_signal(tmp_path):
    fixture = tmp_path / 'local.jsonl'
    records = [{'source':'x','kind':'public_homepage_heading','text':'marketing'},
               {'kind':'reply','text':'prior local text'}]
    fixture.write_text(''.join(json.dumps(r)+'\n' for r in records), encoding='utf-8')
    result = process_file(fixture, tmp_path / 'out')
    assert result['rejected'] == 1 and result['manual_review'] == 1


def test_cli_path_runs_offline_without_config_or_http(tmp_path, monkeypatch, capsys):
    import sys
    import main
    monkeypatch.setattr(sys, 'argv', ['main.py', 'process-signals', str(FIXTURE), str(tmp_path / 'cli'), '--reviews', str(REVIEWS)])
    monkeypatch.setattr(main.Settings, 'load', lambda: pytest.fail('offline processing must not load network configuration'))
    monkeypatch.setattr(main, 'HttpClient', lambda *a, **k: pytest.fail('network client must not be created'))
    assert main.main() == 0
    assert json.loads(capsys.readouterr().out)['accepted'] == 1
    assert rows(tmp_path / 'cli' / 'accepted.jsonl')[0]['record']['synthetic'] is True


def test_reused_review_id_cannot_approve_multiple_records(tmp_path):
    path = tmp_path / 'dup-ids.jsonl'
    row = {'record_id':'same','source':'s','source_url':'https://example.test/item/1',
           'content_type':'UserRequest','text':'Need a tool'}
    path.write_text((json.dumps(row) + '\n') * 2, encoding='utf-8')
    result = process_file(path, tmp_path / 'out', ['same'])
    assert result['accepted'] == 0 and result['manual_review'] == 2
