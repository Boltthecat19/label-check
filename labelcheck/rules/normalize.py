"""Text normalization shared by every rule.

Two levels: normalize_keep_case flattens whitespace and unicode punctuation but keeps
case, for checks where case matters (the government warning header). normalize goes
further: uppercase and strip everything except letters, digits, percent, and periods.
"""

import re
import unicodedata

_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}


def normalize_keep_case(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    for k, v in _QUOTES.items():
        text = text.replace(k, v)
    return re.sub(r"\s+", " ", text).strip()


def normalize(text: str) -> str:
    text = normalize_keep_case(text).upper()
    text = re.sub(r"[^A-Z0-9%.\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()
