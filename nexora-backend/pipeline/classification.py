"""
Stage 2 — Prompt Classification.
Stage 3 — Intent Detection.

Lightweight keyword-weighted classifier. Swap this for an embedding-based
or fine-tuned classifier in production.
"""
import re

_CATEGORY_KEYWORDS = {
    "Programming": ["code", "function", "bug", "python", "javascript", "typescript",
                    "compile", "stack trace", "api", "repository", "debug", "class ",
                    "variable", "algorithm"],
    "Mathematics": ["solve", "equation", "integral", "derivative", "theorem", "proof",
                    "calculate", "matrix", "probability"],
    "Research": ["research", "study", "paper", "literature review", "survey", "hypothesis"],
    "Medical": ["symptom", "diagnosis", "medication", "dosage", "treatment", "patient",
                "disease", "prescription"],
    "Legal": ["contract", "lawsuit", "liability", "clause", "compliance", "regulation",
              "terms of service", "nda"],
    "Education": ["explain", "teach me", "how does", "what is", "eli5", "homework", "lesson"],
    "Business": ["revenue", "marketing", "strategy", "pitch deck", "roadmap", "budget",
                 "quarter", "kpi"],
    "Creative": ["poem", "story", "write a song", "screenplay", "creative", "fiction",
                 "haiku", "lyrics"],
    "Image": ["generate an image", "draw", "picture of", "illustration"],
    "Voice": ["transcribe", "voice memo", "audio", "speech to text"],
    "File": ["this document", "this pdf", "this spreadsheet", "attached file", "uploaded file"],
    "Code Execution": ["run this code", "execute this script", "output of this program"],
    "Security": ["security policy", "access control", "encryption", "firewall", "auth"],
    "Cybersecurity": ["vulnerability", "penetration test", "cve", "exploit", "malware",
                       "threat actor", "incident response"],
}


def classify(text: str, injection: bool, jailbreak: bool, pii_found: bool):
    if injection or jailbreak:
        return "Sensitive"
    lower = text.lower()
    scores = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score:
            scores[category] = score
    if pii_found and not scores:
        return "Sensitive"
    if not scores:
        return "Conversation"
    return max(scores, key=scores.get)


def detect_intent(category: str, injection: bool, jailbreak: bool):
    if jailbreak:
        return "Jailbreak Attempt"
    if injection:
        return "Prompt Injection Attempt"
    intent_map = {
        "Programming": "Code Generation",
        "Mathematics": "Problem Solving",
        "Research": "Information Retrieval",
        "Medical": "Medical Information Request",
        "Legal": "Legal Information Request",
        "Education": "Explanation Request",
        "Business": "Business Assistance",
        "Creative": "Creative Generation",
        "Image": "Image Generation",
        "Voice": "Voice Processing",
        "File": "Document Analysis",
        "Code Execution": "Code Execution Request",
        "Security": "Security Guidance",
        "Cybersecurity": "Cybersecurity Guidance",
        "Sensitive": "Sensitive Request",
    }
    return intent_map.get(category, "General Conversation")
