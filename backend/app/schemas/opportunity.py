from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.models.opportunity import OPPORTUNITY_STATUSES, OPPORTUNITY_TYPES


class OpportunityOrganizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=240)
    website_url: AnyHttpUrl | None = None
    official_domain: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    organization_type: str | None = Field(default=None, max_length=80)
    location: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def require_organization_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Organization name is required.")
        return value

    @field_validator("official_domain", "description", "organization_type", "location")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class OpportunityCategoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def require_category_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Category name is required.")
        return value

    @field_validator("description")
    @classmethod
    def trim_category_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class OpportunitySkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    is_required: bool = False

    @field_validator("name")
    @classmethod
    def trim_skill_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Skill name is required.")
        return value


class OpportunitySkillResponse(BaseModel):
    name: str
    is_required: bool


class OpportunityWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=30000)
    organization: OpportunityOrganizationInput
    category: OpportunityCategoryInput
    opportunity_type: str
    qualification: str | None = Field(default=None, max_length=10000)
    branch: str | None = Field(default=None, max_length=240)
    experience_required: str | None = Field(default=None, max_length=200)
    age_limit: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=300)
    work_mode: str | None = Field(default=None, max_length=40)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    stipend_amount: Decimal | None = Field(default=None, ge=0)
    compensation_currency: str = Field(default="INR", min_length=3, max_length=3)
    application_fee: Decimal | None = Field(default=None, ge=0)
    opening_date: date | None = None
    closing_date: date | None = None
    exam_date: date | None = None
    result_date: date | None = None
    eligibility: dict[str, Any] = Field(default_factory=dict)
    skills: list[OpportunitySkillInput] = Field(default_factory=list, max_length=80)
    documents_required: list[str] = Field(default_factory=list, max_length=100)
    selection_process: list[str] = Field(default_factory=list, max_length=100)
    application_steps: list[str] = Field(default_factory=list, max_length=100)
    official_url: AnyHttpUrl
    source_url: AnyHttpUrl
    source_name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=60)
    notification_number: str | None = Field(default=None, max_length=160)
    status: str = "UPCOMING"
    publish_after_review: bool = False

    @field_validator("title", "description", "source_name", "source_type")
    @classmethod
    def require_opportunity_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator(
        "qualification",
        "branch",
        "experience_required",
        "age_limit",
        "location",
        "work_mode",
        "notification_number",
    )
    @classmethod
    def trim_optional_opportunity_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("opportunity_type")
    @classmethod
    def validate_opportunity_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in OPPORTUNITY_TYPES:
            raise ValueError("Unsupported opportunity type.")
        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in OPPORTUNITY_STATUSES:
            raise ValueError("Unsupported opportunity status.")
        return normalized

    @field_validator("compensation_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return normalized

    @field_validator("documents_required", "selection_process", "application_steps")
    @classmethod
    def trim_list_entries(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]

    @field_validator("skills")
    @classmethod
    def deduplicate_skills(
        cls, values: list[OpportunitySkillInput]
    ) -> list[OpportunitySkillInput]:
        unique: dict[str, OpportunitySkillInput] = {}
        for item in values:
            key = item.name.casefold()
            existing = unique.get(key)
            if existing is None or item.is_required:
                unique[key] = item
        return list(unique.values())

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        if self.opening_date and self.closing_date and self.opening_date > self.closing_date:
            raise ValueError("Opening date cannot be after closing date.")
        if self.publish_after_review and self.status in {"CLOSED", "CANCELLED"}:
            raise ValueError("Closed or cancelled opportunities cannot be published.")
        return self


class OpportunityResponse(BaseModel):
    id: UUID
    title: str
    description: str
    organization_name: str | None
    organization_website_url: str | None
    category_name: str
    category_slug: str
    opportunity_type: str
    qualification: str | None
    branch: str | None
    experience_required: str | None
    age_limit: str | None
    location: str | None
    work_mode: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    stipend_amount: Decimal | None
    compensation_currency: str
    application_fee: Decimal | None
    opening_date: date | None
    closing_date: date | None
    exam_date: date | None
    result_date: date | None
    eligibility: dict[str, Any]
    skills: list[OpportunitySkillResponse]
    documents_required: list[Any]
    selection_process: list[Any]
    application_steps: list[Any]
    official_url: str | None
    source_url: str | None
    source_name: str | None
    source_type: str | None
    status: str
    published_at: datetime | None
    last_verified_at: datetime | None
    expires_at: datetime | None
    is_stale: bool


class OpportunityPage(BaseModel):
    items: list[OpportunityResponse]
    total: int
    page: int
    page_size: int
    page_count: int


class OpportunitySaveResponse(BaseModel):
    opportunity_id: UUID
    saved: bool


class OpportunityCategoryOption(BaseModel):
    name: str
    slug: str


class OpportunityFilters(BaseModel):
    q: str | None = None
    category: str | None = None
    opportunity_type: str | None = None
    government_private: str | None = None
    qualification: str | None = None
    branch: str | None = None
    experience: str | None = None
    location: str | None = None
    work_mode: str | None = None
    compensation_currency: str | None = None
    min_compensation: Decimal | None = None
    max_compensation: Decimal | None = None
    deadline_after: date | None = None
    deadline_before: date | None = None
    organization: str | None = None
    skill: str | None = None
    exam_type: str | None = None
    sort: str = "newest"
    page: int = 1
    page_size: int = 20