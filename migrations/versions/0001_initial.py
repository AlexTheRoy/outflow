"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-13

Creates all core tables. You can regenerate/replace this at any time with:
    alembic revision --autogenerate -m "message"
This hand-written version lets you run `alembic upgrade head` immediately.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="trial"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_campaigns_org_id", "campaigns", ["org_id"])

    op.create_table(
        "campaign_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.String(length=36),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product", sa.Text(), server_default=""),
        sa.Column("value_prop", sa.Text(), server_default=""),
        sa.Column("pricing", sa.Text(), server_default=""),
        sa.Column("icp", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="heuristic"),
    )
    op.create_index(
        "ix_campaign_profiles_campaign_id", "campaign_profiles", ["campaign_id"]
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.String(length=36),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), server_default=""),
        sa.Column("company", sa.String(length=255), server_default=""),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("linkedin_url", sa.String(length=512), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("fit_score", sa.Float(), server_default="0"),
        sa.Column("intent_score", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(length=50), server_default="new"),
        sa.Column("source", sa.String(length=50), server_default="stub"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_leads_campaign_id", "leads", ["campaign_id"])
    op.create_index("ix_leads_email", "leads", ["email"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "lead_id",
            sa.String(length=36),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("step", sa.Integer(), server_default="1"),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("body", sa.Text(), server_default=""),
        sa.Column("status", sa.String(length=50), server_default="draft"),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_messages_lead_id", "messages", ["lead_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "lead_id",
            sa.String(length=36),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_events_lead_id", "events", ["lead_id"])

    op.create_table(
        "calls",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "lead_id",
            sa.String(length=36),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_sid", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="queued"),
        sa.Column("transcript_uri", sa.String(length=1024), nullable=True),
        sa.Column("outcome", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calls_lead_id", "calls", ["lead_id"])


def downgrade() -> None:
    op.drop_table("calls")
    op.drop_table("events")
    op.drop_table("messages")
    op.drop_table("leads")
    op.drop_table("campaign_profiles")
    op.drop_table("campaigns")
    op.drop_table("organizations")
