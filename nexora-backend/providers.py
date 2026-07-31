"""
providers.py — real model calls, replacing Ollama.

Text chat priority:  Groq (free, very fast)  ->  OpenRouter (free-tier models)
                      ->  OpenAI (optional, requires a paid key)  ->  local template

Vision (image understanding):  Groq vision model  ->  OpenRouter free vision model
                                ->  apologetic fallback text

Voice transcription:  Groq Whisper (free, fast)  ->  Hugging Face Whisper  ->  None

Image generation:  Hugging Face Inference API (Stable Diffusion family)

Every function here is defensive: missing keys, network errors, timeouts, and
provider-side errors are all caught and turned into a graceful fallback
instead of a 500. Nothing here ever raises out to the route handlers.

Get free keys:
  Groq          -> https://console.groq.com/keys           (free, fast, generous limits)
  OpenRouter    -> https://openrouter.ai/keys               (free-tier ":free" models)
  Hugging Face  -> https://huggingface.co/settings/tokens   (free "read" token)
  OpenAI        -> https://platform.openai.com/api-keys     (NOT free — paid, optional)

Note: there is no free/public "ChatGPT" API — OpenAI's real API (GPT-4o etc.)
requires a billed account. Groq + OpenRouter + Hugging Face cover the "fast
and free" requirement instead; OpenAI is wired in as an optional extra if you
ever add a paid key later.
"""

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import llm_client  # local template fallback

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
HF_API_KEY = os.getenv("HF_API_KEY", "").strip()

GROQ_BASE = "https://api.groq.com/openai/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENAI_BASE = "https://api.openai.com/v1"
HF_BASE = "https://api-inference.huggingface.co/models"

GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
OPENROUTER_TEXT_MODEL = os.getenv("OPENROUTER_TEXT_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", "meta-llama/llama-3.2-11b-vision-instruct:free")
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
HF_WHISPER_MODEL = os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3")

TIMEOUT = 25
SYSTEM_PROMPT = (
    "You are Nexora, an enterprise AI assistant reached through a secure gateway. "
    "Every message you see has already been screened for prompt injection, jailbreak "
    "attempts, and sensitive data by an upstream security layer, and anything sensitive "
    "has been masked as [MASKED]. Answer helpfully and directly. Never claim to be a "
    "different product. Do not narrate or mention the security screening in your answer "
    "— just answer the question."
)


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
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def chat_complete(masked_prompt: str, category: str) -> str:
    """Stage 12 — Forward to LLM. Tries providers in order, always returns text."""
    if GROQ_API_KEY:
        try:
            return _openai_style_chat(GROQ_BASE, GROQ_API_KEY, GROQ_TEXT_MODEL, masked_prompt)
        except Exception as e:
            print(f"[providers] Groq text failed: {e}")

    if OPENROUTER_API_KEY:
        try:
            return _openai_style_chat(
                OPENROUTER_BASE, OPENROUTER_API_KEY, OPENROUTER_TEXT_MODEL, masked_prompt,
                extra_headers={"HTTP-Referer": "http://localhost", "X-Title": "Nexora Gateway"},
            )
        except Exception as e:
            print(f"[providers] OpenRouter text failed: {e}")

    if OPENAI_API_KEY:
        try:
            return _openai_style_chat(OPENAI_BASE, OPENAI_API_KEY, OPENAI_TEXT_MODEL, masked_prompt)
        except Exception as e:
            print(f"[providers] OpenAI text failed: {e}")

    return llm_client.template_fallback(category)


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
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def vision_complete(prompt: str, image_b64: str, mime: str) -> str:
    """Image understanding for uploaded images. Always returns text."""
    if GROQ_API_KEY:
        try:
            return _openai_style_vision(GROQ_BASE, GROQ_API_KEY, GROQ_VISION_MODEL, prompt, image_b64, mime)
        except Exception as e:
            print(f"[providers] Groq vision failed: {e}")

    if OPENROUTER_API_KEY:
        try:
            return _openai_style_vision(
                OPENROUTER_BASE, OPENROUTER_API_KEY, OPENROUTER_VISION_MODEL, prompt, image_b64, mime,
                extra_headers={"HTTP-Referer": "http://localhost", "X-Title": "Nexora Gateway"},
            )
        except Exception as e:
            print(f"[providers] OpenRouter vision failed: {e}")

    return ("I received the image, but no vision-capable model provider is configured. "
            "Add GROQ_API_KEY or OPENROUTER_API_KEY to your `.env` to enable image understanding.")


def transcribe_audio(file_bytes: bytes, filename: str, mime: str) -> str:
    """Voice input -> text. Returns '' if nothing is configured or every provider fails."""
    if GROQ_API_KEY:
        try:
            files = {"file": (filename, file_bytes, mime)}
            data = {"model": GROQ_WHISPER_MODEL}
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            r = requests.post(f"{GROQ_BASE}/audio/transcriptions", files=files, data=data,
                               headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json().get("text", "").strip()
        except Exception as e:
            print(f"[providers] Groq transcription failed: {e}")

    if HF_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": mime or "audio/webm"}
            r = requests.post(f"{HF_BASE}/{HF_WHISPER_MODEL}", data=file_bytes, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            result = r.json()
            return (result.get("text") or "").strip() if isinstance(result, dict) else ""
        except Exception as e:
            print(f"[providers] Hugging Face transcription failed: {e}")

    return ""


def generate_image(prompt: str):
    """Text -> image bytes (PNG) via Hugging Face. Returns None on any failure."""
    if not HF_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        r = requests.post(f"{HF_BASE}/{HF_IMAGE_MODEL}", headers=headers,
                           json={"inputs": prompt}, timeout=60)
        if r.status_code == 503:
            # Model is cold-starting on HF's shared infra — ask the caller to retry shortly.
            print(f"[providers] HF image model warming up: {r.json()}")
            return None
        r.raise_for_status()
        if r.headers.get("content-type", "").startswith("image/"):
            return r.content
        print(f"[providers] HF image response was not an image: {r.text[:200]}")
        return None
    except Exception as e:
        print(f"[providers] HF image generation failed: {e}")
        return None


def providers_status() -> dict:
    return {
        "text": "groq" if GROQ_API_KEY else "openrouter" if OPENROUTER_API_KEY else "openai" if OPENAI_API_KEY else "template-fallback",
        "vision": "groq" if GROQ_API_KEY else "openrouter" if OPENROUTER_API_KEY else "unavailable",
        "voice": "groq" if GROQ_API_KEY else "huggingface" if HF_API_KEY else "unavailable",
        "image_generation": "huggingface" if HF_API_KEY else "unavailable",
    }
