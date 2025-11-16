# app/models.py
from __future__ import annotations

from datetime import date
from typing import Any, List, Optional
from pydantic import BaseModel


class Clause(BaseModel):
    label: str                 # e.g. "limitation_of_liability"
    raw_text: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ExtractedContract(BaseModel):
    parties: List[str]
    effective_date: Optional[date] = None
    term_months: Optional[int] = None
    auto_renewal: Optional[bool] = None
    governing_law: Optional[str] = None
    contract_type: Optional[str] = None  # "saas" | "services" | "employment"
    clauses: List[Clause]


class PrecedentClause(BaseModel):
    id: str
    clause_type: str
    text: str
    risk_level: str
    jurisdiction: Optional[str] = None
    contract_type: Optional[str] = None


class ClauseAnalysis(BaseModel):
    clause_label: str                     # "limitation_of_liability" | "termination" | "governing_law"
    risk_level: str                       # "GREEN" | "AMBER" | "RED"
    explanation: str
    suggested_text: str
    precedent_snippets: List[str]


class ContractAnalysis(BaseModel):
    summary: str
    key_terms: dict[str, Any]
    clauses: List[ClauseAnalysis]


class AnalyzeRequest(BaseModel):
    contract_type: str   # "saas" | "services" | "employment"
    risk_profile: str    # "conservative" | "balanced" | "aggressive"


class AnalyzeResponse(BaseModel):
    analysis: ContractAnalysis
