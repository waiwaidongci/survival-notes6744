from fastapi import HTTPException
from ..models import SurvivalRun, RecurrentRun, MaintenanceNote
from ..utils.clock import now
from ..utils.serialize import record
from .audit_service import log

def list_notes(db):return [record(x) for x in db.query(MaintenanceNote).order_by(MaintenanceNote.id.desc())]

def _validate_target(db, data):
    if data.recurrent_run_id is not None:
        run = db.get(RecurrentRun, data.recurrent_run_id)
        if not run or run.status != "completed":
            raise HTTPException(409, "只能为已完成的复发研究提交维护建议")
        return "recurrent"
    run = db.get(SurvivalRun, data.run_id)
    if not run or run.status != "completed":
        raise HTTPException(409, "只能为已完成研究提交维护建议")
    return "terminal"

def create_note(db,data,user):
    _validate_target(db, data)
    row=MaintenanceNote(**data.model_dump(),owner=user.name,status="submitted")
    db.add(row);db.flush()
    kind = "recurrent" if data.recurrent_run_id is not None else "survival"
    log(db,user.email,f"maintenance.submit.{kind}",row.id);db.commit()
    return record(row)

def review_note(db,nid,data,user):
    row=db.get(MaintenanceNote,nid)
    if not row:raise HTTPException(404,"维护建议不存在")
    if row.status!="submitted":raise HTTPException(409,"已复核记录不可重复审批")
    row.status=data.status;row.review_note=data.review_note;row.reviewer=user.name;row.reviewed_at=now()
    kind = "recurrent" if row.recurrent_run_id is not None else "survival"
    log(db,user.email,"maintenance."+data.status+"."+kind,row.id);db.commit()
    return record(row)
