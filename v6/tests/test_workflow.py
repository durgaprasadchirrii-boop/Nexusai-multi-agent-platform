
from app.agents.orchestrator import ExecutionPlan, PlannedTask
from app.graph.workflow import build_workflow


def initial_state(request):
    return {
        "user_request": request,
        "objective": "",
        "tasks": [],
        "results": [],
        "execution_log": [],
        "final_report": "",
        "status": "running",
        "review": {},
        "revision_count": 0,
        "verification_status": "pending",
        "unresolved_issues": [],
        "approval_required": False,
        "approval_status": "not_required",
        "approval_comment": "",
    }


def test_parallel_tasks_are_aggregated(monkeypatch):
    import app.graph.workflow as workflow

    monkeypatch.setattr(
        workflow,
        "create_plan",
        lambda request: ExecutionPlan(
            objective="Analyze business performance",
            tasks=[
                PlannedTask(
                    task_id="task-1",
                    task_type="business_analysis",
                    description="Analyze the business problem",
                ),
                PlannedTask(
                    task_id="task-2",
                    task_type="risk_review",
                    description="Identify risks",
                ),
            ],
        ),
    )

    def fake_execute(user_request, task):
        return {
            "task_id": task["task_id"],
            "task_type": task["task_type"],
            "status": "completed",
            "output": f"Evidence for {task['task_id']}",
            "attempts": 1,
            "duration_ms": 10,
            "error": None,
        }

    monkeypatch.setattr(workflow, "execute_task", fake_execute)
    monkeypatch.setattr(
        workflow,
        "write_report",
        lambda **kwargs: "# Business Report\nSupported findings.",
    )
    monkeypatch.setattr(
        workflow,
        "review_report",
        lambda **kwargs: {
            "passed": True,
            "issues": [],
            "requires_approval": False,
        },
    )

    result = build_workflow().invoke(
        initial_state("Analyze business performance and risks"),
        config={"configurable": {"thread_id": "test-parallel-v4"}},
    )

    assert len(result["results"]) == 2
    assert result["verification_status"] == "passed"
    assert result["status"] == "completed"
    assert result["final_report"].startswith("# Business Report")


def test_failed_verification_gets_bounded_revision(monkeypatch):
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
                    description="Review business risks",
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
            "status": "completed",
            "output": "Some risks need more evidence.",
            "attempts": 1,
            "duration_ms": 10,
            "error": None,
        },
    )

    revision_calls = {"count": 0}

    def fake_report(**kwargs):
        if kwargs.get("previous_report"):
            revision_calls["count"] += 1
            return "# Revised Report\nLimitations disclosed."
        return "# Initial Report\nSome claims need checking."

    reviews = [
        {
            "passed": False,
            "issues": ["Clarify missing evidence."],
            "requires_approval": False,
        },
        {
            "passed": True,
            "issues": [],
            "requires_approval": False,
        },
    ]

    def fake_review(**kwargs):
        return reviews.pop(0)

    monkeypatch.setattr(workflow, "write_report", fake_report)
    monkeypatch.setattr(workflow, "review_report", fake_review)

    result = build_workflow().invoke(
        initial_state("Review business risks and missing evidence"),
        config={"configurable": {"thread_id": "test-revision-v4"}},
    )

    assert revision_calls["count"] == 1
    assert result["revision_count"] == 1
    assert result["verification_status"] == "passed"
    assert result["status"] == "completed"
