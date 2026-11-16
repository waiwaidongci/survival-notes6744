import csv
import io
from redis import Redis
from fastapi import HTTPException
from ..models import RecurrentRun, TestCohort, MaintenanceNote
from ..config.settings import REDIS_URL
from ..utils.serialize import record
from .audit_service import log

queue = Redis.from_url(REDIS_URL, decode_responses=True)
QUEUE_KEY = "recurrent:jobs"


def list_runs(db):
    return [record(x) for x in db.query(RecurrentRun).order_by(RecurrentRun.id.desc())]


def get_run(db, rid):
    row = db.get(RecurrentRun, rid)
    if not row:
        raise HTTPException(404, "复发研究不存在")
    return row


def create_run(db, data, user):
    if data.cohort_a_id == data.cohort_b_id:
        raise HTTPException(422, "必须选择两批不同工艺")
    if not db.get(TestCohort, data.cohort_a_id) or not db.get(TestCohort, data.cohort_b_id):
        raise HTTPException(404, "工艺批次不存在")
    row = RecurrentRun(**data.model_dump(), owner=user.name)
    db.add(row)
    db.flush()
    log(db, user.email, "recurrent.enqueue", row.id)
    db.commit()
    try:
        queue.rpush(QUEUE_KEY, row.id)
    except Exception:
        row.status = "failed"
        row.error = "队列不可用，请重新提交"
        db.commit()
        raise HTTPException(503, row.error)
    return record(row)


def export_run(db, rid):
    """获批导出：MCF曲线、同时带、在险历程、隔离清单分区块写入同一CSV。"""
    row = get_run(db, rid)
    if row.status != "completed":
        raise HTTPException(409, "研究尚未完成")
    approved = (db.query(MaintenanceNote)
                .filter_by(recurrent_run_id=rid, status="approved").first())
    if not approved:
        raise HTTPException(403, "维护建议尚未经负责人确认，不能导出")
    res = row.result
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["# section", "paper_mcf_recurrent_export", "input_hash", res["input_hash"],
                "method", res["method_version"]])
    # 1) MCF 曲线与逐点区间、同时带
    w.writerow(["section", "mcf_curve"])
    w.writerow(["cohort", "time_hours", "at_risk", "events", "mcf",
                "pointwise_lower", "pointwise_upper", "band_lower", "band_upper"])
    for g in res["groups"]:
        band_grid = dict(zip(g["band"]["grid"], zip(g["band"]["lower"], g["band"]["upper"])))
        for p in g["curve"]:
            bl, bu = band_grid.get(p["time"], ("", ""))
            w.writerow([g["cohort"]["code"], p["time"], p["at_risk"], p["events"],
                        p["mcf"], p["lower"], p["upper"], bl, bu])
    # 2) 差值曲线
    w.writerow(["section", "difference_a_minus_b"])
    w.writerow(["time_hours", "mcf_diff", "pointwise_lower", "pointwise_upper",
                "simultaneous_lower", "simultaneous_upper"])
    d = res["difference"]
    for i, t in enumerate(d["grid"]):
        w.writerow([t, d["mcf_diff"][i], d["pointwise_lower"][i], d["pointwise_upper"][i],
                    d["simultaneous_lower"][i], d["simultaneous_upper"][i]])
    # 3) 在险历程（每个有效试件的工作区间）
    w.writerow(["section", "at_risk_history"])
    w.writerow(["cohort", "specimen_code", "terminal_state", "failure_count",
                "exposure_hours", "interval_start", "interval_end", "interval_exposure"])
    for g in res["groups"]:
        for h in g["specimen_histories"]:
            for iv in h["intervals"]:
                w.writerow([g["cohort"]["code"], h["code"], h["terminal_state"],
                            h["failure_count"], h["exposure_hours"],
                            iv["start"], iv["end"], iv["exposure"]])
    # 4) 隔离清单与原因
    w.writerow(["section", "quarantined_specimens"])
    w.writerow(["cohort", "specimen_code", "isolation_reason", "isolation_reason_text",
                "trigger_event_id", "terminal_state"])
    for g in res["groups"]:
        for q in g["quarantined_specimens"]:
            w.writerow([g["cohort"]["code"], q["code"], q["isolation_reason"],
                        q["isolation_reason_text"], q["isolation_event_id"], q["terminal_state"]])
    return out.getvalue()
