"""Rules query route for CricketIQ API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cricketiq.backend.app.api.schemas.query import QueryRequest
from cricketiq.backend.app.api.schemas.response import QueryResponse
from cricketiq.backend.app.application.query_orchestrator import QueryOrchestrator
from cricketiq.backend.app.database.connection import get_db
from cricketiq.backend.app.database.repository import CricketIQRepository

router = APIRouter(prefix="/v1/rules", tags=["Cricket Rules"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query cricket rules with format-aware evidence grounding and deterministic citations",
    description=(
        "Processes a natural language cricket rule inquiry. Resolves governing applicability "
        "(MCC vs ICC), retrieves authoritative clauses via hybrid sparse/dense search, performs "
        "pre-generation evidence sufficiency checks, synthesizes an answer bounded strictly by retrieved "
        "evidence, and validates all citations deterministically against the source database."
    ),
)
def query_rules(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """Execute grounded cricket rules query pipeline."""
    try:
        repo = CricketIQRepository(db)
        orchestrator = QueryOrchestrator(repository=repo)
        response = orchestrator.execute(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule query execution failed: {str(exc)}"
        )
