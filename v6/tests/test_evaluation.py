import pytest

from app.evaluation.metrics import (
    citation_presence,
    evaluate_response,
    keyword_coverage,
)


def test_keyword_coverage():
    result = keyword_coverage(
        "Revenue was reviewed using the database.",
        ["revenue", "database", "profit"],
    )

    assert result["score"] == pytest.approx(2 / 3)
    assert result["missing"] == ["profit"]


def test_citation_presence():
    assert citation_presence(
        "The policy requires approval. "
        "[Source: policy.pdf, page 2]"
    )

    assert not citation_presence(
        "The policy requires approval."
    )


def test_evaluate_response_passes_expected_checks():
    response = {
        "status": "completed",
        "verification_status": "passed",
        "final_report": (
            "The risk review recommends next steps."
        ),
        "tasks": [
            {"task_type": "risk_review"}
        ],
    }

    result = evaluate_response(
        response=response,
        expected_terms=["risk", "recommends"],
        expected_task_types=["risk_review"],
        require_citation=False,
    )

    assert result["passed"] is True
    assert result["task_coverage_passed"] is True


def test_missing_required_citation_fails():
    response = {
        "status": "completed",
        "verification_status": "passed",
        "final_report": "The policy says approval is required.",
        "tasks": [
            {"task_type": "document_research"}
        ],
    }

    result = evaluate_response(
        response=response,
        expected_terms=["policy"],
        expected_task_types=["document_research"],
        require_citation=True,
    )

    assert result["passed"] is False
    assert result["citation_check_passed"] is False
