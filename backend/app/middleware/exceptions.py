from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def _error_response(status_code: int, code: str, message: str, details=None):
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }

    if details is not None:
        payload["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=payload)


async def app_exception_handler(request: Request, exc: AppException):
    return _error_response(exc.status_code, exc.code, exc.message)


async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(exc.status_code, "HTTP_ERROR", message)


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return _error_response(
        422,
        "VALIDATION_ERROR",
        "One or more fields failed validation.",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    return _error_response(
        500,
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred.",
    )
