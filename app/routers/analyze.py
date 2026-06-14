"""Step 1 endpoint — WORKING. Scrapes the URL, returns a CampaignProfile, and
persists it (best-effort) so it shows up in the dashboard/CRM."""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud
from ..db import get_db
from ..schemas import AnalyzeRequest, CampaignProfile
from ..security import require_api_key
from ..services import analyzer, scraper

logger = logging.getLogger("outflow")
router = APIRouter(prefix="/analyze", tags=["1 - analyze"])


@router.post("", response_model=CampaignProfile)
async def analyze_website(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
) -> CampaignProfile:
    try:
        scraped = await scraper.scrape(str(req.url))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {e}")

    profile = analyzer.analyze(scraped)

    # Persistence is best-effort: a DB hiccup must not fail the analysis.
    try:
        profile.campaign_id = crud.save_analysis(db, profile)
    except Exception:
        db.rollback()
        logger.warning("could not persist analysis for %s", profile.url, exc_info=True)

    return profile
