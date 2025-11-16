# app/qdrant_client.py
from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from .config import settings


# Gemini text-embedding-004 returns 768-dimensional embeddings
EMBEDDING_DIM = 768


client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)


def ensure_collection() -> None:
    """
    Create the collection in Qdrant if it does not already exist,
    and ensure payload indexes exist for the fields we filter on.
    """

    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if settings.qdrant_collection not in names:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )

    # Ensure payload indexes for filters (clause_type, contract_type)
    for field in ("clause_type", "contract_type"):
        try:
            client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=field,
                field_schema="keyword",
            )
        except UnexpectedResponse:
            # Index probably already exists – safe to ignore for our purposes
            pass
        except Exception:
            # In a hackathon context, we silently ignore other index errors too
            pass



def add_precedents(points: list[PointStruct]) -> None:
    """
    Insert or upsert precedent points.
    """

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )


def search_precedents(
    vector: list[float],
    clause_type: str,
    contract_type: str,
    limit: int = 3,
):
    """
    Search Qdrant with filters for clause_type and contract_type.
    """

    qfilter = Filter(
        must=[
            FieldCondition(
                key="clause_type",
                match=MatchValue(value=clause_type),
            ),
            FieldCondition(
                key="contract_type",
                match=MatchValue(value=contract_type),
            ),
        ]
    )

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        query_filter=qfilter,
        limit=limit,
    )

    return results
