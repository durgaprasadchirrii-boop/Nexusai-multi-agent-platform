
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph.workflow import nexus_workflow
from app.schemas.request import AnalysisRequest, AnalysisResponse
from app.tools.document_store import ingest_file, retrieve_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Multi-agent orchestration with RAG and controlled analytics",
    version="3.0.0",
)


class DocumentSearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    k: int = Field(default=4, ge=1, le=10)
    source: str | None = Field(default=None, max_length=255)


@app.get("/")
def root():
    return {
        "application": settings.app_name,
        "version": "3.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": settings.app_name,
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    logger.info("Received V3 orchestration request")

    initial_state = {
        "user_request": request.request,
        "objective": "",
        "tasks": [],
        "results": [],
        "execution_log": [],
        "final_report": "",
        "status": "running",
    }

    try:
        result = nexus_workflow.invoke(initial_state)

        return AnalysisResponse(
            request=request.request,
            objective=result["objective"],
            tasks=result["tasks"],
            results=result["results"],
            final_report=result["final_report"],
            status=result["status"],
            execution_log=result["execution_log"],
        )

    except Exception:
        logger.exception("NexusAI V3 workflow failed")
        raise HTTPException(
            status_code=500,
            detail="The orchestration workflow failed. Check application logs.",
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

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.upload_dir / safe_name

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Maximum upload size is 20 MB.",
            )

        destination.write_bytes(content)
        result = ingest_file(destination)

        return {
            "status": "indexed",
            **result,
            "message": "Document indexed successfully.",
        }

    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Document ingestion failed")
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed. Check application logs.",
        )
    finally:
        await file.close()


@app.post("/api/documents/search")
def search_documents(request: DocumentSearchRequest):
    try:
        results = retrieve_documents(
            question=request.question,
            k=request.k,
            source_filter=request.source,
        )
        return {
            "question": request.question,
            "count": len(results),
            "results": results,
        }
    except Exception:
        logger.exception("Document retrieval failed")
        raise HTTPException(
            status_code=500,
            detail="Document retrieval failed. Check application logs.",
        )
