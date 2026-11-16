import json
import random
from src.config.database import Base, engine, SessionLocal
from src.models import (User, TestCohort, Specimen, FollowupEvent, SurvivalRun,
                        MaintenanceNote, RepairEvent, RecurrentRun)
from src.utils.security import hash_password
from src.services.specimen_service import specimen_rows
from src.services.survival_algorithm import analyze_survival
from src.services.recurrent_service import specimen_event_rows, analyze_recurrent

# 复发事件观察窗（小时）
RECURRENT_CUTOFF = 1450.0


def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role, name in [("admin", "阮青 · 材料负责人"), ("analyst", "江栩 · 耐久研究员"),
                           ("viewer", "林舟 · 维护阅读者")]:
            email = role + "@zhihe.demo"
            if not db.query(User).filter_by(email=email).first():
                db.add(User(email=email, name=name, role=role,
                            password_hash=hash_password("Zhihe2026!")))
        cohorts = []
        for code, name, process, scale, seed_value in [
                ("ZH-A", "常规封装批", "常规硅胶封装", 900., 73),
                ("ZH-B", "改进封装批", "低应力复合封装", 1200., 74)]:
            c = db.query(TestCohort).filter_by(code=code).first()
            if not c:
                c = TestCohort(code=code, name=name, process=process,
                               description="独立灯带试件恒定环境耐久观察；右删失表示观察截止仍工作，不能当作失效。")
                db.add(c)
                db.flush()
            rng = random.Random(seed_value)
            for i in range(1, 181):
                key = f"{code}-{i:04}"
                lifetime = rng.weibullvariate(scale, 1.8)
                censor = rng.uniform(900, 1450)
                observed = lifetime <= censor
                duration = max(25., round(min(lifetime, censor) / 25) * 25.)
                s = db.query(Specimen).filter_by(code=key).first()
                if not s:
                    s = Specimen(code=key, cohort_id=c.id, material="24V展陈柔性灯带 · 500mm",
                                 enrolled_at="2026-08-01T00:00:00+00:00")
                    db.add(s)
                    db.flush()
                if not db.query(FollowupEvent).filter_by(specimen_id=s.id).first():
                    db.add(FollowupEvent(
                        specimen_id=s.id, duration_hours=duration, event_observed=observed,
                        note="观察到光通量降至阈值，记为耐久事件。" if observed
                        else "试验观察截止，灯带仍工作，记为右删失。"))
            db.flush()
            cohorts.append(c)

        # 基准终态研究（旧口径，结果保持不变）
        if not db.query(SurvivalRun).filter_by(name="两批封装耐久 · 基准比较").first():
            a, b = cohorts
            result = analyze_survival(a, b, specimen_rows(db, a.id),
                                      specimen_rows(db, b.id), .95)
            run = SurvivalRun(name="两批封装耐久 · 基准比较", cohort_a_id=a.id,
                              cohort_b_id=b.id, confidence=.95, status="completed",
                              result=result, owner="江栩 · 耐久研究员")
            db.add(run)
            db.flush()
            db.add(MaintenanceNote(
                run_id=run.id, title="基准维护观察说明",
                interpretation="已分开事件和删失，比较结果只反映当前试验条件，不作工艺因果保证。",
                recommendation="优先保留尾部在险样本观察，结合环境应力记录讨论维护窗口。",
                status="approved", owner="江栩 · 耐久研究员", reviewer="阮青 · 材料负责人",
                review_note="批准研究底稿归档；维护周期仍需现场条件复核。",
                reviewed_at="2026-11-01T00:00:00+00:00"))

        _seed_recurrent(db, cohorts)
        db.commit()
        print(json.dumps({m.__tablename__: db.query(m).count() for m in
                          [User, TestCohort, Specimen, FollowupEvent, RepairEvent,
                           SurvivalRun, RecurrentRun, MaintenanceNote]}, ensure_ascii=False))


def _seed_recurrent(db, cohorts):
    """生成可修复灯带的乱序故障/修复/退出事件流。"""
    if db.query(RepairEvent).count() > 0:
        return
    # 每批约180件；改进批故障率更低、修复更快
    profiles = {
        "ZH-A": dict(rate=0.0026, repair_lo=18., repair_hi=70., seed=7301),
        "ZH-B": dict(rate=0.0011, repair_lo=10., repair_hi=45., seed=7401),
    }
    # 固定的隔离演示试件编号（每批各2件，覆盖不同隔离原因）
    quarantine_demo = {
        "ZH-A": {4: "failure_while_down", 9: "event_after_withdrawal"},
        "ZH-B": {4: "withdrawal_while_working", 9: "repair_while_working"},
    }
    for cohort in cohorts:
        prof = profiles[cohort.code]
        rng = random.Random(prof["seed"])
        specimens = (db.query(Specimen).filter(Specimen.cohort_id == cohort.id)
                     .order_by(Specimen.code).all())
        for idx, sp in enumerate(specimens, start=1):
            raw = []  # (event_time, kind, note) 先按时间生成

            def add(t, kind, note):
                raw.append((round(t, 1), kind, note))

            t = 0.0
            q_reason = quarantine_demo[cohort.code].get(idx)
            if q_reason == "repair_while_working":
                # 确定性演示：故障->修复->工作态再收到无对应故障的修复
                t1 = min(300., RECURRENT_CUTOFF * .2)
                add(t1, "failure", "灯带熄灭，光通量低于展陈阈值，登记故障。")
                rep1 = t1 + prof["repair_lo"] + 5
                add(rep1, "repair", "更换驱动后恢复点亮，维修期间不在险。")
                add(rep1 + 60, "repair", "工作状态下收到无对应故障的修复记录，状态断裂。")
            elif q_reason == "failure_while_down":
                # 确定性演示：停机未修复又来故障
                t1 = min(320., RECURRENT_CUTOFF * .2)
                add(t1, "failure", "灯带熄灭，光通量低于展陈阈值，登记故障。")
                add(t1 + 5, "failure", "停机未修复期间又上报熄灭，事件链断裂。")
            elif q_reason == "withdrawal_while_working":
                # 确定性演示：故障->修复->工作中永久退出（未闭合）
                t1 = min(300., RECURRENT_CUTOFF * .2)
                add(t1, "failure", "灯带熄灭，光通量低于展陈阈值，登记故障。")
                rep1 = t1 + prof["repair_lo"] + 5
                add(rep1, "repair", "更换驱动后恢复点亮，维修期间不在险。")
                add(rep1 + 40, "withdrawal", "工作状态下直接永久退出，故障-修复链未闭合。")
            elif q_reason == "event_after_withdrawal":
                # 确定性演示：故障->停机中退出->退出后又到达修复
                t1 = min(320., RECURRENT_CUTOFF * .2)
                add(t1, "failure", "灯带熄灭，光通量低于展陈阈值，登记故障。")
                wd = t1 + 6
                add(wd, "withdrawal", "停机维修中决定永久退出该试件。")
                add(wd + 12, "repair", "退出后才到达的修复记录，应整件隔离。")
            else:
                # 普通试件：随机可修复复发过程
                while True:
                    t += rng.expovariate(prof["rate"])
                    if t >= RECURRENT_CUTOFF:
                        break
                    add(t, "failure", "灯带熄灭，光通量低于展陈阈值，登记故障。")
                    rep = t + rng.uniform(prof["repair_lo"], prof["repair_hi"])
                    if rep >= RECURRENT_CUTOFF:
                        break
                    add(rep, "repair", "更换驱动/灯珠后恢复点亮，维修期间不在险。")
                    t = rep

            # 乱序入库：打乱到达顺序，received_seq 记录真实接收次序
            order = list(range(len(raw)))
            rng.shuffle(order)
            for received, pos in enumerate(order, start=1):
                et, kind, note = raw[pos]
                db.add(RepairEvent(specimen_id=sp.id, kind=kind, event_time=et,
                                   received_seq=received, note=note))
        db.flush()

    # 获批的复发研究示例（真实算法计算）
    if not db.query(RecurrentRun).filter_by(name="两批灯带累计故障负担 · MCF比较").first():
        a, b = cohorts
        result = analyze_recurrent(
            a, b, specimen_event_rows(db, a.id), specimen_event_rows(db, b.id),
            RECURRENT_CUTOFF, .95)
        run = RecurrentRun(name="两批灯带累计故障负担 · MCF比较", cohort_a_id=a.id,
                           cohort_b_id=b.id, cutoff_hours=RECURRENT_CUTOFF,
                           confidence=.95, status="completed", result=result,
                           owner="江栩 · 耐久研究员")
        db.add(run)
        db.flush()
        db.add(MaintenanceNote(
            recurrent_run_id=run.id, title="复发故障与维修在险口径说明",
            interpretation=("以试件为单位累计各次熄灭故障，维修停机时间不计在险；"
                            "断裂或退出后到达事件的试件已整件隔离，原因可在事件链核对。"),
            recommendation="结合MCF同时带与现场应力安排预防性检修，不把单次故障或p值当作更换依据。",
            status="approved", owner="江栩 · 耐久研究员", reviewer="阮青 · 材料负责人",
            review_note="批准复发研究归档；隔离试件清单与在险历程已核对，维护周期另行现场复核。",
            reviewed_at="2026-11-10T00:00:00+00:00"))


if __name__ == "__main__":
    seed()
