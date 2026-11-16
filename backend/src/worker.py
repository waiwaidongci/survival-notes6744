import json, time, traceback
from pathlib import Path
from .config.database import Base, engine, SessionLocal
from .config.settings import ARTIFACTS_DIR
from .models import SurvivalRun, RecurrentRun, TestCohort
from .constants.status import RunStatus
from .services.run_service import queue as survival_queue
from .services.recurrent_run_service import queue as recurrent_queue, QUEUE_KEY as RECURRENT_KEY
from .services.specimen_service import specimen_rows
from .services.survival_algorithm import analyze_survival
from .services.recurrent_service import specimen_event_rows, analyze_recurrent
from .services.audit_service import log

Base.metadata.create_all(engine)
ARTIFACTS = Path(ARTIFACTS_DIR)
ARTIFACTS.mkdir(exist_ok=True)


def process_survival(db, rid):
    run = db.get(SurvivalRun, rid)
    if not run or run.status != RunStatus.QUEUED:
        return
    run.status = RunStatus.RUNNING
    db.commit()
    try:
        a, b = db.get(TestCohort, run.cohort_a_id), db.get(TestCohort, run.cohort_b_id)
        run.result = analyze_survival(a, b, specimen_rows(db, a.id),
                                      specimen_rows(db, b.id), run.confidence)
        run.status = RunStatus.COMPLETED
        (ARTIFACTS / f"run-{run.id}.json").write_text(
            json.dumps(run.result, ensure_ascii=False))
        log(db, "worker", "survival.completed", run.id)
    except Exception as e:
        run.status = RunStatus.FAILED
        run.error = str(e)
        traceback.print_exc()
    db.commit()


def process_recurrent(db, rid):
    run = db.get(RecurrentRun, rid)
    if not run or run.status != RunStatus.QUEUED:
        return
    run.status = RunStatus.RUNNING
    db.commit()
    try:
        a, b = db.get(TestCohort, run.cohort_a_id), db.get(TestCohort, run.cohort_b_id)
        result = analyze_recurrent(
            a, b,
            specimen_event_rows(db, a.id),
            specimen_event_rows(db, b.id),
            run.cutoff_hours, run.confidence)
        run.result = result
        run.status = RunStatus.COMPLETED
        (ARTIFACTS / f"recurrent-run-{run.id}.json").write_text(
            json.dumps(result, ensure_ascii=False))
        log(db, "worker", "recurrent.completed", run.id)
    except Exception as e:
        run.status = RunStatus.FAILED
        run.error = str(e)
        traceback.print_exc()
    db.commit()


def main():
    while True:
        (ARTIFACTS / "heartbeat").write_text(str(time.time()))
        # 非阻塞轮询两个队列，复发任务不阻塞终态任务
        job = survival_queue.lpop("survival:jobs")
        if job:
            with SessionLocal() as db:
                process_survival(db, int(job))
            continue
        job = recurrent_queue.lpop(RECURRENT_KEY)
        if job:
            with SessionLocal() as db:
                process_recurrent(db, int(job))
            continue
        time.sleep(0.5)


if __name__ == "__main__":
    main()
