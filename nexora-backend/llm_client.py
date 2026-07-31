"""
Local template fallback — used by providers.py only when no model provider
is configured/reachable (no API keys set, or every provider request fails).
This keeps the gateway demoable and non-crashing even with zero setup.
"""
import random

_TEMPLATES_BY_CATEGORY = {
    "Programming": [
        "Here's an approach:\n\n```python\ndef solve():\n    # implementation goes here\n    pass\n```\n\nWant me to fill in the implementation details, or adapt this to a specific language?",
    ],
    "Mathematics": [
        "Let's work through this step by step. Could you confirm the exact values involved so I give you an precise result rather than a general method?",
    ],
    "Business": [
        "Here's a structured way to think about this:\n\n- Define the goal in one sentence\n- List the two or three levers that actually move it\n- Pick the smallest experiment that tests the biggest lever first\n\nWant this turned into a one-page plan?",
    ],
    "Creative": [
        "Here's a first draft — happy to adjust tone, length, or style from here.",
    ],
    "Conversation": [
        "Got it — here's a direct answer, validated and ready to go. Let me know if you'd like more detail on any part of it.",
    ],
}

_DEFAULT = [
    "*(No model provider is configured — this is a placeholder response. Add GROQ_API_KEY, OPENROUTER_API_KEY, or OPENAI_API_KEY to your `.env` to get real answers.)*\n\nRequest validated and processed based on what you asked.",
]


def template_fallback(category: str) -> str:
    options = _TEMPLATES_BY_CATEGORY.get(category, _DEFAULT)
    return random.choice(options)


# Backwards-compatible alias (old code called llm_client.generate(...))
def generate(masked_prompt: str, category: str) -> str:
    return template_fallback(category)

