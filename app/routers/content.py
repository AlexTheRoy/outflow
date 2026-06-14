"""Content generation endpoints — research reports, social/blog posts, call scripts.

All use the unified LLM layer (Claude/OpenAI) with template fallbacks.
"""
from fastapi import APIRouter, Depends

from ..schemas import (
    CallScript,
    CallScriptRequest,
    ResearchReport,
    ResearchRequest,
    SocialPost,
    SocialPostRequest,
)
from ..security import require_api_key
from ..services import content

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/research", response_model=ResearchReport)
async def research(req: ResearchRequest, _key: str = Depends(require_api_key)) -> ResearchReport:
    return content.research(req.lead, req.profile)


@router.post("/social", response_model=SocialPost)
async def social(req: SocialPostRequest, _key: str = Depends(require_api_key)) -> SocialPost:
    return content.social_post(req.profile, req.platform, req.topic, req.tone)


@router.post("/script", response_model=CallScript)
async def script(req: CallScriptRequest, _key: str = Depends(require_api_key)) -> CallScript:
    return content.call_script(req.lead, req.profile)
