"""
Stage 4 — Prompt Injection Detection.

Pattern-based heuristics for instruction override / system-prompt-extraction
style attacks. Each match contributes weight toward the injection score.
"""
import re

_PATTERNS = [
    (r"ignore (all|any)? ?(previous|prior|above|earlier) instructions", 40),
    (r"disregard (the )?(above|previous|prior) (instructions|rules)", 40),
    (r"forget (your|all|previous) (instructions|rules|guidelines)", 35),
    (r"(reveal|show|print|output) (your|the) (system prompt|hidden prompt|instructions)", 40),
    (r"what (are|were) your (initial|original|system) instructions", 35),
    (r"you are now (in )?(developer|debug|god|admin) mode", 35),
    (r"pretend (you|that you) (are|have) no (rules|restrictions|guidelines)", 35),
    (r"override (your|the) (guidelines|rules|restrictions|safety)", 40),
    (r"bypass (your|the) (safety|security|filters|restrictions|guardrails)", 40),
    (r"act as (if )?(you (are|were) )?(an? )?(unrestricted|unfiltered|jailbroken)", 35),
    (r"repeat (the|your) (text|words|instructions) above", 25),
    (r"this is a (test|simulation)[,.]? (ignore|disregard)", 30),
    (r"\bsystem prompt\b", 15),
    (r"\bdeveloper (prompt|instructions)\b", 15),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS]


def detect_injection(text: str):
    """Return (detected: bool, score: int 0-100, matched: list[str])."""
    score = 0
    matched = []
    for pattern, weight in _COMPILED:
        if pattern.search(text):
            score += weight
            matched.append(pattern.pattern)
    score = min(score, 100)
    return score >= 30, score, matched