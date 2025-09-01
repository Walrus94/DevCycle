"""Complete DevCycle database schema - consolidated migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user table (FastAPI Users base table) with all fields
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for user table
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_index(op.f("ix_user_id"), "user", ["id"], unique=True)
    op.create_index(op.f("ix_user_role"), "user", ["role"], unique=False)

    # Create audit_logs table (non-auth related)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for audit_logs table
    op.create_index(
        op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_resource"), "audit_logs", ["resource"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False
    )

    # Create agents table
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("capabilities", sa.Text(), nullable=False),  # JSON string
        sa.Column("configuration", sa.Text(), nullable=False),  # JSON string
        sa.Column("metadata_json", sa.Text(), nullable=False),  # JSON string
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="offline"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default=0),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("uptime_seconds", sa.Integer(), nullable=False, server_default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for agents table
    op.create_index(op.f("ix_agents_id"), "agents", ["id"], unique=True)
    op.create_index(op.f("ix_agents_name"), "agents", ["name"], unique=True)
    op.create_index(
        op.f("ix_agents_agent_type"), "agents", ["agent_type"], unique=False
    )
    op.create_index(op.f("ix_agents_status"), "agents", ["status"], unique=False)

    # Create agent_tasks table
    op.create_table(
        "agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),  # JSON string
        sa.Column("result", sa.Text(), nullable=True),  # JSON string
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for agent_tasks table
    op.create_index(op.f("ix_agent_tasks_id"), "agent_tasks", ["id"], unique=True)
    op.create_index(
        op.f("ix_agent_tasks_agent_id"), "agent_tasks", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_tasks_task_type"), "agent_tasks", ["task_type"], unique=False
    )
    op.create_index(
        op.f("ix_agent_tasks_status"), "agent_tasks", ["status"], unique=False
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("agent_tasks")
    op.drop_table("agents")
    op.drop_table("audit_logs")
    op.drop_table("user")
