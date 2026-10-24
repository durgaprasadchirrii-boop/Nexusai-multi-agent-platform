
from langgraph.graph import END, START, StateGraph

from app.agents.analyst import analyze_request
from app.agents.orchestrator import create_plan
from app.agents.reporter import write_report
from app.graph.state import NexusState


def orchestrator_node(state: NexusState) -> dict:
    plan = create_plan(state["user_request"])
    return {"task_plan": plan}


def analyst_node(state: NexusState) -> dict:
    analysis = analyze_request(
        user_request=state["user_request"],
        task_plan=state["task_plan"],
    )
    return {"analysis": analysis}


def reporter_node(state: NexusState) -> dict:
    report = write_report(
        user_request=state["user_request"],
        task_plan=state["task_plan"],
        analysis=state["analysis"],
    )
    return {"final_report": report}


def build_workflow():
    graph = StateGraph(NexusState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reporter", reporter_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "analyst")
    graph.add_edge("analyst", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile()


nexus_workflow = build_workflow()
