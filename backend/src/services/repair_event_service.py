from fastapi import HTTPException
from ..models import TestCohort, Specimen, RepairEvent
from ..utils.serialize import record


def list_repair_events(db, cohort_id):
    """按试件返回复发事件原始流（接收顺序），供前端重建与核对事件链。"""
    if not db.get(TestCohort, cohort_id):
        raise HTTPException(404, "工艺批次不存在")
    specimens = (db.query(Specimen).filter(Specimen.cohort_id == cohort_id)
                 .order_by(Specimen.code).all())
    out = []
    for sp in specimens:
        events = (db.query(RepairEvent).filter(RepairEvent.specimen_id == sp.id)
                  .order_by(RepairEvent.received_seq).all())
        out.append({
            "specimen_id": sp.id,
            "code": sp.code,
            "material": sp.material,
            "event_count": len(events),
            "events": [record(e) for e in events],
        })
    return out
