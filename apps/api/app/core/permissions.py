"""Permission toggles and role presets.

Signup creates a plain account. Joining a business by code creates an Employee in
"pending" state with no access. Only the owner (role "admin") can approve a member and
grant a role or permissions. The "admin" role itself can never be assigned to someone else.

The four stored roles come from the AssetFlow problem statement. The owner-facing presets
(helper, packer, manager) are shortcuts that map to them.
"""

# Only the owner has these, they cannot be granted to anyone else.
ADMIN_ONLY = frozenset({"manage_team", "manage_setup", "manage_audit_cycles"})

# Permissions the owner may switch on for a team member.
ASSIGNABLE = frozenset(
    {
        "book_resources",
        "raise_cases",          # maintenance, rework, disputes
        "request_returns",      # initiate return or transfer requests
        "view_orders",
        "manage_orders",
        "reply_to_chats",
        "confirm_payments",
        "edit_prices",
        "manage_assets",        # register and edit assets
        "allocate_assets",
        "approve_transfers",
        "approve_returns",
        "approve_cases",
        "resolve_discrepancies",
        "audit_assets",         # mark assets Verified, Missing or Damaged
        "view_reports",
    }
)

ALL_PERMISSIONS = ADMIN_ONLY | ASSIGNABLE

ROLE_PRESETS: dict[str, frozenset[str]] = {
    "admin": ALL_PERMISSIONS,
    "asset_manager": frozenset(
        {
            "manage_assets", "allocate_assets", "approve_transfers", "approve_returns",
            "approve_cases", "resolve_discrepancies", "audit_assets", "book_resources",
            "raise_cases", "request_returns", "view_orders", "manage_orders",
        }
    ),
    "dept_head": frozenset(
        {"approve_transfers", "book_resources", "raise_cases", "request_returns", "view_orders"}
    ),
    "employee": frozenset({"book_resources", "raise_cases", "request_returns"}),
}

ASSIGNABLE_ROLES = ("employee", "dept_head", "asset_manager")

# Owner-facing shortcuts: name -> (stored role, extra permissions)
UI_PRESETS: dict[str, tuple[str, frozenset[str]]] = {
    "helper": ("employee", frozenset({"view_orders", "reply_to_chats"})),
    "packer": ("employee", frozenset({"view_orders", "manage_orders"})),
    "manager": ("asset_manager", frozenset({"confirm_payments", "reply_to_chats", "view_reports"})),
}


def effective_permissions(role: str, extras: list[str] | None = None) -> frozenset[str]:
    """Permissions a member actually has: the role's preset plus any owner-granted extras."""
    if role == "admin":
        return ALL_PERMISSIONS
    granted = ROLE_PRESETS.get(role, frozenset())
    return granted | (frozenset(extras or []) & ASSIGNABLE)
