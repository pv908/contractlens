# app/precedent_agent.py
from __future__ import annotations

from typing import List

from .gemini_client import get_embedding
from .qdrant_client import search_precedents
from .models import PrecedentClause


def get_precedents_for_clause(
    clause_text: str,
    clause_type: str,
    contract_type: str,
    limit: int = 3,
) -> List[PrecedentClause]:
    """
    Embed the clause and retrieve similar precedents from Qdrant.
    """

    emb = get_embedding(clause_text)
    hits = search_precedents(
        vector=emb,
        clause_type=clause_type,
        contract_type=contract_type,
        limit=limit,
    )

    results: List[PrecedentClause] = []

    for hit in hits:
        payload = hit.payload or {}
        results.append(
            PrecedentClause(
                id=str(hit.id),
                clause_type=payload.get("clause_type", ""),
                contract_type=payload.get("contract_type", None),
                risk_level=payload.get("risk_level", ""),
                jurisdiction=payload.get("jurisdiction"),
                text=payload.get("text", ""),
            )
        )

    return results
