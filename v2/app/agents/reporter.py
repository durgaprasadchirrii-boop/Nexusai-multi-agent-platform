
from app.llm import invoke_llm


def write_report(
    user_request: str,
    objective: str,
    results: list[dict],
) -> str:
    completed = [
        item for item in results
        if item["status"] == "completed"
    ]
    failed = [
        item for item in results
        if item["status"] != "completed"
    ]

    evidence = "\n\n".join(
        f"TASK: {item['task_id']} ({item['task_type']})\n"
        f"FINDINGS:\n{item['output']}"
        for item in completed
    )

    failure_notes = "\n".join(
        f"- {item['task_id']}: task failed after "
        f"{item['attempts']} attempt(s)"
        for item in failed
    ) or "None"

    prompt = f"""
You are the NexusAI Report Writer.

Create a professional report using only the supplied task outputs.

USER REQUEST:
{user_request}

OBJECTIVE:
{objective}

COMPLETED TASK OUTPUTS:
{evidence or "No tasks completed successfully."}

FAILED TASKS:
{failure_notes}

Requirements:
- Include an executive summary and key findings.
- Give recommendations only when supported by the available findings.
- State important assumptions and missing evidence.
- Never invent statistics, sources, or citations.
- Disclose incomplete work and unresolved questions.
- Do not imply that a failed task succeeded.

Return the report in Markdown.
"""

    return invoke_llm(prompt)
