"""Step 2 endpoint — returns mock leads until a data vendor key is set."""
from fastapi import APIRouter, Depends

from ..schemas import FindLeadsRequest, Lead
from ..security import require_api_key
from ..services import leads as leads_service

router = APIRouter(prefix="/leads", tags=["2 - find buyers"])


@router.post("/find", response_model=list[Lead])
async def find(
    req: FindLeadsRequest, _key: str = Depends(require_api_key)
) -> list[Lead]:
    return await leads_service.find_leads(req.icp, req.limit)
