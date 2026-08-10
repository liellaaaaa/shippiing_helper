"""Text sanitization utilities — strip Unicode surrogates from external data."""

import re

# Surrogate code points: U+D800 – U+DFFF (not valid in UTF-8)
_SURROGATE_RE = re.compile(r'[\ud800-\udfff]')


def strip_surrogates(text: str) -> str:
    """Remove all Unicode surrogate characters (U+D800-U+DFFF) from text.

    These code points are invalid in UTF-8 and will crash json.dumps().
    They can appear when reading .xls files via xlrd (UTF-16LE unpaired
    surrogates) or from corrupt PDF CMap tables.
    """
    return _SURROGATE_RE.sub('', text)


def sanitize_text(text: str) -> str:
    """Sanitize text from external sources: strip surrogates and normalize."""
    return strip_surrogates(text)
