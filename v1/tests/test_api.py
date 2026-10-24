
from fastapi.testclient import TestClient

from app.main import app
# from app.graph.workflow import nexus_workflow


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "NexusAI"


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
                "task_plan": "Plan: analyze the business request.",
                "analysis": "Findings: sample analysis.",
                "final_report": "# Executive Report\nSample report.",
            }

    monkeypatch.setattr("app.main.nexus_workflow", FakeWorkflow())

    response = client.post(
        "/api/analyze",
        json={
            "request": (
                "Analyze our quarterly revenue "
                "and recommend improvements."
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["task_plan"]
    assert data["analysis"]
    assert data["final_report"]    


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
