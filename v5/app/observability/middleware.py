
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.telemetry import (
    HTTP_DURATION,
    HTTP_REQUESTS,
    record_event,
    tracer,
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        route = request.url.path
        status_code = 500

        with tracer.start_as_current_span("nexusai.http.request") as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("http.route", route)

            try:
                response = await call_next(request)
                status_code = response.status_code
                span.set_attribute("http.response.status_code", status_code)
                return response
            except Exception as exc:
                span.record_exception(exc)
                raise
            finally:
                duration = time.perf_counter() - started

                HTTP_REQUESTS.labels(
                    method=request.method,
                    route=route,
                    status=str(status_code),
                ).inc()

                HTTP_DURATION.labels(
                    method=request.method,
                    route=route,
                ).observe(duration)

                record_event({
                    "event": "http_request",
                    "method": request.method,
                    "route": route,
                    "status_code": status_code,
                    "duration_seconds": round(duration, 4),
                })
