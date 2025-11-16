# app/extraction_agent.py
from __future__ import annotations

import json

from .gemini_client import call_gemini_json
from .models import ExtractedContract

EXTRACTION_SYSTEM = """
You are a contract analysis engine.
Extract structured key terms and clauses from the contract text.
Return ONLY valid JSON matching this schema (do not include any extra keys):

{
  "parties": ["Party A Ltd", "Party B Ltd"],
  "effective_date": "YYYY-MM-DD or null",
  "term_months": 12,
  "auto_renewal": true,
  "governing_law": "England and Wales",
  "contract_type": "saas" | "services" | "employment" | null,
  "clauses": [
    {
      "label": "limitation_of_liability" | "termination" | "governing_law" | "ip" | "other",
      "raw_text": "exact clause text from the contract",
      "start_char": 123,
      "end_char": 456
    }
  ]
}

Rules:
- If you are not sure about a value, use null (or [] for lists).
- "term_months" should be an integer number of months if you can infer it, otherwise null.
- "auto_renewal" should be true, false or null.
- "governing_law" should be a simple string like "England and Wales" if you can extract it.
- "contract_type" should be a best guess: "saas", "services", or "employment", or null if unclear.
- For clauses, include at least any limitation of liability, termination, and governing law clauses if present.
- "start_char" and "end_char" are offsets into the provided contract text string; if you cannot compute them reliably, use null.
"""


def _build_user_prompt(contract_text: str) -> str:
    # Truncate to avoid giant prompts
    truncated = contract_text[:15000]
    return f"""
Contract text:
<contract>
{truncated}
</contract>

Return ONLY the JSON object as described. Do not include any commentary or Markdown.
"""


def extract_contract(contract_text: str) -> ExtractedContract:
    """
    Call Gemini to extract key terms and clauses into an ExtractedContract object.
    """

    user_prompt = _build_user_prompt(contract_text)
    raw = call_gemini_json(EXTRACTION_SYSTEM, user_prompt)

    try:
        return ExtractedContract(**raw)
    except Exception as e:  # noqa: BLE001
        # Attempt a single self-healing roundtrip to Gemini
        fix_prompt = f"""
The following JSON had validation errors in my schema: {e}.

Here is the JSON you produced:
{json.dumps(raw)}

Please return corrected JSON that strictly matches the schema in the system instruction.
Return ONLY the corrected JSON object.
"""
        fixed_raw = call_gemini_json(EXTRACTION_SYSTEM, fix_prompt)
        return ExtractedContract(**fixed_raw)
