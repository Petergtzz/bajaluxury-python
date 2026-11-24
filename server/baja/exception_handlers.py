from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from baja.exceptions import BajaError


async def baja_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, BajaError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "detail": exc.message},
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        content={
            "error": "RequestValidationError",
            "detail": jsonable_encoder(exc.errors(), custom_encoder={Exception: str}),
        },
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    status = HTTPStatus(exc.status_code)
    error = (
        "ResourceNotFound"
        if status == HTTPStatus.NOT_FOUND
        else "".join(word.capitalize() for word in status.phrase.split())
    )
    detail = exc.detail.capitalize() if exc.detail == status.phrase else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error, "detail": detail},
        headers=exc.headers,
    )


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(BajaError, baja_error_handler)
