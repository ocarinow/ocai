"""Public errors that never serialize exception or request contents."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


def error_response(status: int, code: str, message: str, request_id: str) -> JSONResponse:
    """Build an error using only explicitly public messages."""
    body = ErrorEnvelope(error=ErrorDetail(code=code, message=message, request_id=request_id))
    return JSONResponse(body.model_dump(), status_code=status)


async def _validation_error(request: Request, _exc: Exception) -> JSONResponse:
    return error_response(
        422, "invalid_request", "The request is invalid.", request.state.request_id
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    status = exc.status_code if isinstance(exc, HTTPException) else 500
    messages = {
        401: ("unauthenticated", "Authentication is required."),
        403: ("forbidden", "This operation is not permitted."),
        404: ("not_found", "The resource was not found."),
        405: ("method_not_allowed", "The method is not allowed."),
    }
    code, message = messages.get(status, ("request_failed", "The request could not be completed."))
    response = error_response(status, code, message, request.state.request_id)
    if status == 401:
        response.headers["www-authenticate"] = "Bearer"
    # Only controlled protocol headers survive, not arbitrary exception headers.
    if isinstance(exc, HTTPException) and exc.headers:
        for name, value in exc.headers.items():
            if name.lower() == "allow":
                response.headers["allow"] = value
    return response


def install_error_handlers(app: FastAPI) -> None:
    """Install safe validation and HTTP errors on one explicit app instance."""
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)
