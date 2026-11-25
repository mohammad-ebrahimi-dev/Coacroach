import json
import time
import httpx

from market_tool.dashboard_state import DashboardState
from market_tool.ninisite_continuous import ContinuousNiniSiteCollector, topic_link


def test_topic_links_reject_other_hosts_and_queries():
    assert topic_link('https://www.ninisite.com/discussion/topic/123/test') == '123'
    assert topic_link('https://evil.example/discussion/topic/123/test') is None
    assert topic_link('https://www.ninisite.com/discussion/topic/123/test?token=secret') is None
    assert topic_link('https://www.ninisite.com:invalid/discussion/topic/123/test') is None


def test_continuous_monitor_saves_filtered_text_and_pauses(tmp_path):
    state = DashboardState(tmp_path)
    calls = []
    class FakeMonitor:
        delay_seconds = 10
        stop_reason = None
        def get(self, url, *, before_request):
            before_request()
            calls.append(url)
            request = httpx.Request('GET', url)
            if url.endswith('/robots.txt'):
                return httpx.Response(200, headers={'Content-Type': 'text/plain'}, text='User-agent: *\nAllow: /', request=request)
            if url.endswith('/discussion'):
                return httpx.Response(200, headers={'Content-Type': 'text/html'}, text='<a href="/discussion/topic/123/test">link</a>', request=request)
            return httpx.Response(200, headers={'Content-Type': 'text/html; charset=utf-8'}, content=('<h1>موضوع</h1><span class="nickname">نام‌کاربری</span><div class="post-message topic-post__message">سلام نام‌کاربری</div><div class="post-message topic-post__message">بارداری</div>').encode('utf-8'), request=request)
        def close(self): pass
    collector = ContinuousNiniSiteCollector(state, monitor_factory=FakeMonitor, cycle_wait=60)
    assert collector.start()
    for _ in range(200):
        files = list((tmp_path / 'processed' / 'ninisite').glob('P*/*.jsonl'))
        if files:
            try:
                json.loads(files[0].read_text(encoding='utf-8').splitlines()[0])
                if state.counts['messages_saved'] != 1:
                    continue
                break
            except (OSError, ValueError):
                pass
        time.sleep(.005)
    assert state.counts['topics_examined'] == 1
    assert state.counts['topics_saved'] == 0
    assert state.pause()
    for _ in range(200):
        if state.status == 'paused':
            break
        time.sleep(.005)
    assert state.status == 'paused'
    count = len(calls)
    time.sleep(.02)
    assert len(calls) == count
    output = list((tmp_path / 'processed' / 'ninisite').glob('P*/*.jsonl'))
    assert len(output) == 1
    content = output[0].read_text(encoding='utf-8')
    assert 'نام‌کاربری' not in content and 'بارداری' not in content
    lines = [json.loads(line) for line in content.splitlines()]
    assert lines[0]['messages_on_first_page'] == 2
    assert lines[0]['complete'] is False and lines[0]['title'] == 'موضوع'
    assert lines[1]['text'] == 'سلام [redacted]'
    assert state.counts['messages_saved'] == 1
    assert state.stop()
    for _ in range(200):
        if not state.attached:
            break
        time.sleep(.005)
    assert state.status == 'stopped' and state.reason == 'user_stop'


def test_permission_guard_rejects_unknown_status(tmp_path):
    collector = ContinuousNiniSiteCollector(DashboardState(tmp_path))
    collector.permission_status = 'unknown'
    assert not collector.start()


def test_numbered_topic_groups_preserve_existing_files(tmp_path):
    from market_tool.ninisite_pilot import save_numbered_topic
    folder = tmp_path / 'processed' / 'ninisite'
    folder.mkdir(parents=True)
    (folder / '1.jsonl').write_text('old', encoding='utf-8')
    paths = [save_numbered_topic(tmp_path, [{'text': 'نمونه'}], source='ninisite') for _ in range(61)]
    assert len(list((folder / 'P1').glob('*.jsonl'))) == 60
    assert len(list((folder / 'P2').glob('*.jsonl'))) == 1
    assert paths[0].name == '2.jsonl' and paths[-1].name == '62.jsonl'
    assert (folder / '1.jsonl').read_text(encoding='utf-8') == 'old'


def test_connection_recovery_waits_and_reuses_monitor(tmp_path, monkeypatch):
    state = DashboardState(tmp_path)
    collector = ContinuousNiniSiteCollector(state)
    calls, waits = [], []
    class Monitor:
        stop_reason = None
        def close(self): calls.append('close')
    monitor = Monitor()
    state.attached = True
    def run(m):
        assert m is monitor
        calls.append('run')
        return len([x for x in calls if x == 'run']) == 1
    monkeypatch.setattr(collector, '_run', run)
    monkeypatch.setattr(state, 'wait_for_next_cycle', lambda seconds: waits.append(seconds) or True)
    collector._supervise(monitor)
    assert calls == ['run', 'run', 'close'] and waits == [60]
    assert not state.attached


def test_existing_ids_are_found_across_source_directories(tmp_path):
    folder=tmp_path/'processed'/'ninisite'/'P1';folder.mkdir(parents=True)
    (folder/'1.jsonl').write_text(json.dumps({'kind':'topic_first_page','topic_id':'123'})+'\n',encoding='utf-8')
    collector=ContinuousNiniSiteCollector(DashboardState(tmp_path))
    assert '123' in collector._existing_ids()


def test_short_username_is_redacted_without_removing_message():
    from market_tool.text_safety import clean_message
    assert clean_message('hello ab and abstract',['ab']) == 'hello [redacted] and abstract'


def test_sensitive_keyword_as_username_is_redacted_before_filtering():
    from market_tool.text_safety import clean_message
    name='\u067e\u0632\u0634\u06a9'
    assert clean_message('hello '+name,[name]) == 'hello [redacted]'
    assert clean_message('hello '+name,[]) is None


def test_dashboard_worker_collects_observed_next_page(tmp_path):
    state=DashboardState(tmp_path)
    calls=[]
    class FakeMonitor:
        delay_seconds=10
        stop_reason=None
        def get(self,url,*,before_request):
            before_request(); calls.append(url)
            request=httpx.Request('GET',url)
            if url.endswith('/robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /',request=request)
            if url.endswith('/discussion'):
                return httpx.Response(200,headers={'content-type':'text/html'},text='<a href="/discussion/topic/987/test">topic</a>',request=request)
            if url.endswith('?page=2'):
                return httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},text='<h1>Synthetic topic</h1><div class="post-message topic-post__message">Synthetic reply</div>',request=request)
            return httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},text='<h1>Synthetic topic</h1><div class="post-message topic-post__message">Synthetic post</div><div class="pagination-box"><a href="?page=2">2</a></div>',request=request)
        def close(self): pass
    collector=ContinuousNiniSiteCollector(state,monitor_factory=FakeMonitor,cycle_wait=60)
    assert collector.start()
    for _ in range(200):
        if state.counts['messages_saved']==2: break
        time.sleep(.01)
    assert state.counts['messages_saved']==2
    files=list((tmp_path/'processed'/'ninisite'/'P1').glob('*.jsonl'))
    assert len(files)==2
    assert any(json.loads(p.read_text(encoding='utf-8').splitlines()[0])['kind']=='topic_additional_page' for p in files)
    assert len(calls)==4 and calls[-1].endswith('?page=2')
    assert state.stop()
    for _ in range(200):
        if not state.attached: break
        time.sleep(.005)
