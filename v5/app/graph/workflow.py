import uuid
import logging
import sqlite3
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agents.analyst import execute_task
from app.agents.critic import review_report
from app.agents.orchestrator import create_plan
from app.agents.reporter import write_report
from app.config import get_settings
from app.graph.state import NexusState, TaskInput
from app.observability.telemetry import observe_node

logger = logging.getLogger(__name__)


settings = get_settings()
checkpoint_path = Path(settings.upload_dir).parent / "nexusai_checkpoints.db"
checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

# Keep the connection alive for the lifetime of this process.
_checkpoint_connection = sqlite3.connect(
    str(checkpoint_path),
    check_same_thread=False,
)
checkpointer = SqliteSaver(_checkpoint_connection)
checkpointer.setup()

@observe_node("orchestrator")
def orchestrator_node(state: NexusState) -> dict:
    plan = create_plan(state["user_request"])
    return {
        "objective": plan.objective,
        "tasks": [task.model_dump() for task in plan.tasks],
        "execution_log": [{
            "event": "plan_created",
            "task_count": len(plan.tasks),
        }],
    }


def dispatch_tasks(state: NexusState):
    return [
        Send(
            "analyst",
            {
                "user_request": state["user_request"],
                "task": task,
            },
        )
        for task in state["tasks"]
    ]

@observe_node("analyst")
def analyst_node(state: TaskInput) -> dict:
    result = execute_task(
        user_request=state["user_request"],
        task=state["task"],
    )

    trace = {
        "event": "task_finished",
        "task_id": result["task_id"],
        "task_type": result["task_type"],
        "status": result["status"],
        "attempts": result["attempts"],
        "duration_ms": result.get("duration_ms", 0),
    }

    return {
        "results": [result],
        "execution_log": [trace],
    }


@observe_node("reporter")
def reporter_node(state: NexusState) -> dict:
    report = write_report(
        user_request=state["user_request"],
        objective=state["objective"],
        results=state["results"],
    )

    return {
        "final_report": report,
        "revision_count": 0,
        "execution_log": [{"event": "report_created"}],
    }


@observe_node("critic")
def critic_node(state: NexusState) -> dict:
    review = review_report(
        user_request=state["user_request"],
        report=state["final_report"],
        results=state["results"],
    )

    passed = bool(review["passed"])
    attempts_exhausted = (
        state["revision_count"] >= settings.max_revision_attempts
    )

    if passed:
        verification_status = "passed"
        unresolved = []
    elif attempts_exhausted:
        verification_status = "needs_human_review"
        unresolved = review.get("issues", [])
    else:
        verification_status = "revision_needed"
        unresolved = review.get("issues", [])

    # Some requests need human approval even when the critic passes.
    # In addition, unresolved defects must not be silently released.
    consequential = any(
        result.get("task_type") in {"recommendations", "sales_analytics"}
        and result.get("status") == "completed"
        for result in state["results"]
    )

    approval_required = (
        bool(review.get("requires_approval", False))
        or consequential
        or verification_status == "needs_human_review"
    )

    return {
        "review": review,
        "verification_status": verification_status,
        "unresolved_issues": unresolved,
        "approval_required": approval_required,
        "execution_log": [{
            "event": "critic_reviewed",
            "passed": passed,
            "revision_count": state["revision_count"],
            "verification_status": verification_status,
            "approval_required": approval_required,
        }],
    }


def route_after_critic(state: NexusState) -> str:
    if state["verification_status"] == "passed":
        return "approval_check"

    if state["verification_status"] == "revision_needed":
        return "revise_report"

    # Exhausted revisions: pause for human review.
    return "approval_check"


@observe_node("revise_report")
def revise_report_node(state: NexusState) -> dict:
    report = write_report(
        user_request=state["user_request"],
        objective=state["objective"],
        results=state["results"],
        previous_report=state["final_report"],
        review_issues=state["review"].get("issues", []),
    )

    return {
        "final_report": report,
        "revision_count": state["revision_count"] + 1,
        "execution_log": [{
            "event": "report_revised",
            "revision_count": state["revision_count"] + 1,
        }],
    }


def route_approval(state: NexusState) -> str:
    return "approval_gate" if state["approval_required"] else "finish"


@observe_node("approval_gate")
def approval_gate_node(state: NexusState) -> dict:
    decision = interrupt({
        "type": "human_approval_required",
        "message": "Review the report before final release.",
        "objective": state["objective"],
        "report": state["final_report"],
        "verification_status": state["verification_status"],
        "unresolved_issues": state["unresolved_issues"],
        "review": state["review"],
    })

    if not isinstance(decision, dict):
        decision = {"approved": False, "comment": "Invalid approval payload"}

    approved = decision.get("approved") is True
    comment = str(decision.get("comment", ""))[:2000]

    return {
        "approval_status": "approved" if approved else "rejected",
        "approval_comment": comment,
        "execution_log": [{
            "event": "human_decision",
            "decision": "approved" if approved else "rejected",
        }],
    }

@observe_node("finish")
def finish_node(state: NexusState) -> dict:
    if state["approval_required"]:
        if state["approval_status"] == "approved":
            status = (
                "completed"
                if state["verification_status"] == "passed"
                else "approved_with_warnings"
            )
        elif state["approval_status"] == "rejected":
            status = "rejected"
        else:
            status = "pending_approval"
    else:
        status = (
            "completed"
            if state["verification_status"] == "passed"
            else "needs_review"
        )

    return {
        "status": status,
        "execution_log": [{
            "event": "workflow_finished",
            "status": status,
        }],
    }


def build_workflow():
    graph = StateGraph(NexusState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reporter", reporter_node)
    graph.add_node("critic", critic_node)
    graph.add_node("revise_report", revise_report_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges("orchestrator", dispatch_tasks)
    graph.add_edge("analyst", "reporter")
    graph.add_edge("reporter", "critic")

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "approval_check": "approval_check",
            "revise_report": "revise_report",
        },
    )

    graph.add_node(
        "approval_check",
        lambda state: {},
    )
    graph.add_conditional_edges(
        "approval_check",
        route_approval,
        {
            "approval_gate": "approval_gate",
            "finish": "finish",
        },
    )

    graph.add_edge("revise_report", "critic")
    graph.add_edge("approval_gate", "finish")
    graph.add_edge("finish", END)

    return graph.compile(checkpointer=checkpointer)


nexus_workflow = build_workflow()


def invoke_workflow(
    initial_state: dict[str, Any] | Command,
    run_id: str,
) -> dict:
    return nexus_workflow.invoke(
        initial_state,
        config={
    "configurable": {
        "thread_id": f"test-parallel-{uuid.uuid4()}"
    }
},
    )
