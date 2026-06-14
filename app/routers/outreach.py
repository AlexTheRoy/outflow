"""Step 3 endpoints — generate outreach copy and send it via a campaign provider."""
from fastapi import APIRouter, Depends

from ..schemas import (
    GenerateOutreachRequest,
    OutreachMessage,
    SendOutreachRequest,
    SendResult,
)
from ..security import require_api_key
from ..services import outreach as outreach_service

router = APIRouter(prefix="/outreach", tags=["3 - outreach"])


@router.post("/generate", response_model=OutreachMessage)
async def generate(
    req: GenerateOutreachRequest, _key: str = Depends(require_api_key)
) -> OutreachMessage:
    return outreach_service.generate(req.profile, req.lead, req.channel)


@router.post("/send", response_model=SendResult)
async def send(
    req: SendOutreachRequest, _key: str = Depends(require_api_key)
) -> SendResult:
    return await outreach_service.send(req.lead, req.message)
