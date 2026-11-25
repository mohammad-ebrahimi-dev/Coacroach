import json
import httpx
from market_tool.ninisite_phase9 import inspect_topics
from market_tool.load_safety_monitor import CollectionStopped


def test_probe_classifies_and_stops_on_403():
    topics=[{'topic_id':'1','url':'https://www.ninisite.com/discussion/topic/1/a'},
            {'topic_id':'2','url':'https://www.ninisite.com/discussion/topic/2/b'},
            {'topic_id':'3','url':'https://www.ninisite.com/discussion/topic/3/c'}]
    class Monitor:
        stop_reason=None
        def __init__(self): self.calls=[]
        def get(self,url):
            self.calls.append(url)
            if url.endswith('robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /')
            if '/2/' in url:
                self.stop_reason='http_403'
                raise CollectionStopped('blocked')
            return httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},
                text='<h1>Synthetic title</h1><div class="post-message topic-post__message">Synthetic post</div>',request=httpx.Request('GET',url))
    monitor=Monitor()
    index={'counts':{},'ninisite_topic_ids':[],'url_sha256':[],'title_sha256':[],'content_sha256':[]}
    result=inspect_topics(topics,index,monitor)
    assert [r['status'] for r in result]==['requires_manual_review','inaccessible','requires_manual_review']
    assert result[0]['reason']=='privacy_review_required_after_dedup'
    assert len(monitor.calls)==3 and 'Synthetic post' not in json.dumps(result)


def test_redirect_is_recorded_without_following():
    topic={'topic_id':'1','url':'https://www.ninisite.com/discussion/topic/1/a'}
    class Monitor:
        stop_reason=None
        def get(self,url):
            if url.endswith('robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /')
            return httpx.Response(301,headers={'location':'https://example.test/'})
    index={'counts':{},'ninisite_topic_ids':[],'url_sha256':[],'title_sha256':[],'content_sha256':[]}
    result=inspect_topics([topic],index,Monitor())
    assert result[0]['status']=='requires_manual_review' and result[0]['reason']=='redirect_301'
