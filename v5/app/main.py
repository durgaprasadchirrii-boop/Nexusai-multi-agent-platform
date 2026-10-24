# app/main.py

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.graph.workflow import invoke_workflow
from app.observability.middleware import ObservabilityMiddleware
from app.observability.telemetry import (
    APPROVALS,
    REVISIONS,
    RUNS,
    TASKS,
    record_event,
)
from app.tools.document_store import ingest_file, retrieve_documents

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NexusAI",
    description="Multi-agent orchestration platform with RAG, verification, and observability.",
    version="5.0.0",
)

app.add_middleware(ObservabilityMiddleware)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class AnalyzeRequest(BaseModel):
    request: str = Field(..., min_length=3, description="The task NexusAI should perform.")
    run_id: str | None = Field(default=None, description="Optional workflow run identifier.")


class ApprovalRequest(BaseModel):
    run_id: str
    approved: bool
    comment: str = ""


class DocumentSearchRequest(BaseModel):
    question: str = Field(..., min_length=2)
    k: int = Field(default=4, ge=1, le=20)
    source_filter: str | None = None


def response_from_state(state: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Return a consistent API response without exposing internal checkpoint data."""
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "objective": state.get("objective", ""),
        "tasks": state.get("results", []),
        "execution_log": state.get("execution_log", []),
        "final_report": state.get("final_report", ""),
        "review": state.get("review", {}),
        "verification_status": state.get("verification_status", "unknown"),
        "unresolved_issues": state.get("unresolved_issues", []),
        "revision_count": state.get("revision_count", 0),
        "approval_required": state.get("approval_required", False),
        "approval_status": state.get("approval_status", "not_required"),
    }


@app.get("/")
def root():
    return {
        "service": "NexusAI",
        "version": "5.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "nexusai", "version": "5.0.0"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    run_id = request.run_id or str(uuid.uuid4())

    initial_state = {
        "user_request": request.request,
        "objective": "",
        "tasks": [],
        "results": [],
        "execution_log": [],
        "final_report": "",
        "status": "started",
        "review": {},
        "revision_count": 0,
        "verification_status": "pending",
        "unresolved_issues": [],
        "approval_required": False,
        "approval_status": "not_required",
        "approval_comment": "",
    }

    try:
        result = invoke_workflow(initial_state, run_id)

        RUNS.labels(status=result.get("status", "unknown")).inc()

        for item in result.get("results", []):
            TASKS.labels(
                task_type=item.get("task_type", "unknown"),
                status=item.get("status", "unknown"),
            ).inc()

        revision_count = result.get("revision_count", 0)
        if revision_count:
            REVISIONS.inc(revision_count)

        record_event({
            "event": "workflow_finished",
            "run_id": run_id,
            "status": result.get("status"),
            "verification_status": result.get("verification_status"),
            "task_count": len(result.get("results", [])),
            "revision_count": revision_count,
        })

        return response_from_state(result, run_id)

    except Exception as exc:
        logger.exception("NexusAI analysis failed. run_id=%s", run_id)
        record_event({
            "event": "workflow_failed",
            "run_id": run_id,
            "error_type": type(exc).__name__,
        })
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed. Run ID: {run_id}",
        ) from exc


@app.post("/api/approve")
def approve(request: ApprovalRequest):
    decision = {
        "approved": request.approved,
        "comment": request.comment,
    }

    try:
        # LangGraph resumes the paused workflow using its checkpoint/thread ID.
        from langgraph.types import Command

        result = invoke_workflow(
            Command(resume=decision),
            request.run_id,
        )

        approval_status = result.get("approval_status", "unknown")

        if approval_status in {"approved", "rejected"}:
            APPROVALS.labels(decision=approval_status).inc()

        record_event({
            "event": "approval_resumed",
            "run_id": request.run_id,
            "decision": approval_status,
        })

        return response_from_state(result, request.run_id)

    except Exception as exc:
        logger.exception(
            "Could not resume workflow. run_id=%s",
            request.run_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Could not resume workflow. Run ID: {request.run_id}",
        ) from exc


@app.post("/api/documents/upload")
def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    # Avoid using a user-provided path as a destination.
    safe_name = Path(file.filename).name
    suffix = Path(safe_name).suffix.lower()

    if suffix not in {".pdf", ".txt", ".md", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Supported file types: PDF, TXT, MD, DOCX.",
        )

    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"

    try:
        with destination.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        ingestion_result = ingest_file(str(destination))

        record_event({
            "event": "document_uploaded",
            "filename": safe_name,
            "result": str(ingestion_result),
        })

        return {
            "message": "Document ingestion completed.",
            "filename": safe_name,
            "result": ingestion_result,
        }

    except Exception as exc:
        logger.exception("Document ingestion failed.")
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed. Check the server logs.",
        ) from exc

    finally:
        file.file.close()


@app.post("/api/documents/search")
def search_documents(request: DocumentSearchRequest):
    try:
        documents = retrieve_documents(
            question=request.question,
            k=request.k,
            source_filter=request.source_filter,
        )

        return {
            "question": request.question,
            "count": len(documents),
            "documents": documents,
        }

    except Exception as exc:
        logger.exception("Document retrieval failed.")
        raise HTTPException(
            status_code=500,
            detail="Document retrieval failed. Check the server logs.",
        ) from exc