# Nexora Secure AI Gateway — Backend

A FastAPI implementation of the Nexora security pipeline, now wired to real
model providers instead of a local Ollama install. Every prompt is
classified, screened for prompt injection/jailbreak attempts, checked for
PII, masked, policy-validated, risk-scored — and only then sent to a model.
Guest-restricted features (voice, image, file, personalization, settings)
are rejected before the pipeline even runs.

```
nexora-backend/
├── main.py              FastAPI app + the 14-stage pipeline + /api routes
├── providers.py          Real model calls: Groq / OpenRouter / OpenAI / Hugging Face
├── llm_client.py         Local template fallback (used only if no provider is configured)
├── pipeline/
│   ├── blocklist.py       Automatic block conditions (hard stops)
│   ├── classification.py  Stage 2/3 — category + intent
│   ├── injection.py       Stage 4 — prompt injection detection
│   ├── jailbreak.py       Stage 5 — jailbreak detection
│   ├── pii.py              Stage 6/7 — PII detection + masking
│   └── risk.py             Stage 9 — risk scoring
├── requirements.txt
├── .env.example
└── README.md
```

## Why not Ollama

Ollama needs a model running locally on whatever machine hosts the backend,
which breaks the moment you move the project to another computer. Instead,
this now calls hosted, free-tier inference APIs over HTTPS — the backend has
no model weights of its own, so it runs the same anywhere.

**There's no free public "ChatGPT" API** — OpenAI's real API (GPT-4o, etc.)
needs a billed account. The free/fast options wired in here instead:

| Capability | Provider (in priority order) | Free? |
|---|---|---|
| Text chat | **Groq** → OpenRouter → OpenAI (optional) | Groq & OpenRouter: yes |
| Image understanding (upload) | **Groq vision model** → OpenRouter vision model | Yes |
| Voice transcription | **Groq Whisper** → Hugging Face Whisper | Yes |
| Image generation | **Hugging Face** (Stable Diffusion) | Yes (rate-limited) |

If nothing is configured, text chat falls back to a local template so the
gateway still runs — but vision, voice, and image generation have **no**
local fallback since they need a real model.

## 1. Get free API keys

- **Groq** (do this one first — covers text + vision + voice): https://console.groq.com/keys
- **Hugging Face** (needed for image generation): https://huggingface.co/settings/tokens → create a "Read" token
- Optional extras: **OpenRouter** (https://openrouter.ai/keys) as a text/vision fallback, **OpenAI** (https://platform.openai.com/api-keys) as a paid third fallback

## 2. Configure

```bash
cd nexora-backend
cp .env.example .env
# then open .env and paste in your keys
```

## 3. Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it's alive and see which providers it detected:
```bash
curl http://localhost:8000/api/health
```
```json
{"status":"ok","providers":{"text":"groq","vision":"groq","voice":"groq","image_generation":"huggingface"}}
```

Then open `nexora.html` → **Try Nexora**. The connection dot in the top nav
turns cyan ("Connected") once it can reach this server.

## API

### `POST /api/gateway`
Text chat — runs the full 14-stage pipeline, then calls `providers.chat_complete()`.
```jsonc
{ "prompt": "Write me a Python function to reverse a string", "is_guest": false, "feature": "text" }
```

### `POST /api/vision`  (multipart form)
Fields: `is_guest`, `question`, `image` (file). Guest-restricted.

### `POST /api/transcribe`  (multipart form)
Fields: `is_guest`, `audio` (file). Guest-restricted.

### `POST /api/generate-image`
```jsonc
{ "prompt": "a lighthouse at sunset, watercolor style", "is_guest": false }
```
Returns `image_base64` (PNG) on success. Guest-restricted.

### `GET /api/health`
Liveness + which providers are actually configured.

## In the frontend

- **Text**: same as before, now hits a real model when a key is set.
- **Image upload**: `+` → "Upload image (ask about it)" → pick a file → it's sent to `/api/vision` along with whatever you typed in the composer as the question.
- **Voice**: click the mic to start recording, click again to stop — the recording is sent to `/api/transcribe` and the text is dropped into the composer for you to review before sending.
- **Image generation**: `+` → "Generate an image" (or just type `/image <description>`) → sent to `/api/generate-image`, the result renders inline in the chat.

All three are guest-restricted client-side (locked icons, upsell modal) *and* server-side (the endpoints themselves reject `is_guest: true` regardless of what the frontend sends).

## Notes on the Hugging Face free tier

Shared/free Inference API models can take 10–30 seconds to "cold start" if
they haven't been called recently — the first image generation after a
while may fail with a warm-up message. Just try again a few seconds later.

## What's real vs. mocked now

- **Real**: input validation, classification, injection/jailbreak detection,
  PII detection + masking, automatic block rules, risk scoring, guest policy
  enforcement, the full stage pipeline — and now real text/vision/voice/image
  generation once you add keys.
- **Mocked (only without keys)**: text chat falls back to a canned template.
- **Stubbed**: retrieval — `retrieval_needed` is computed but nothing is
  queried from a real vector store yet.

## Before this touches real traffic

The injection/jailbreak/PII/blocklist detectors are regex and keyword
heuristics — solid for demoing the full pipeline honestly, not a substitute
for a trained safety classifier.
