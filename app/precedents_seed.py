# app/precedents_seed.py
from __future__ import annotations

from qdrant_client.models import PointStruct

from .gemini_client import get_embedding
from .qdrant_client import ensure_collection, add_precedents


RAW_PRECEDENTS = [
    # Limitation of liability – customer-friendly (cap, carve-outs)
    {
        "id": "liab_saas_customer_friendly_1",
        "clause_type": "limitation_of_liability",
        "contract_type": "saas",
        "risk_level": "low",
        "jurisdiction": "England and Wales",
        "text": """
The Supplier's aggregate liability arising out of or in connection with this Agreement,
whether in contract, tort (including negligence) or otherwise, shall not exceed an amount
equal to the Fees paid or payable by the Customer under this Agreement in the twelve (12)
months immediately preceding the event giving rise to the claim.

Nothing in this Agreement excludes or limits either party's liability for death or personal
injury caused by negligence, fraud or fraudulent misrepresentation, or any other liability
which cannot lawfully be excluded or limited.
""".strip(),
    },
    # Limitation of liability – supplier-friendly (almost no liability)
    {
        "id": "liab_saas_supplier_friendly_1",
        "clause_type": "limitation_of_liability",
        "contract_type": "saas",
        "risk_level": "high",
        "jurisdiction": "England and Wales",
        "text": """
To the fullest extent permitted by law, the Supplier shall have no liability to the Customer
arising out of or in connection with this Agreement, whether in contract, tort (including
negligence) or otherwise.
""".strip(),
    },
    # Governing law – standard English law
    {
        "id": "govlaw_england_wales_1",
        "clause_type": "governing_law",
        "contract_type": "saas",
        "risk_level": "low",
        "jurisdiction": "England and Wales",
        "text": """
This Agreement and any dispute or claim (including non-contractual disputes or claims)
arising out of or in connection with it or its subject matter or formation shall be
governed by and construed in accordance with the laws of England and Wales.
""".strip(),
    },
    # Governing law – random foreign law (from an English customer POV: higher risk)
    {
        "id": "govlaw_newyork_1",
        "clause_type": "governing_law",
        "contract_type": "saas",
        "risk_level": "medium",
        "jurisdiction": "New York",
        "text": """
This Agreement shall be governed by and construed in accordance with the laws of the State
of New York, without regard to its conflict of law provisions.
""".strip(),
    },
    # Termination – reasonable notice
    {
        "id": "termination_30_days_1",
        "clause_type": "termination",
        "contract_type": "saas",
        "risk_level": "low",
        "jurisdiction": "England and Wales",
        "text": """
Either party may terminate this Agreement for convenience by giving the other party not less
than thirty (30) days' prior written notice.

Either party may terminate this Agreement with immediate effect by written notice if the
other party commits a material breach which is not remedied (if remediable) within thirty
(30) days after receipt of written notice describing the breach.
""".strip(),
    },
    # Termination – very supplier-friendly (immediate termination)
    {
        "id": "termination_immediate_supplier_1",
        "clause_type": "termination",
        "contract_type": "saas",
        "risk_level": "high",
        "jurisdiction": "England and Wales",
        "text": """
The Supplier may terminate this Agreement at any time, with immediate effect and without
cause, by giving written notice to the Customer. The Customer shall have no right to any
refund of Fees paid in advance.
""".strip(),
    },
]


def main() -> None:
    """
    Seed Qdrant with a handful of precedent clauses.
    Run this once from the project root:

        python -m app.precedents_seed
    """
    print("Ensuring collection exists...")
    ensure_collection()

    points: list[PointStruct] = []

    print(f"Building embeddings for {len(RAW_PRECEDENTS)} precedents...")
    for idx, item in enumerate(RAW_PRECEDENTS):
        emb = get_embedding(item["text"])
        points.append(
            PointStruct(
                id=idx,  # Qdrant now expects unsigned int or UUID
                vector=emb,
                payload={
                    "clause_type": item["clause_type"],
                    "contract_type": item["contract_type"],
                    "risk_level": item["risk_level"],
                    "jurisdiction": item["jurisdiction"],
                    "text": item["text"],
                    "precedent_id": item["id"],  # keep your human-readable ID in payload
                },
            )
        )


    print("Upserting precedents into Qdrant...")
    add_precedents(points)
    print("Seeded precedents successfully.")


if __name__ == "__main__":
    main()
