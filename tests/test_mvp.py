import json
import httpx
import pytest
from pydantic import ValidationError

from market_tool.config import Settings
from market_tool.connectors import WorldBankConnector
from market_tool.http_client import FetchError, HttpClient


def payload():
    return [{'pages': 1, 'total': 2}, [
        {'indicator': {'id': 'SL.TLF.ACTI.FE.ZS', 'value': 'Example label'}, 'countryiso3code': 'IRN', 'date': '2022', 'value': 12.5},
        {'indicator': {'id': 'SL.TLF.ACTI.FE.ZS', 'value': 'Example label'}, 'countryiso3code': 'IRN', 'date': '2021', 'value': None},
    ]]


def test_configuration_validation():
    with pytest.raises(ValidationError): Settings(http_timeout=0)
    with pytest.raises(ValidationError): Settings(max_retries=6)
    with pytest.raises(ValidationError): Settings(log_level='VERBOSE')
    assert Settings(http_proxy='').http_proxy is None


def test_proxy_validation_and_no_direct_fallback():
    with pytest.raises(ValidationError): Settings(https_proxy='bad')
    settings = Settings(http_proxy='http://localhost:8080')
    with pytest.raises(FetchError, match='proxy_missing_for_scheme'):
        HttpClient(settings).get('https://example.test/', 'test')
    assert 'secret' not in repr(Settings(https_proxy='http://user:secret@localhost:8080'))


def test_explicit_proxy_is_passed_without_environment_fallback(monkeypatch):
    captured = {}
    class FakeClient:
        def __init__(self, **kwargs): captured.update(kwargs)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, *args, **kwargs): return httpx.Response(200)
    monkeypatch.setattr(httpx, 'Client', FakeClient)
    settings = Settings(https_proxy='http://user:secret@localhost:8080')
    HttpClient(settings).get('https://example.test/', 'test')
    assert captured['proxy'] == settings.https_proxy
    assert captured['trust_env'] is False and captured['verify'] is True


def test_timeout_and_retry_limit():
    calls, sleeps = [], []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout('sensitive diagnostic', request=request)
    client = HttpClient(Settings(max_retries=2, connect_timeout=3), httpx.MockTransport(handler), sleeps.append)
    assert client.timeout.connect == 3
    with pytest.raises(FetchError, match='ReadTimeout') as err:
        client.get('https://example.test/', 'test')
    assert err.value.retries == 2 and len(calls) == 3 and sleeps == [1, 2]


def test_rate_limit_stops_without_retry():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={'Retry-After': '120'})
    client = HttpClient(Settings(max_retries=5), httpx.MockTransport(handler), lambda _: pytest.fail('must stop'))
    with pytest.raises(FetchError, match='rate_limited_retry_after_present'):
        client.get('https://example.test/', 'test')
    assert len(calls) == 1


def test_retry_500_then_success():
    calls, sleeps = [], []
    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) == 1 else 200)
    client = HttpClient(Settings(max_retries=2), httpx.MockTransport(handler), sleeps.append)
    assert client.get('https://example.test/', 'test').status_code == 200
    assert len(calls) == 2 and sleeps == [1]


def test_response_and_serialization(tmp_path):
    data = payload()
    client = HttpClient(Settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=data)))
    rows = WorldBankConnector().run(client, tmp_path)
    assert rows[1]['value'] is None and rows[0]['year'] == 2022
    directory = tmp_path / 'processed'
    j = json.loads((directory / 'world-bank-female-labor-force.json').read_text(encoding='utf-8'))
    jl = [json.loads(line) for line in (directory / 'world-bank-female-labor-force.jsonl').read_text(encoding='utf-8').splitlines()]
    assert j == jl == rows


def test_wrong_or_incomplete_response_rejected():
    connector = WorldBankConnector()
    bad = payload()
    bad[1][0]['countryiso3code'] = 'USA'
    with pytest.raises(FetchError, match='invalid_response'): connector.validate(bad)
    bad = payload()
    bad[0]['pages'] = 2
    with pytest.raises(FetchError, match='invalid_response'): connector.validate(bad)


def test_unapproved_source_refuses_before_request(tmp_path):
    connector = WorldBankConnector()
    connector.permission_status = 'Requires Review'
    class Never:
        def get(self, *args): pytest.fail('must not fetch')
    with pytest.raises(PermissionError): connector.run(Never(), tmp_path)
    assert not list(tmp_path.iterdir())


def test_http_503_retry_exhaustion():
    calls, sleeps = [], []
    def handler(request):
        calls.append(request)
        return httpx.Response(503)
    client = HttpClient(Settings(max_retries=2), httpx.MockTransport(handler), sleeps.append)
    with pytest.raises(FetchError) as error:
        client.get('https://example.test/', 'test')
    assert error.value.status == 503 and error.value.retries == 2
    assert len(calls) == 3 and sleeps == [1, 2]


def test_proxy_error_does_not_leak_exception_details(caplog):
    secret = 'example-credential-do-not-log'
    def handler(request):
        raise httpx.ProxyError(secret, request=request)
    client = HttpClient(Settings(max_retries=0), httpx.MockTransport(handler))
    with caplog.at_level('DEBUG'):
        with pytest.raises(FetchError) as error:
            client.get('https://example.test/', 'test')
    assert error.value.category == 'ProxyError'
    assert secret not in str(error.value) and secret not in caplog.text


def test_invalid_json_does_not_save(tmp_path):
    client = HttpClient(Settings(), httpx.MockTransport(lambda _: httpx.Response(200, text='not JSON')))
    with pytest.raises(FetchError, match='invalid_json'):
        WorldBankConnector().run(client, tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('mutation', ['wrong_indicator', 'duplicate_year', 'wrong_count', 'invalid_value'])
def test_malformed_observations_rejected(mutation):
    data = payload()
    if mutation == 'wrong_indicator': data[1][0]['indicator']['id'] = 'OTHER'
    elif mutation == 'duplicate_year': data[1][1]['date'] = data[1][0]['date']
    elif mutation == 'wrong_count': data[0]['total'] = 3
    elif mutation == 'invalid_value': data[1][0]['value'] = 'not-a-number'
    with pytest.raises(FetchError, match='invalid_response'):
        WorldBankConnector().validate(data)


def test_forbidden_http_response_does_not_retry():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(403)
    client = HttpClient(Settings(max_retries=2), httpx.MockTransport(handler), lambda _: pytest.fail('must stop'))
    with pytest.raises(FetchError) as error:
        client.get('https://example.test/', 'test')
    assert error.value.status == 403 and len(calls) == 1
