"""可修复系统的平均累计故障函数（Mean Cumulative Function, MCF）。

口径（Nelson, 《Recurrent Events Data Analysis for Product Repairs...》；
Lawless & Nadeau 1995 的计数过程稳健方差）：
- 以**试件**为独立单位；同一试件的多次故障是相关的重复观测，不能拆成独立试件，
  否则会低估不确定性（稳健方差与 bootstrap 都在试件层面重抽样）。
- 在险人数 n(t) 只统计在 t 时刻处于工作区间内的试件；维修停机、永久退出后均不在险。
  故障时刻本身计入在险（工作区间在故障时刻闭合）。
- 事件时点 t 的增量 ΔMCF = d(t)/n(t)，MCF 为累计阶梯；维修本身不使曲线上升。
- 不确定性以**试件非参数 bootstrap** 为准：
  * 逐点区间 = bootstrap 分位数（自动容纳故障计数的偏态，小样本优于正态近似）；
  * 同时置信带 = bootstrap 偏差上确界分位数，覆盖率面向整条曲线而非单个时点；
  * 另附 Lawless-Nadeau 稳健标准误作描述量。
"""
import bisect
import math
import random

BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20261116


class RiskCoverage:
    """工作区间覆盖计数：n(t)=#{区间: start<=t<=end}，故障时刻本身在险。"""

    def __init__(self, specimens):
        starts, ends = [], []
        for sp in specimens:
            for iv in sp["intervals"]:
                starts.append(iv["start"])
                ends.append(iv["end"])
        starts.sort()
        ends.sort()
        self.starts = starts
        self.ends = ends

    def at_risk(self, t):
        return bisect.bisect_right(self.starts, t) - bisect.bisect_left(self.ends, t)


def _failure_events(specimens):
    events = []
    for sp in specimens:
        for t in sp["failure_times"]:
            events.append(t)
    events.sort()
    return events


def _mcf_on_grid(specimens, grid):
    """在给定时间网格上返回MCF阶梯取值（阶梯右连续，网格点取(0,t]累计值）。"""
    events = _failure_events(specimens)
    distinct = sorted(set(events))
    coverage = RiskCoverage(specimens)
    mcf = 0.
    values = []
    di = 0
    for t in grid:
        while di < len(distinct) and distinct[di] <= t:
            tev = distinct[di]
            d = sum(1 for x in events if x == tev)
            mcf += d / coverage.at_risk(tev)
            di += 1
        values.append(mcf)
    return values


def _robust_se_curve(specimens, grid, base_vals, n_specimens):
    """Lawless-Nadeau 稳健标准误：以试件累计故障计数 N_s(t) 的样本方差/n。"""
    ses = []
    count_so_far = [0] * n_specimens
    failure_lists = [sp["failure_times"] for sp in specimens]
    for t, mcf in zip(grid, base_vals):
        for i, fts in enumerate(failure_lists):
            count_so_far[i] += sum(1 for x in fts if x == t)
        if n_specimens > 1:
            sample_var = sum((c - mcf) ** 2 for c in count_so_far) / (n_specimens - 1)
            ses.append(math.sqrt(sample_var / n_specimens))
        else:
            ses.append(0.)
    return ses


def mcf_bootstrap(specimens, confidence=.95,
                  n_resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    """单批MCF：点估计 + bootstrap逐点分位数区间 + 原始尺度上确界同时带 + 稳健SE。"""
    n = len(specimens)
    if n < 2:
        raise ValueError("每组隔离后至少需要2个有效试件")
    if not math.isfinite(confidence) or not .8 <= confidence <= .99:
        raise ValueError("置信水平必须位于[0.8,0.99]")

    events = _failure_events(specimens)
    distinct = sorted(set(events))
    coverage = RiskCoverage(specimens)
    base = _mcf_on_grid(specimens, distinct) if distinct else []
    robust_ses = _robust_se_curve(specimens, distinct, base, n) if distinct else []

    # 在险数（用于前端在险历程核对）
    at_risk = [coverage.at_risk(t) for t in distinct]
    event_counts = [sum(1 for x in events if x == t) for t in distinct]

    result = {
        "n_specimens": n,
        "n_failures": len(events),
        "total_exposure_hours": sum(sp["exposure_hours"] for sp in specimens),
        "last_observed": max((iv["end"] for sp in specimens for iv in sp["intervals"]),
                             default=0.),
        "confidence": confidence,
        "variance_method": "Lawless-Nadeau robust SE + specimen nonparametric bootstrap",
    }

    # t=0 起点
    curve = [{"time": 0., "at_risk": n, "events": 0, "mcf": 0.,
              "se": 0., "lower": 0., "upper": 0.}]
    if not distinct:
        result.update({
            "curve": curve,
            "pointwise_method": "bootstrap percentile",
            "band": {"band_method": "specimen bootstrap (raw-scale supremum)",
                     "n_resamples": n_resamples, "seed": seed, "achieved_level": confidence,
                     "grid": [], "base_mcf": [], "lower": [], "upper": [],
                     "estimable": False, "reason": "无故障事件，MCF恒为0，同时带退化为[0,0]。"},
        })
        return result

    alpha = 1 - confidence
    q_lo = max(0, math.floor(n_resamples * alpha / 2) - 1)
    q_hi = min(n_resamples - 1, math.ceil(n_resamples * (1 - alpha / 2)) - 1)

    rng = random.Random(seed)
    # 每个网格点收集 bootstrap MCF；同时收集每条重抽样曲线的偏差上/下确界
    boot_cols = [[] for _ in distinct]
    lower_dev, upper_dev = [], []
    for _ in range(n_resamples):
        resample = [specimens[rng.randrange(n)] for _ in range(n)]
        vals = _mcf_on_grid(resample, distinct)
        for col, v in zip(boot_cols, vals):
            col.append(v)
        deltas = [v - b for v, b in zip(vals, base)]
        lower_dev.append(min(deltas))
        upper_dev.append(max(deltas))
    for col in boot_cols:
        col.sort()
    lower_dev.sort()
    upper_dev.sort()

    for i, t in enumerate(distinct):
        curve.append({
            "time": t, "at_risk": at_risk[i], "events": event_counts[i],
            "mcf": base[i], "se": robust_ses[i],
            "lower": boot_cols[i][q_lo], "upper": boot_cols[i][q_hi],
        })
    band = {
        "band_method": "specimen nonparametric bootstrap, raw-scale supremum",
        "n_resamples": n_resamples, "seed": seed, "achieved_level": confidence,
        "grid": list(distinct), "base_mcf": list(base),
        "lower": [b + lower_dev[q_lo] for b in base],
        "upper": [b + upper_dev[q_hi] for b in base],
        "estimable": True,
        "reason": "分位数基于试件重抽样；维修停机与退出后的时间不在险，带的覆盖率面向整条MCF曲线。",
    }
    result.update({"curve": curve, "pointwise_method": "bootstrap percentile", "band": band})
    return result


def compare_mcf(spec_a, spec_b, confidence=.95,
                n_resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    """两批MCF及差值 A-B 的逐点bootstrap区间与同时置信带。"""
    fit_a = mcf_bootstrap(spec_a, confidence, n_resamples, seed)
    fit_b = mcf_bootstrap(spec_b, confidence, n_resamples, seed + 1)

    grid = sorted(set(p["time"] for p in fit_a["curve"] if p["time"] > 0)
                  | set(p["time"] for p in fit_b["curve"] if p["time"] > 0))
    va = _mcf_on_grid(spec_a, grid)
    vb = _mcf_on_grid(spec_b, grid)
    diff = [a - b for a, b in zip(va, vb)]

    # 差值：两组独立，分别按试件重抽样，差值带用原始尺度上确界
    rng = random.Random(seed + 2)
    na, nb = len(spec_a), len(spec_b)
    diff_cols = [[] for _ in grid]
    dev_lo, dev_hi = [], []
    for _ in range(n_resamples):
        ra = [spec_a[rng.randrange(na)] for _ in range(na)]
        rb = [spec_b[rng.randrange(nb)] for _ in range(nb)]
        rdiff = [a - b for a, b in zip(_mcf_on_grid(ra, grid), _mcf_on_grid(rb, grid))]
        for col, v in zip(diff_cols, rdiff):
            col.append(v)
        deltas = [r - d for r, d in zip(rdiff, diff)]
        dev_lo.append(min(deltas))
        dev_hi.append(max(deltas))
    alpha = 1 - confidence
    q_lo = max(0, math.floor(n_resamples * alpha / 2) - 1)
    q_hi = min(n_resamples - 1, math.ceil(n_resamples * (1 - alpha / 2)) - 1)
    for col in diff_cols:
        col.sort()
    dev_lo.sort()
    dev_hi.sort()
    return {
        "fit_a": fit_a,
        "fit_b": fit_b,
        "difference": {
            "grid": grid,
            "mcf_diff": diff,
            "pointwise_lower": [col[q_lo] for col in diff_cols],
            "pointwise_upper": [col[q_hi] for col in diff_cols],
            "simultaneous_lower": [d + dev_lo[q_lo] for d in diff],
            "simultaneous_upper": [d + dev_hi[q_hi] for d in diff],
            "excludes_zero_everywhere": all(
                lo > 0 or hi < 0
                for lo, hi in zip([d + dev_lo[q_lo] for d in diff],
                                  [d + dev_hi[q_hi] for d in diff])),
            "band_method": "specimen bootstrap, difference-scale supremum",
            "pointwise_method": "bootstrap percentile",
            "n_resamples": n_resamples,
            "seed": seed + 2,
        },
    }
