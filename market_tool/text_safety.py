"""Best-effort minimization; not a guarantee of anonymization."""
import re

EMAIL = re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b', re.I)
PHONE = re.compile(r'(?<!\w)[+۰-۹٠-٩0-9][۰-۹٠-٩0-9() .-]{7,}[۰-۹٠-٩0-9](?!\w)')
HANDLE = re.compile(r'(?<!\w)@[\w.]+')
SENSITIVE = re.compile(r'باردار|حاملگ|سقط|نابارور|پزشک|دارو|بیمار|درمان|تشخیص|سلامت جنسی|تجاوز|خشونت|خودکشی|افسردگ|آزمایش خون|کودکم|فرزندم', re.I)


def clean_message(text, author_names=()):
    """Skip obvious sensitive posts; remove obvious contact data and handles.

    Names and sensitive disclosures cannot be detected reliably by regex.
    The result requires human privacy review before broader reuse.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    cleaned = EMAIL.sub('[redacted]', text)
    cleaned = PHONE.sub('[redacted]', cleaned)
    cleaned = HANDLE.sub('[redacted]', cleaned)
    for name in author_names:
        if len(name) >= 2:
            cleaned = re.sub(r'(?<!\w)' + re.escape(name) + r'(?!\w)', '[redacted]', cleaned)
    if SENSITIVE.search(cleaned):
        return None
    return cleaned.strip() or None
