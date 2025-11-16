# app/risk_engine.py
from __future__ import annotations

from typing import List

from .models import Clause, ClauseAnalysis
from .precedent_agent import get_precedents_for_clause
from .gemini_client import call_gemini_json


# Simple hard-coded rules / playbook
PLAYBOOK = {
    "limitation_of_liability": {
        "max_cap_months": 12,
        "allow_unlimited_for": ["death_or_personal_injury", "fraud"],
        "disallow_exclusions": ["gross_negligence", "wilful_misconduct"],
    },
    "governing_law": {
        "preferred": ["England and Wales"],
        "discouraged": [],
        "forbidden": [],
    },
    "termination": {
        "min_notice_days": 30,
    },
}

RISK_SYSTEM = """
You are a conservative contract risk reviewer.
Given a specific clause, a playbook, a risk profile, and some model precedents,
assign a risk level and suggest a better clause.

Return ONLY JSON matching this schema:

{
  "risk_level": "GREEN" | "AMBER" | "RED",
  "explanation": "short explanation",
  "suggested_text": "improved clause text, in similar style",
  "precedent_snippets": ["short snippet 1", "short snippet 2"]
}

Rules:
- "GREEN" means broadly OK for a conservative customer.
- "AMBER" means acceptable but with some concerns.
- "RED" means high-risk and should be renegotiated.
- Use the playbook and the rule-based preliminary risk as strong signals.
- Use the precedent clauses as models of better wording where useful.
"""


def basic_rules_risk(clause: Clause, playbook: dict, risk_profile: str) -> str:
    """
    Very simple deterministic checks to get a first-pass risk score.
    You can extend this later; for now it's enough to drive the demo.
    """
    label = clause.label
    text = clause.raw_text.lower()

    if label == "limitation_of_liability":
        # Very crude logic:
        if "unlimited" in text and "death" not in text and "personal injury" not in text:
            return "RED"
        if "cap" in text or "maximum" in text or "shall not exceed" in text:
            return "AMBER"
        # No obvious cap at all → red
        return "RED"

    if label == "governing_law":
        if "england" in text and "wales" in text:
            return "GREEN"
        return "AMBER"

    if label == "termination":
        if "immediate" in text and "any reason" in text:
            return "RED"
        # If there's a notice period mentioned, treat as amber by default
        if "days" in text or "months" in text:
            return "AMBER"
        return "AMBER"

    # Default
    return "AMBER"


def analyse_clause(
    clause: Clause,
    contract_type: str,
    risk_profile: str,
) -> ClauseAnalysis:
    """
    Run rule-based risk + Gemini reasoning for a single clause.
    """

    playbook = PLAYBOOK.get(clause.label, {})
    rule_risk = basic_rules_risk(clause, playbook, risk_profile)

    # Retrieve similar precedents from Qdrant
    precedents = get_precedents_for_clause(
        clause_text=clause.raw_text,
        clause_type=clause.label,
        contract_type=contract_type,
    )

    precedents_text = "\n\n".join(
        f"- [{p.risk_level}] {p.text}" for p in precedents
    )

    user_prompt = f"""
Clause label: {clause.label}
Risk profile: {risk_profile}
Rule-based preliminary risk: {rule_risk}

Playbook for this clause type:
{playbook}

Actual contract clause:
<clause>
{clause.raw_text}
</clause>

Relevant precedent clauses:
{precedents_text}

Return strictly the JSON schema specified in the system instruction.
"""

    raw = call_gemini_json(RISK_SYSTEM, user_prompt)

    return ClauseAnalysis(
        clause_label=clause.label,
        risk_level=raw["risk_level"],
        explanation=raw["explanation"],
        suggested_text=raw["suggested_text"],
        precedent_snippets=raw.get("precedent_snippets", []),
    )


def analyse_clauses(
    clauses: List[Clause],
    contract_type: str,
    risk_profile: str,
) -> List[ClauseAnalysis]:
    """
    Analyse only the clause types we care about for the MVP.
    """
    analyses: List[ClauseAnalysis] = []

    for c in clauses:
        if c.label in {"limitation_of_liability", "governing_law", "termination"}:
            analyses.append(analyse_clause(c, contract_type, risk_profile))

    return analyses
