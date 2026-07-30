"""
Automatic Block Conditions.

These categories are hard-blocked regardless of risk score — if any of
these patterns match, the request never reaches the LLM. This module is a
lightweight keyword/pattern reference layer; a production deployment should
back it with a dedicated trust & safety classifier (and, for the child
safety category specifically, specialized detection systems rather than a
public keyword list — intentionally not enumerated here).
"""
import re

_CATEGORIES = {
    "Malware / Exploit Generation": [
        r"write (a |some )?(malware|ransomware|keylogger|computer virus)",
        r"create (a |an )?(ransomware|worm|trojan|rootkit)",
        r"(generate|write) (a |an )?(remote |working )?exploit",
        r"(sql|command) injection payload",
        r"reverse shell (script|payload|code)",
        r"zero-day exploit",
    ],
    "Credential Theft": [
        r"steal (someone'?s |a |their )?(password|credentials|credit card)",
        r"phishing (email|page|site|kit) (for|to)",
        r"crack (a |someone'?s )?password",
        r"brute[- ]force (a |someone'?s )?(password|login|account)",
    ],
    "Illegal Activity / Violence": [
        r"how to (make|build|construct) (a |an )?(bomb|explosive|pipe bomb)",
        r"how to (build|acquire|make) (a |an )?(weapon|firearm) illegally",
        r"plan (a |an )?(terrorist attack|mass shooting|bombing)",
        r"synthesi[sz]e (a |an )?(nerve agent|chemical weapon|bioweapon)",
    ],
    "Self-Harm Instructions": [
        r"(how to|ways to|methods to) (kill myself|commit suicide|end my life)",
        r"(most effective|lethal) (way|method) to (self-harm|hurt myself)",
    ],
    "Identity Theft / Financial Fraud": [
        r"(commit|help me commit) (identity theft|financial fraud|credit card fraud)",
        r"create (a |an )?fake (id|passport|identity) to (defraud|scam)",
    ],
    "Nexora Self-Manipulation": [
        r"ignore (all|any)? ?(previous|prior|above) instructions",
        r"reveal (your|the) (system prompt|hidden instructions)",
        r"disable (your|the) (safety|security) (filters|checks)",
    ],
}

_COMPILED = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in _CATEGORIES.items()
}


def check_auto_block(text: str):
    """Return (blocked: bool, category: str | None)."""
    for category, patterns in _COMPILED.items():
        for pattern in patterns:
            if pattern.search(text):
                return True, category
    return False, None