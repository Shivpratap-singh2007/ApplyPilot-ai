"""Add user profiles, resumes, applications, approval snapshots, transitions, and SaaS usage tracking.

Revision ID: 20261110_0002
Revises: 20261110_0001
Create Date: 2026-11-10 21:52:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261110_0002"
down_revision: str | Sequence[str] | None = "20261110_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("plan_tier", sa.String(length=40), nullable=False, server_default="free_local"))
        batch_op.add_column(sa.Column("preferred_ollama_model", sa.String(length=120), nullable=True))

    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_rel_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("extracted_data_json", sa.JSON(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_preferred", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_resumes_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resumes")),
    )
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.String(length=400), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=40), nullable=True),
        sa.Column("college", sa.String(length=240), nullable=True),
        sa.Column("degree", sa.String(length=120), nullable=True),
        sa.Column("branch", sa.String(length=160), nullable=True),
        sa.Column("current_semester", sa.String(length=60), nullable=True),
        sa.Column("graduation_year", sa.String(length=20), nullable=True),
        sa.Column("cgpa", sa.String(length=30), nullable=True),
        sa.Column("school_education", sa.JSON(), nullable=False),
        sa.Column("technical_skills", sa.JSON(), nullable=False),
        sa.Column("programming_languages", sa.JSON(), nullable=False),
        sa.Column("projects", sa.JSON(), nullable=False),
        sa.Column("work_experience", sa.JSON(), nullable=False),
        sa.Column("internships", sa.JSON(), nullable=False),
        sa.Column("certifications", sa.JSON(), nullable=False),
        sa.Column("achievements", sa.JSON(), nullable=False),
        sa.Column("github_url", sa.String(length=500), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("portfolio_url", sa.String(length=500), nullable=True),
        sa.Column("preferred_roles", sa.JSON(), nullable=False),
        sa.Column("preferred_locations", sa.JSON(), nullable=False),
        sa.Column("work_mode_preference", sa.String(length=40), nullable=True),
        sa.Column("internship_duration", sa.String(length=100), nullable=True),
        sa.Column("availability", sa.String(length=160), nullable=True),
        sa.Column("preferred_resume_id", sa.String(length=36), nullable=True),
        sa.Column("team_name", sa.String(length=160), nullable=True),
        sa.Column("team_members", sa.JSON(), nullable=False),
        sa.Column("hackathon_project_idea", sa.Text(), nullable=True),
        sa.Column("hackathon_tech_stack", sa.JSON(), nullable=False),
        sa.Column("hackathon_repo_url", sa.String(length=500), nullable=True),
        sa.Column("hackathon_project_description", sa.Text(), nullable=True),
        sa.Column("verified_fields", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["preferred_resume_id"], ["resumes.id"], name=op.f("fk_user_profiles_preferred_resume_id_resumes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_profiles_user_id")),
    )
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("resume_id", sa.String(length=36), nullable=True),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("application_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("company_or_org", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("detected_fields_json", sa.JSON(), nullable=False),
        sa.Column("draft_matches_json", sa.JSON(), nullable=False),
        sa.Column("edited_values_json", sa.JSON(), nullable=False),
        sa.Column("validation_warnings_json", sa.JSON(), nullable=False),
        sa.Column("missing_fields_json", sa.JSON(), nullable=False),
        sa.Column("draft_screenshot_rel_path", sa.String(length=500), nullable=True),
        sa.Column("confirmation_screenshot_rel_path", sa.String(length=500), nullable=True),
        sa.Column("confirmation_reference", sa.String(length=200), nullable=True),
        sa.Column("confirmation_evidence_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("ai_provider_used", sa.String(length=120), nullable=True),
        sa.Column("allow_localhost", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], name=op.f("fk_applications_resume_id_resumes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_applications_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    op.create_index(op.f("ix_applications_created_at"), "applications", ["created_at"], unique=False)
    op.create_index(op.f("ix_applications_status"), "applications", ["status"], unique=False)
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)

    op.create_table(
        "approval_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("resume_id", sa.String(length=36), nullable=True),
        sa.Column("resume_sha256", sa.String(length=64), nullable=True),
        sa.Column("approved_values_json", sa.JSON(), nullable=False),
        sa.Column("form_structure_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("is_consumed", sa.Boolean(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name=op.f("fk_approval_snapshots_application_id_applications"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_approval_snapshots_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_snapshots")),
    )
    op.create_index(op.f("ix_approval_snapshots_application_id"), "approval_snapshots", ["application_id"], unique=False)
    op.create_index(op.f("ix_approval_snapshots_user_id"), "approval_snapshots", ["user_id"], unique=False)

    op.create_table(
        "application_state_transitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name=op.f("fk_application_state_transitions_application_id_applications"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_state_transitions")),
    )
    op.create_index(op.f("ix_application_state_transitions_application_id"), "application_state_transitions", ["application_id"], unique=False)
    op.create_index(op.f("ix_application_state_transitions_created_at"), "application_state_transitions", ["created_at"], unique=False)

    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_usage_events_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_events")),
    )
    op.create_index(op.f("ix_usage_events_created_at"), "usage_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_usage_events_event_type"), "usage_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_usage_events_user_id"), "usage_events", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("usage_events")
    op.drop_table("application_state_transitions")
    op.drop_table("approval_snapshots")
    op.drop_table("applications")
    op.drop_table("user_profiles")
    op.drop_table("resumes")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("preferred_ollama_model")
        batch_op.drop_column("plan_tier")

