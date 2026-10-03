from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_admin_user, get_current_local_user
from backend.app.db.session import get_db
from backend.app.models.identity import Skill, User
from backend.app.models.opportunity import (
    OPPORTUNITY_TYPES,
    Opportunity,
    OpportunityCategory,
    OpportunitySkill,
    OpportunitySource,
    Organization,
    SavedOpportunity,
)
from backend.app.schemas.opportunity import (
    OpportunityFilters,
    OpportunityPage,
    OpportunityCategoryOption,
    OpportunityResponse,
    OpportunitySaveResponse,
    OpportunityWrite,
)

public_router = APIRouter(prefix="/opportunities", tags=["opportunities"])
search_router = APIRouter(prefix="/search", tags=["search"])
admin_router = APIRouter(
    prefix="/admin/opportunities",
    tags=["admin opportunities"],
    dependencies=[Depends(get_current_admin_user)],
)

_PUBLIC_STATUSES = ("UPCOMING", "OPEN", "CLOSING_SOON", "UPDATED")
_GOVERNMENT_TYPES = ("GOVERNMENT_JOB", "GOVERNMENT_SCHEME")
_PRIVATE_TYPES = ("PRIVATE_JOB",)
_STALE_AFTER = timedelta(hours=24)


def _clean_filter(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_opportunity_filters(
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=120),
    opportunity_type: str | None = Query(default=None, max_length=40),
    government_private: Literal["government", "private", "both"] | None = Query(default=None),
    qualification: str | None = Query(default=None, max_length=200),
    branch: str | None = Query(default=None, max_length=200),
    experience: str | None = Query(default=None, max_length=100),
    location: str | None = Query(default=None, max_length=200),
    work_mode: str | None = Query(default=None, max_length=40),
    compensation_currency: str | None = Query(default=None, min_length=3, max_length=3),
    min_compensation: Decimal | None = Query(default=None, ge=0),
    max_compensation: Decimal | None = Query(default=None, ge=0),
    deadline_after: date | None = Query(default=None),
    deadline_before: date | None = Query(default=None),
    organization: str | None = Query(default=None, max_length=200),
    skill: str | None = Query(default=None, max_length=120),
    exam_type: str | None = Query(default=None, max_length=120),
    sort: Literal["newest", "deadline", "relevance", "salary"] = Query(default="newest"),
    page: int = Query(default=1, ge=1, le=100_000),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OpportunityFilters:
    opportunity_type = _clean_filter(opportunity_type)
    if opportunity_type and opportunity_type.upper() not in OPPORTUNITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported opportunity type.",
        )

    minimum = min_compensation
    maximum = max_compensation
    currency = _clean_filter(compensation_currency)
    if currency and not currency.isalpha():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Compensation currency must be a three-letter code.",
        )
    if (minimum is not None or maximum is not None) and not currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose a currency when filtering by compensation.",
        )
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Minimum compensation cannot exceed maximum compensation.",
        )
    if deadline_after and deadline_before and deadline_after > deadline_before:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The start deadline cannot be after the end deadline.",
        )

    return OpportunityFilters(
        q=_clean_filter(q),
        category=_clean_filter(category),
        opportunity_type=opportunity_type.upper() if opportunity_type else None,
        government_private=government_private,
        qualification=_clean_filter(qualification),
        branch=_clean_filter(branch),
        experience=_clean_filter(experience),
        location=_clean_filter(location),
        work_mode=_clean_filter(work_mode),
        compensation_currency=currency.upper() if currency else None,
        min_compensation=minimum,
        max_compensation=maximum,
        deadline_after=deadline_after,
        deadline_before=deadline_before,
        organization=_clean_filter(organization),
        skill=_clean_filter(skill),
        exam_type=_clean_filter(exam_type),
        sort=sort,
        page=page,
        page_size=page_size,
    )


def _search_expressions(filters: OpportunityFilters):
    conditions = []
    if filters.q:
        query = func.plainto_tsquery("simple", filters.q)
        search_document = func.to_tsvector(
            "simple",
            func.concat_ws(
                " ",
                Opportunity.title,
                Opportunity.description,
                Opportunity.qualification,
                Opportunity.branch,
                Opportunity.experience_required,
                Opportunity.age_limit,
                Opportunity.location,
                Opportunity.work_mode,
                Organization.name,
                OpportunityCategory.name,
            ),
        )
        conditions.append(search_document.op("@@")(query))
    if filters.category:
        conditions.append(func.lower(OpportunityCategory.slug) == filters.category.casefold())
    if filters.opportunity_type:
        conditions.append(Opportunity.opportunity_type == filters.opportunity_type)
    if filters.government_private == "government":
        conditions.append(Opportunity.opportunity_type.in_(_GOVERNMENT_TYPES))
    elif filters.government_private == "private":
        conditions.append(Opportunity.opportunity_type.in_(_PRIVATE_TYPES))
    elif filters.government_private == "both":
        conditions.append(
            Opportunity.opportunity_type.in_(_GOVERNMENT_TYPES + _PRIVATE_TYPES)
        )
    if filters.qualification:
        conditions.append(Opportunity.qualification.ilike(f"%{filters.qualification}%"))
    if filters.branch:
        conditions.append(Opportunity.branch.ilike(f"%{filters.branch}%"))
    if filters.experience:
        conditions.append(Opportunity.experience_required.ilike(f"%{filters.experience}%"))
    if filters.location:
        conditions.append(Opportunity.location.ilike(f"%{filters.location}%"))
    if filters.work_mode:
        conditions.append(Opportunity.work_mode.ilike(f"%{filters.work_mode}%"))
    if filters.min_compensation is not None or filters.max_compensation is not None:
        if filters.compensation_currency:
            conditions.append(
                Opportunity.compensation_currency == filters.compensation_currency
            )
    if filters.min_compensation is not None:
        salary_ceiling = func.coalesce(Opportunity.salary_max, Opportunity.salary_min)
        conditions.append(
            or_(
                salary_ceiling >= filters.min_compensation,
                Opportunity.stipend_amount >= filters.min_compensation,
            )
        )
    if filters.max_compensation is not None:
        salary_floor = func.coalesce(Opportunity.salary_min, Opportunity.salary_max)
        conditions.append(
            or_(
                salary_floor <= filters.max_compensation,
                Opportunity.stipend_amount <= filters.max_compensation,
            )
        )
    if filters.deadline_after:
        conditions.append(Opportunity.closing_date >= filters.deadline_after)
    if filters.deadline_before:
        conditions.append(Opportunity.closing_date <= filters.deadline_before)
    if filters.organization:
        conditions.append(Organization.name.ilike(f"%{filters.organization}%"))
    if filters.skill:
        skill_match = (
            select(OpportunitySkill.opportunity_id)
            .join(Skill, Skill.id == OpportunitySkill.skill_id)
            .where(
                OpportunitySkill.opportunity_id == Opportunity.id,
                Skill.name.ilike(f"%{filters.skill}%"),
            )
            .exists()
        )
        conditions.append(skill_match)
    if filters.exam_type:
        conditions.append(Opportunity.opportunity_type.in_(("EXAM", "ENTRANCE_EXAM")))
        conditions.append(
            Opportunity.eligibility["exam_type"].as_string().ilike(f"%{filters.exam_type}%")
        )
    return conditions


def _public_opportunity_conditions(now: datetime) -> list:
    return [
        Opportunity.published_at.is_not(None),
        Opportunity.last_verified_at.is_not(None),
        Opportunity.official_url.is_not(None),
        Opportunity.source_url.is_not(None),
        Opportunity.status.in_(_PUBLIC_STATUSES),
        or_(Opportunity.expires_at.is_(None), Opportunity.expires_at > now),
        or_(Opportunity.closing_date.is_(None), Opportunity.closing_date >= now.date()),
        OpportunityCategory.is_active.is_(True),
    ]


def _base_statement():
    return (
        select(
            Opportunity,
            Organization.name.label("organization_name"),
            Organization.website_url.label("organization_website_url"),
            OpportunityCategory.name.label("category_name"),
            OpportunityCategory.slug.label("category_slug"),
        )
        .join(OpportunityCategory, OpportunityCategory.id == Opportunity.category_id)
        .outerjoin(Organization, Organization.id == Opportunity.organization_id)
    )


def _skill_map(db: Session, opportunity_ids: list[UUID]) -> dict[UUID, list[dict]]:
    if not opportunity_ids:
        return {}
    skills: dict[UUID, list[dict]] = {}
    rows = db.execute(
        select(
            OpportunitySkill.opportunity_id,
            Skill.name,
            OpportunitySkill.is_required,
        )
        .join(Skill, Skill.id == OpportunitySkill.skill_id)
        .where(OpportunitySkill.opportunity_id.in_(opportunity_ids))
        .order_by(func.lower(Skill.name))
    ).all()
    for opportunity_id, name, is_required in rows:
        skills.setdefault(opportunity_id, []).append(
            {"name": name, "is_required": is_required}
        )
    return skills


def _to_response(
    row,
    now: datetime,
    skills: list[dict] | None = None,
) -> OpportunityResponse:
    opportunity, organization_name, organization_website_url, category_name, category_slug = row
    verified_at = opportunity.last_verified_at
    if verified_at is not None and verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)
    return OpportunityResponse(
        id=opportunity.id,
        title=opportunity.title,
        description=opportunity.description,
        organization_name=organization_name,
        organization_website_url=organization_website_url,
        category_name=category_name,
        category_slug=category_slug,
        opportunity_type=opportunity.opportunity_type,
        qualification=opportunity.qualification,
        branch=opportunity.branch,
        experience_required=opportunity.experience_required,
        age_limit=opportunity.age_limit,
        location=opportunity.location,
        work_mode=opportunity.work_mode,
        salary_min=opportunity.salary_min,
        salary_max=opportunity.salary_max,
        stipend_amount=opportunity.stipend_amount,
        compensation_currency=opportunity.compensation_currency,
        application_fee=opportunity.application_fee,
        opening_date=opportunity.opening_date,
        closing_date=opportunity.closing_date,
        exam_date=opportunity.exam_date,
        result_date=opportunity.result_date,
        eligibility=opportunity.eligibility or {},
        skills=skills or [],
        documents_required=opportunity.documents_required or [],
        selection_process=opportunity.selection_process or [],
        application_steps=opportunity.application_steps or [],
        official_url=opportunity.official_url,
        source_url=opportunity.source_url,
        source_name=opportunity.source_name,
        source_type=opportunity.source_type,
        status=opportunity.status,
        published_at=opportunity.published_at,
        last_verified_at=verified_at,
        expires_at=opportunity.expires_at,
        is_stale=verified_at is None or verified_at < now - _STALE_AFTER,
    )


def _run_search(
    db: Session,
    filters: OpportunityFilters,
    *,
    public_only: bool,
    saved_user_id: UUID | None = None,
) -> OpportunityPage:
    conditions = _search_expressions(filters)
    now = datetime.now(timezone.utc)
    if public_only:
        conditions.extend(_public_opportunity_conditions(now))

    statement = _base_statement()
    count_statement = (
        select(func.count(Opportunity.id))
        .join(OpportunityCategory, OpportunityCategory.id == Opportunity.category_id)
        .outerjoin(Organization, Organization.id == Opportunity.organization_id)
    )
    if saved_user_id is not None:
        saved_condition = SavedOpportunity.user_id == saved_user_id
        statement = statement.join(
            SavedOpportunity,
            SavedOpportunity.opportunity_id == Opportunity.id,
        ).where(saved_condition)
        count_statement = count_statement.join(
            SavedOpportunity,
            SavedOpportunity.opportunity_id == Opportunity.id,
        ).where(saved_condition)
    statement = statement.where(*conditions)
    count_statement = count_statement.where(*conditions)

    if filters.sort == "deadline":
        statement = statement.order_by(
            Opportunity.closing_date.asc().nulls_last(),
            Opportunity.published_at.desc().nulls_last(),
            Opportunity.created_at.desc(),
        )
    elif filters.sort == "salary":
        compensation = func.coalesce(
            Opportunity.salary_max,
            Opportunity.salary_min,
            Opportunity.stipend_amount,
        )
        statement = statement.order_by(
            compensation.desc().nulls_last(),
            Opportunity.published_at.desc().nulls_last(),
        )
    elif filters.sort == "relevance" and filters.q:
        query = func.plainto_tsquery("simple", filters.q)
        search_document = func.to_tsvector(
            "simple",
            func.concat_ws(
                " ",
                Opportunity.title,
                Opportunity.description,
                Opportunity.qualification,
                Opportunity.branch,
                Opportunity.experience_required,
                Opportunity.age_limit,
                Opportunity.location,
                Opportunity.work_mode,
                Organization.name,
                OpportunityCategory.name,
            ),
        )
        statement = statement.order_by(
            func.ts_rank(search_document, query).desc(),
            Opportunity.published_at.desc().nulls_last(),
        )
    else:
        statement = statement.order_by(
            Opportunity.published_at.desc().nulls_last(),
            Opportunity.created_at.desc(),
        )

    total = db.scalar(count_statement) or 0
    rows = db.execute(
        statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
    ).all()
    skills = _skill_map(db, [row[0].id for row in rows])
    return OpportunityPage(
        items=[_to_response(row, now, skills.get(row[0].id)) for row in rows],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        page_count=ceil(total / filters.page_size) if total else 0,
    )


@public_router.get("", response_model=OpportunityPage)
def list_opportunities(
    filters: OpportunityFilters = Depends(get_opportunity_filters),
    db: Session = Depends(get_db),
) -> OpportunityPage:
    return _run_search(db, filters, public_only=True)


@search_router.get("", response_model=OpportunityPage)
def search_opportunities(
    filters: OpportunityFilters = Depends(get_opportunity_filters),
    db: Session = Depends(get_db),
) -> OpportunityPage:
    return _run_search(db, filters, public_only=True)


@public_router.get("/categories", response_model=list[OpportunityCategoryOption])
def list_public_opportunity_categories(
    db: Session = Depends(get_db),
) -> list[OpportunityCategoryOption]:
    now = datetime.now(timezone.utc)
    categories = db.execute(
        select(OpportunityCategory.name, OpportunityCategory.slug)
        .join(Opportunity, Opportunity.category_id == OpportunityCategory.id)
        .where(
            OpportunityCategory.is_active.is_(True),
            *_public_opportunity_conditions(now),
        )
        .group_by(OpportunityCategory.name, OpportunityCategory.slug)
        .order_by(func.lower(OpportunityCategory.name))
    ).all()
    return [
        OpportunityCategoryOption(name=name, slug=slug)
        for name, slug in categories
    ]


@public_router.get("/saved", response_model=OpportunityPage)
def list_saved_opportunities(
    filters: OpportunityFilters = Depends(get_opportunity_filters),
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> OpportunityPage:
    return _run_search(
        db,
        filters,
        public_only=True,
        saved_user_id=user.id,
    )


@public_router.get("/saved/ids", response_model=list[UUID])
def list_saved_opportunity_ids(
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> list[UUID]:
    return list(
        db.scalars(
            select(SavedOpportunity.opportunity_id)
            .join(Opportunity, Opportunity.id == SavedOpportunity.opportunity_id)
            .join(OpportunityCategory, OpportunityCategory.id == Opportunity.category_id)
            .where(
                SavedOpportunity.user_id == user.id,
                *_public_opportunity_conditions(datetime.now(timezone.utc)),
            )
            .order_by(SavedOpportunity.created_at.desc())
        ).all()
    )


@public_router.post(
    "/{opportunity_id}/save",
    response_model=OpportunitySaveResponse,
)
def save_opportunity(
    opportunity_id: UUID,
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> OpportunitySaveResponse:
    now = datetime.now(timezone.utc)
    opportunity_exists = db.scalar(
        select(Opportunity.id)
        .join(OpportunityCategory, OpportunityCategory.id == Opportunity.category_id)
        .where(
            Opportunity.id == opportunity_id,
            *_public_opportunity_conditions(now),
        )
    )
    if opportunity_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found.",
        )
    saved = db.get(SavedOpportunity, (user.id, opportunity_id))
    if saved is None:
        db.add(SavedOpportunity(user_id=user.id, opportunity_id=opportunity_id))
        db.commit()
    return OpportunitySaveResponse(opportunity_id=opportunity_id, saved=True)


@public_router.delete(
    "/{opportunity_id}/save",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unsave_opportunity(
    opportunity_id: UUID,
    response: Response,
    user: User = Depends(get_current_local_user),
    db: Session = Depends(get_db),
) -> Response:
    db.execute(
        delete(SavedOpportunity).where(
            SavedOpportunity.user_id == user.id,
            SavedOpportunity.opportunity_id == opportunity_id,
        )
    )
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@public_router.get("/{opportunity_id}", response_model=OpportunityResponse)
def read_opportunity(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    now = datetime.now(timezone.utc)
    row = db.execute(
        _base_statement()
        .where(
            Opportunity.id == opportunity_id,
            *_public_opportunity_conditions(now),
        )
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found.",
        )
    skills = _skill_map(db, [row[0].id])
    return _to_response(row, now, skills.get(row[0].id))


def _get_category(db: Session, payload: OpportunityWrite) -> OpportunityCategory:
    category = db.scalar(
        select(OpportunityCategory).where(
            func.lower(OpportunityCategory.slug) == payload.category.slug.casefold()
        )
    )
    if category is None:
        category = OpportunityCategory(
            name=payload.category.name,
            slug=payload.category.slug,
            description=payload.category.description,
            is_active=True,
        )
        db.add(category)
        db.flush()
    return category


def _get_organization(db: Session, payload: OpportunityWrite) -> Organization:
    organization_data = payload.organization
    domain = organization_data.official_domain
    if not domain and organization_data.website_url:
        domain = urlsplit(str(organization_data.website_url)).hostname
    if domain:
        domain = domain.lower().removeprefix("www.")
        organization = db.scalar(
            select(Organization).where(
                func.lower(Organization.official_domain) == domain
            )
        )
    else:
        organization = None
    if organization is None:
        organization = db.scalar(
            select(Organization).where(
                func.lower(Organization.name) == organization_data.name.casefold()
            )
        )
    if organization is None:
        organization = Organization(
            name=organization_data.name,
            website_url=(
                str(organization_data.website_url)
                if organization_data.website_url
                else None
            ),
            official_domain=domain,
            description=organization_data.description,
            organization_type=organization_data.organization_type,
            location=organization_data.location,
        )
        db.add(organization)
        db.flush()
    return organization


def _write_values(payload: OpportunityWrite) -> dict:
    values = payload.model_dump(
        exclude={
            "organization",
            "category",
            "skills",
            "official_url",
            "source_url",
            "source_name",
            "source_type",
            "publish_after_review",
        }
    )
    values["official_url"] = str(payload.official_url)
    values["source_url"] = str(payload.source_url)
    values["source_name"] = payload.source_name
    values["source_type"] = payload.source_type
    return values


def _replace_opportunity_skills(
    db: Session,
    opportunity: Opportunity,
    skills: list,
) -> None:
    db.query(OpportunitySkill).filter(
        OpportunitySkill.opportunity_id == opportunity.id
    ).delete(synchronize_session=False)
    for item in skills:
        skill = db.scalar(
            select(Skill).where(func.lower(Skill.name) == item.name.casefold())
        )
        if skill is None:
            skill = Skill(name=item.name)
            db.add(skill)
            db.flush()
        db.add(
            OpportunitySkill(
                opportunity_id=opportunity.id,
                skill_id=skill.id,
                is_required=item.is_required,
            )
        )


def _set_primary_source(
    db: Session,
    opportunity: Opportunity,
    payload: OpportunityWrite,
    verified_at: datetime | None,
) -> None:
    source = db.scalar(
        select(OpportunitySource).where(
            OpportunitySource.opportunity_id == opportunity.id,
            OpportunitySource.is_primary.is_(True),
        )
    )
    if source is None:
        source = OpportunitySource(
            opportunity_id=opportunity.id,
            source_name=payload.source_name,
            source_url=str(payload.source_url),
            source_type=payload.source_type,
            last_verified_at=verified_at,
            is_primary=True,
        )
        db.add(source)
    else:
        source.source_name = payload.source_name
        source.source_url = str(payload.source_url)
        source.source_type = payload.source_type
        source.last_verified_at = verified_at


def _serialize_by_id(db: Session, opportunity_id: UUID, now: datetime) -> OpportunityResponse:
    row = db.execute(
        _base_statement().where(Opportunity.id == opportunity_id).limit(1)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The saved opportunity could not be read.",
        )
    skills = _skill_map(db, [opportunity_id])
    return _to_response(row, now, skills.get(opportunity_id))


@admin_router.get("", response_model=OpportunityPage)
def list_admin_opportunities(
    filters: OpportunityFilters = Depends(get_opportunity_filters),
    db: Session = Depends(get_db),
) -> OpportunityPage:
    return _run_search(db, filters, public_only=False)


@admin_router.post(
    "",
    response_model=OpportunityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity(
    payload: OpportunityWrite,
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    now = datetime.now(timezone.utc)
    verified_at = now if payload.publish_after_review else None
    try:
        category = _get_category(db, payload)
        organization = _get_organization(db, payload)
        values = _write_values(payload)
        values["category_id"] = category.id
        values["organization_id"] = organization.id
        values["published_at"] = verified_at
        values["last_verified_at"] = verified_at
        opportunity = Opportunity(**values)
        db.add(opportunity)
        db.flush()
        _replace_opportunity_skills(db, opportunity, payload.skills)
        _set_primary_source(db, opportunity, payload, verified_at)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An opportunity with this official link or notification identity already exists.",
        ) from exc
    return _serialize_by_id(db, opportunity.id, now)


@admin_router.put("/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(
    opportunity_id: UUID,
    payload: OpportunityWrite,
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found.",
        )

    now = datetime.now(timezone.utc)
    verified_at = now if payload.publish_after_review else None
    try:
        category = _get_category(db, payload)
        organization = _get_organization(db, payload)
        for field, value in _write_values(payload).items():
            setattr(opportunity, field, value)
        opportunity.category_id = category.id
        opportunity.organization_id = organization.id
        opportunity.published_at = verified_at
        opportunity.last_verified_at = verified_at
        _replace_opportunity_skills(db, opportunity, payload.skills)
        _set_primary_source(db, opportunity, payload, verified_at)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An opportunity with this official link or notification identity already exists.",
        ) from exc
    return _serialize_by_id(db, opportunity.id, now)


@admin_router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_opportunity(
    opportunity_id: UUID,
    response: Response,
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Response:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found.",
        )
    opportunity.status = "CANCELLED"
    opportunity.published_at = None
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response