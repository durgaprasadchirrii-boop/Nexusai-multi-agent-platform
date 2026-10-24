
import logging

from pydantic import BaseModel, Field

from app.llm import get_llm
from app.config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_TASKS = {
    "business_analysis",
    "risk_review",
    "recommendations",
    "writing",
    "document_research",
    "sales_analytics",
}


class PlannedTask(BaseModel):
    task_id: str = Field(description="Unique task identifier")
    task_type: str = Field(
        description="One of the six supported task types"
    )
    description: str = Field(
        description="Specific work this task must perform"
    )


class ExecutionPlan(BaseModel):
    objective: str
    tasks: list[PlannedTask]


def create_plan(user_request: str) -> ExecutionPlan:
    settings = get_settings()
    planner = get_llm().with_structured_output(ExecutionPlan)

    prompt = f"""
You are the NexusAI Orchestrator.

Break the user's request into independent specialist tasks.

Allowed task types:
- business_analysis: analyze a business problem.
- risk_review: identify risks, uncertainty, and missing evidence.
- recommendations: suggest actionable next steps.
- writing: create or improve business communication.
- document_research: search uploaded PDFs/TXT documents and cite evidence.
- sales_analytics: retrieve approved metrics from the local demo sales database.

Rules:
- Create between 1 and {settings.max_parallel_tasks} tasks.
- Use only allowed task types.
- Give every task a unique ID.
- Use document_research when the request asks about uploaded documents,
  policies, reports, manuals, or document evidence.
- Use sales_analytics only when the user requests supported sales metrics.
- Use business_analysis for general business analysis.
- Use writing for writing-only requests.
- Do not claim documents or databases were checked unless the task does so.
- Do not invent data or sources.
- Do not create unrelated tasks.
- The objective must describe the user's goal.

USER REQUEST:
{user_request}
"""

    plan = planner.invoke(prompt)

    if not 1 <= len(plan.tasks) <= settings.max_parallel_tasks:
        raise ValueError("Planner returned an invalid number of tasks")

    task_ids = [task.task_id for task in plan.tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Planner returned duplicate task IDs")

    for task in plan.tasks:
        if task.task_type not in ALLOWED_TASKS:
            raise ValueError(
                f"Unsupported task type: {task.task_type}"
            )

    logger.info("Created plan with %s tasks", len(plan.tasks))
    return plan
