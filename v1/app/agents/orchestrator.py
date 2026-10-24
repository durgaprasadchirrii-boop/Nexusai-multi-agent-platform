
from app.llm import invoke_llm


def create_plan(user_request: str) -> str:
    prompt = f"""
You are the Orchestrator Agent in NexusAI.

Your job is to plan a business-analysis request for other agents.

Create a concise plan with:
1. The main objective.
2. The key questions to answer.
3. The evidence or calculations needed.
4. The expected final deliverable.

Do not claim that you have performed analysis.
Do not invent facts.

USER REQUEST:
{user_request}

Return only the plan.
"""

    return invoke_llm(prompt)
