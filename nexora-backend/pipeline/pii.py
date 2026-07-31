"""
Stage 6/7 — PII Detection & Privacy Masking.

Regex-based detection for common sensitive data types. This is a reference
implementation: real deployments should layer in a proper NER/PII model
(e.g. Presidio) for recall beyond pattern matching.
"""
import re

PII_PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+"),
    "PHONE": re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"),
    "CREDIT_CARD": re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[ -]?\d{4}[ -]?\d{4}[ -]?\d{1,4}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "API_KEY": re.compile(r"\b(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z\-_]{35})\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN(?: RSA| EC| OPENSSH)? PRIVATE KEY-----[\s\S]+?-----END(?: RSA| EC| OPENSSH)? PRIVATE KEY-----"),
    "PASSWORD": re.compile(r"(?i)\bpassword\s*[:=]\s*\S+"),
    "BANK_ACCOUNT": re.compile(r"(?i)\baccount\s*(?:no\.?|number)?\s*[:#]?\s*\d{8,18}\b"),
}

# Order matters: check the more specific patterns before the broader ones
_ORDER = ["PRIVATE_KEY", "JWT", "API_KEY", "EMAIL", "CREDIT_CARD", "SSN",
          "PAN", "AADHAAR", "BANK_ACCOUNT", "PASSWORD", "PHONE"]


def detect_pii(text: str):
    """Return a list of {"type", "count"} for every PII category found."""
    found = []
    for key in _ORDER:
        matches = PII_PATTERNS[key].findall(text)
        if matches:
            found.append({"type": key, "count": len(matches)})
    return found


def mask_pii(text: str):
    """Replace every detected PII span with [MASKED]. Returns (masked_text, detected_list)."""
    masked = text
    detected = []
    for key in _ORDER:
        pattern = PII_PATTERNS[key]
        count = len(pattern.findall(masked))
        if count:
            masked = pattern.sub("[MASKED]", masked)
            detected.append({"type": key, "count": count})
    return masked, detected
