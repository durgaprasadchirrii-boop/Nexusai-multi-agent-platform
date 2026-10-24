
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents.analyst import execute_task
from app.agents.orchestrator import create_plan
from app.agents.reporter import write_report
from app.graph.state import NexusState, TaskInput


def orchestrator_node(state: NexusState) -> dict:
    plan = create_plan(state["user_request"])

    return {
        "objective": plan.objective,
        "tasks": [
            task.model_dump()
            for task in plan.tasks
        ],
        "execution_log": [
            {
                "event": "plan_created",
                "task_count": len(plan.tasks),
            }
        ],
    }


def dispatch_tasks(state: NexusState):
    # Each Send creates an independent worker invocation.
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


def reporter_node(state: NexusState) -> dict:
    report = write_report(
        user_request=state["user_request"],
        objective=state["objective"],
        results=state["results"],
    )

    failed = any(
        result["status"] != "completed"
        for result in state["results"]
    )

    return {
        "final_report": report,
        "status": "partial" if failed else "completed",
        "execution_log": [
            {
                "event": "report_created",
                "status": "partial" if failed else "completed",
            }
        ],
    }


def build_workflow():
    graph = StateGraph(NexusState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reporter", reporter_node)

    graph.add_edge(START, "orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        dispatch_tasks,
    )

    # LangGraph joins the parallel worker branches before
    # proceeding to the downstream report node.
    graph.add_edge("analyst", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile()


nexus_workflow = build_workflow()
