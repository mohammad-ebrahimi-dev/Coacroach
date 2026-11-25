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


def test_saves_filtered_first_page_and_never_overwrites(tmp_path):
    from market_tool.ninisite_phase9 import save_filtered_topic
    from market_tool.persian_html import parse_topic
    url='https://www.ninisite.com/discussion/topic/9/test'
    author='\u0646\u0627\u0645\u06a9\u0627\u0631\u0628\u0631'
    title='\u0645\u0648\u0636\u0648\u0639'
    text='\u0633\u0644\u0627\u0645 ' + author
    html=f'<h1>{title}</h1><span class="nickname">{author}</span><div class="post-message topic-post__message">{text}</div><div class="post-message topic-post__message">reply</div>'
    response=httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},content=html.encode('utf-8'),request=httpx.Request('GET',url))
    parsed_title, messages=parse_topic(response)
    (tmp_path/'1.jsonl').write_text('old',encoding='utf-8')
    result=save_filtered_topic(response,'9',url,parsed_title,messages,tmp_path)
    path,replies,excluded=result
    records=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    assert path.name=='2.jsonl' and (tmp_path/'1.jsonl').read_text()=='old'
    assert records[0]['title']==title and not records[0]['complete']
    assert author not in path.read_text(encoding='utf-8')
    assert records[1]['text'].startswith('\u0633\u0644\u0627\u0645') and replies==1 and excluded==0


def test_output_opt_in_and_known_topic_are_handled(tmp_path):
    topic={'topic_id':'1','url':'https://www.ninisite.com/discussion/topic/1/a'}
    class Monitor:
        stop_reason=None
        def get(self,url):
            if url.endswith('robots.txt'):
                return httpx.Response(200,headers={'content-type':'text/plain'},text='User-agent: *\nAllow: /')
            return httpx.Response(200,headers={'content-type':'text/html; charset=utf-8'},text='<h1>title</h1><div class="post-message topic-post__message">content</div>',request=httpx.Request('GET',url))
    index={'counts':{},'ninisite_topic_ids':[],'url_sha256':[],'title_sha256':[],'content_sha256':[]}
    result=inspect_topics([topic],index,Monitor(),output_dir=tmp_path)
    assert result[0]['status']=='new_unique_topic' and (tmp_path/'1.jsonl').exists()
    assert inspect_topics([topic],index,Monitor(),output_dir=tmp_path)[0]['status']=='duplicate'
