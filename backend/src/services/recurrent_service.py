"""复发事件研究编排：事件流 -> 工作区间重建/隔离 -> 两批MCF比较。"""
import math
from ..models import Specimen, RepairEvent
from ..utils.fingerprint import fingerprint
from .event_chain import build_specimen_chain, REASON_TEXT
from .mcf_algorithm import compare_mcf, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED


def specimen_event_rows(db, cohort_id):
    """取一批所有试件的复发事件原始记录（保持接收乱序）。"""
    specimens = (db.query(Specimen)
                 .filter(Specimen.cohort_id == cohort_id)
                 .order_by(Specimen.code).all())
    result = []
    for sp in specimens:
        events = (db.query(RepairEvent)
                  .filter(RepairEvent.specimen_id == sp.id)
                  .order_by(RepairEvent.received_seq).all())
        result.append({
            "specimen_id": sp.id,
            "code": sp.code,
            "material": sp.material,
            "events": [{"id": e.id, "kind": e.kind, "event_time": e.event_time,
                        "received_seq": e.received_seq, "note": e.note} for e in events],
        })
    return result


def build_cohort_specimens(rows, cutoff):
    """对一批试件逐个重建事件链，返回有效试件链与隔离清单。"""
    valid, quarantined = [], []
    for row in rows:
        chain = build_specimen_chain(row["events"], cutoff)
        chain["specimen_id"] = row["specimen_id"]
        chain["code"] = row["code"]
        chain["material"] = row["material"]
        if chain["quarantined"]:
            quarantined.append({
                "specimen_id": row["specimen_id"],
                "code": row["code"],
                "isolation_reason": chain["isolation_reason"],
                "isolation_reason_text": chain["isolation_reason_text"],
                "isolation_event_id": chain["isolation_event_id"],
                "terminal_state": chain["terminal_state"],
                "chain": chain["chain"],
            })
        else:
            valid.append(chain)
    return valid, quarantined


def analyze_recurrent(cohort_a, cohort_b, rows_a, rows_b, cutoff, confidence=.95,
                      n_resamples=BOOTSTRAP_RESAMPLES):
    if cohort_a.id == cohort_b.id:
        raise ValueError("必须选择两批不同工艺")
    if not math.isfinite(cutoff) or cutoff <= 0 or cutoff > 1e6:
        raise ValueError("观察窗右端点必须是(0,1000000]内的有限小时数")

    valid_a, quar_a = build_cohort_specimens(rows_a, cutoff)
    valid_b, quar_b = build_cohort_specimens(rows_b, cutoff)
    if len(valid_a) < 2 or len(valid_b) < 2:
        raise ValueError("隔离后每批至少需要2个有效试件才能估计MCF与置信带")

    comparison = compare_mcf(valid_a, valid_b, confidence, n_resamples, BOOTSTRAP_SEED)

    def group_payload(cohort, rows, valid, quarantined, fit):
        return {
            "cohort": {"id": cohort.id, "code": cohort.code, "name": cohort.name,
                       "process": cohort.process},
            "specimen_total": len(rows),
            "specimen_valid": len(valid),
            "specimen_quarantined": len(quarantined),
            "n_failures": fit["n_failures"],
            "total_exposure_hours": fit["total_exposure_hours"],
            "curve": fit["curve"],
            "band": fit["band"],
            "pointwise_method": fit["pointwise_method"],
            "variance_method": fit["variance_method"],
            "last_observed": fit["last_observed"],
            # 每个有效试件的在险历程与事件链，供页面/导出核对
            "specimen_histories": [{
                "specimen_id": c["specimen_id"], "code": c["code"],
                "terminal_state": c["terminal_state"],
                "failure_count": c["failure_count"],
                "failure_times": c["failure_times"],
                "exposure_hours": c["exposure_hours"],
                "intervals": c["intervals"],
                "chain": c["chain"],
                "censored_while_down": c["censored_while_down"],
            } for c in valid],
            "quarantined_specimens": quarantined,
        }

    groups = [
        group_payload(cohort_a, rows_a, valid_a, quar_a, comparison["fit_a"]),
        group_payload(cohort_b, rows_b, valid_b, quar_b, comparison["fit_b"]),
    ]
    inputs = [
        {"cohort": groups[0]["cohort"], "cutoff": cutoff,
         "specimens": [{"code": r["code"], "events": r["events"]} for r in rows_a]},
        {"cohort": groups[1]["cohort"], "cutoff": cutoff,
         "specimens": [{"code": r["code"], "events": r["events"]} for r in rows_b]},
    ]
    return {
        "groups": groups,
        "difference": comparison["difference"],
        "cutoff_hours": cutoff,
        "confidence": confidence,
        "time_unit": "小时",
        "bootstrap_resamples": n_resamples,
        "input_hash": fingerprint({
            "method": "mcf-bootstrap-supremum-v1",
            "groups": inputs, "confidence": confidence,
            "cutoff_hours": cutoff, "time_unit": "hours",
            "bootstrap_seed": BOOTSTRAP_SEED,
        }),
        "method_version": "mcf-bootstrap-supremum-v1",
        "isolation_reasons": REASON_TEXT,
        "interpretation": _interpret(comparison["difference"]),
        "assumptions": (
            "以试件为独立重抽样单位，同一试件的多次故障是相关重复观测，不拆成独立试件；"
            "维修停机与永久退出后的时间不在险，故障时刻本身在险。"
            "逐点区间为bootstrap分位数区间，同时置信带为bootstrap偏差上确界带，覆盖率面向整条MCF曲线；"
            "断裂或退出后到达事件的试件整件隔离并保留原因。结果为关联研究，不自动决定维修周期。"
        ),
    }


def _interpret(diff):
    if not diff["grid"]:
        return "两批均无故障事件，MCF恒为0，无法比较累计故障负担。"
    grid = diff["grid"]
    lo, hi = diff["simultaneous_lower"], diff["simultaneous_upper"]
    if diff["excludes_zero_everywhere"]:
        if all(d > 0 for d in diff["mcf_diff"]):
            return "同时置信带全程位于零上方：A批平均累计故障函数在整个观察窗内系统性高于B批。"
        return "同时置信带全程位于零下方：A批平均累计故障函数在整个观察窗内系统性低于B批。"
    # 带在部分（通常是信息不足的早期）含零：找出带首次稳定不含零的时点
    first_clear = next((t for t, l, u in zip(grid, lo, hi) if l > 0 or u < 0), None)
    if first_clear is not None:
        direction = "高于" if diff["mcf_diff"][-1] > 0 else "低于"
        return (f"同时置信带在约 {first_clear:.0f} 小时后稳定不含零，A批累计故障负担{direction}B批；"
                "早期在险信息不足，差异需经过一段观察时间才建立，不能外推到时间原点。")
    return "差值的同时置信带在整个观察窗内都包含零：尚不能断言两批累计故障负担存在稳定差异。"
