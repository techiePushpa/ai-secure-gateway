"""
Stage 12 — Forward to LLM.

This is a MOCK client so the gateway is runnable and demoable without any
model credentials. Swap `generate()` for a real call (Ollama, an OpenAI/
Anthropic-compatible endpoint, etc.) when you're ready to connect a real
downstream model. The gateway logic in main.py does not need to change —
only this function.
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
    "Request validated and processed. Here's a response based on what you asked — let me know if you'd like it reformatted or expanded.",
]


def generate(masked_prompt: str, category: str) -> str:
    """Mock generation. Replace with a real downstream model call."""
    options = _TEMPLATES_BY_CATEGORY.get(category, _DEFAULT)
    return random.choice(options)