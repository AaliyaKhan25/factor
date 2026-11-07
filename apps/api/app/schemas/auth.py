"""Signup and login schemas.

Signup has no role field and rejects unknown fields, so nobody can pick a role at signup.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
