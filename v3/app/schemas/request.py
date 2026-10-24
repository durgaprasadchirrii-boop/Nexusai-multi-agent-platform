
from typing import Any

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    request: str = Field(
        min_length=10,
        max_length=5000,
        description="Business request to analyze",
    )


class AnalysisResponse(BaseModel):
    request: str
    objective: str
    tasks: list[dict[str, Any]]
    results: list[dict[str, Any]]
    final_report: str
    status: str
    execution_log: list[dict[str, Any]]
