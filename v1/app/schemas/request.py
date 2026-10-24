
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    request: str = Field(
        min_length=10,
        max_length=5000,
        description="Business request to analyze",
        examples=[
            "Analyze why our quarterly revenue declined "
            "and recommend next steps."
        ],
    )


class AnalysisResponse(BaseModel):
    request: str
    task_plan: str
    analysis: str
    final_report: str
    status: str = "completed"
