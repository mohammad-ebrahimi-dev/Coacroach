import http.client
import json
import re
import threading
import time
from pathlib import Path

import httpx
import pytest

from dashboard import make_server
from market_tool.dashboard_state import DashboardState, safe_path
from market_tool.load_safety_monitor import CollectionStopped, LoadSafetyMonitor


def test_real_sizes_and_private_paths(tmp_path):
    (tmp_path / 'raw').mkdir()
    (tmp_path / 'processed').mkdir()
    (tmp_path / 'raw' / 'private-name').write_bytes(b'1234')
    (tmp_path / 'processed' / 'private-name').write_bytes(b'123456')
    state = DashboardState(tmp_path)
    snapshot = state.snapshot()
    assert snapshot['size'] == {'raw_bytes': 4, 'processed_bytes': 6, 'total_bytes': 10}
    assert 'private-name' not in json.dumps(snapshot)
    assert safe_path('https://example.test/discussion/topic/123/name?token=secret') == '/discussion/topic/[redacted]'
    assert safe_path('https://example.test/private-name?x=secret') == '/[redacted]'


def test_topic_counts_are_unique_per_stage(tmp_path):
    state = DashboardState(tmp_path)
    state.count_topic_once('topics_identified', 'same-topic')
    state.count_topic_once('topics_identified', 'same-topic')
    state.count_topic_once('topics_examined', 'same-topic')
    state.count_topic_once('topics_identified', 'other-topic')
    counts = state.snapshot()['counts']
    assert counts['topics_identified'] == 2 and counts['topics_examined'] == 1


def test_real_monitor_records_safe_data_and_safety_stop(tmp_path):
    state = DashboardState(tmp_path)
    transport = httpx.MockTransport(lambda request: httpx.Response(429, content=b'secret content'))
    with LoadSafetyMonitor(transport=transport) as monitor:
        state.attach(monitor, lambda: True)
        with pytest.raises(CollectionStopped):
            state.monitored_get('https://example.test/discussion/topic/1/user-name?token=secret')
        s = state.snapshot()
        assert s['status'] == 'error' and s['counts']['failed'] == 1
        assert s['last_request']['status'] == 429
        assert s['safety']['state'] == 'stopped' and not state.resume()
        assert all(x not in json.dumps(s) for x in ['secret', 'user-name'])


def test_pause_blocks_worker_and_resume_checks_permission(tmp_path):
    state = DashboardState(tmp_path)
    permission = [True]
    with LoadSafetyMonitor(transport=httpx.MockTransport(lambda req: httpx.Response(200))) as monitor:
        state.attach(monitor, lambda: permission[0])
        assert state.pause()
        done = threading.Event()
        worker = threading.Thread(target=lambda: (state.checkpoint(), done.set()))
        worker.start()
        for _ in range(100):
            if state.snapshot()['status'] == 'paused':
                break
            time.sleep(.005)
        assert state.snapshot()['status'] == 'paused' and not done.is_set()
        permission[0] = False
        assert not state.resume() and not done.is_set()
        permission[0] = True
        assert state.resume()
        worker.join(1)
        assert done.is_set()
        state.detach()


def test_pause_during_request_prevents_next_request(tmp_path):
    state = DashboardState(tmp_path)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def handler(request):
        calls.append(request)
        entered.set()
        assert release.wait(2)
        return httpx.Response(200)
    with LoadSafetyMonitor(transport=httpx.MockTransport(handler)) as monitor:
        state.attach(monitor, lambda: True)
        def work():
            state.monitored_get('https://example.test/')
            state.checkpoint()
            finished.set()
        worker = threading.Thread(target=work)
        worker.start()
        assert entered.wait(2)
        assert state.pause()
        release.set()
        for _ in range(100):
            if state.snapshot()['status'] == 'paused':
                break
            time.sleep(.005)
        assert state.snapshot()['status'] == 'paused'
        assert not finished.is_set() and len(calls) == 1
        assert state.resume()
        worker.join(1)
        assert finished.is_set()
        state.detach()


def test_http_loopback_and_control_security(tmp_path):
    state = DashboardState(tmp_path)
    server = make_server(0, state=state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert server.server_address[0] == '127.0.0.1'
        port = server.server_port
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
        conn.request('GET', '/api/state')
        resp = conn.getresponse()
        body = json.loads(resp.read())
        assert resp.status == 200 and body['status'] == 'stopped' and not body['controls']['pause']
        conn.request('GET', '/')
        resp = conn.getresponse()
        html = resp.read().decode('utf-8')
        token = re.search(r'name="dashboard-token" content="([^"]+)"', html).group(1)
        assert resp.status == 200 and token != '__TOKEN__'
        conn.request('GET', '/api/records')
        resp = conn.getresponse(); resp.read()
        assert resp.status == 403
        conn.request('GET', '/api/records', headers={'X-Dashboard-Token': token})
        resp = conn.getresponse(); stored = json.loads(resp.read())
        assert resp.status == 200 and stored['records'] == []
        with LoadSafetyMonitor(transport=httpx.MockTransport(lambda req: httpx.Response(200))) as monitor:
            state.attach(monitor, lambda: True)
            conn.request('POST', '/api/pause', headers={'Origin': f'http://127.0.0.1:{port}', 'X-Dashboard-Token': token})
            resp = conn.getresponse(); data = json.loads(resp.read())
            assert resp.status == 200 and data['ok'] and state.status == 'pausing'
            state.detach()
        conn.request('GET', '/api/state', headers={'Host': 'evil.example'})
        resp = conn.getresponse(); resp.read()
        assert resp.status == 403
        conn.request('POST', '/api/pause', headers={'Origin': 'https://evil.example', 'X-Dashboard-Token': 'invalid'})
        resp = conn.getresponse(); resp.read()
        assert resp.status == 403
        conn.request('POST', '/api/start', headers={'Origin': f'http://127.0.0.1:{port}'})
        resp = conn.getresponse(); resp.read()
        assert resp.status == 403
        conn.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(2)


def test_dashboard_frontend_is_single_page_and_polling():
    html = (Path(__file__).parents[1] / 'dashboard' / 'index.html').read_text(encoding='utf-8')
    assert "fetch('/api/state'" in html
    assert "setInterval(poll,3000)" in html
    assert 'Disconnected' in html
    assert '/api/start' not in html
    assert 'messages_identified' in html and 'c.messages_saved' not in html


def test_status_categories_and_response_statistics(tmp_path, monkeypatch):
    state = DashboardState(tmp_path)
    ticks = iter([0, .1, 1, 1.2, 2, 2.3])
    monkeypatch.setattr('market_tool.dashboard_state.time.monotonic', lambda: next(ticks))
    class Monitor:
        stop_reason = None
        delay_seconds = 10
        def __init__(self): self.statuses = iter([200, 301, 410])
        def get(self, url, *, before_request):
            before_request()
            return httpx.Response(next(self.statuses))
    state.attach(Monitor(), lambda: True)
    for _ in range(3): state.monitored_get('https://example.test/')
    snapshot = state.snapshot()
    assert [event['result'] for event in snapshot['events']] == ['success', 'redirected', 'gone']
    assert snapshot['counts']['failed'] == 0
    assert snapshot['response_time_stats'] == {'count': 3, 'mean_ms': 200, 'median_ms': 200, 'p95_ms': 300}


def test_gone_url_persists_and_is_not_requested_again(tmp_path):
    from market_tool.ninisite_continuous import ContinuousNiniSiteCollector
    state = DashboardState(tmp_path)
    calls = []
    class Monitor:
        stop_reason = None
        delay_seconds = 10
        def get(self, url, *, before_request):
            before_request()
            calls.append(url)
            return httpx.Response(410)
    state.attach(Monitor(), lambda: True)
    url = 'https://www.ninisite.com/discussion/topic/123/private-name'
    collector = ContinuousNiniSiteCollector(state)
    assert collector._request(url).status_code == 410
    with pytest.raises(ValueError, match='url_gone'):
        ContinuousNiniSiteCollector(state)._request(url)
    assert calls == [url]
    assert 'private-name' not in (tmp_path / 'gone-url-sha256.txt').read_text()


def test_local_dataset_reports_saved_records_without_internal_paths(tmp_path):
    from market_tool.local_dataset import local_records
    folder = tmp_path / 'processed' / 'ninisite' / 'P1'
    folder.mkdir(parents=True)
    entries = [{'kind':'topic_first_page','retrieved_at':'2026-11-25T00:00:00+00:00','source_url':'https://private.example/path?token=secret'},
               {'kind':'post','text':'Hello test@example.com'},
               {'kind':'reply','text':'Another message'},
               {'kind':'reply','text':'Another message'}]
    (folder/'1.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in entries),encoding='utf-8')
    data = local_records(tmp_path)
    assert data['counts']=={'sources_with_records':1,'posts':1,'replies':1,'duplicates':1,'rejected':None}
    assert data['latest']=='2026-11-25T00:00:00+00:00'
    serialized=json.dumps(data)
    assert 'test@example.com' not in serialized and 'secret' not in serialized
    assert 'private.example' not in serialized and str(tmp_path) not in serialized
    assert '[redacted]' in serialized


def test_latest_batch_metrics_are_read_without_leaking_files(tmp_path):
    from market_tool.local_dataset import local_records
    folder=tmp_path/'processed'/'phase-12'; folder.mkdir(parents=True)
    (folder/'continuation-result.json').write_text(json.dumps({'new':78,'duplicates':11,'rejected':3,'private_path':'sensitive'}),encoding='utf-8')
    data=local_records(tmp_path)
    assert data['last_batch']=={'new':78,'duplicates':11,'rejected':3}
    assert 'sensitive' not in json.dumps(data)


def test_local_records_supports_pagination_without_losing_long_text(tmp_path):
    from market_tool.local_dataset import local_records
    folder=tmp_path/'processed'/'ninisite'/'P1';folder.mkdir(parents=True)
    records=[{'kind':'post','text':f'synthetic item {i}'} for i in range(26)]
    records.append({'kind':'reply','text':'x'*6000})
    (folder/'1.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records),encoding='utf-8')
    first=local_records(tmp_path)
    second=local_records(tmp_path,offset=25)
    assert len(first['records'])==25 and first['has_more']
    assert len(second['records'])==2 and not second['has_more']
    assert len(second['records'][-1]['text'])==6000
    assert first['counts']['posts']==26 and second['counts']['replies']==1
