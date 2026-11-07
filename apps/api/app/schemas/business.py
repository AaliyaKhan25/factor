"""Business schemas."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BusinessCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    upi_id: str | None = Field(default=None, pattern=r"^[\w.\-]{2,}@[A-Za-z]{2,}$")
    language: Literal["en", "hi"] = "en"
    template: Literal["general", "rental", "handmade", "tiffin"] = "general"
