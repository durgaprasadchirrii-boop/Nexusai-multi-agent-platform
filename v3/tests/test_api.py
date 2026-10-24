
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == "3.0.0"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_rejects_short_request():
    response = client.post(
        "/api/analyze",
        json={"request": "Hi"},
    )

    assert response.status_code == 422


def test_analysis_endpoint(monkeypatch):
    class FakeWorkflow:
        def invoke(self, initial_state):
            return {
                **initial_state,
                "objective": "Analyze revenue",
                "tasks": [
                    {
                        "task_id": "task-1",
                        "task_type": "business_analysis",
                        "description": "Analyze revenue",
                    }
                ],
                "results": [
                    {
                        "task_id": "task-1",
                        "task_type": "business_analysis",
                        "status": "completed",
                        "output": "Revenue requires further investigation.",
                        "attempts": 1,
                        "duration_ms": 15,
                        "error": None,
                    }
                ],
                "final_report": "# Revenue Report",
                "status": "completed",
                "execution_log": [
                    {"event": "plan_created", "task_count": 1},
                    {
                        "event": "task_finished",
                        "task_id": "task-1",
                        "task_type": "business_analysis",
                        "status": "completed",
                        "attempts": 1,
                        "duration_ms": 15,
                    },
                    {"event": "report_created", "status": "completed"},
                ],
            }

    monkeypatch.setattr("app.main.nexus_workflow", FakeWorkflow())

    response = client.post(
        "/api/analyze",
        json={
            "request": (
                "Analyze quarterly revenue and recommend "
                "practical improvements for management."
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["objective"] == "Analyze revenue"
    assert len(data["tasks"]) == 1
    assert len(data["results"]) == 1
    assert data["execution_log"]
    assert data["final_report"] == "# Revenue Report"

  


# def test_analysis_endpoint(monkeypatch):
#     def fake_invoke(initial_state):
#         return {
#             **initial_state,
#             "task_plan": "Plan: analyze the business request.",
#             "analysis": "Findings: sample analysis.",
#             "final_report": "# Executive Report\nSample report.",
#         }

#     monkeypatch.setattr(nexus_workflow, "invoke", fake_invoke)

#     response = client.post(
#         "/api/analyze",
#         json={
#             "request": (
#                 "Analyze our quarterly revenue "
#                 "and recommend improvements."
#             )
#         },
#     )

#     assert response.status_code == 200

#     data = response.json()

#     assert data["status"] == "completed"
#     assert data["task_plan"]
#     assert data["analysis"]
#     assert data["final_report"]
