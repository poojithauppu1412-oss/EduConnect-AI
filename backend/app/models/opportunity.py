from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

OPPORTUNITY_TYPES = (
    "GOVERNMENT_JOB",
    "PRIVATE_JOB",
    "INTERNSHIP",
    "APPRENTICESHIP",
    "SCHOLARSHIP",
    "FELLOWSHIP",
    "EXAM",
    "ENTRANCE_EXAM",
    "HACKATHON",
    "COMPETITION",
    "RESEARCH",
    "GOVERNMENT_SCHEME",
    "SKILL_PROGRAM",
    "OTHER",
)
OPPORTUNITY_STATUSES = (
    "UPCOMING",
    "OPEN",
    "CLOSING_SOON",
    "CLOSED",
    "CANCELLED",
    "RESULT_AVAILABLE",
    "UPDATED",
)


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    website_url: Mapped[str | None] = mapped_column(String(2048))
    official_domain: Mapped[str | None] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    organization_type: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(200))


class OpportunityCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity_categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "opportunity_type IN (" + ", ".join(f"'{item}'" for item in OPPORTUNITY_TYPES) + ")",
            name="valid_opportunity_type",
        ),
        CheckConstraint(
            "status IN (" + ", ".join(f"'{item}'" for item in OPPORTUNITY_STATUSES) + ")",
            name="valid_opportunity_status",
        ),
        UniqueConstraint(
            "organization_id",
            "notification_number",
            "closing_date",
            name="uq_opportunity_notification_identity",
        ),
        Index(
            "uq_opportunities_official_url",
            "official_url",
            unique=True,
            postgresql_where=text("official_url IS NOT NULL"),
        ),
        Index(
            "uq_opportunities_identity_hash",
            "identity_hash",
            unique=True,
            postgresql_where=text("identity_hash IS NOT NULL"),
        ),
        Index("ix_opportunities_opening_date", "opening_date"),
        Index("ix_opportunities_closing_date", "closing_date"),
        Index("ix_opportunities_status_type", "status", "opportunity_type"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("opportunity_categories.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    qualification: Mapped[str | None] = mapped_column(Text)
    branch: Mapped[str | None] = mapped_column(String(240))
    experience_required: Mapped[str | None] = mapped_column(String(200))
    age_limit: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(300), index=True)
    work_mode: Mapped[str | None] = mapped_column(String(40))
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    stipend_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    compensation_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    application_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    opening_date: Mapped[date | None] = mapped_column(Date)
    closing_date: Mapped[date | None] = mapped_column(Date, index=True)
    exam_date: Mapped[date | None] = mapped_column(Date)
    result_date: Mapped[date | None] = mapped_column(Date)
    eligibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    documents_required: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    selection_process: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    application_steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    official_url: Mapped[str | None] = mapped_column(String(2048))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_type: Mapped[str | None] = mapped_column(String(60))
    notification_number: Mapped[str | None] = mapped_column(String(160))
    identity_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UPCOMING", server_default="UPCOMING", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OpportunitySkill(Base):
    __tablename__ = "opportunity_skills"

    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class OpportunitySource(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "opportunity_sources"
    __table_args__ = (UniqueConstraint("opportunity_id", "source_url", name="uq_opportunity_source_url"),)

    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(200))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class OpportunityDocument(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "opportunity_documents"

    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(80))
    content_type: Mapped[str | None] = mapped_column(String(120))
    checksum: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SavedOpportunity(Base):
    __tablename__ = "saved_opportunities"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED', 'APPLIED', 'ASSESSMENT', 'INTERVIEW', 'OFFER', 'REJECTED', 'WITHDRAWN')",
            name="valid_application_status",
        ),
        Index("ix_applications_user_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PLANNED", server_default="PLANNED")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)