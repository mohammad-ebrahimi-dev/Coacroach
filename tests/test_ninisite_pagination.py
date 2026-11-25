import json
import httpx
from market_tool.ninisite_pagination import page_link, collect_pages
from market_tool.dedup_index import text_key
from market_tool.ninisite_continuous import ContinuousNiniSiteCollector
from market_tool.dashboard_state import DashboardState

BASE='https://www.ninisite.com/discussion/topic/123/test'


def test_page_links_are_same_topic_and_observed_query_only():
    assert page_link(BASE, '?page=2') == (BASE+'?page=2',2)
    assert page_link(BASE, '?page=1') is None
    assert page_link(BASE, '?page=2&token=secret') is None
    assert page_link(BASE, 'https://evil.test/discussion/topic/123/test?page=2') is None
    assert page_link(BASE, '/discussion/topic/124/test?page=2') is None


def test_continuation_deduplicates_redacts_and_writes_without_overwrite(tmp_path):
    author='\u0639\u0644'
    class Monitor:
        stop_reason=None
        def __init__(self): self.calls=[]
        def get(self,url):
            self.calls.append(url)
            request=httpx.Request('GET',url)
            if url.endswith('/robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /',request=request)
            html=(f'<h1>synthetic</h1><span class="nickname">{author}</span>'
                  f'<div class="post-message topic-post__message">old</div>'
                  f'<div class="post-message topic-post__message">hello {author}</div>')
            return httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},content=html.encode('utf-8'),request=request)
    (tmp_path/'1.jsonl').write_text('old',encoding='utf-8')
    monitor=Monitor()
    summary=collect_pages([{'topic_id':'123','url':BASE+'?page=2'}],{'123':BASE},{text_key('old')},monitor,tmp_path,collector=ContinuousNiniSiteCollector(DashboardState(tmp_path)))
    assert (summary['received'],summary['new'],summary['duplicates'])==(2,1,1)
    assert summary['complete'] and summary['files']==['2.jsonl']
    rows=[json.loads(line) for line in (tmp_path/'2.jsonl').read_text(encoding='utf-8').splitlines()]
    assert rows[0]['page_number']==2 and rows[1]['parent_topic_id']=='123'
    assert rows[1]['quality_decision']=='manual_review'
    assert rows[1]['source']=='ninisite' and rows[1]['source_url']==BASE+'?page=2' and rows[1]['retrieved_at']
    assert author not in (tmp_path/'2.jsonl').read_text(encoding='utf-8')
    assert (tmp_path/'1.jsonl').read_text(encoding='utf-8')=='old'
    assert len(monitor.calls)==2


def test_permission_check_precedes_network(tmp_path):
    import pytest
    class Monitor:
        def get(self, url): pytest.fail('network must not run')
    with pytest.raises(PermissionError):
        collect_pages([], {}, set(), Monitor(), tmp_path, collector=object())


def test_continuation_rolls_into_next_group_with_global_number(tmp_path):
    root=tmp_path/'ninisite';p1=root/'P1';p1.mkdir(parents=True)
    for number in range(1,61): (p1/f'{number}.jsonl').write_text('{}\n',encoding='utf-8')
    class Monitor:
        stop_reason=None
        def get(self,url):
            request=httpx.Request('GET',url)
            if url.endswith('/robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /',request=request)
            return httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},text='<h1>synthetic</h1><div class="post-message topic-post__message">new synthetic reply</div>',request=request)
    collector=ContinuousNiniSiteCollector(DashboardState(tmp_path))
    result=collect_pages([{'topic_id':'123','url':BASE+'?page=2'}],{'123':BASE},set(),Monitor(),p1,collector=collector)
    assert result['new']==1 and result['files']==['P2/61.jsonl']
    assert (root/'P2'/'61.jsonl').exists()
