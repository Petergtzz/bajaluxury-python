from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class LoginCodeAuthenticate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: str = Field(min_length=1, max_length=32)
