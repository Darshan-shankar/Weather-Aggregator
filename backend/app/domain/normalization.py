"""City-name normalisation used as the lookup key for aliases."""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_city(name: str) -> str:
    """Case-fold, strip accents and collapse whitespace.

    "  Bangalore " -> "bangalore"
    """
    decomposed = unicodedata.normalize("NFKD", name.strip())
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _WHITESPACE.sub(" ", without_marks).casefold()
