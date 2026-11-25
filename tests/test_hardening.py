import json
import os

import pytest

import market_tool.connectors as module
from market_tool.connectors import WorldBankConnector
from market_tool.http_client import FetchError


def response(value):
    return [{'pages': 1, 'total': 1}, [{'indicator': {'id': 'SL.TLF.ACTI.FE.ZS'},
            'countryiso3code': 'IRN', 'date': '2022', 'value': value}]]


@pytest.mark.parametrize('value', [None, 0, 42, -3, 3.5])
def test_valid_values(value):
    row = WorldBankConnector().validate(response(value))[0]
    assert row.value == value


@pytest.mark.parametrize('value', ['12.3', 'bad', True, False, [], {}, float('nan'), float('inf'), -float('inf')])
def test_invalid_values_have_context(value):
    with pytest.raises(FetchError, match=r'record=0 field=value'):
        WorldBankConnector().validate(response(value))


@pytest.mark.parametrize('status', ['Requires Review', 'Rejected', 'unknown', None])
@pytest.mark.parametrize('entry', ['run', 'retrieve'])
def test_unapproved_entry_points(status, entry, tmp_path):
    connector = WorldBankConnector()
    connector.permission_status = status
    class Never:
        def get(self, *args): pytest.fail('must not retrieve')
    with pytest.raises(PermissionError):
        if entry == 'run': connector.run(Never(), tmp_path)
        else: connector.retrieve(Never())
    assert not list(tmp_path.iterdir())


def test_unapproved_subclass_cannot_self_approve(tmp_path):
    class Unapproved(WorldBankConnector):
        permission_status = 'Approved'
    class Never:
        def get(self, *args): pytest.fail('must not retrieve')
    with pytest.raises(PermissionError): Unapproved().retrieve(Never())
    with pytest.raises(PermissionError): Unapproved().run(Never(), tmp_path)


def test_missing_permission_status_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delattr(WorldBankConnector, 'permission_status')
    connector = WorldBankConnector()
    with pytest.raises(PermissionError): connector.retrieve(None)
    with pytest.raises(PermissionError): connector.run(None, tmp_path)


@pytest.mark.parametrize('attr,value', [('source_url', 'https://example.test'), ('identifier', 'other')])
def test_changed_scope_rejected(attr, value):
    c = WorldBankConnector()
    setattr(c, attr, value)
    with pytest.raises(PermissionError): c.retrieve(None)


def old_files(tmp_path):
    d = tmp_path / 'processed'
    d.mkdir()
    first = d / 'world-bank-female-labor-force.json'
    second = d / 'world-bank-female-labor-force.jsonl'
    first.write_bytes(b'previous-json')
    second.write_bytes(b'previous-jsonl')
    return d, first, second


def assert_old_and_clean(directory, first, second):
    assert first.read_bytes() == b'previous-json'
    assert second.read_bytes() == b'previous-jsonl'
    assert sorted(x.name for x in directory.iterdir()) == sorted([first.name, second.name])


@pytest.mark.parametrize('phase', ['json', 'jsonl'])
def test_serialization_failure_preserves_outputs(tmp_path, monkeypatch, phase):
    directory, first, second = old_files(tmp_path)
    original = module.json.dumps
    def dumps(*args, **kwargs):
        if ('indent' in kwargs) == (phase == 'json'):
            raise ValueError('injected serialization failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(module.json, 'dumps', dumps)
    with pytest.raises(ValueError): WorldBankConnector().save([{'value': 1}], tmp_path)
    assert_old_and_clean(directory, first, second)


def test_temp_write_failure_preserves_outputs(tmp_path, monkeypatch):
    directory, first, second = old_files(tmp_path)
    real = module.tempfile.NamedTemporaryFile
    class BrokenFile:
        def __init__(self, *args, **kwargs): self.file = real(*args, **kwargs)
        def __enter__(self): return self
        def __exit__(self, *args): self.file.close()
        @property
        def name(self): return self.file.name
        def write(self, content): raise OSError('injected write failure')
    monkeypatch.setattr(module.tempfile, 'NamedTemporaryFile', BrokenFile)
    with pytest.raises(OSError): WorldBankConnector().save([{'value': 1}], tmp_path)
    assert_old_and_clean(directory, first, second)


@pytest.mark.parametrize('failure_at', [1, 2])
def test_replacement_failure_rolls_back(tmp_path, monkeypatch, failure_at):
    directory, first, second = old_files(tmp_path)
    original = os.replace
    calls = []
    def replace(src, dst):
        calls.append((src, dst))
        if len(calls) == failure_at: raise OSError('injected replacement failure')
        return original(src, dst)
    monkeypatch.setattr(module.os, 'replace', replace)
    with pytest.raises(OSError): WorldBankConnector().save([{'value': 1}], tmp_path)
    assert_old_and_clean(directory, first, second)
    assert len(calls) == (3 if failure_at == 2 else 1)


def test_successful_replacement_updates_both(tmp_path):
    directory, first, second = old_files(tmp_path)
    rows = [{'value': 1}, {'value': None}]
    WorldBankConnector().save(rows, tmp_path)
    assert json.loads(first.read_text(encoding='utf-8')) == rows
    assert [json.loads(x) for x in second.read_text(encoding='utf-8').splitlines()] == rows
    assert len(list(directory.iterdir())) == 2


def test_failed_second_replace_removes_new_first_output(tmp_path, monkeypatch):
    original = os.replace
    calls = []
    def replace(src, dst):
        calls.append(1)
        if len(calls) == 2: raise OSError('injected')
        return original(src, dst)
    monkeypatch.setattr(module.os, 'replace', replace)
    with pytest.raises(OSError): WorldBankConnector().save([{'value': 1}], tmp_path)
    assert not list((tmp_path / 'processed').iterdir())


def test_failed_rollback_reports_and_retains_backups(tmp_path, monkeypatch):
    directory, first, second = old_files(tmp_path)
    original = os.replace
    calls = []
    def replace(src, dst):
        calls.append(1)
        if len(calls) >= 2: raise OSError('injected')
        return original(src, dst)
    monkeypatch.setattr(module.os, 'replace', replace)
    with pytest.raises(OSError, match='rollback failed'):
        WorldBankConnector().save([{'value': 1}], tmp_path)
    assert second.read_bytes() == b'previous-jsonl'
    assert b'previous-json' in [p.read_bytes() for p in directory.glob('.world-bank-*.tmp')]
