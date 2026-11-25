"""Decode and inspect public topic HTML; this module does not make requests."""

from email.message import Message
import json
from pathlib import Path

from bs4 import BeautifulSoup


def parse_topic(response):
    """Use the HTTP charset when declared; otherwise let BeautifulSoup inspect bytes.

    A declared, invalid byte sequence raises an error rather than replacing text.
    Callers must independently check permissions and privacy before saving text.
    """
    response.raise_for_status()
    header = Message()
    header['content-type'] = response.headers.get('content-type', '')
    charset = header.get_content_charset()
    content = response.content.decode(charset, errors='strict') if charset else response.content
    soup = BeautifulSoup(content, 'html.parser')
    title = soup.select_one('h1')
    messages = soup.select('.post-message.topic-post__message')
    if not title or not messages:
        raise ValueError('Topic title or messages not found')
    # Links and quoted blocks may contain usernames or profile details. Exclude
    # them from the candidate text, which still needs individual privacy review.
    for block in messages:
        for element in block.select('blockquote, .quote, .quoted, a, script, style, img'):
            element.decompose()
    return title.get_text(' ', strip=True), [block.get_text(' ', strip=True) for block in messages]


def write_jsonl_new(path, records):
    """Create a new file only; never replace previously collected data."""
    serialized = ''.join(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n' for record in records)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8', newline='\n') as out:
        out.write(serialized)
