"""
Stage 5 — Jailbreak Detection.

Detects well-known jailbreak framing techniques (persona overrides,
"no restrictions" framings, hypothetical/roleplay wrappers used to
launder disallowed requests, etc).
"""
import re

_PATTERNS = [
    (r"\bDAN\b", 45),
    (r"do anything now", 45),
    (r"\bjailbreak(ed|ing)?\b", 40),
    (r"no (rules|restrictions|limitations|filters) (apply|whatsoever)", 40),
    (r"without any (restrictions|limitations|rules|filters)", 35),
    (r"\bunfiltered (mode|version|ai)\b", 35),
    (r"\bunlocked mode\b", 35),
    (r"hypothetically,? if you had no (rules|restrictions|guidelines)", 35),
    (r"pretend (this is|we('| a)re in) a (world|universe) (with|without) no rules", 35),
    (r"respond (only )?as (if )?(your|the) (guidelines|filters|rules) (don'?t|do not) (apply|exist)", 35),
    (r"opposite day", 20),
    (r"evil (confidant|twin|version of yourself)", 30),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS]


def detect_jailbreak(text: str):
    """Return (detected: bool, score: int 0-100, matched: list[str])."""
    score = 0
    matched = []
    for pattern, weight in _COMPILED:
        if pattern.search(text):
            score += weight
            matched.append(pattern.pattern)
    score = min(score, 100)
    return score >= 30, score, matched