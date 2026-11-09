"""Add inventory ledger, sheet sync, courier tracking, and voice proposals."""
from alembic import op
import sqlalchemy as sa

revision = "20261109_factor_ops"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(240), nullable=False, server_default=""),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for col in ("business_id", "catalog_item_id", "created_at"):
        op.create_index(f"ix_stock_logs_{col}", "stock_logs", [col])

    op.create_table(
        "sheet_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("spreadsheet_id", sa.String(128), nullable=False),
        sa.Column("spreadsheet_url", sa.String(500), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=False, server_default=""),
        sa.Column("sync_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("business_id", name="uq_sheet_connection_business"),
    )
    op.create_index("ix_sheet_connections_business_id", "sheet_connections", ["business_id"])

    op.create_table(
        "courier_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default="generic"),
        sa.Column("credentials_encrypted", sa.String(4000), nullable=False, server_default=""),
        sa.Column("webhook_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("webhook_secret_encrypted", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_courier_connections_business_id", "courier_connections", ["business_id"])
    op.create_index("ix_courier_connections_webhook_token_hash", "courier_connections", ["webhook_token_hash"])

    op.create_table(
        "courier_shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("courier_connection_id", sa.Integer(), sa.ForeignKey("courier_connections.id"), nullable=True),
        sa.Column("courier_name", sa.String(100), nullable=False),
        sa.Column("awb", sa.String(100), nullable=False),
        sa.Column("tracking_url", sa.String(1000), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="label_created"),
        sa.Column("status_detail", sa.String(300), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_courier_shipment_order"),
    )
    for col in ("business_id", "order_id", "awb"):
        op.create_index(f"ix_courier_shipments_{col}", "courier_shipments", [col])

    op.create_table(
        "courier_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("courier_connections.id"), nullable=False),
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("connection_id", "event_id", name="uq_courier_event_id"),
    )
    op.create_index("ix_courier_webhook_events_connection_id", "courier_webhook_events", ["connection_id"])

    op.create_table(
        "voice_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for col in ("token_hash", "business_id", "actor_user_id", "session_id", "expires_at"):
        op.create_index(f"ix_voice_proposals_{col}", "voice_proposals", [col])


def downgrade() -> None:
    op.drop_table("voice_proposals")
    op.drop_table("courier_webhook_events")
    op.drop_table("courier_shipments")
    op.drop_table("courier_connections")
    op.drop_table("sheet_connections")
    op.drop_table("stock_logs")
