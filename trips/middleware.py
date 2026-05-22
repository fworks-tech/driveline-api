import logging
import uuid
from typing import Callable

from django.http import HttpRequest, JsonResponse

from trips.error_handler import TripPlanningError

logger = logging.getLogger(__name__)


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
            request_id = str(uuid.uuid4())
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
            request_id = str(uuid.uuid4())
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
