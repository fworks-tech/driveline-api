import contextvars
import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, JsonResponse

from trips.error_handler import TripPlanningError

logger = logging.getLogger(__name__)

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=None
)


class RequestLoggingMiddleware:
    """Django middleware for structured HTTP request logging.

    Logs method, path, status code, elapsed time, and request_id for every request.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Read inbound X-Request-ID header; fall back to generating UUID
        request_id = request.META.get("HTTP_X_REQUEST_ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request object and context var for access throughout request lifecycle
        request.request_id = request_id
        request_id_var.set(request_id)

        start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)

        # Write X-Request-ID header to response for client correlation
        response["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "request_id": request_id,
            },
        )
        return response


class ErrorHandlingMiddleware:
    """Django middleware for structured error handling and logging.

    Catches unhandled exceptions and returns a consistent error response envelope.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        try:
            response = self.get_response(request)
            return response
        except TripPlanningError as e:
            request_id = getattr(request, "request_id", str(uuid.uuid4()))
            logger.error(
                f"[{request_id}] TripPlanningError: {e.message}",
                extra={
                    "request_id": request_id,
                    "status_code": e.status_code,
                    "detail": e.detail,
                },
            )
            return JsonResponse(
                {
                    "error": e.__class__.__name__,
                    "detail": e.detail,
                    "request_id": request_id,
                },
                status=e.status_code,
            )
        except Exception as e:
            request_id = getattr(request, "request_id", str(uuid.uuid4()))
            logger.error(
                f"[{request_id}] Unhandled exception: {type(e).__name__}: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True,
            )
            return JsonResponse(
                {
                    "error": "internal_server_error",
                    "detail": "An unexpected error occurred. Please try again later.",
                    "request_id": request_id,
                },
                status=500,
            )
