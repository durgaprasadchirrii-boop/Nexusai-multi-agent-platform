
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == "4.0.0"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_rejects_short_request():
    response = client.post("/api/analyze", json={"request": "Hi"})
    assert response.status_code == 422


def test_analysis_endpoint(monkeypatch):
    def fake_invoke(initial_state, run_id):
        return {
            **initial_state,
            "objective": "Analyze revenue",
            "tasks": [],
            "results": [],
            "final_report": "# Revenue Report",
            "status": "completed",
            "verification_status": "passed",
            "review": {"passed": True, "issues": []},
            "unresolved_issues": [],
            "approval_required": False,
            "approval_status": "not_required",
        }

    monkeypatch.setattr("app.main.invoke_workflow", fake_invoke)

    response = client.post("/api/analyze", json={
        "request": "Analyze quarterly revenue and recommend improvements."
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["verification_status"] == "passed"
    assert data["run_id"]


def test_approval_requires_run_id():
    response = client.post("/api/approve", json={
        "approved": True,
        "comment": "Reviewed",
    })
    assert response.status_code == 422
