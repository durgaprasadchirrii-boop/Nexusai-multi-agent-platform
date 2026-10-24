
import logging

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.graph.workflow import nexus_workflow
from app.schemas.request import AnalysisRequest, AnalysisResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Dynamic multi-agent business analysis with LangGraph",
    version="2.0.0",
)


@app.get("/")
def root():
    return {
        "application": settings.app_name,
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "application": settings.app_name}


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    logger.info("Received V2 orchestration request")

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
        logger.exception("NexusAI V2 workflow failed")

        raise HTTPException(
            status_code=500,
            detail="The orchestration workflow failed. Check application logs.",
        )
