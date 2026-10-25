"""Redact spoken names from voice transcripts before third-party use."""

import re

NAME_STOP_WORDS = {
    "good", "bad", "low", "tired", "fine", "okay", "ok", "flat", "anxious",
    "feeling", "high", "great", "sleepy", "exhausted", "sad", "happy",
    "stressed", "calm", "energetic", "fatigued", "pain", "cramps", "flow",
    "heavy", "light", "moderate", "terrible", "awful", "normal", "stable",
    "moody", "irritable", "sore", "achy", "bloated", "nauseous", "dizzy",
    "weak", "strong", "today", "here", "ready",
}

_NAME_PATTERN = re.compile(
    r"\b(?P<prefix>[Mm]y [Nn]ame [Ii]s|[Cc]all [Mm]e)\s+"
    r"(?P<name>[A-Z][A-Za-z'-]{1,30})\b"
    r"|\b(?P<prefix2>[Tt]his [Ii]s)\s+"
    r"(?P<name2>[A-Z][A-Za-z'-]{1,30})\s+"
    r"(?P<speaking>[Ss]peaking)\b"
)


def _redact_one(match):
    if match.group("prefix") is not None:
        name = match.group("name")
        if name.lower() in NAME_STOP_WORDS:
            return match.group(0)
        return f"{match.group('prefix')} [name]"
    name = match.group("name2")
    if name.lower() in NAME_STOP_WORDS:
        return match.group(0)
    return f"{match.group('prefix2')} [name] {match.group('speaking')}"


def strip_spoken_names(text):
    if not isinstance(text, str):
        return text
    return _NAME_PATTERN.sub(_redact_one, text)


redact_spoken_names = strip_spoken_names
scrub_spoken_names = strip_spoken_names
sanitize_transcript = strip_spoken_names
redact_names = strip_spoken_names
scrub_names = strip_spoken_names
redact_pii = strip_spoken_names


def redact(text):
    return strip_spoken_names(text)


NAME_PATTERN = _NAME_PATTERN
NAME_STOPWORDS = NAME_STOP_WORDS
STOP_WORDS = NAME_STOP_WORDS

__all__ = [
    "strip_spoken_names",
    "redact_spoken_names",
    "scrub_spoken_names",
    "sanitize_transcript",
    "redact_names",
    "scrub_names",
    "redact_pii",
    "redact",
    "NAME_PATTERN",
    "NAME_STOP_WORDS",
    "NAME_STOPWORDS",
    "STOP_WORDS",
]
