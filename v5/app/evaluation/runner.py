
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.evaluation.metrics import evaluate_response

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "app" / "evaluation" / "dataset.jsonl"
OUTPUT_DIR = ROOT / "evaluation_results"


def load_dataset():
    cases = []
    with DATASET.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                cases.append(json.loads(line))
    return cases


def run_evaluation():
    base_url = os.getenv(
        "NEXUSAI_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    with httpx.Client(timeout=300.0) as client:
        for case in load_dataset():
            started = time.perf_counter()

            try:
                response = client.post(
                    f"{base_url}/api/analyze",
                    json={"request": case["request"]},
                )
                response.raise_for_status()
                payload = response.json()

                scores = evaluate_response(
                    response=payload,
                    expected_terms=case.get("expected_terms", []),
                    expected_task_types=case.get(
                        "expected_task_types", []
                    ),
                    require_citation=case.get(
                        "require_citation", False
                    ),
                )

                result = {
                    "case_id": case["id"],
                    "duration_seconds": round(
                        time.perf_counter() - started, 3
                    ),
                    "error": None,
                    **scores,
                }

            except Exception as exc:
                result = {
                    "case_id": case["id"],
                    "duration_seconds": round(
                        time.perf_counter() - started, 3
                    ),
                    "passed": False,
                    "error": str(exc),
                }

            results.append(result)
            print(json.dumps(result, indent=2))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = OUTPUT_DIR / f"evaluation-{timestamp}.json"

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "passed": sum(item.get("passed", False) for item in results),
        "failed": sum(not item.get("passed", False) for item in results),
        "results": results,
    }

    output_file.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nEvaluation summary")
    print(f"Cases: {summary['case_count']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    run_evaluation()
