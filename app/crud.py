"""Thin persistence helpers between the API and the ORM models."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .schemas import CampaignProfile as ProfileSchema

_DEFAULT_ORG_NAME = "Default Org"


def get_or_create_default_org(db: Session) -> models.Organization:
    org = db.scalar(
        select(models.Organization).where(models.Organization.name == _DEFAULT_ORG_NAME)
    )
    if org is None:
        org = models.Organization(name=_DEFAULT_ORG_NAME, plan="trial")
        db.add(org)
        db.flush()
    return org


def save_analysis(db: Session, profile: ProfileSchema) -> str:
    """Persist a campaign + its profile. Returns the campaign id."""
    org = get_or_create_default_org(db)
    campaign = models.Campaign(
        org_id=org.id, source_url=profile.url, status="analyzed"
    )
    db.add(campaign)
    db.flush()

    db.add(
        models.CampaignProfile(
            campaign_id=campaign.id,
            product=profile.product,
            value_prop=profile.value_prop,
            pricing=profile.pricing,
            icp=profile.icp.model_dump(),
            source=profile.source,
        )
    )
    db.commit()
    return campaign.id


def db_healthy(db: Session) -> bool:
    try:
        db.execute(select(1))
        return True
    except Exception:
        return False
