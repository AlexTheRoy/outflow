"""Step 4 endpoint — simulated dial until Twilio credentials are set."""
from fastapi import APIRouter, Depends

from ..schemas import DialRequest, DialResponse
from ..security import require_api_key
from ..services import dialer as dialer_service

router = APIRouter(prefix="/dial", tags=["4 - dialer"])


@router.post("", response_model=DialResponse)
async def dial(req: DialRequest, _key: str = Depends(require_api_key)) -> DialResponse:
    return await dialer_service.dial(req.lead)
