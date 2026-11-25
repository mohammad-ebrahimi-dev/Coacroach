from market_tool.market_signals import Candidate, ContentType, assess


def test_rejects_homepage_and_navigation_even_if_reviewed():
    for kind in (ContentType.HOMEPAGE_METADATA, ContentType.MARKETING, ContentType.NAVIGATION, ContentType.OTHER):
        assert not assess(Candidate('s', 'https://example.test/project/1', kind, 'market leader', True))[0]


def test_request_requires_review_and_nonempty_text():
    assert assess(Candidate('s', 'https://example.test/project/1', ContentType.PROJECT_LISTING, 'Need an app'))[1] == 'requires_evidence_review'
    assert assess(Candidate('s', 'https://example.test/project/1', ContentType.USER_REQUEST, ' ', True))[1] == 'empty_content'
    assert assess(Candidate('s', 'https://example.test/project/1', ContentType.USER_REQUEST, 'Need an app', True))[0]


def test_deduplication_does_not_alter_original():
    seen = set()
    first = Candidate('s', 'https://example.test/project/1', ContentType.QUESTION, 'Need  help?', True)
    assert assess(first, seen)[0]
    assert assess(Candidate('s', 'https://example.test/2', ContentType.QUESTION, 'need help?', True), seen)[1] == 'duplicate'
    assert first.original_text == 'Need  help?'


def test_homepage_rejected_even_if_wrongly_marked_reviewed():
    c = Candidate('s', 'https://example.test/', ContentType.USER_REQUEST, 'A site slogan', True)
    assert assess(c)[1] == 'homepage_or_invalid_url'
