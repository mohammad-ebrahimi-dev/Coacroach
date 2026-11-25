import json
import httpx
import pytest
from market_tool.persian_html import parse_topic, write_jsonl_new


def test_http_response_to_jsonl_preserves_unicode(tmp_path):
    title = 'عنوان فارسی English العربية ۱۲۳\u200cآزمایش'
    message = 'پاسخ فارسی ك ي ۴۵۶\u200cنیم‌فاصله Mixed'
    html = f'<html><h1>{title}</h1><div class="post-message topic-post__message">{message}</div></html>'
    request = httpx.Request('GET', 'https://example.test/topic')
    response = httpx.Response(200, headers={'Content-Type': 'text/html; charset=utf-8'}, content=html.encode('utf-8'), request=request)
    parsed_title, messages = parse_topic(response)
    output = tmp_path / 'sample.jsonl'
    records = [{'title': parsed_title, 'text': messages[0]}]
    write_jsonl_new(output, records)
    data = output.read_bytes()
    assert data.decode('utf-8').count('?') == 0
    assert [json.loads(line) for line in data.decode('utf-8').splitlines()] == records
    assert parsed_title == title and messages == [message]
    assert title.encode('utf-8') in data and message.encode('utf-8') in data


def test_declared_charset_invalid_bytes_are_not_replaced():
    response = httpx.Response(200, headers={'Content-Type': 'text/html; charset=utf-8'}, content=b'\xff', request=httpx.Request('GET', 'https://example.test'))
    with pytest.raises(UnicodeDecodeError):
        parse_topic(response)


def test_existing_output_is_not_overwritten(tmp_path):
    path = tmp_path / 'existing.jsonl'
    path.write_text('existing', encoding='utf-8')
    with pytest.raises(FileExistsError):
        write_jsonl_new(path, [{'text': 'فارسی'}])
    assert path.read_text(encoding='utf-8') == 'existing'
