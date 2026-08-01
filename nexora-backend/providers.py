"""
providers.py — real model calls, using your specified free-tier stack.

Text chat routing (by prompt category):
  Programming / Code Execution  -> Groq   : CODING_MODEL
  Research/Legal/Medical/Math/
  Security/Cybersecurity/Sensitive -> OpenRouter : REASONING_MODEL
  everything else               -> Groq   : CHAT_MODEL
  any of the above failing      -> OpenRouter : FALLBACK_MODEL -> OpenAI (optional) -> local template

Vision (image understanding):   OpenRouter VISION_MODEL -> Groq vision model -> apology text
Voice transcription:            Hugging Face STT_MODEL -> Groq Whisper -> ""
OCR (image -> text):            Hugging Face OCR_MODEL
Embeddings:                     Hugging Face EMBEDDING_MODEL
Image generation:               Hugging Face IMAGE_MODEL

Prompt Shield (ML-backed, layered on top of the regex pipeline in pipeline/):
  Prompt injection:  Hugging Face PROMPT_SHIELD_MODEL
  Toxicity:          Hugging Face TOXICITY_MODEL
  PII / NER:         Hugging Face PII_MODEL

Every function here is defensive — missing keys, timeouts, and provider
errors are caught and turned into a graceful fallback (or `None`), never a
crash. All three ML shield checks are skipped entirely (zero network calls)
if HF_API_KEY isn't set, so the regex-only pipeline keeps working exactly
as before with no latency cost.

Free keys:
  Groq          -> https://console.groq.com/keys
  OpenRouter    -> https://openrouter.ai/keys
  Hugging Face  -> https://huggingface.co/settings/tokens
  OpenAI (optional, NOT free) -> https://platform.openai.com/api-keys
"""

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import llm_client  # local template fallback for text chat

# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
HF_API_KEY = os.getenv("HF_API_KEY", "").strip()

GROQ_BASE = "https://api.groq.com/openai/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENAI_BASE = "https://api.openai.com/v1"
HF_BASE = "https://api-inference.huggingface.co/models"
OR_HEADERS = {"HTTP-Referer": "http://localhost", "X-Title": "Nexora Gateway"}

# ---------------------------------------------------------------------------
# Model configuration — matches the .env keys you specified
# ---------------------------------------------------------------------------
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")                       # Groq
CODING_MODEL = os.getenv("CODING_MODEL", "llama-3.3-70b-versatile")                   # Groq
REASONING_MODEL = os.getenv("REASONING_MODEL", "deepseek/deepseek-r1:free")           # OpenRouter
VISION_MODEL = os.getenv("VISION_MODEL", "qwen/qwen2.5-vl:free")                      # OpenRouter
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "openrouter/free")                       # OpenRouter
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")    # Groq (vision fallback)
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")                     # OpenAI (optional)

STT_MODEL = os.getenv("STT_MODEL", "openai/whisper-large-v3")                         # Hugging Face
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")              # Groq (voice fallback)
OCR_MODEL = os.getenv("OCR_MODEL", "microsoft/trocr-base-printed")                    # Hugging Face
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")              # Hugging Face
PROMPT_SHIELD_MODEL = os.getenv("PROMPT_SHIELD_MODEL", "ProtectAI/deberta-v3-base-prompt-injection-v2")
TOXICITY_MODEL = os.getenv("TOXICITY_MODEL", "unitary/toxic-bert")
PII_MODEL = os.getenv("PII_MODEL", "dslim/bert-base-NER")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "black-forest-labs/FLUX.1-dev")

TIMEOUT = 25
SHIELD_TIMEOUT = 8  # ML shield checks must stay fast — never block the pipeline for long

SYSTEM_PROMPT = (
    "You are Nexora, an enterprise AI assistant reached through a secure gateway. "
    "Every message you see has already been screened for prompt injection, jailbreak "
    "attempts, and sensitive data by an upstream security layer, and anything sensitive "
    "has been masked as [MASKED]. Answer helpfully and directly. Do not narrate or "
    "mention the security screening in your answer — just answer the question."
)

CODING_CATEGORIES = {"Programming", "Code Execution"}
REASONING_CATEGORIES = {"Research", "Legal", "Medical", "Mathematics", "Security", "Cybersecurity", "Sensitive"}


# ============================================================================
# TEXT CHAT
# ============================================================================

def _openai_style_chat(base_url, api_key, model, prompt, extra_headers=None):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 900,
    }
    r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def chat_complete(masked_prompt: str, category: str) -> str:
    """Stage 12 — Forward to LLM, routed by category, with cascading fallback."""
    if category in CODING_CATEGORIES and GROQ_API_KEY:
        try:
            return _openai_style_chat(GROQ_BASE, GROQ_API_KEY, CODING_MODEL, masked_prompt)
        except Exception as e:
            print(f"[providers] Groq coding model failed: {e}")

    if category in REASONING_CATEGORIES and OPENROUTER_API_KEY:
        try:
            return _openai_style_chat(OPENROUTER_BASE, OPENROUTER_API_KEY, REASONING_MODEL, masked_prompt, OR_HEADERS)
        except Exception as e:
            print(f"[providers] OpenRouter reasoning model failed: {e}")

    if GROQ_API_KEY:
        try:
            return _openai_style_chat(GROQ_BASE, GROQ_API_KEY, CHAT_MODEL, masked_prompt)
        except Exception as e:
            print(f"[providers] Groq chat model failed: {e}")

    if OPENROUTER_API_KEY:
        try:
            return _openai_style_chat(OPENROUTER_BASE, OPENROUTER_API_KEY, FALLBACK_MODEL, masked_prompt, OR_HEADERS)
        except Exception as e:
            print(f"[providers] OpenRouter fallback model failed: {e}")

    if OPENAI_API_KEY:
        try:
            return _openai_style_chat(OPENAI_BASE, OPENAI_API_KEY, OPENAI_TEXT_MODEL, masked_prompt)
        except Exception as e:
            print(f"[providers] OpenAI failed: {e}")

    return llm_client.template_fallback(category)


# ============================================================================
# VISION (image understanding)
# ============================================================================

def _openai_style_vision(base_url, api_key, model, prompt, image_b64, mime, extra_headers=None):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": prompt or "Describe this image in detail."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
            ]},
        ],
        "temperature": 0.4,
        "max_tokens": 700,
    }
    r = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def vision_complete(prompt: str, image_b64: str, mime: str) -> str:
    if OPENROUTER_API_KEY:
        try:
            return _openai_style_vision(OPENROUTER_BASE, OPENROUTER_API_KEY, VISION_MODEL, prompt, image_b64, mime, OR_HEADERS)
        except Exception as e:
            print(f"[providers] OpenRouter vision failed: {e}")

    if GROQ_API_KEY:
        try:
            return _openai_style_vision(GROQ_BASE, GROQ_API_KEY, GROQ_VISION_MODEL, prompt, image_b64, mime)
        except Exception as e:
            print(f"[providers] Groq vision failed: {e}")

    return ("I received the image, but no vision-capable provider is configured. "
            "Add OPENROUTER_API_KEY or GROQ_API_KEY to your `.env` to enable image understanding.")


# ============================================================================
# VOICE TRANSCRIPTION
# ============================================================================

def transcribe_audio(file_bytes: bytes, filename: str, mime: str) -> str:
    if HF_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": mime or "audio/webm"}
            r = requests.post(f"{HF_BASE}/{STT_MODEL}", data=file_bytes, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            result = r.json()
            text = (result.get("text") or "").strip() if isinstance(result, dict) else ""
            if text:
                return text
        except Exception as e:
            print(f"[providers] Hugging Face transcription failed: {e}")

    if GROQ_API_KEY:
        try:
            files = {"file": (filename, file_bytes, mime)}
            data = {"model": GROQ_WHISPER_MODEL}
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            r = requests.post(f"{GROQ_BASE}/audio/transcriptions", files=files, data=data, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json().get("text", "").strip()
        except Exception as e:
            print(f"[providers] Groq transcription failed: {e}")

    return ""


# ============================================================================
# OCR (image -> text)
# ============================================================================

def ocr_image(image_bytes: bytes, mime: str = "image/png"):
    if not HF_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": mime or "image/png"}
        r = requests.post(f"{HF_BASE}/{OCR_MODEL}", headers=headers, data=image_bytes, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "").strip()
        return ""
    except Exception as e:
        print(f"[providers] HF OCR failed: {e}")
        return None


# ============================================================================
# EMBEDDINGS  (stubbed retrieval hook — not yet wired to a vector store)
# ============================================================================

def get_embeddings(text: str):
    if not HF_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        r = requests.post(f"{HF_BASE}/{EMBEDDING_MODEL}", headers=headers, json={"inputs": text}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[providers] HF embeddings failed: {e}")
        return None


# ============================================================================
# IMAGE GENERATION
# ============================================================================

def generate_image(prompt: str):
    if not HF_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        r = requests.post(f"{HF_BASE}/{IMAGE_MODEL}", headers=headers, json={"inputs": prompt}, timeout=90)
        if r.status_code == 503:
            print(f"[providers] HF image model warming up: {r.text[:200]}")
            return None
        r.raise_for_status()
        if r.headers.get("content-type", "").startswith("image/"):
            return r.content
        print(f"[providers] HF image response was not an image: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[providers] HF image generation failed: {e}")
        return None


# ============================================================================
# ML-BACKED PROMPT SHIELD  (used by main.py to enhance the regex pipeline)
# ============================================================================

def _hf_classify(model: str, text: str):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    r = requests.post(f"{HF_BASE}/{model}", headers=headers, json={"inputs": text}, timeout=SHIELD_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data and isinstance(data[0], list):
        return data[0]
    return data


def ml_prompt_injection(text: str):
    """Returns {'detected': bool, 'score': int 0-100} or None if unavailable."""
    if not HF_API_KEY:
        return None
    try:
        results = _hf_classify(PROMPT_SHIELD_MODEL, text)
        top = max(results, key=lambda r: r["score"])
        is_injection = top["label"].upper() in ("INJECTION", "LABEL_1", "UNSAFE", "MALICIOUS") and top["score"] > 0.5
        return {"detected": is_injection, "score": round(top["score"] * 100)}
    except Exception as e:
        print(f"[providers] HF prompt-injection model failed: {e}")
        return None


def ml_toxicity(text: str):
    """Returns an int 0-100 toxicity score, or None if unavailable."""
    if not HF_API_KEY:
        return None
    try:
        results = _hf_classify(TOXICITY_MODEL, text)
        toxic = next((r for r in results if r["label"].lower() in ("toxic", "label_1")), None)
        score = toxic["score"] if toxic else 0
        return round(score * 100)
    except Exception as e:
        print(f"[providers] HF toxicity model failed: {e}")
        return None


def ml_pii_entities(text: str):
    """Returns a list of {'type','word'} named entities, or None if unavailable."""
    if not HF_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        r = requests.post(f"{HF_BASE}/{PII_MODEL}", headers=headers, json={"inputs": text}, timeout=SHIELD_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return [{"type": e.get("entity_group", e.get("entity", "ENTITY")), "word": e.get("word", "")} for e in data]
    except Exception as e:
        print(f"[providers] HF PII/NER model failed: {e}")
        return None


def providers_status() -> dict:
    return {
        "text": {
            "coding": CODING_MODEL if GROQ_API_KEY else None,
            "reasoning": REASONING_MODEL if OPENROUTER_API_KEY else None,
            "chat": CHAT_MODEL if GROQ_API_KEY else (FALLBACK_MODEL if OPENROUTER_API_KEY else "template-fallback"),
        },
        "vision": VISION_MODEL if OPENROUTER_API_KEY else (GROQ_VISION_MODEL if GROQ_API_KEY else "unavailable"),
        "voice": STT_MODEL if HF_API_KEY else (GROQ_WHISPER_MODEL if GROQ_API_KEY else "unavailable"),
        "ocr": OCR_MODEL if HF_API_KEY else "unavailable",
        "embeddings": EMBEDDING_MODEL if HF_API_KEY else "unavailable",
        "image_generation": IMAGE_MODEL if HF_API_KEY else "unavailable",
        "prompt_shield_ml": {
            "injection_model": PROMPT_SHIELD_MODEL if HF_API_KEY else None,
            "toxicity_model": TOXICITY_MODEL if HF_API_KEY else None,
            "pii_model": PII_MODEL if HF_API_KEY else None,
        } if HF_API_KEY else "regex-only (add HF_API_KEY to enable ML shield)",
    }
