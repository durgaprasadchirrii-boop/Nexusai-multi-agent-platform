
import json
import logging
import os
import time
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    ConsoleSpanExporter,
)
from prometheus_client import Counter, Histogram

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize once per Python process.
if not isinstance(trace.get_tracer_provider(), TracerProvider):
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": "nexusai",
            "service.version": "5.0.0",
            "deployment.environment": settings.app_env,
        })
    )

    # Local development: spans are printed to the server console.
    # In a hosted environment, configure an OTLP exporter instead.
    if os.getenv("NEXUSAI_TRACE_CONSOLE", "true").lower() == "true":
        provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("nexusai", "5.0.0")

RUNS = Counter(
    "nexusai_runs_total",
    "Total NexusAI workflow runs",
    ["status"],
)

HTTP_REQUESTS = Counter(
    "nexusai_http_requests_total",
    "HTTP requests handled",
    ["method", "route", "status"],
)

HTTP_DURATION = Histogram(
    "nexusai_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
)

NODE_DURATION = Histogram(
    "nexusai_node_duration_seconds",
    "Workflow node duration in seconds",
    ["node"],
)

TASKS = Counter(
    "nexusai_tasks_total",
    "Specialist task outcomes",
    ["task_type", "status"],
)

REVISIONS = Counter(
    "nexusai_report_revisions_total",
    "Number of report revisions",
)

APPROVALS = Counter(
    "nexusai_approval_decisions_total",
    "Human approval decisions",
    ["decision"],
)

EVENT_PATH = Path("data") / "observability.jsonl"
_event_lock = Lock()


def record_event(event: dict[str, Any]) -> None:
    """Append a JSON event for local debugging and audit analysis."""
    EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": time.time(),
        "service": "nexusai",
        **event,
    }

    with _event_lock:
        with EVENT_PATH.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, default=str) + "\n")


def observe_node(node_name: str):
    """Trace a workflow node and measure its execution time."""
    def decorator(function: Callable):
        @wraps(function)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()

            with tracer.start_as_current_span(
                f"nexusai.node.{node_name}"
            ) as span:
                span.set_attribute("nexusai.node", node_name)

                try:
                    result = function(*args, **kwargs)
                    span.set_attribute("nexusai.outcome", "success")
                    return result
                except Exception as exc:
                    span.set_attribute("nexusai.outcome", "error")
                    span.record_exception(exc)
                    raise
                finally:
                    elapsed = time.perf_counter() - started
                    NODE_DURATION.labels(node=node_name).observe(elapsed)

                    record_event({
                        "event": "node_finished",
                        "node": node_name,
                        "duration_seconds": round(elapsed, 4),
                    })

        return wrapper
    return decorator
