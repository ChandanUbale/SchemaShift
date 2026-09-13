"""
services/recommendation/ai_explainer.py — Optional Ollama LLM explanation layer.

IMPORTANT: This module is OPTIONAL and NEVER blocks the wizard.
  - If USE_LOCAL_LLM=false (default): returns None immediately.
  - If Ollama is unavailable / times out / errors: returns None.
  - The router always falls back to template text from reason codes.

The rule engine (scoring_engine.py) makes the decision.
Ollama only rewrites the reasons as nicer prose.
"""

import httpx
from app.config import settings


PROMPT_TEMPLATE = """
You are a database migration advisor. Given these rule-based reasons for recommending
a {target_type} database model, write a concise 2–3 sentence explanation in plain English.

Reasons:
{reasons}

Keep the explanation factual, brief, and non-technical enough for a business stakeholder.
"""


async def explain(recommendation: dict) -> str | None:
    """
    Optionally call Ollama to generate a natural-language explanation.

    Returns:
        str — Ollama-generated prose  (if enabled and available)
        None — if USE_LOCAL_LLM=false or Ollama call fails
    """
    if not settings.use_local_llm or not settings.ollama_model:
        return None

    reasons_text = "\n".join(
        f"- {r['message']}" for r in recommendation.get("reasons", [])
    )
    prompt = PROMPT_TEMPLATE.format(
        target_type=recommendation.get("target_type", ""),
        reasons=reasons_text,
    )

    # TODO: call Ollama /api/generate or OpenAI-compatible /v1/chat/completions
    #       with a short timeout (e.g. 5s). Return None on timeout or error.
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/chat/completions",
                json={
                    "model": settings.ollama_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        # Never block the wizard on an LLM failure
        return None
