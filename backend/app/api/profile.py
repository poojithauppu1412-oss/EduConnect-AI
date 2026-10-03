from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_local_user
from backend.app.db.session import get_db
from backend.app.models.identity import Profile, Skill, User, UserSkill
from backend.app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_or_create_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


def _profile_completion(profile: Profile, skills: list[str]) -> int:
    experience_filled = (
        bool(profile.experience_summary and profile.experience_summary.strip())
        or profile.experience_years is not None
    )
    required_values: list[Any] = [
        profile.name,
        profile.education,
        profile.degree,
        profile.branch,
        profile.graduation_year,
        skills,
        experience_filled,
        profile.preferred_career,
        profile.preferred_industry,
        profile.preferred_location,
        profile.work_mode,
        profile.government_private_preference,
    ]
    completed = sum(
        bool(value.strip()) if isinstance(value, str) else bool(value)
        for value in required_values
    )
    return round(completed * 100 / len(required_values))


def _skill_names(db: Session, user: User) -> list[str]:
    return list(
        db.scalars(
            select(Skill.name)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .where(UserSkill.user_id == user.id)
            .order_by(func.lower(Skill.name))
        ).all()
    )


def _serialize_profile(db: Session, user: User, profile: Profile) -> ProfileResponse:
    skills = _skill_names(db, user)
    return ProfileResponse(
        email=user.email,
        name=profile.name,
        education=profile.education,
        degree=profile.degree,
        branch=profile.branch,
        graduation_year=profile.graduation_year,
        skills=skills,
        certifications=profile.certifications or [],
        experience_summary=profile.experience_summary,
        experience_years=(
            float(profile.experience_years)
            if profile.experience_years is not None
            else None
        ),
        preferred_career=profile.preferred_career,
        preferred_industry=profile.preferred_industry,
        preferred_location=profile.preferred_location,
        work_mode=profile.work_mode,
        government_private_preference=profile.government_private_preference,
        internship_preference=profile.internship_preference,
        exam_preferences=profile.exam_preferences or {},
        completion_percent=_profile_completion(profile, skills),
        updated_at=profile.updated_at,
    )


def _replace_skills(db: Session, user: User, skills: list[str]) -> None:
    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))

    for name in skills:
        skill = db.scalar(
            select(Skill).where(func.lower(Skill.name) == name.casefold())
        )
        if skill is None:
            db.execute(
                pg_insert(Skill)
                .values(id=uuid4(), name=name)
                .on_conflict_do_nothing(index_elements=[Skill.name])
            )
            skill = db.scalar(
                select(Skill).where(func.lower(Skill.name) == name.casefold())
            )
        if skill is not None:
            db.add(UserSkill(user_id=user.id, skill_id=skill.id))


@router.get("", response_model=ProfileResponse)
def read_profile(
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile = _get_or_create_profile(db, user)
    db.commit()
    db.refresh(profile)
    return _serialize_profile(db, user, profile)


@router.put("", response_model=ProfileResponse)
def update_profile(
    update: ProfileUpdate,
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile = _get_or_create_profile(db, user)
    changes = update.model_dump(exclude_unset=True)
    skills = changes.pop("skills", None) if "skills" in changes else None

    for field, value in changes.items():
        if field == "certifications" and value is None:
            value = []
        elif field == "exam_preferences" and value is None:
            value = {}
        elif field == "internship_preference" and value is None:
            value = False
        setattr(profile, field, value)

    if "skills" in update.model_fields_set:
        _replace_skills(db, user, skills or [])

    db.commit()
    db.refresh(profile)
    return _serialize_profile(db, user, profile)