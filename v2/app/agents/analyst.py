
import logging
import time

from app.config import get_settings
from app.llm import invoke_llm

logger = logging.getLogger(__name__)


TASK_INSTRUCTIONS = {
    "business_analysis": """
Analyze the business problem.
Identify plausible explanations, distinguish facts from hypotheses,
and specify which data would be needed to verify each explanation.
""",
    "risk_review": """
Review the request for business risks, uncertainty, assumptions,
missing evidence, and possible unintended consequences.
""",
    "recommendations": """
Develop practical recommendations. Explain why each action may help,
what information is needed, and how success could be measured.
""",
    "writing": """
Create or improve the requested business document.
Use a clear, professional structure and preserve the user's intent.
""",
}


def execute_task(user_request: str, task: dict) -> dict:
    settings = get_settings()

    task_id = task["task_id"]
    task_type = task["task_type"]
    description = task["description"]

    if task_type not in TASK_INSTRUCTIONS:
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "failed",
            "output": "",
            "attempts": 0,
            "error": "Unsupported task type",
        }

    instructions = TASK_INSTRUCTIONS[task_type]
    started = time.perf_counter()
    last_error = "Task failed"

    for attempt in range(1, settings.max_task_attempts + 1):
        try:
            prompt = f"""
You are a specialist agent in NexusAI.

YOUR ROLE:
{instructions}

TASK:
{description}

USER REQUEST:
{user_request}

Rules:
- Do not invent data, statistics, sources, or completed actions.
- Clearly label assumptions and uncertainty.
- Return useful, structured findings.
"""

            output = invoke_llm(prompt)

            if not output.strip():
                raise ValueError("The model returned an empty response")

            elapsed_ms = round(
                (time.perf_counter() - started) * 1000, 2
            )

            logger.info(
                "Task %s succeeded on attempt %s",
                task_id,
                attempt,
            )

            return {
                "task_id": task_id,
                "task_type": task_type,
                "status": "completed",
                "output": output,
                "attempts": attempt,
                "duration_ms": elapsed_ms,
                "error": None,
            }

        except Exception as exc:
            last_error = str(exc)

            logger.warning(
                "Task %s failed on attempt %s: %s",
                task_id,
                attempt,
                exc,
            )

    elapsed_ms = round(
        (time.perf_counter() - started) * 1000, 2
    )

    return {
        "task_id": task_id,
        "task_type": task_type,
        "status": "failed",
        "output": "",
        "attempts": settings.max_task_attempts,
        "duration_ms": elapsed_ms,
        "error": last_error,
    }
