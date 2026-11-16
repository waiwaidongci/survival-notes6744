"""按试件重建可修复灯带的工作区间。

输入是试件接收时乱序的故障(failure)/修复(repair)/永久退出(withdrawal)记录。
本模块负责：
1. 按 (时间, 接收序号) 稳定排序，恢复事件链；
2. 逐事件推进“工作/停机/已退出”状态机，切出工作区间（维修期间不在险）；
3. 断裂或退出之后到达的事件不静默丢弃，而是把整件隔离，并给出可核对的隔离原因。

被隔离试件的全部记录保留在事件链里用于审计，但其在险历程不进入MCF计算。
"""
import math

# 隔离原因代码，页面与导出共用
REASON_UNKNOWN_KIND = "unknown_event_kind"            # 事件类型无法识别
REPAIR_WHILE_WORKING = "repair_while_working"          # 工作中收到修复，状态断裂
WITHDRAWAL_WHILE_WORKING = "withdrawal_while_working"  # 工作中永久退出（无故障终止，链不闭合）
FAILURE_WHILE_DOWN = "failure_while_down"              # 停机未修复又来故障
EVENT_AFTER_WITHDRAWAL = "event_after_withdrawal"      # 永久退出后仍有事件到达
EVENT_AFTER_CHAIN_BREAK = "event_after_chain_break"    # 已断裂之后又有事件到达
EVENT_BEYOND_CUTOFF = "event_beyond_study_cutoff"      # 记录时间超出研究观察窗
NON_POSITIVE_TIME = "non_positive_event_time"          # 时间必须为正

REASON_TEXT = {
    REASON_UNKNOWN_KIND: "事件类型无法识别，整件隔离",
    REPAIR_WHILE_WORKING: "工作状态下收到修复记录，事件链断裂，整件隔离",
    WITHDRAWAL_WHILE_WORKING: "工作状态下永久退出，未闭合的故障-修复链断裂，整件隔离",
    FAILURE_WHILE_DOWN: "停机维修期间又到达故障记录，事件链断裂，整件隔离",
    EVENT_AFTER_WITHDRAWAL: "永久退出后仍有事件到达，整件隔离",
    EVENT_AFTER_CHAIN_BREAK: "链断裂后仍有事件到达，整件隔离",
    EVENT_BEYOND_CUTOFF: "记录时间超出研究观察窗，整件隔离",
    NON_POSITIVE_TIME: "存在非正时间记录，整件隔离",
}

KINDS = ("failure", "repair", "withdrawal")
_KIND_CN = {"failure": "故障", "repair": "修复", "withdrawal": "永久退出"}


def validate_raw_event(ev):
    """单条记录的硬校验；返回错误原因代码或 None。"""
    if ev.get("kind") not in KINDS:
        return REASON_UNKNOWN_KIND
    t = ev.get("event_time")
    if type(t) not in (int, float) or not math.isfinite(t) or t <= 0 or abs(t) > 1e6:
        return NON_POSITIVE_TIME
    return None


def build_specimen_chain(events, cutoff):
    """重建单个试件的事件链与工作区间。

    events: [{"id","kind","event_time","received_seq","note"}, ...] 乱序记录
    cutoff: 研究观察窗右端点（小时）
    返回 dict：事件链（排序后、含状态标记）、工作区间、在险时长、隔离信息。
    """
    ordered = sorted(events, key=lambda e: (e["event_time"], e.get("received_seq", 0), e.get("id", 0)))
    chain = []
    intervals = []          # [work_start, work_end) 形式的工作区间，故障时刻仍在险
    failure_count = 0
    quarantined = False
    reason_code = ""
    reason_event_id = None

    state = "working"       # working | down | withdrawn
    seg_start = 0.0         # 当前工作区间起点

    def isolate(code, ev):
        nonlocal quarantined, reason_code, reason_event_id
        if not quarantined:
            quarantined = True
            reason_code = code
            reason_event_id = ev.get("id")

    for ev in ordered:
        bad = validate_raw_event(ev)
        if bad:
            isolate(bad, ev)
            chain.append({**ev, "kind_cn": _KIND_CN.get(ev.get("kind"), "未知"),
                          "state_after": "quarantined", "accepted": False,
                          "isolation_reason": reason_code if reason_event_id == ev.get("id") else ""})
            continue
        t = ev["event_time"]
        kind = ev["kind"]
        accepted = True

        if t > cutoff + 1e-9:
            isolate(EVENT_BEYOND_CUTOFF, ev)
            accepted = False
        elif quarantined:
            # 首次隔离之后到达的任何事件一律不接收入链计算
            isolate(EVENT_AFTER_CHAIN_BREAK, ev)
            accepted = False
        elif state == "withdrawn":
            isolate(EVENT_AFTER_WITHDRAWAL, ev)
            accepted = False
        elif kind == "failure":
            if state == "down":
                isolate(FAILURE_WHILE_DOWN, ev)
                accepted = False
            else:  # working
                intervals.append((seg_start, t))
                failure_count += 1
                state = "down"
        elif kind == "repair":
            if state == "working":
                isolate(REPAIR_WHILE_WORKING, ev)
                accepted = False
            else:  # down
                state = "working"
                seg_start = t
        elif kind == "withdrawal":
            if state == "down":
                # 停机中永久退出：当前停机区间自然结束，不产生在险时间
                state = "withdrawn"
            else:  # working：未闭合退出，链断裂
                isolate(WITHDRAWAL_WHILE_WORKING, ev)
                accepted = False

        chain.append({
            **ev,
            "kind_cn": _KIND_CN[kind],
            "state_after": "quarantined" if quarantined else state,
            "accepted": accepted and not quarantined,
            "isolation_reason": (reason_code if quarantined and reason_event_id == ev.get("id") else ""),
        })

    # 观察窗结束时仍在工作：补一段到 cutoff 的右删失工作区间
    censored_while_down = False
    if not quarantined and state == "working":
        intervals.append((seg_start, cutoff))
    elif not quarantined and state == "down":
        # 最后一次故障后未修复也未退出：故障时刻已计入上一工作区间，停机时间不在险
        censored_while_down = True

    exposure = sum(b - a for a, b in intervals)
    # 隔离试件不向MCF提供任何在险历程
    if quarantined:
        intervals = []
        exposure = 0.0
        failure_count = 0

    return {
        "chain": chain,
        "intervals": [{"start": a, "end": b, "exposure": b - a} for a, b in intervals],
        "failure_times": [e["event_time"] for e in chain
                          if e["kind"] == "failure" and e["accepted"] and not quarantined],
        "failure_count": failure_count,
        "exposure_hours": exposure,
        "quarantined": quarantined,
        "isolation_reason": reason_code,
        "isolation_reason_text": REASON_TEXT.get(reason_code, ""),
        "isolation_event_id": reason_event_id,
        "terminal_state": ("quarantined" if quarantined else state),
        "censored_while_down": censored_while_down,
    }
