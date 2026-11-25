"""Conservative, offline gate for candidate market signals.

This module does not fetch or persist content. Human evidence review and source
permission checks remain mandatory; classification is not inferred from keywords.
"""
from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from urllib.parse import urlsplit


class ContentType(str, Enum):
    HOMEPAGE_METADATA = 'HomepageMetadata'
    MARKETING = 'MarketingContent'
    NAVIGATION = 'NavigationContent'
    USER_REQUEST = 'UserRequest'
    PROJECT_LISTING = 'ProjectListing'
    PROJECT_DESCRIPTION = 'ProjectDescription'
    CUSTOMER_REVIEW = 'CustomerReview'
    COMPLAINT = 'Complaint'
    QUESTION = 'Question'
    DISCUSSION = 'Discussion'
    FEATURE_REQUEST = 'FeatureRequest'
    JOB_POSTING = 'JobPosting'
    OTHER = 'Other'


SIGNAL_TYPES = frozenset({ContentType.USER_REQUEST, ContentType.PROJECT_LISTING,
    ContentType.PROJECT_DESCRIPTION, ContentType.CUSTOMER_REVIEW,
    ContentType.COMPLAINT, ContentType.QUESTION, ContentType.DISCUSSION,
    ContentType.FEATURE_REQUEST, ContentType.JOB_POSTING})


@dataclass(frozen=True)
class Candidate:
    source: str
    source_url: str
    content_type: ContentType
    original_text: str
    evidence_reviewed: bool = False


def assess(candidate, seen=None):
    """Return (accepted, reason); never mutate text, and fail closed.

    evidence_reviewed is a trusted review decision, not proof of permission or
    privacy. Deduplication stores a normalized text hash only after acceptance.
    """
    if not isinstance(candidate, Candidate) or not isinstance(candidate.content_type, ContentType):
        return False, 'invalid_record'
    if not isinstance(candidate.source, str) or not candidate.source.strip() or not isinstance(candidate.source_url, str) or not candidate.source_url.startswith('https://'):
        return False, 'missing_source'
    try:
        parsed = urlsplit(candidate.source_url)
        if not parsed.hostname or parsed.username or parsed.password or parsed.path in ('', '/'):
            return False, 'homepage_or_invalid_url'
    except ValueError:
        return False, 'missing_source'
    if candidate.content_type not in SIGNAL_TYPES:
        return False, 'non_signal_content_type'
    if not isinstance(candidate.original_text, str) or not candidate.original_text.strip():
        return False, 'empty_content'
    if candidate.evidence_reviewed is not True:
        return False, 'requires_evidence_review'
    normalized = re.sub(r'\s+', ' ', candidate.original_text).strip().casefold()
    fingerprint = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    if seen is not None:
        if fingerprint in seen:
            return False, 'duplicate'
        seen.add(fingerprint)
    return True, 'reviewed_signal'
