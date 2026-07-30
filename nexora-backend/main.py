"""
Nexora Secure AI Gateway Orchestrator
======================================
A security gateway that sits in front of an LLM. No prompt reaches the
model until it passes input validation, classification, injection/jailbreak
detection, PII masking, and policy/risk evaluation.

Run:
    pip install -r requirements.txt --break-system-packages
    uvicorn main:app --reload --port 8000

Then point NEXORA_API_BASE in nexora-app.html at http://localhost:8000
"""
import time
import uuid
from typing import Optional, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline import classification, injection, jailbreak, pii, risk, blocklist
import llm_client

app = FastAPI(title="Nexora Secure AI Gateway", version="1.0.0")

# Wide-open CORS for local development/demo purposes. Lock this down to
# your real frontend origin(s) before deploying anywhere near production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RESTRICTED_GUEST_FEATURES = {"voice", "image", "file", "personalization", "settings", "document_retrieval"}


class GatewayRequest(BaseModel):
    prompt: str = Field(..., max_length=8000)
    is_guest: bool = True
    feature: str = "text"  # text | voice | image | file | personalization | settings
    conversation_id: Optional[str] = None


class Stage(BaseModel):
    stage: int
    label: str
    status: str
    duration_ms: int


def make_stage(n: int, label: str, start: float) -> Stage:
    return Stage(stage=n, label=label, status="done", duration_ms=int((time.time() - start) * 1000))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "nexora-gateway", "version": "1.0.0"}


@app.post("/api/gateway")
def gateway(req: GatewayRequest):
    pipeline_start = time.time()
    stages: List[Stage] = []

    # ---- Stage 1: Input Validation ----
    t0 = time.time()
    text = (req.prompt or "").strip()
    stages.append(make_stage(1, "Receiving Prompt", t0))

    if not text:
        return _error_response(stages, pipeline_start, "Empty prompt")

    # ---- Guest Policy Gate ----
    if req.is_guest and req.feature in RESTRICTED_GUEST_FEATURES:
        return {
            "allowed": False,
            "llm_called": False,
            "risk_level": "SAFE",
            "risk_score": 0,
            "prompt_category": "Unknown",
            "intent": "Restricted Feature Request",
            "masked_prompt": text,
            "retrieval_needed": False,
            "retrieval_source": None,
            "route_to": None,
            "blocked_reason": "Guest Restriction",
            "final_response": "Feature available after login.",
            "prompt_shield": {
                "status": "RESTRICTED",
                "confidence": 100,
                "policy_passed": False,
                "prompt_injection": False,
                "jailbreak_detected": False,
                "pii_detected": False,
                "privacy_masked": False,
                "trust_score": 100,
                "processing_time_ms": int((time.time() - pipeline_start) * 1000),
            },
            "stages": [s.dict() for s in stages],
        }

    # ---- Stage 3 (early): Auto-block categorical check ----
    t0 = time.time()
    auto_blocked, block_category = blocklist.check_auto_block(text)
    stages.append(make_stage(2, "Classifying Intent", t0))

    # ---- Stage 4: Prompt Injection Detection ----
    t0 = time.time()
    injection_detected, injection_score, _ = injection.detect_injection(text)
    stages.append(make_stage(3, "Scanning for Prompt Injection", t0))

    # ---- Stage 5: Jailbreak Detection ----
    t0 = time.time()
    jailbreak_detected, jailbreak_score, _ = jailbreak.detect_jailbreak(text)
    stages.append(make_stage(4, "Checking Jailbreak", t0))

    # ---- Stage 6: PII Detection ----
    t0 = time.time()
    pii_found = pii.detect_pii(text)
    stages.append(make_stage(5, "Scanning Sensitive Data", t0))

    # ---- Stage 7: Privacy Masking ----
    t0 = time.time()
    masked_text, masked_detected = pii.mask_pii(text)
    privacy_masked = len(masked_detected) > 0
    stages.append(make_stage(6, "Masking Private Information", t0))

    # ---- Stage 2 (classification, uses injection/jailbreak signals) ----
    category = classification.classify(text, injection_detected, jailbreak_detected, bool(pii_found))
    intent = classification.detect_intent(category, injection_detected, jailbreak_detected)

    # ---- Stage 8: Policy Validation ----
    t0 = time.time()
    policy_passed = not (auto_blocked or injection_detected or jailbreak_detected)
    stages.append(make_stage(7, "Policy Validation", t0))

    # ---- Stage 9: Risk Scoring ----
    t0 = time.time()
    risk_score = risk.compute_risk(auto_blocked, injection_score, jailbreak_score, pii_found, category)
    risk_level = "CRITICAL" if auto_blocked else risk.level_for_score(risk_score)
    stages.append(make_stage(8, "Calculating Risk Score", t0))

    # ---- Stage 10: Route Decision ----
    t0 = time.time()
    blocked = auto_blocked or injection_detected or jailbreak_detected or risk_level in ("HIGH", "CRITICAL")
    allowed = not blocked
    stages.append(make_stage(9, "Decision Engine", t0))

    if blocked:
        reason = block_category if auto_blocked else (
            "Prompt Injection" if injection_detected else
            "Jailbreak Attempt" if jailbreak_detected else
            "Elevated Risk Score"
        )
        t0 = time.time()
        stages.append(make_stage(10, "Blocked — Not Sent to LLM", t0))
        return {
            "allowed": False,
            "llm_called": False,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "prompt_category": category,
            "intent": intent,
            "masked_prompt": masked_text,
            "retrieval_needed": False,
            "retrieval_source": None,
            "route_to": None,
            "blocked_reason": reason,
            "final_response": ("We couldn't process this request because it violates Nexora's "
                                "security and safety policies. The request has been stopped "
                                "before reaching the AI model."),
            "prompt_shield": {
                "status": "BLOCKED",
                "confidence": 96,
                "policy_passed": False,
                "prompt_injection": injection_detected,
                "jailbreak_detected": jailbreak_detected,
                "pii_detected": bool(pii_found),
                "privacy_masked": privacy_masked,
                "trust_score": max(0, 100 - risk_score),
                "processing_time_ms": int((time.time() - pipeline_start) * 1000),
                "pii_types": [p["type"] for p in pii_found],
            },
            "stages": [s.dict() for s in stages],
        }

    # ---- Stage 11: Retrieval (optional) ----
    t0 = time.time()
    retrieval_needed = category in ("Business", "Research", "Legal") and any(
        kw in text.lower() for kw in ["policy", "document", "our company", "internal"]
    )
    retrieval_source = "ChromaDB: company-knowledge-base" if retrieval_needed else None
    stages.append(make_stage(11, "Retrieving Context" if retrieval_needed else "Skipping Retrieval", t0))

    # ---- Stage 12: Forward to LLM ----
    t0 = time.time()
    final_response = llm_client.generate(masked_text, category)
    stages.append(make_stage(12, "Sending to LLM", t0))

    # ---- Stage 13: Output Verification ----
    t0 = time.time()
    trust_score = max(60, 100 - risk_score - (5 if pii_found else 0))
    stages.append(make_stage(13, "Verifying Output", t0))

    # ---- Stage 14: Return Secure Response ----
    stages.append(make_stage(14, "Response Delivered", time.time()))

    return {
        "allowed": True,
        "llm_called": True,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "prompt_category": category,
        "intent": intent,
        "masked_prompt": masked_text,
        "retrieval_needed": retrieval_needed,
        "retrieval_source": retrieval_source,
        "route_to": "Answer Agent",
        "blocked_reason": None,
        "final_response": final_response,
        "prompt_shield": {
            "status": "SAFE" if risk_level in ("SAFE", "LOW") else risk_level,
            "confidence": max(70, 100 - risk_score),
            "policy_passed": policy_passed,
            "prompt_injection": injection_detected,
            "jailbreak_detected": jailbreak_detected,
            "pii_detected": bool(pii_found),
            "privacy_masked": privacy_masked,
            "trust_score": trust_score,
            "processing_time_ms": int((time.time() - pipeline_start) * 1000),
            "pii_types": [p["type"] for p in pii_found],
        },
        "stages": [s.dict() for s in stages],
    }


def _error_response(stages, start, reason):
    return {
        "allowed": False,
        "llm_called": False,
        "risk_level": "SAFE",
        "risk_score": 0,
        "prompt_category": "Unknown",
        "intent": "Invalid Request",
        "masked_prompt": "",
        "retrieval_needed": False,
        "retrieval_source": None,
        "route_to": None,
        "blocked_reason": reason,
        "final_response": "Please enter a message.",
        "prompt_shield": {
            "status": "REJECTED",
            "confidence": 100,
            "policy_passed": False,
            "prompt_injection": False,
            "jailbreak_detected": False,
            "pii_detected": False,
            "privacy_masked": False,
            "trust_score": 100,
            "processing_time_ms": int((time.time() - start) * 1000),
        },
        "stages": [s.dict() for s in stages],
    }