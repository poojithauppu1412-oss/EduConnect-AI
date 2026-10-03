from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    education: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    branch: str | None = Field(default=None, max_length=200)
    graduation_year: int | None = Field(default=None, ge=1950)
    skills: list[str] | None = Field(default=None, max_length=80)
    certifications: list[str] | None = Field(default=None, max_length=50)
    experience_summary: str | None = Field(default=None, max_length=5000)
    experience_years: float | None = Field(default=None, ge=0, le=80)
    preferred_career: str | None = Field(default=None, max_length=200)
    preferred_industry: str | None = Field(default=None, max_length=200)
    preferred_location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = Field(default=None, max_length=40)
    government_private_preference: str | None = Field(default=None, max_length=40)
    internship_preference: bool | None = None
    exam_preferences: dict[str, Any] | None = None

    @field_validator(
        "name",
        "education",
        "degree",
        "branch",
        "experience_summary",
        "preferred_career",
        "preferred_industry",
        "preferred_location",
        "work_mode",
        "government_private_preference",
    )
    @classmethod
    def trim_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("graduation_year")
    @classmethod
    def validate_graduation_year(cls, value: int | None) -> int | None:
        if value is not None and value > datetime.now(timezone.utc).year + 10:
            raise ValueError("Graduation year cannot be more than ten years in the future.")
        return value

    @field_validator("skills", "certifications")
    @classmethod
    def normalize_text_lists(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            folded = item.casefold()
            if item and folded not in seen:
                normalized.append(item)
                seen.add(folded)
        return normalized


class ProfileResponse(BaseModel):
    email: str
    name: str | None
    education: str | None
    degree: str | None
    branch: str | None
    graduation_year: int | None
    skills: list[str]
    certifications: list[str]
    experience_summary: str | None
    experience_years: float | None
    preferred_career: str | None
    preferred_industry: str | None
    preferred_location: str | None
    work_mode: str | None
    government_private_preference: str | None
    internship_preference: bool
    exam_preferences: dict[str, Any]
    completion_percent: int
    updated_at: datetime