# app/gemini_client.py
from __future__ import annotations

import json
from typing import Any, Dict, List

import google.generativeai as genai

from .config import settings


# Configure Gemini client once at import
genai.configure(api_key=settings.gemini_api_key)

# Main text model instance
_model = genai.GenerativeModel(settings.gemini_model_name)


def call_gemini_json(system_instruction: str, user_prompt: str) -> Dict[str, Any]:
    """
    Helper to call Gemini and force a pure-JSON response.
    Returns a Python dict parsed from that JSON.
    """

    # We jam the "system" instruction into the same user message for simplicity.
    content = system_instruction.strip() + "\n\n" + user_prompt.strip()

    response = _model.generate_content(
        contents=[{"role": "user", "parts": [content]}],
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )

    # Depending on SDK version, the text may be under .text or .candidates[0].content.parts[0].text
    text = getattr(response, "text", None)
    if not text:
        # Fallback – be defensive
        try:
            # Newer SDKs sometimes expose this structure
            text = response.candidates[0].content.parts[0].text
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Could not extract JSON text from Gemini response: {e}") from e

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini did not return valid JSON: {e}\nRaw response:\n{text}") from e


def get_embedding(text: str) -> List[float]:
    """
    Get an embedding vector from Gemini embedding model.

    The google-generativeai SDK has changed return shapes across versions, so this
    function is defensive and handles dict, object, and list responses.
    """
    embed_resp = genai.embed_content(
        model=settings.gemini_embed_model,
        content=text,
    )

    # Case 1: response is a plain dict
    if isinstance(embed_resp, dict):
        maybe_embedding = embed_resp.get("embedding")

        # Most likely shape for you right now:
        # {"embedding": [float, float, ...]}
        if isinstance(maybe_embedding, list):
            return maybe_embedding

        # Alternative shape: {"embedding": {"values": [...]}}
        if isinstance(maybe_embedding, dict) and "values" in maybe_embedding:
            return maybe_embedding["values"]

        # Or sometimes: {"data": [{"embedding": {"values": [...]}}]}
        data = embed_resp.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                emb = first.get("embedding")
                if isinstance(emb, dict) and "values" in emb:
                    return emb["values"]

        raise RuntimeError(f"Unexpected embedding dict format: {embed_resp}")

    # Case 2: response is a list (e.g. list of embeddings)
    if isinstance(embed_resp, list):
        first = embed_resp[0]
        if isinstance(first, dict):
            emb = first.get("embedding")
            if isinstance(emb, list):
                return emb
            if isinstance(emb, dict) and "values" in emb:
                return emb["values"]
        # Or list of objects with .embedding.values
        try:
            return first.embedding.values  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Unexpected embedding list format: {embed_resp}") from e

    # Case 3: response is an object with .embedding or .values
    try:
        # object.embedding is already a list
        maybe_embedding = getattr(embed_resp, "embedding", None)
        if isinstance(maybe_embedding, list):
            return maybe_embedding
        # object.embedding.values
        if hasattr(embed_resp, "embedding") and hasattr(embed_resp.embedding, "values"):
            return embed_resp.embedding.values  # type: ignore[attr-defined]
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Unexpected embedding response object format: {embed_resp}") from e

    raise RuntimeError(f"Completely unexpected embedding response format: {embed_resp}")


