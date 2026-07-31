"""Add job_postings, matches, and generated_artifacts tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # job_postings
    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("required_skills", postgresql.JSONB, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_id", "source", name="uq_job_external_source"),
    )

    # matches
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # generated_artifacts
    artifact_enum = sa.Enum("rewrite", "cover_letter", "interview_questions", "skill_gap", name="artifacttype")
    op.create_table(
        "generated_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", artifact_enum, nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generated_artifacts")
    op.drop_table("matches")
    op.drop_table("job_postings")
    sa.Enum("rewrite", "cover_letter", "interview_questions", "skill_gap", name="artifacttype").drop(op.get_bind(), checkfirst=False)
