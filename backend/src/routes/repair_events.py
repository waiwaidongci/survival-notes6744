from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user
from ..services.repair_event_service import list_repair_events

router = APIRouter(prefix="/cohorts", tags=["repair-events"])


@router.get("/{cid}/repair-events")
def repair_events(cid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    return list_repair_events(db, cid)
