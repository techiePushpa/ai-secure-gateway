"""
Stage 9 — Risk Scoring.

Combines every upstream signal into a single 0-100 risk score and a
categorical risk level.
"""

_LEVEL_THRESHOLDS = [
    (20, "SAFE"),
    (40, "LOW"),
    (60, "MEDIUM"),
    (80, "HIGH"),
    (101, "CRITICAL"),
]


def level_for_score(score: int) -> str:
    for threshold, label in _LEVEL_THRESHOLDS:
        if score < threshold:
            return label
    return "CRITICAL"


def compute_risk(auto_blocked: bool, injection_score: int, jailbreak_score: int,
                  pii_detected: list, category: str) -> int:
    if auto_blocked:
        return 97

    score = 0
    score += int(injection_score * 0.6)
    score += int(jailbreak_score * 0.6)
    score += min(len(pii_detected) * 8, 24)

    if category in ("Sensitive", "Cybersecurity", "Security"):
        score += 8

    return max(0, min(score, 100))