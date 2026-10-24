
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from langgraph.types import Command

from app.config import get_settings
from app.graph.workflow import invoke_workflow
from app.schemas.request import (
    AnalysisRequest,
    AnalysisResponse,
    ApprovalRequest,
)
from app.tools.document_store import ingest_file, retrieve_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="NexusAI: multi-agent orchestration with RAG and verification",
    version="4.0.0",
)


def response_from_state(
    request_text: str,
    state: dict,
    run_id: str,
) -> dict:
    interrupted = bool(state.get("__interrupt__"))

    # The interrupt may leave status as running; expose the actual
    # user-facing status while preserving the checkpointed state.
    if interrupted:
        status = "pending_approval"
    else:
        status = state.get("status", "running")

    return {
        "request": request_text,
        "objective": state.get("objective", ""),
        "tasks": state.get("tasks", []),
        "results": state.get("results", []),
        "final_report": state.get("final_report", ""),
        "status": status,
        "execution_log": state.get("execution_log", []),
        "run_id": run_id,
        "verification_status": state.get("verification_status", "pending"),
        "review": state.get("review", {}),
        "unresolved_issues": state.get("unresolved_issues", []),
        "approval_required": state.get("approval_required", False),
        "approval_status": (
            "pending" if interrupted
            else state.get("approval_status", "not_required")
        ),
    }


@app.get("/")
def root():
    return {
        "application": settings.app_name,
        "version": "4.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "application": settings.app_name}


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    run_id = str(uuid4())

    initial_state = {
        "user_request": request.request,
        "objective": "",
        "tasks": [],
        "results": [],
        "execution_log": [],
        "final_report": "",
        "status": "running",
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
        return response_from_state(request.request, result, run_id)
    except Exception:
        logger.exception("NexusAI V4 workflow failed")
        raise HTTPException(
            status_code=500,
            detail="Workflow failed. Check application logs.",
        )


@app.post("/api/approve", response_model=AnalysisResponse)
def approve(request: ApprovalRequest):
    try:
        decision = {
            "approved": request.approved,
            "comment": request.comment,
        }

        result = invoke_workflow(
            Command(resume=decision),
            request.run_id,
        )

        # The original request is stored in the checkpoint.
        original_request = result.get("user_request", "")
        return response_from_state(
            original_request,
            result,
            request.run_id,
        )

    except Exception:
        logger.exception("Could not resume NexusAI approval workflow")
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not resume the workflow. Verify the run ID, "
                "checkpoint database, and application logs."
            ),
        )


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    safe_name = Path(file.filename).name
    suffix = Path(safe_name).suffix.lower()

    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="The file is empty.")

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum upload size is 20 MB.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.upload_dir / safe_name

    try:
        destination.write_bytes(content)
        result = ingest_file(destination)
        return {"status": "indexed", **result}
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Document ingestion failed")
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed. Check application logs.",
        )


@app.post("/api/documents/search")
def search_documents(request: dict):
    question = request.get("question")
    if not isinstance(question, str) or not 3 <= len(question) <= 2000:
        raise HTTPException(
            status_code=422,
            detail="question must contain between 3 and 2000 characters.",
        )

    k = request.get("k", 4)
    if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 10:
        raise HTTPException(status_code=422, detail="k must be between 1 and 10.")

    source = request.get("source")
    if source is not None and not isinstance(source, str):
        raise HTTPException(status_code=422, detail="source must be a string.")

    try:
        results = retrieve_documents(question, k=k, source_filter=source)
        return {
            "question": question,
            "count": len(results),
            "results": results,
        }
    except Exception:
        logger.exception("Document search failed")
        raise HTTPException(
            status_code=500,
            detail="Document search failed. Check application logs.",
        )
