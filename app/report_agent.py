# app/report_agent.py
from __future__ import annotations
import json
from typing import List

from .gemini_client import call_gemini_json
from .models import ExtractedContract, ClauseAnalysis, ContractAnalysis

SUMMARY_SYSTEM = """
You help SME founders understand contracts.

Given:
- structured contract data, and
- clause analyses with risk levels,

produce a concise summary and a simple key_terms dict.

Return ONLY JSON like:

{
  "summary": "string, 3-6 sentences, plain English, non-technical",
  "key_terms": {
    "parties": ["A", "B"],
    "governing_law": "England and Wales",
    "term_months": 12,
    "auto_renewal": true,
    "headline_risk": "e.g. 'Liability very supplier-friendly; termination OK'",
    "flags": ["short list of key issues"]
  }
}

Rules:
- summary: 3–6 sentences max, no bullet points, clear and non-legalistic.
- key_terms: keep it simple; you can reuse fields from the structured data.
- "flags" should be a short list of the main risk issues (based on clause analyses).
"""


def build_contract_analysis(
    extracted: ExtractedContract,
    clause_analyses: List[ClauseAnalysis],
) -> ContractAnalysis:
    """
    Combine the extracted data and the clause analyses into a ContractAnalysis.
    """

    clause_summaries = [
        {
            "clause_label": c.clause_label,
            "risk_level": c.risk_level,
            "explanation": c.explanation,
        }
        for c in clause_analyses
    ]

    extracted_json = json.dumps(extracted.model_dump(), indent=2)
    clause_summaries_json = json.dumps(clause_summaries, indent=2)

    user_prompt = f"""
Structured contract data (JSON):
{extracted_json}

Clause analyses (label + risk + explanation):
{clause_summaries_json}

Return ONLY the JSON object specified in the system instruction.
"""

    raw = call_gemini_json(SUMMARY_SYSTEM, user_prompt)

    summary = raw.get("summary", "")
    key_terms = raw.get("key_terms", {})

    return ContractAnalysis(
        summary=summary,
        key_terms=key_terms,
        clauses=clause_analyses,
    )
