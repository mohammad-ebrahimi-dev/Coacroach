import json
from market_tool.dedup_index import scan, text_key, url_key, compare_topic


def test_normalizes_and_redacts_sensitive_parts():
    assert text_key('Hello   world') == text_key('hello world')
    assert url_key('https://example.test/a?token=secret') == url_key('https://example.test/a')
    assert url_key('https://user:secret@example.test/a') is None


def test_scans_existing_jsonl_without_text_or_fake_records(tmp_path):
    folder=tmp_path/'processed'/'ninisite'; folder.mkdir(parents=True)
    records=[{'kind':'topic_first_page','topic_id':'123'},
             {'text':'Private sample','source_url':'https://www.ninisite.com/discussion/topic/123/a?secret=x'},
             {'text':'private   sample'}, {'record':{'synthetic':True,'text':'fake'}}]
    (folder/'1.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records)+'bad json\n',encoding='utf-8')
    result=scan(tmp_path)
    assert result['counts']['unique_text_lines']==1
    assert result['counts']['duplicate_text_lines']==1
    assert result['counts']['synthetic_lines_excluded']==1
    assert result['counts']['invalid_lines']==1
    assert result['ninisite_topic_ids']==['123']
    assert 'Private sample' not in json.dumps(result) and 'secret' not in json.dumps(result)


def test_legacy_content_and_title_matches_require_review(tmp_path):
    folder=tmp_path/'processed'; folder.mkdir()
    (folder/'old.jsonl').write_text(json.dumps({'title':'Old title','text':'Old body'})+'\n',encoding='utf-8')
    index=scan(tmp_path)
    u='https://www.ninisite.com/discussion/topic/99/test'
    assert compare_topic(index,'99',u,'Old title','Different text')[1]=='matching_legacy_title'
    assert compare_topic(index,'99',u,'Different title','Old body')[1]=='matching_legacy_content'
    assert compare_topic(index,'99',u,'Different title','Different text')[0]=='new_unique_topic'
    assert compare_topic(index,'99',u,'Different title','')[0]=='extraction_failed'


def test_known_topic_id_and_broken_index_fail_closed():
    u='https://www.ninisite.com/discussion/topic/123/test'
    index={'counts':{},'ninisite_topic_ids':['123'],'url_sha256':[],'title_sha256':[],'content_sha256':[]}
    assert compare_topic(index,'123',u,'title','post')[0]=='duplicate'
    index['counts']['invalid_lines']=1
    assert compare_topic(index,'999',u,'title','post')[1]=='incomplete_existing_index'
