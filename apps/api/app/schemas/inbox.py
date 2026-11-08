"""Inbox schemas."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SimulateIn(BaseModel):
    """A pretend incoming DM, for demos and testing without Meta access."""
    model_config = ConfigDict(extra="forbid")
    channel: Literal["instagram", "whatsapp"] = "instagram"
    handle: str = Field(min_length=2, max_length=120)
    name: str = Field(default="", max_length=120)
    text: str = Field(min_length=1, max_length=2000)


class ReplyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)


class ConvStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["agent", "needs_owner", "resolved"]


class ChannelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: Literal["instagram", "whatsapp"]
    label: str = Field(default="", max_length=120)


class GoogleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential: str = Field(min_length=10)
