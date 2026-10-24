
from app.agents.orchestrator import ExecutionPlan, PlannedTask
from app.graph.workflow import build_workflow


def test_parallel_tasks_are_aggregated(monkeypatch):
    import app.graph.workflow as workflow

    def fake_plan(user_request):
        return ExecutionPlan(
            objective="Analyze the business situation",
            tasks=[
                PlannedTask(
                    task_id="task-1",
                    task_type="business_analysis",
                    description="Analyze the business problem",
                ),
                PlannedTask(
                    task_id="task-2",
                    task_type="risk_review",
                    description="Identify major risks",
                ),
            ],
        )

    def fake_execute(user_request, task):
        return {
            "task_id": task["task_id"],
            "task_type": task["task_type"],
            "status": "completed",
            "output": f"Results for {task['task_id']}",
            "attempts": 1,
            "duration_ms": 10,
            "error": None,
        }

    def fake_report(user_request, objective, results):
        assert len(results) == 2
        return "# Business Report\nBoth tasks completed."

    monkeypatch.setattr(workflow, "create_plan", fake_plan)
    monkeypatch.setattr(workflow, "execute_task", fake_execute)
    monkeypatch.setattr(workflow, "write_report", fake_report)

    graph = build_workflow()

    result = graph.invoke({
        "user_request": "Analyze our business performance and risks",
        "objective": "",
        "tasks": [],
        "results": [],
        "execution_log": [],
        "final_report": "",
        "status": "running",
    })

    assert result["status"] == "completed"
    assert len(result["results"]) == 2
    assert len(result["execution_log"]) == 4
    assert result["final_report"].startswith("# Business Report")


def test_failed_task_produces_partial_status(monkeypatch):
    import app.graph.workflow as workflow

    monkeypatch.setattr(
        workflow,
        "create_plan",
        lambda request: ExecutionPlan(
            objective="Review risks",
            tasks=[
                PlannedTask(
                    task_id="risk-1",
                    task_type="risk_review",
                    description="Review risks",
                )
            ],
        ),
    )

    monkeypatch.setattr(
        workflow,
        "execute_task",
        lambda user_request, task: {
            "task_id": task["task_id"],
            "task_type": task["task_type"],
            "status": "failed",
            "output": "",
            "attempts": 2,
            "duration_ms": 20,
            "error": "Simulated failure",
        },
    )

    monkeypatch.setattr(
        workflow,
        "write_report",
        lambda user_request, objective, results:
            "# Partial Report\nOne task failed.",
    )

    graph = build_workflow()

    result = graph.invoke({
        "user_request": "Review business risks and suggest mitigations",
        "objective": "",
        "tasks": [],
        "results": [],
        "execution_log": [],
        "final_report": "",
        "status": "running",
    })

    assert result["status"] == "partial"
    assert result["results"][0]["status"] == "failed"
    assert result["final_report"]
