"""Team schemas: joining by code and approving members."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..core.permissions import ASSIGNABLE, UI_PRESETS


class JoinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=4, max_length=32)


class MemberAccess(BaseModel):
    """What the owner grants when approving or editing a member.

    Give a preset (helper, packer, manager) or a role, plus optional extra permissions.
    "admin" is not an allowed role and admin-only permissions cannot be granted.
    """

    model_config = ConfigDict(extra="forbid")

    preset: Literal["helper", "packer", "manager"] | None = None
    role: Literal["employee", "dept_head", "asset_manager"] | None = None
    permissions: list[str] = []

    @field_validator("permissions")
    @classmethod
    def _only_assignable(cls, value: list[str]) -> list[str]:
        unknown = set(value) - ASSIGNABLE
        if unknown:
            raise ValueError(f"These permissions cannot be granted: {sorted(unknown)}")
        return sorted(set(value))

    @model_validator(mode="after")
    def _preset_or_role(self):
        if self.preset and self.role:
            raise ValueError("Give either a preset or a role, not both")
        return self

    def resolve(self) -> tuple[str, list[str]]:
        """Return (stored role, extra permissions)."""
        extras = set(self.permissions)
        if self.preset:
            role, preset_extras = UI_PRESETS[self.preset]
            return role, sorted(extras | preset_extras)
        return self.role or "employee", sorted(extras)
