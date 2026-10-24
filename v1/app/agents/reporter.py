
from app.llm import invoke_llm


def write_report(
    user_request: str,
    task_plan: str,
    analysis: str,
) -> str:
    prompt = f"""
You are the Report Writer Agent in NexusAI.

Create a professional business report using the supplied analysis.

Requirements:
- Include an executive summary.
- Present key findings and recommendations.
- Clearly disclose assumptions and missing evidence.
- Never present unsupported claims as verified facts.
- Do not invent statistics, sources, or citations.
- Keep the report useful to a business decision-maker.

USER REQUEST:
{user_request}

PLAN:
{task_plan}

ANALYST FINDINGS:
{analysis}

Return the final report in Markdown.
"""

    return invoke_llm(prompt)
