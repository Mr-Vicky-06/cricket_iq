"""Health check routes for CricketIQ API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from cricketiq.backend.app.database.connection import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def liveness():
    """Liveness probe: returns 200 if server process is running."""
    return {"status": "alive"}


@router.get("/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe: verifies database connectivity and corpus readiness."""
    try:
        # Check basic database query execution
        db.execute(text("SELECT 1"))

        # Check clause count
        clause_count_res = db.execute(text("SELECT COUNT(*) FROM rule_clauses")).scalar()
        doc_count_res = db.execute(text("SELECT COUNT(*) FROM source_documents")).scalar()

        is_ready = (clause_count_res or 0) > 0 and (doc_count_res or 0) > 0

        return {
            "status": "ready" if is_ready else "not_ready",
            "database": "connected",
            "documents_count": doc_count_res or 0,
            "clauses_count": clause_count_res or 0,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database readiness check failed: {str(exc)}"
        )
