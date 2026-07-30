# Nexora Secure AI Gateway — Backend

A FastAPI implementation of the Nexora security pipeline: every prompt is
classified, screened for prompt injection/jailbreak attempts, checked for
PII, masked, policy-validated, risk-scored, and only then "forwarded" to a
model. Guest-restricted features (voice, image, file, personalization,
settings, document retrieval) are rejected before the pipeline even runs.

```
nexora-backend/
├── main.py              FastAPI app + the 14-stage pipeline orchestration
├── llm_client.py         Stage 12 — mock "Answer Agent" (swap for a real model)
├── pipeline/
│   ├── blocklist.py       Automatic block conditions (hard stops)
│   ├── classification.py  Stage 2/3 — category + intent
│   ├── injection.py       Stage 4 — prompt injection detection
│   ├── jailbreak.py       Stage 5 — jailbreak detection
│   ├── pii.py              Stage 6/7 — PII detection + masking
│   └── risk.py             Stage 9 — risk scoring
├── requirements.txt
└── README.md
```

## Run it

```bash
cd nexora-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it's alive:

```bash
curl http://localhost:8000/api/health
```

Then open `nexora-app.html` in a browser (same machine). It calls
`http://localhost:8000/api/gateway` automatically on every message and falls
back to a local, client-side demo pipeline if this server isn't reachable —
so the frontend still works standalone, but is materially smarter with the
backend running: real classification, real injection/jailbreak pattern
matching, real PII masking, and a risk score computed server-side instead of
randomized client-side.

## API

### `POST /api/gateway`

```jsonc
{
  "prompt": "Write me a Python function to reverse a string",
  "is_guest": false,
  "feature": "text"          // text | voice | image | file | personalization | settings
}
```

Returns the full pipeline result — `allowed`, `risk_level`, `risk_score`,
`prompt_category`, `masked_prompt`, `prompt_shield` (the metrics that drive
the Prompt Shield panel), and `stages` (a per-stage log you can use to
animate the pipeline in the UI).

### `GET /api/health`

Simple liveness check, used by the frontend to show Connected / Offline in
the top nav.

## What's real vs. mocked

- **Real**: input validation, classification, injection/jailbreak pattern
  detection, PII detection + masking, automatic block rules, risk scoring,
  guest policy enforcement, the full stage pipeline and timing.
- **Mocked**: `llm_client.generate()` returns a templated response instead
  of calling an actual model. Swap it for a real call (Ollama running
  Llama 3.1 8B Instruct, per the original spec, or any OpenAI/Anthropic-
  compatible endpoint) — nothing else in the pipeline needs to change.
- **Stubbed**: retrieval — `retrieval_needed` is computed, but nothing is
  actually queried from ChromaDB. Wire `pipeline/` up to a real vector store
  when you're ready.

## Before this touches real traffic

The injection/jailbreak/PII/blocklist detectors here are regex and keyword
heuristics — good enough to demo the full pipeline end-to-end honestly, not
a substitute for a trained safety classifier. Treat this as the orchestration
skeleton, not a certified security control.
