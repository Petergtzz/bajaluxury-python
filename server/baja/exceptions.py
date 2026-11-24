from typing import ClassVar, Literal

from pydantic import BaseModel, Field, create_model


class BajaError(Exception):
    """An error the API answers with `{"error": <class name>, "detail": <message>}`."""

    _schema: ClassVar[type[BaseModel] | None] = None

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.headers = headers

    @classmethod
    def schema(cls) -> type[BaseModel]:
        """The response body as an OpenAPI model, so clients can branch on `error`."""
        if cls.__dict__.get("_schema") is None:
            cls._schema = create_model(
                cls.__name__,
                error=(  # type: ignore[arg-type]
                    Literal[cls.__name__],
                    Field(description="Stable error code to branch on in code."),
                ),
                detail=(str, Field(description="Message for people, may change.")),
            )
        return cls.__dict__["_schema"]  # type: ignore[no-any-return]


class BadRequest(BajaError):
    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message, 400)


class Unauthorized(BajaError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(
            message, 401, headers={"WWW-Authenticate": 'Bearer realm="baja"'}
        )


class NotPermitted(BajaError):
    def __init__(self, message: str = "Not permitted") -> None:
        super().__init__(message, 403)


class ResourceNotFound(BajaError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, 404)


class Conflict(BajaError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 409)
