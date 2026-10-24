
from app.llm import invoke_llm


def analyze_request(user_request: str, task_plan: str) -> str:
    prompt = f"""
You are the Business Analyst Agent in NexusAI.

Analyze the request according to the supplied plan.

Rules:
- Separate known facts from assumptions.
- Do not invent company data, metrics, or external research.
- If the request provides no actual data, state this limitation.
- Give actionable insights where the available information supports them.
- Identify what additional data would improve the analysis.

USER REQUEST:
{user_request}

ORCHESTRATOR PLAN:
{task_plan}

Return your structured analysis with these headings:
1. Findings
2. Reasoning
3. Assumptions and limitations
4. Recommended next steps
"""

    return invoke_llm(prompt)
