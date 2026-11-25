import httpx
import pytest
from market_tool.parscoders import parse_project_listing, project_url, fetch_projects


def response(html):
    return httpx.Response(200, headers={'content-type':'text/html; charset=utf-8'},
                          content=html.encode('utf-8'), request=httpx.Request('GET','https://parscoders.com/project'))


def test_public_listing_parses_farsi_and_omits_private_or_offsite():
    title='\u0633\u0627\u062e\u062a \u0628\u0631\u0646\u0627\u0645\u0647'
    desc='\u0646\u06cc\u0627\u0632 \u0628\u0647 \u0628\u0631\u0646\u0627\u0645\u0647'
    html=f'''<div class="project-list-item"><div class="project-title"><h6><a class="project--link" href="/project/123/demo">{title}</a></h6></div><div class="project-text">{desc} <a href="/user/private">ignore</a></div></div>
    <div class="project-list-item"><div class="project-title"><h6>private</h6></div><div class="project-text">private</div></div>
    <div class="project-list-item"><div class="project-title"><h6><a class="project--link" href="https://evil.test/project/9/a">x</a></h6></div><div class="project-text">x</div></div>'''
    rows=parse_project_listing(response(html))
    assert len(rows)==1 and rows[0]['title']==title and rows[0]['text']==desc
    assert rows[0]['review_required'] and rows[0]['project_id']=='123'
    assert 'private' not in str(rows[0])


def test_disabled_execution_fails_before_network():
    class Client:
        def get(self,*args): pytest.fail('network called')
    with pytest.raises(PermissionError): fetch_projects(Client())


def test_url_and_missing_structure_rejected():
    assert project_url('https://parscoders.com/project/1/a?token=secret') is None
    assert project_url('https://parscoders.com.evil.test/project/1/a') is None
    with pytest.raises(ValueError): parse_project_listing(response('<h1>home</h1>'))


def test_simulated_approved_scope_passes_preview_to_review_pipeline(monkeypatch):
    import market_tool.parscoders as pc
    class Monitor:
        delay_seconds=10
        def __init__(self): self.calls=[]
        def get(self, url):
            self.calls.append(url)
            if url.endswith('/robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /')
            return response('<div class="project-list-item"><div class="project-title"><h6><a class="project--link" href="/project/123/demo">Synthetic title</a></h6></div><div class="project-text">Synthetic project need</div></div>')
    monkeypatch.setattr(pc,'_APPROVED_SCOPE',('parscoders',pc.LISTING,'market-research'))
    monitor=Monitor(); decisions=pc.fetch_projects(monitor)
    assert len(monitor.calls)==2 and len(decisions)==1
    assert decisions[0]['decision']=='manual_review'
    assert decisions[0]['record']['project_id']=='123'
