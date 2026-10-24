
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
    objective: str = ""
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    final_report: str = ""
    status: str = "running"
    execution_log: list[dict[str, Any]] = Field(default_factory=list)

    run_id: str | None = None
    verification_status: str = "pending"
    review: dict[str, Any] = Field(default_factory=dict)
    unresolved_issues: list[str] = Field(default_factory=list)
    approval_required: bool = False
    approval_status: str = "not_required"


class ApprovalRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=100)
    approved: bool
    comment: str = Field(default="", max_length=2000)
