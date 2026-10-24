
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
    description=(
        "A LangGraph-powered multi-agent business "
        "analysis and report generation API."
    ),
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "application": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "application": settings.app_name}


@app.post(
    "/api/analyze",
    response_model=AnalysisResponse,
)
def analyze(request: AnalysisRequest):
    logger.info("Received business analysis request")

    initial_state = {
        "user_request": request.request,
        "task_plan": "",
        "analysis": "",
        "final_report": "",
    }

    try:
        result = nexus_workflow.invoke(initial_state)

        return AnalysisResponse(
            request=request.request,
            task_plan=result["task_plan"],
            analysis=result["analysis"],
            final_report=result["final_report"],
        )

    except Exception:
        logger.exception("Business analysis workflow failed")

        raise HTTPException(
            status_code=500,
            detail="The analysis workflow failed. Check application logs.",
        )
