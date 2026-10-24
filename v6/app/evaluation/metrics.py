
import re
from typing import Any


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def keyword_coverage(
    text: str,
    expected_terms: list[str],
) -> dict[str, Any]:
    """
    Deterministic lexical check, not a semantic correctness score.
    """
    normalized = normalize(text)
    matched = [
        term for term in expected_terms
        if normalize(term) in normalized
    ]
    missing = [
        term for term in expected_terms
        if normalize(term) not in normalized
    ]

    score = (
        len(matched) / len(expected_terms)
        if expected_terms else 1.0
    )

    return {
        "score": round(score, 3),
        "matched": matched,
        "missing": missing,
    }


def citation_presence(text: str) -> bool:
    """Check for a basic source-citation pattern."""
    pattern = r"\[Source:\s*[^,\]]+,\s*(?:page|chunk)\s+\d+\]"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def evaluate_response(
    response: dict,
    expected_terms: list[str],
    expected_task_types: list[str] | None = None,
    require_citation: bool = False,
) -> dict[str, Any]:
    report = response.get("final_report", "")
    task_types = {
        task.get("task_type")
        for task in response.get("tasks", [])
    }

    keyword_result = keyword_coverage(report, expected_terms)
    citation_ok = citation_presence(report) if require_citation else True
    task_coverage = (
        all(task_type in task_types for task_type in expected_task_types)
        if expected_task_types else True
    )

    return {
        "status": response.get("status", "unknown"),
        "verification_status": response.get("verification_status", "unknown"),
        "keyword_coverage": keyword_result,
        "citation_required": require_citation,
        "citation_present": citation_presence(report),
        "citation_check_passed": citation_ok,
        "expected_task_types": expected_task_types or [],
        "actual_task_types": sorted(task_types),
        "task_coverage_passed": task_coverage,
        "passed": (
            keyword_result["score"] >= 0.5
            and citation_ok
            and task_coverage
            and response.get("status") in {
                "completed", "approved_with_warnings"
            }
        ),
    }
