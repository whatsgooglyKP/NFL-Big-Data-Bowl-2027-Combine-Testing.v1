#!/usr/bin/env python3
"""DL burst vs. Sunday get-off — a quick, honest check for BDB 2027.

Question: does Combine burst (especially the official 10-yard split)
show up as get-off on pass-rush snaps, and does that get-off — and the
10-yard split itself — travel with on-field success (pressure and sack
rate), not just playing time?

The headline sample is **all defensive linemen** (official 10-yard split
and at least 20 pass-rush snaps, 2023–2025 classes pooled). Every table
and chart also breaks out Edge (DE + OLB who tested in the DL Combine
group) vs Interior (DT + NT). Within Edge alone or Interior alone, the
10-yard-to-pressure link is weaker and not significant; part of the
pooled all-DL effect comes from edges being both faster and better
rushers. Offensive linemen are out of scope.

Game tracking in this competition covers only the 510-player rookie
cohort, so get-off is measured from the rusher's own track, not from a
QB or blocker track.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/dl_burst.py
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/dl_burst.py --rebuild
"""
from __future__ import annotations

import argparse
import gc
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

MPH = 2.0455
ACCEL_CLIP = 12.0
GAME_YEARS = (2023, 2024, 2025)
CHUNKSIZE = 2_000_000
MIN_RUSH_PLAYS = 20
N_BOOT = 2000
BOOT_SEED = 2027
T_FIRST_STEP = 0.40  # seconds after snap (or after first Combine frame)
S15 = 15.0 / MPH     # yd/s
S18 = 18.0 / MPH
SNAP_EVENTS = frozenset({"ball_snap", "autoevent_ballsnap"})
LINED_UP_RUSH = frozenset({"EDGE", "INTERIOR_LINE"})
DL_POSITIONS = ("DE", "DT", "NT", "OLB")
EDGE_POS = frozenset({"DE", "OLB"})
INTERIOR_POS = frozenset({"DT", "NT"})
SUBTYPE_ORDER = ["Edge", "Interior"]
SUBTYPE_COLOR = {"Edge": "#D55E00", "Interior": "#0072B2", "All DL": "#333333"}

# Primary Combine burst features. "direction" is the sign of a *good* Combine
# number: -1 means a lower value (faster time) is better.
PRIMARY_FEATURES = [
    ("official_ten_yd", "Official 10-yard split", -1),
    ("c_40_accel", "40-yard peak acceleration", +1),
    ("c_t15", "40 time to 15 mph", -1),
    ("dl_pass_rush_accel", "Pass-rush drill peak accel", +1),
]
PRIMARY_OUTCOME = "speed_1s_mph"  # median speed 1.0s after snap, higher = better get-off

# Secondary Combine features (reported, not in the Holm family).
SECONDARY_FEATURES = [
    ("official_forty", "Official 40 time", -1),
    ("c_top_mph", "40-yard tracked top speed", +1),
    ("c_t90", "40 time to 90% top speed", -1),
    ("c_t18", "40 time to 18 mph", -1),
    ("c_t10_derived", "Derived 10-yard split", -1),
    ("c_40_accel_first", "40 first-step acceleration", +1),
    ("dl_pass_rush_max_s", "Pass-rush drill top speed", +1),
    ("dl_pass_rush_accel_first", "Pass-rush drill first-step accel", +1),
    ("dl_front_start_accel", "Front-start / wave drill accel", +1),
    ("dl_four_bag_accel", "Four-bag agility drill accel", +1),
    ("dl_run_club_accel", "Run-and-club drill accel", +1),
    ("dl_body_control_accel", "Body-control drill accel", +1),
    ("dl_hoop_accel", "Run-the-hoop drill accel", +1),
]

SECONDARY_OUTCOMES = [
    ("player_get_off", "NFL get-off time (sec, lower=faster)", -1),
    ("speed_1s_mph", "Speed at 1.0s after snap (mph)", +1),
    ("speed_15s_mph", "Speed at 1.5s after snap (mph)", +1),
    ("time_to_5yd", "Time to travel 5 yards (sec)", -1),
    ("accel_first", "First-step acceleration after snap", +1),
]

# Official success outcomes are on-field gameplay, not playing time.
# Pressure / sack / hurry rates are measured on the same REG standing
# pass-rush snaps as get-off (≥20 snaps). Playing time is context only.
# career_defensive_snaps is cumulative, so 2023 rookies have a head start
# (three seasons vs one for 2025); any snap test still controls for
# draft year (never draft slot).
SUCCESS_PRIMARY = [
    ("pressure_rate", "Pressure rate on pass-rush plays"),
    ("sack_rate", "Sack rate on pass-rush plays"),
]
SUCCESS_COMPANION = [
    ("hurry_rate", "Hurry rate on pass-rush plays"),
    ("pressure_rate_blocked", "Pressure rate excluding unblocked pressures"),
]
PLAYTIME_SECONDARY = [
    ("career_defensive_snaps", "Career defensive snaps"),
    ("snaps_per_game", "Defensive snaps per game active"),
    ("start_rate", "Start rate (starts / games active)"),
]
# Backward-compatible aliases used by the older career-family printer.
CAREER_PRIMARY = SUCCESS_PRIMARY
CAREER_SECONDARY = PLAYTIME_SECONDARY

DL_DRILLS = {
    "PASS_RUSH_DRILL": "pass_rush",
    "FRONT_START_WAVE_DRILL_AND_LATERAL_REACTION": "front_start",
    "FOUR_BAG_AGILITY_DRILL": "four_bag",
    "RUN_AND_CLUB_DRILL": "run_club",
    "BODY_CONTROL_DRILL": "body_control",
    "RUN_THE_HOOP_DRILL": "hoop",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def coerce_bool(s: pd.Series) -> pd.Series:
    return s.map({
        True: True, False: False, "TRUE": True, "FALSE": False,
        "True": True, "False": False, 1: True, 0: False, 1.0: True, 0.0: False,
    })


def spearman_partial(x: pd.Series, y: pd.Series, year: pd.Series) -> dict:
    """Spearman ρ plus the draft-year-controlled partial (both sides demeaned within draft-year cells).

    No draft slot / pick / round is used (Kevin's rule, 11/2026).
    """
    d = pd.DataFrame({"x": x, "y": y, "year": year}).dropna()
    out = {"n": int(len(d)), "rho": np.nan, "p": np.nan, "partial_rho": np.nan, "partial_p": np.nan}
    if len(d) < 8:
        return out
    if d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    if d["year"].nunique() >= 2:
        rx = d["x"] - d.groupby("year")["x"].transform("mean")
        ry = d["y"] - d.groupby("year")["y"].transform("mean")
        if rx.nunique() >= 2 and ry.nunique() >= 2:
            pr, pp = stats.spearmanr(rx, ry)
            out["partial_rho"], out["partial_p"] = float(pr), float(pp)
    return out


def _residualize(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    # Drop constant / collinear columns so lstsq is stable in small subtype samples.
    keep = [0]
    for j in range(1, A.shape[1]):
        cand = A[:, keep + [j]]
        if np.linalg.matrix_rank(cand) > len(keep):
            keep.append(j)
    A = A[:, keep]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def spearman_controlled(x: pd.Series, y: pd.Series, df: pd.DataFrame, control_kind: str = "year") -> dict:
    """Spearman ρ after residualizing both sides on draft-year dummies (the only control; no draft slot)."""
    d = pd.DataFrame({"x": x, "y": y, "draft_year": df["draft_year"]}).dropna()
    out = {
        "n": int(len(d)), "rho": np.nan, "p": np.nan,
        "partial_year_rho": np.nan, "partial_year_p": np.nan,
        "control": "year",
        "official_partial_rho": np.nan, "official_partial_p": np.nan,
    }
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    year_dummies = pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True).astype(float)
    if year_dummies.shape[1] >= 1:
        X = year_dummies.to_numpy(dtype=float)
        if np.unique(X, axis=0).shape[0] >= 2:
            rx = _residualize(d["x"].to_numpy(dtype=float), X)
            ry = _residualize(d["y"].to_numpy(dtype=float), X)
            if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
                pr, pp = stats.spearmanr(rx, ry)
                out["partial_year_rho"], out["partial_year_p"] = float(pr), float(pp)
    out["official_partial_rho"], out["official_partial_p"] = out["partial_year_rho"], out["partial_year_p"]
    return out


def _year_controls(d: pd.DataFrame, extra: pd.DataFrame | None = None) -> pd.DataFrame:
    """Design matrix used for official DL partials: draft-year dummies (+ optional extra). No draft slot."""
    year_dummies = pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True).astype(float)
    parts = []
    if year_dummies.shape[1] >= 1:
        parts.append(year_dummies)
    if extra is not None:
        parts.append(extra)
    if not parts:
        return pd.DataFrame(index=d.index)
    return pd.concat(parts, axis=1)


def spearman_residualized(x: pd.Series, y: pd.Series, controls: pd.DataFrame) -> dict:
    """Spearman ρ of x vs y after residualizing both sides on `controls` (OLS)."""
    d = pd.concat([x.rename("x"), y.rename("y"), controls], axis=1).dropna()
    out = {"n": int(len(d)), "rho": np.nan, "p": np.nan}
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    X = controls.loc[d.index].to_numpy(dtype=float)
    if np.unique(X, axis=0).shape[0] < 2:
        return out
    rx = _residualize(d["x"].to_numpy(dtype=float), X)
    ry = _residualize(d["y"].to_numpy(dtype=float), X)
    if np.unique(rx).size < 2 or np.unique(ry).size < 2:
        return out
    rho, p = stats.spearmanr(rx, ry)
    out["rho"], out["p"] = float(rho), float(p)
    return out


def bootstrap_partial_ci(
    x: pd.Series,
    y: pd.Series,
    df: pd.DataFrame,
    extra: pd.DataFrame | None = None,
    n_boot: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> tuple[float, float, int]:
    """95% percentile CI for the year (plus optional extra) partial Spearman.

    Resamples players with replacement. Returns (lo, hi, n_valid_draws).
    """
    base = pd.DataFrame({
        "x": x.to_numpy(),
        "y": y.to_numpy(),
        "draft_year": df["draft_year"].to_numpy(),
    }, index=x.index if hasattr(x, "index") else None)
    if extra is not None:
        for c in extra.columns:
            base[f"ex_{c}"] = extra[c].to_numpy()
    base = base.dropna().reset_index(drop=True)
    if len(base) < 8:
        return np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    rhos: list[float] = []
    ex_cols = [c for c in base.columns if c.startswith("ex_")]
    for _ in range(n_boot):
        idx = rng.integers(0, len(base), size=len(base))
        b = base.iloc[idx].reset_index(drop=True)
        if b["x"].nunique() < 2 or b["y"].nunique() < 2:
            continue
        extra_b = b[ex_cols].rename(columns=lambda c: c[3:]) if ex_cols else None
        controls = _year_controls(b, extra_b)
        X = controls.to_numpy(dtype=float)
        if np.unique(X, axis=0).shape[0] < 2:
            continue
        rx = _residualize(b["x"].to_numpy(dtype=float), X)
        ry = _residualize(b["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size < 2 or np.unique(ry).size < 2:
            continue
        rho, _p = stats.spearmanr(rx, ry)
        if np.isfinite(rho):
            rhos.append(float(rho))
    if len(rhos) < max(50, n_boot // 20):
        return np.nan, np.nan, len(rhos)
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return float(lo), float(hi), len(rhos)


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#333333",
        "axes.labelcolor": "#222222",
        "text.color": "#222222",
        "xtick.color": "#222222",
        "ytick.color": "#222222",
        "axes.grid": True,
        "grid.color": "#DDDDDD",
        "grid.linewidth": 0.6,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "figure.titlesize": 15,
        "font.family": "DejaVu Sans",
    })


def load_roster() -> pd.DataFrame:
    pl = pd.read_csv(DATA / "players.csv")
    cr = pd.read_csv(DATA / "combine_results.csv")
    cs = pd.read_csv(DATA / "player_career_successes.csv")
    M = pl[pl["nfl_position"].isin(DL_POSITIONS)].merge(cr, on=["nfl_id", "draft_year"], how="left")
    M = M.merge(cs, on="nfl_id", how="left")
    # Every DE/DT/NT/OLB in this cohort tested in the DL Combine group.
    # OLB are included as Edge because they ran DL drills and almost always
    # line up as EDGE on Sundays. Offensive linemen are not in this file.
    M["subtype"] = np.where(M["nfl_position"].isin(EDGE_POS), "Edge", "Interior")
    M = M.drop(columns=[c for c in M.columns if "pick" in c.lower() or c in ("draft_round",)], errors="ignore")
    M["start_rate"] = M["career_games_started"] / M["career_games_active"].replace(0, np.nan)
    M["snaps_per_game"] = M["career_defensive_snaps"] / M["career_games_active"].replace(0, np.nan)
    M = M.rename(columns={"ten_yd_split": "official_ten_yd", "forty": "official_forty"})
    log(
        f"DL roster: {len(M)} players "
        f"(Edge {int((M.subtype=='Edge').sum())} = DE {(M.nfl_position=='DE').sum()} + OLB {(M.nfl_position=='OLB').sum()}; "
        f"Interior {int((M.subtype=='Interior').sum())} = DT {(M.nfl_position=='DT').sum()} + NT {(M.nfl_position=='NT').sum()})"
    )
    return M


def _attempt_burst(g: pd.DataFrame) -> dict:
    """Peak speed, peak accel, first-step accel, and time to 15/18 mph."""
    g = g.sort_values("time")
    t0 = pd.to_datetime(g["time"].iloc[0])
    t = (pd.to_datetime(g["time"]) - t0).dt.total_seconds().to_numpy()
    s = g["s"].to_numpy(dtype=float)
    x = g["x"].to_numpy(dtype=float)
    n = len(g)
    out = {
        "max_s": np.nan, "accel": np.nan, "accel_first": np.nan,
        "t90": np.nan, "t15": np.nan, "t18": np.nan,
        "t10": np.nan, "n_frames": n,
    }
    if n == 0 or not np.isfinite(s).any():
        return out
    i_max = int(np.nanargmax(s))
    max_s = float(s[i_max])
    out["max_s"] = max_s
    if max_s > 0:
        hit = np.where(s >= 0.9 * max_s)[0]
        if len(hit):
            out["t90"] = float(t[hit[0]])
    dt = np.diff(t)
    ds = np.diff(s)
    acc = np.full(n, np.nan)
    ok = dt > 0
    acc[1:][ok] = ds[ok] / dt[ok]
    acc[np.abs(acc) > ACCEL_CLIP] = np.nan
    if np.isfinite(acc).any():
        out["accel"] = float(np.nanmax(acc))
        first = acc[(t <= T_FIRST_STEP) & np.isfinite(acc)]
        if first.size:
            out["accel_first"] = float(np.nanmax(first))

    def t_cross_speed(target: float) -> float:
        if not np.isfinite(target):
            return np.nan
        hit = np.where(s >= target)[0]
        if not len(hit):
            return np.nan
        i = int(hit[0])
        if i == 0 or s[i] == s[i - 1]:
            return float(t[i])
        return float(t[i - 1] + (target - s[i - 1]) / (s[i] - s[i - 1]) * (t[i] - t[i - 1]))

    out["t15"] = t_cross_speed(S15)
    out["t18"] = t_cross_speed(S18)

    # Derived 10-yard split, 40-yard dash only (same method as build_dataset.py).
    if g["drill_type"].iloc[0] == "FORTY_YARD_DASH" and n >= 8 and np.isfinite(x).sum() >= 8:
        start_x = float(np.nanmax(x) - 40.0)
        n_fit = min(8, n)

        def t_cross_x(target: float) -> float:
            if x[0] >= target:
                coef = np.polyfit(t[:n_fit], x[:n_fit], 1)
                if abs(coef[0]) < 1e-6:
                    return np.nan
                return float((target - coef[1]) / coef[0])
            hit = np.where(x >= target)[0]
            if not len(hit):
                return np.nan
            i = int(hit[0])
            if i == 0 or x[i] == x[i - 1]:
                return float(t[i])
            return float(t[i - 1] + (target - x[i - 1]) / (x[i] - x[i - 1]) * (t[i] - t[i - 1]))

        t_start = t_cross_x(start_x)
        if np.isfinite(t_start):
            tc = t_cross_x(start_x + 10.0)
            if np.isfinite(tc):
                out["t10"] = float(tc - t_start)
    return out


def build_combine_features(ids: pd.Index) -> pd.DataFrame:
    log("Loading Combine tracking for DL...")
    usecols = ["event_id", "nfl_id", "entity_type", "time", "drill_type", "drill_name", "x", "s"]
    ct = pd.read_csv(DATA / "combine_tracking.csv", usecols=usecols)
    ct = ct[(ct["entity_type"] == "PLAYER") & ct["nfl_id"].isin(ids)]
    ct["drill_name"] = ct["drill_name"].replace({"LINE": "LINE_DRILL"})
    log(f"  {len(ct):,} PLAYER frames, {ct['nfl_id'].nunique()} players, {ct['event_id'].nunique()} attempts")

    rows = []
    grouped = ct.groupby(["event_id", "nfl_id", "drill_type", "drill_name"], sort=False)
    for (event_id, nfl_id, drill_type, drill_name), g in grouped:
        feat = _attempt_burst(g)
        feat.update({
            "event_id": event_id, "nfl_id": nfl_id,
            "drill_type": drill_type, "drill_name": drill_name,
        })
        rows.append(feat)
    att = pd.DataFrame(rows)
    log(f"  {len(att):,} attempt feature rows")
    del ct
    gc.collect()

    f40 = att[att["drill_type"] == "FORTY_YARD_DASH"].copy()
    parts = []
    if len(f40):
        idx = f40.groupby("nfl_id")["max_s"].idxmax()
        best = f40.loc[idx, ["nfl_id", "t10", "t15", "t18", "accel", "accel_first", "t90"]].set_index("nfl_id")
        best = best.rename(columns={
            "t10": "c_t10_derived", "t15": "c_t15", "t18": "c_t18",
            "accel": "c_40_accel", "accel_first": "c_40_accel_first", "t90": "c_t90",
        })
        c40 = f40.groupby("nfl_id").agg(c_top=("max_s", "max"))
        c40["c_top_mph"] = c40["c_top"] * MPH
        parts.append(c40.join(best))

    drills = att[att["drill_type"] == "SKILL_DRILLS_DL"]
    for raw, short in DL_DRILLS.items():
        sub = drills[drills["drill_name"] == raw]
        if sub.empty:
            continue
        agg = sub.groupby("nfl_id").agg(
            max_s=("max_s", "max"),
            accel=("accel", "max"),
            accel_first=("accel_first", "max"),
            n_att=("max_s", "size"),
        )
        agg.columns = [f"dl_{short}_{c}" for c in agg.columns]
        parts.append(agg)

    C = parts[0]
    for p in parts[1:]:
        C = C.join(p, how="outer")
    log(f"  Combine feature table: {len(C)} DL with tracking features")
    return C.reset_index()


def load_pass_rush_plays(ids: pd.Index) -> pd.DataFrame:
    log("Loading pass-rush plays from player_play...")
    usecols = [
        "game_id", "play_id", "nfl_id", "lined_up_position",
        "play_nullified_by_penalty", "pass_result",
        "player_get_off", "sack", "time_to_pressure", "time_to_qb_hurry",
        "quick_pressure", "unblocked_pressure", "blitzing",
    ]
    parts = []
    id_set = set(ids.tolist())
    for ch in pd.read_csv(DATA / "player_play.csv", usecols=usecols, chunksize=100_000):
        parts.append(ch[ch["nfl_id"].isin(id_set)])
    pp = pd.concat(parts, ignore_index=True)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season", "season_type", "week"])
    pp = pp.merge(games, on="game_id", how="left")
    pp["is_reg_clean"] = (pp["season_type"] == "REG") & (pp["play_nullified_by_penalty"] == "N")
    pp["is_pass_rush"] = (
        pp["is_reg_clean"]
        & pp["pass_result"].notna()
        & pp["lined_up_position"].isin(LINED_UP_RUSH)
    )
    rush = pp[pp["is_pass_rush"]].copy()
    log(
        f"  {len(pp):,} DL player-plays; {len(rush):,} REG standing pass-rush snaps "
        f"({rush['nfl_id'].nunique()} players) lined up EDGE/INTERIOR_LINE"
    )
    return rush


def _nearest_at(g: pd.DataFrame, t_target: float, col: str, tol: float = 0.15) -> float:
    if g.empty:
        return np.nan
    i = (g["t"] - t_target).abs().to_numpy().argmin()
    if abs(float(g["t"].iloc[i]) - t_target) > tol:
        return np.nan
    val = g[col].iloc[i]
    return float(val) if np.isfinite(val) else np.nan


def _first_cross(t: np.ndarray, d: np.ndarray, target: float) -> float:
    hit = np.where(d >= target)[0]
    if not len(hit):
        return np.nan
    i = int(hit[0])
    if i == 0:
        return float(t[0]) if d[0] >= target else np.nan
    if d[i] == d[i - 1]:
        return float(t[i])
    return float(t[i - 1] + (target - d[i - 1]) / (d[i] - d[i - 1]) * (t[i] - t[i - 1]))


def _play_getoff(g: pd.DataFrame) -> pd.Series:
    """Get-off features for one rusher on one play, from snap-aligned frames."""
    out = {
        "speed_1s": np.nan, "speed_15s": np.nan,
        "time_to_5yd": np.nan, "time_to_10yd": np.nan,
        "accel_first": np.nan, "dist_1s": np.nan, "has_snap": False,
    }
    snap_rows = g[g["event"].isin(SNAP_EVENTS)]
    if snap_rows.empty:
        return pd.Series(out)
    snap_time = snap_rows["time"].min()
    g = g.copy()
    g["t"] = (g["time"] - snap_time).dt.total_seconds()
    win = g[(g["t"] >= -0.05) & (g["t"] <= 2.05)].sort_values("t")
    if win.empty:
        return pd.Series(out)
    # Position at the snap frame (nearest t>=0, else nearest to 0).
    after = win[win["t"] >= 0]
    origin = after.iloc[0] if len(after) else win.iloc[(win["t"]).abs().argmin()]
    x0, y0 = float(origin["x"]), float(origin["y"])
    win = win[win["t"] >= 0]
    if win.empty:
        return pd.Series(out)
    dist = np.hypot(win["x"].to_numpy() - x0, win["y"].to_numpy() - y0)
    t = win["t"].to_numpy()
    s = win["s"].to_numpy(dtype=float)
    out["has_snap"] = True
    out["speed_1s"] = _nearest_at(win, 1.0, "s")
    out["speed_15s"] = _nearest_at(win, 1.5, "s")
    out["dist_1s"] = _nearest_at(pd.DataFrame({"t": t, "dist": dist}), 1.0, "dist")
    out["time_to_5yd"] = _first_cross(t, dist, 5.0)
    out["time_to_10yd"] = _first_cross(t, dist, 10.0)
    if len(t) >= 2:
        dt = np.diff(t)
        ds = np.diff(s)
        acc = np.full(len(t), np.nan)
        ok = dt > 0
        acc[1:][ok] = ds[ok] / dt[ok]
        acc[np.abs(acc) > ACCEL_CLIP] = np.nan
        first = acc[(t <= T_FIRST_STEP) & np.isfinite(acc)]
        if first.size:
            out["accel_first"] = float(np.nanmax(first))
    return pd.Series(out)


def _nearest_col(win: pd.DataFrame, keys: list[str], t_target: float, col: str, tol: float = 0.15) -> pd.DataFrame:
    tmp = win[["game_id", "play_id", "nfl_id", "t", col]].copy()
    tmp["adiff"] = (tmp["t"] - t_target).abs()
    tmp = tmp[tmp["adiff"] <= tol]
    if tmp.empty:
        return pd.DataFrame(columns=keys + [col])
    idx = tmp.groupby(keys, sort=False)["adiff"].idxmin()
    out = tmp.loc[idx, keys + [col]]
    return out


def _crossing_time(win: pd.DataFrame, keys: list[str], target: float) -> pd.Series:
    w = win[keys + ["t", "dist"]].copy()
    w["prev_t"] = w.groupby(keys, sort=False)["t"].shift(1)
    w["prev_dist"] = w.groupby(keys, sort=False)["dist"].shift(1)
    hit = w[w["dist"] >= target].groupby(keys, sort=False).first()
    if hit.empty:
        return pd.Series(dtype=float, name=f"time_to_{int(target)}yd")
    denom = (hit["dist"] - hit["prev_dist"]).to_numpy()
    t0 = hit["prev_t"].to_numpy()
    t1 = hit["t"].to_numpy()
    d0 = hit["prev_dist"].to_numpy()
    cross = np.where(
        np.isfinite(denom) & (denom != 0) & np.isfinite(t0),
        t0 + (target - d0) / denom * (t1 - t0),
        t1,
    )
    return pd.Series(cross, index=hit.index, name=f"time_to_{int(target)}yd")


def _aggregate_getoff(frames: pd.DataFrame) -> pd.DataFrame:
    """Vectorized play-level get-off from snap-aligned tracking frames."""
    keys = ["game_id", "play_id", "nfl_id"]
    snap = (
        frames.loc[frames["event"].isin(SNAP_EVENTS), keys + ["time"]]
        .groupby(keys, sort=False)["time"].min().rename("snap_time")
    )
    f = frames.merge(snap, on=keys, how="inner")
    f["t"] = (f["time"] - f["snap_time"]).dt.total_seconds()
    win = f[(f["t"] >= -0.05) & (f["t"] <= 2.05)].copy()
    after = win[win["t"] >= 0].sort_values(keys + ["t"])
    origin = after.groupby(keys, sort=False).first()[["x", "y"]].rename(columns={"x": "x0", "y": "y0"})
    win = win.merge(origin, on=keys, how="inner")
    win = win[win["t"] >= 0].sort_values(keys + ["t"])
    win["dist"] = np.hypot(win["x"] - win["x0"], win["y"] - win["y0"])

    s1 = _nearest_col(win, keys, 1.0, "s").rename(columns={"s": "speed_1s"})
    s15 = _nearest_col(win, keys, 1.5, "s").rename(columns={"s": "speed_15s"})
    d1 = _nearest_col(win, keys, 1.0, "dist").rename(columns={"dist": "dist_1s"})
    t5 = _crossing_time(win, keys, 5.0)
    t10 = _crossing_time(win, keys, 10.0)

    win["dt"] = win.groupby(keys, sort=False)["t"].diff()
    win["ds"] = win.groupby(keys, sort=False)["s"].diff()
    acc = np.where(win["dt"] > 0, win["ds"] / win["dt"], np.nan)
    acc = np.where(np.abs(acc) > ACCEL_CLIP, np.nan, acc)
    win["acc"] = acc
    first = (
        win[(win["t"] <= T_FIRST_STEP) & np.isfinite(win["acc"])]
        .groupby(keys, sort=False)["acc"].max().rename("accel_first")
    )

    has_snap = snap.reset_index()[keys].assign(has_snap=True)
    out = has_snap
    for piece in (s1, s15, d1):
        out = out.merge(piece, on=keys, how="left")
    out = out.merge(t5.reset_index(), on=keys, how="left")
    out = out.merge(t10.reset_index(), on=keys, how="left")
    out = out.merge(first.reset_index(), on=keys, how="left")
    out["has_snap"] = out["has_snap"].fillna(False)
    return out


def build_tracking_getoff(rush: pd.DataFrame, rebuild: bool = False) -> pd.DataFrame:
    cache = OUT / "dl_play_getoff.parquet"
    frames_cache = OUT / "dl_rush_frames.parquet"
    if cache.exists() and not rebuild:
        log(f"Loading cached DL get-off plays from {cache}")
        return pd.read_parquet(cache)

    keys = rush[["game_id", "play_id", "nfl_id"]].drop_duplicates()
    if frames_cache.exists() and not rebuild:
        log(f"Loading cached pass-rush frames from {frames_cache}")
        frames = pd.read_parquet(frames_cache)
        t0 = time.time()
    else:
        id_set = set(keys["nfl_id"].tolist())
        log(f"Streaming game tracking for {len(keys):,} pass-rush play-players...")
        t0 = time.time()
        usecols = ["game_id", "play_id", "nfl_id", "time", "x", "y", "s", "event"]
        dtypes = {"game_id": "int64", "play_id": "int64", "nfl_id": "int32", "s": "float32", "x": "float32", "y": "float32"}
        parts: list[pd.DataFrame] = []
        n_chunks = 0
        n_kept = 0
        for year in GAME_YEARS:
            path = DATA / f"game_tracking_{year}.csv"
            log(f"  {path.name}...")
            for chunk in pd.read_csv(path, usecols=usecols, dtype=dtypes, chunksize=CHUNKSIZE):
                n_chunks += 1
                chunk = chunk[chunk["nfl_id"].isin(id_set)]
                if chunk.empty:
                    continue
                chunk = chunk.merge(keys, on=["game_id", "play_id", "nfl_id"], how="inner")
                if chunk.empty:
                    continue
                n_kept += len(chunk)
                parts.append(chunk)
                if n_chunks % 4 == 0:
                    log(f"    chunks={n_chunks}, kept frames={n_kept:,}")
        frames = pd.concat(parts, ignore_index=True)
        del parts
        gc.collect()
        frames.to_parquet(frames_cache, index=False)
        log(f"  cached {len(frames):,} frames to {frames_cache}")

    log(f"  {len(frames):,} frames; parsing times and aggregating plays...")
    frames["time"] = pd.to_datetime(frames["time"])
    frames = frames.sort_values(["game_id", "play_id", "nfl_id", "time"])
    getoff = _aggregate_getoff(frames)
    getoff.to_parquet(cache, index=False)
    log(f"  {len(getoff):,} play rows written to {cache} in {time.time()-t0:.1f}s")
    return getoff


def build_player_table(roster: pd.DataFrame, combine: pd.DataFrame, rush: pd.DataFrame, getoff: pd.DataFrame) -> pd.DataFrame:
    plays = rush.merge(getoff, on=["game_id", "play_id", "nfl_id"], how="left")
    plays["sack_num"] = pd.to_numeric(plays["sack"], errors="coerce").fillna(0.0)
    plays["got_pressure"] = plays["time_to_pressure"].notna().astype(float)
    plays["got_hurry"] = plays["time_to_qb_hurry"].notna().astype(float)
    unblk = coerce_bool(plays["unblocked_pressure"]).fillna(False).astype(bool)
    plays["got_pressure_blocked"] = plays["got_pressure"] * (~unblk).astype(float)

    def agg(g: pd.DataFrame) -> pd.Series:
        n = len(g)
        n_go = int(g["player_get_off"].notna().sum())
        n_s1 = int(g["speed_1s"].notna().sum()) if "speed_1s" in g else 0
        out = {
            "n_rush_plays": n,
            "n_getoff": n_go,
            "n_speed_1s": n_s1,
            "player_get_off": float(g["player_get_off"].median()) if n_go >= MIN_RUSH_PLAYS else np.nan,
            "speed_1s": float(g["speed_1s"].median()) if n_s1 >= MIN_RUSH_PLAYS else np.nan,
            "speed_15s": float(g["speed_15s"].median()) if g["speed_15s"].notna().sum() >= MIN_RUSH_PLAYS else np.nan,
            "time_to_5yd": float(g["time_to_5yd"].median()) if g["time_to_5yd"].notna().sum() >= MIN_RUSH_PLAYS else np.nan,
            "time_to_10yd": float(g["time_to_10yd"].median()) if g["time_to_10yd"].notna().sum() >= MIN_RUSH_PLAYS else np.nan,
            "accel_first": float(g["accel_first"].median()) if g["accel_first"].notna().sum() >= MIN_RUSH_PLAYS else np.nan,
            "dist_1s": float(g["dist_1s"].median()) if g["dist_1s"].notna().sum() >= MIN_RUSH_PLAYS else np.nan,
            "sack_rate": float(g["sack_num"].sum() / n) if n >= MIN_RUSH_PLAYS else np.nan,
            "pressure_rate": float(g["got_pressure"].mean()) if n >= MIN_RUSH_PLAYS else np.nan,
            "hurry_rate": float(g["got_hurry"].mean()) if n >= MIN_RUSH_PLAYS else np.nan,
            "pressure_rate_blocked": float(g["got_pressure_blocked"].mean()) if n >= MIN_RUSH_PLAYS else np.nan,
        }
        return pd.Series(out)

    log("Aggregating player-level get-off and rush outcomes...")
    P = plays.groupby("nfl_id", sort=False).apply(agg, include_groups=False).reset_index()
    P["speed_1s_mph"] = P["speed_1s"] * MPH
    P["speed_15s_mph"] = P["speed_15s"] * MPH
    M = roster.merge(combine, on="nfl_id", how="left").merge(P, on="nfl_id", how="left")
    log(
        f"  players with official get-off median (n≥{MIN_RUSH_PLAYS}): {int(M['player_get_off'].notna().sum())}; "
        f"with speed-at-1s median: {int(M['speed_1s_mph'].notna().sum())}"
    )
    return M


def run_tests(M: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = {
        "All DL": M,
        "Edge": M[M["subtype"] == "Edge"],
        "Interior": M[M["subtype"] == "Interior"],
    }

    log("\n==== Primary family: Combine burst vs speed at 1.0s after snap ====")
    log("Positive ρ below is *not* yet oriented; raw feature vs raw outcome.")
    for gname, g in groups.items():
        for feat, label, _sign in PRIMARY_FEATURES:
            if feat not in g.columns:
                log(f"  SKIP {gname} {label}: column missing")
                continue
            res = spearman_partial(g[feat], g[PRIMARY_OUTCOME], g["draft_year"])
            rows.append({
                "family": "primary", "group": gname, "feature": feat, "feature_label": label,
                "outcome": PRIMARY_OUTCOME, "outcome_label": "Speed at 1.0s after snap (mph)",
                **res,
            })
            log(
                f"  {gname:9s}  {label:32s}  n={res['n']:3d}  ρ={res['rho']:+.2f} (p={fmt_p(res['p'])})  "
                f"partial ρ={res['partial_rho']:+.2f} (p={fmt_p(res['partial_p'])})"
            )

    T = pd.DataFrame(rows)
    fam = T["family"] == "primary"
    pvals = T.loc[fam, "p"].to_numpy(dtype=float)
    finite = np.isfinite(pvals)
    holm_p = np.full(len(pvals), np.nan)
    sig = np.zeros(len(pvals), dtype=bool)
    if finite.sum() >= 1:
        reject, p_adj, _, _ = multipletests(pvals[finite], method="holm")
        holm_p[finite] = p_adj
        sig[finite] = reject
    T.loc[fam, "holm_p"] = holm_p
    T.loc[fam, "sig_holm_05"] = sig
    log("  Holm-adjusted p (primary family, raw Spearman p):")
    for _, r in T.loc[fam].iterrows():
        star = " *" if bool(r["sig_holm_05"]) else ""
        log(f"    {r['group']:9s}  {r['feature_label']:32s}  p={fmt_p(r['p'])} → Holm p={fmt_p(r['holm_p'])}{star}")

    # Secondary: more features and more get-off definitions, including NFL get-off time.
    log("\n==== Secondary get-off definitions and extra Combine features (not Holm-headed) ====")
    extra = []
    feat_list = PRIMARY_FEATURES + [f for f in SECONDARY_FEATURES if f[0] not in {p[0] for p in PRIMARY_FEATURES}]
    for gname, g in groups.items():
        for feat, flabel, _s in feat_list:
            if feat not in g.columns:
                continue
            for out_col, olabel, _os in SECONDARY_OUTCOMES:
                if out_col not in g.columns:
                    continue
                # Skip the exact primary cells so we don't duplicate them.
                if feat in {p[0] for p in PRIMARY_FEATURES} and out_col == PRIMARY_OUTCOME:
                    continue
                res = spearman_partial(g[feat], g[out_col], g["draft_year"])
                extra.append({
                    "family": "secondary", "group": gname, "feature": feat, "feature_label": flabel,
                    "outcome": out_col, "outcome_label": olabel, **res,
                    "holm_p": np.nan, "sig_holm_05": False,
                })
    E = pd.DataFrame(extra)
    # Print a compact view: official 10-yd and pass-rush accel vs official get-off time, plus time-to-5yd.
    highlight = E[
        E["feature"].isin(["official_ten_yd", "c_40_accel", "c_t15", "dl_pass_rush_accel"])
        & E["outcome"].isin(["player_get_off", "time_to_5yd", "accel_first", "speed_15s_mph"])
    ]
    for _, r in highlight.iterrows():
        if r["n"] >= 8:
            log(
                f"  {r['group']:9s}  {r['feature_label']:32s}  vs {r['outcome_label']:40s}  "
                f"n={r['n']:3d}  ρ={r['rho']:+.2f} (p={fmt_p(r['p'])})  partial ρ={r['partial_rho']:+.2f}"
            )

    # Gameplay-success tests: does Sunday get-off relate to pressure and
    # sack rate (primary), not just playing time (now secondary/context)?
    # Official partial residualizes on draft-year dummies (2023 rookies have
    # had more seasons) (the only control; no draft slot). Holm is on the 4 primary All-DL
    # get-off → pressure/sack tests, using the year partial p-value.
    # The Combine-to-outcome family (10-yard split → pressure/sack) is a
    # separate pre-declared family added after this block.
    log("\n==== Get-off → gameplay success (PRIMARY): pressure and sack rate, All DL ====")
    log("Official partial controls for draft year only (no draft slot).")
    career_rows = []
    g = groups["All DL"]
    getoff_measures = [
        ("speed_1s_mph", "Speed at 1.0s after snap (mph)", +1),
        ("player_get_off", "NFL get-off time (sec, lower=faster)", -1),
    ]

    def _career_row(family, gname, gcol, glabel, ccol, clabel, frame):
        res = spearman_controlled(frame[gcol], frame[ccol], frame, "year")
        log(
            f"  {gname:9s}  {glabel:36s} vs {clabel:34s}  n={res['n']:3d}  "
            f"ρ={res['rho']:+.2f} (p={fmt_p(res['p'])})  "
            f"year ρ={res['partial_year_rho']:+.2f} (p={fmt_p(res['partial_year_p'])})"
        )
        return {
            "family": family, "group": gname, "feature": gcol, "feature_label": glabel,
            "outcome": ccol, "outcome_label": clabel, **res,
        }

    for gcol, glabel, _gs in getoff_measures:
        for ccol, clabel in CAREER_PRIMARY:
            career_rows.append(_career_row("getoff_success_primary", "All DL", gcol, glabel, ccol, clabel, g))
    Cprim = pd.DataFrame(career_rows)
    pvals = Cprim["official_partial_p"].to_numpy(dtype=float)
    finite = np.isfinite(pvals)
    holm_p = np.full(len(pvals), np.nan)
    sig = np.zeros(len(pvals), dtype=bool)
    if finite.sum() >= 1:
        reject, p_adj, _, _ = multipletests(pvals[finite], method="holm")
        holm_p[finite] = p_adj
        sig[finite] = reject
    Cprim["holm_p"] = holm_p
    Cprim["sig_holm_05"] = sig
    log("  Holm-adjusted p (4 primary All-DL tests, year partial p):")
    for _, r in Cprim.iterrows():
        star = " *" if bool(r["sig_holm_05"]) else ""
        log(
            f"    {r['feature_label']:36s} vs {r['outcome_label']:34s}  "
            f"p={fmt_p(r['official_partial_p'])} → Holm p={fmt_p(r['holm_p'])}{star}"
        )

    log("\n==== Playing-time family (SECONDARY / context): snaps and start rate ====")
    sec_rows = []
    for gcol, glabel, _gs in getoff_measures:
        for ccol, clabel in PLAYTIME_SECONDARY:
            row = _career_row("playtime_secondary", "All DL", gcol, glabel, ccol, clabel, g)
            row["holm_p"] = np.nan
            row["sig_holm_05"] = False
            sec_rows.append(row)

    log("\n==== Hurry / unblocked-pressure companion (All DL; not in this Holm family) ====")
    for gcol, glabel, _gs in getoff_measures:
        for ccol, clabel in SUCCESS_COMPANION:
            row = _career_row("success_companion", "All DL", gcol, glabel, ccol, clabel, g)
            row["holm_p"] = np.nan
            row["sig_holm_05"] = False
            sec_rows.append(row)

    log("\n==== Get-off → success, subtypes (not in this Holm family) ====")
    sub_rows = []
    for gname in ("Edge", "Interior"):
        frame = groups[gname]
        for gcol, glabel, _gs in getoff_measures:
            for ccol, clabel in SUCCESS_PRIMARY + SUCCESS_COMPANION + PLAYTIME_SECONDARY:
                row = _career_row("career_subtype", gname, gcol, glabel, ccol, clabel, frame)
                row["holm_p"] = np.nan
                row["sig_holm_05"] = False
                sub_rows.append(row)
    C = pd.concat([Cprim, pd.DataFrame(sec_rows), pd.DataFrame(sub_rows)], ignore_index=True, sort=False)

    G = run_combine_to_outcome_tests(M, groups)
    out = pd.concat([T, E, C, G], ignore_index=True, sort=False)
    # Headline is All DL; Edge and Interior are pre-declared breakouts on every row.
    out["subgroup"] = out["group"]
    return out



def run_combine_to_outcome_tests(M: pd.DataFrame, groups: dict) -> pd.DataFrame:
    """Pre-declared Combine → gameplay success family, plus mediation.

    Official family (6 tests, Holm on year partial p): official 10-yard
    split vs pressure rate and sack rate, in All DL / Edge / Interior.
    This is the competition-required Combine-to-NFL-performance link.
    Bootstrap 95% CIs are player-level, 2,000 resamples.
    """
    rows: list[dict] = []

    def _row(family: str, gname: str, frame: pd.DataFrame, feat: str, flabel: str,
             out_col: str, olabel: str, extra: pd.DataFrame | None = None) -> dict:
        res = spearman_controlled(frame[feat], frame[out_col], frame, "year")
        lo, hi, n_boot = bootstrap_partial_ci(frame[feat], frame[out_col], frame, extra=None)
        # If extra controls are requested (mediation), overwrite official partial.
        if extra is not None:
            d = pd.DataFrame({
                "x": frame[feat], "y": frame[out_col],
                "draft_year": frame["draft_year"],
            }).join(extra)
            d = d.dropna()
            controls = _year_controls(d, extra.loc[d.index] if len(d) else extra)
            med = spearman_residualized(d["x"], d["y"], controls) if len(d) else {"n": 0, "rho": np.nan, "p": np.nan}
            res["official_partial_rho"] = med["rho"]
            res["official_partial_p"] = med["p"]
            res["n"] = med["n"]
            lo, hi, n_boot = bootstrap_partial_ci(frame[feat], frame[out_col], frame, extra=extra)
            res["mediation"] = True
        else:
            res["mediation"] = False
        res["partial_ci_low"] = lo
        res["partial_ci_high"] = hi
        res["n_boot"] = n_boot
        log(
            f"  {gname:9s}  {flabel:36s} vs {olabel:42s}  n={res['n']:3d}  "
            f"ρ={res['rho']:+.2f} (p={fmt_p(res['p'])})  "
            f"year ρ={res['official_partial_rho']:+.2f} "
            f"(p={fmt_p(res['official_partial_p'])}, 95% CI "
            f"{lo:+.2f}–{hi:+.2f})"
        )
        return {
            "family": family, "group": gname, "feature": feat, "feature_label": flabel,
            "outcome": out_col, "outcome_label": olabel, **res,
        }

    # ---- Official family: 10-yard split → pressure / sack ----
    log("\n==== Combine → gameplay (PRIMARY family): official 10-yard split vs pressure / sack ====")
    log("Holm is on the 6 year partial p-values. CI is a 2,000-player bootstrap.")
    fam_rows = []
    for gname in ("All DL", "Edge", "Interior"):
        frame = groups[gname]
        for out_col, olabel in SUCCESS_PRIMARY:
            fam_rows.append(_row(
                "combine_success_primary", gname, frame,
                "official_ten_yd", "Official 10-yard split",
                out_col, olabel,
            ))
    F = pd.DataFrame(fam_rows)
    pvals = F["official_partial_p"].to_numpy(dtype=float)
    finite = np.isfinite(pvals)
    holm_p = np.full(len(pvals), np.nan)
    sig = np.zeros(len(pvals), dtype=bool)
    if finite.sum() >= 1:
        reject, p_adj, _, _ = multipletests(pvals[finite], method="holm")
        holm_p[finite] = p_adj
        sig[finite] = reject
    F["holm_p"] = holm_p
    F["sig_holm_05"] = sig
    log("  Holm-adjusted p (6-test family, year partial p):")
    for _, r in F.iterrows():
        star = " *" if bool(r["sig_holm_05"]) else ""
        log(
            f"    {r['group']:9s}  {r['outcome_label']:42s}  "
            f"year ρ={r['official_partial_rho']:+.2f}  "
            f"p={fmt_p(r['official_partial_p'])} → Holm p={fmt_p(r['holm_p'])}{star}"
        )
    rows.append(F)

    # ---- Companion: 10-yard split → hurry / blocked-pressure; other burst features ----
    log("\n==== Combine → gameplay companions (not in the 6-test Holm family) ====")
    extra_rows = []
    for gname in ("All DL", "Edge", "Interior"):
        frame = groups[gname]
        for out_col, olabel in SUCCESS_COMPANION:
            row = _row(
                "combine_success_companion", gname, frame,
                "official_ten_yd", "Official 10-yard split",
                out_col, olabel,
            )
            row["holm_p"] = np.nan
            row["sig_holm_05"] = False
            extra_rows.append(row)
        # Other primary burst features vs pressure rate only, All-DL reported in subtypes too.
        if gname == "All DL":
            for feat, flabel, _s in PRIMARY_FEATURES:
                if feat == "official_ten_yd":
                    continue
                if feat not in frame.columns:
                    continue
                row = _row(
                    "combine_success_companion", gname, frame,
                    feat, flabel, "pressure_rate", "Pressure rate on pass-rush plays",
                )
                row["holm_p"] = np.nan
                row["sig_holm_05"] = False
                extra_rows.append(row)
    rows.append(pd.DataFrame(extra_rows))

    # ---- Mediation: 10-yard split → pressure/sack after get-off ----
    log("\n==== Mediation: does game get-off carry the 10-yard split → pressure link? ====")
    log("Partial residualizes on draft year AND speed at 1.0s after the snap.")
    log("Caveat: no blocker or QB tracks, so this is association, not a causal claim.")
    med_rows = []
    for gname in ("All DL", "Edge", "Interior"):
        frame = groups[gname]
        extra = frame[["speed_1s_mph"]].rename(columns={"speed_1s_mph": "speed_1s_mph"})
        for out_col, olabel in SUCCESS_PRIMARY:
            row = _row(
                "combine_success_mediation", gname, frame,
                "official_ten_yd", "Official 10-yard split",
                out_col, olabel + " | get-off (speed at 1.0s)",
                extra=extra,
            )
            row["holm_p"] = np.nan
            row["sig_holm_05"] = False
            med_rows.append(row)
    rows.append(pd.DataFrame(med_rows))

    # Also attach bootstrap CIs onto the get-off → pressure All-DL primary cells
    # (already computed in run_tests without CIs). We recompute here for the log
    # and a clean CI column on a dedicated family copy.
    log("\n==== Get-off → pressure / sack bootstrap CIs (All DL, year) ====")
    go_rows = []
    frame = groups["All DL"]
    for gcol, glabel, _gs in (
        ("speed_1s_mph", "Speed at 1.0s after snap (mph)", +1),
        ("player_get_off", "NFL get-off time (sec, lower=faster)", -1),
    ):
        for out_col, olabel in SUCCESS_PRIMARY:
            row = _row(
                "getoff_success_ci", "All DL", frame,
                gcol, glabel, out_col, olabel,
            )
            row["holm_p"] = np.nan
            row["sig_holm_05"] = False
            go_rows.append(row)
    rows.append(pd.DataFrame(go_rows))

    T = pd.concat(rows, ignore_index=True, sort=False)
    # Headline is All DL; Edge and Interior are pre-declared breakouts.
    # Keep `group` for compatibility and add an explicit `subgroup` column.
    T["subgroup"] = T["group"]
    return T



def sample_funnel(M: pd.DataFrame) -> dict:
    """Roster funnel for the official 10-yard / pressure sample."""
    total = len(M)
    n_edge = int((M["subtype"] == "Edge").sum())
    n_int = int((M["subtype"] == "Interior").sum())
    no_split = M["official_ten_yd"].isna()
    n_no_split = int(no_split.sum())
    has_split = M["official_ten_yd"].notna()
    thin = has_split & (M["n_rush_plays"].fillna(0) < MIN_RUSH_PLAYS)
    n_thin = int(thin.sum())
    final = has_split & (M["n_rush_plays"].fillna(0) >= MIN_RUSH_PLAYS)
    F = M[final]
    by_year = {int(y): int(n) for y, n in F["draft_year"].value_counts().sort_index().items()}
    return {
        "n_total": total,
        "n_edge": n_edge,
        "n_interior": n_int,
        "n_no_split": n_no_split,
        "n_thin": n_thin,
        "n_final": int(final.sum()),
        "n_final_edge": int((F["subtype"] == "Edge").sum()),
        "n_final_interior": int((F["subtype"] == "Interior").sum()),
        "by_year": by_year,
    }


def log_funnel(funnel: dict) -> None:
    y = funnel["by_year"]
    year_s = "/".join(str(y.get(yr, 0)) for yr in (2023, 2024, 2025))
    log(
        "Sample funnel (headline = official 10-yard split and ≥"
        f"{MIN_RUSH_PLAYS} pass-rush snaps): "
        f"{funnel['n_total']} DL total "
        f"({funnel['n_edge']} Edge / {funnel['n_interior']} Interior); "
        f"{funnel['n_no_split']} no official split "
        "(skipped the Combine 40; this file has no pro-day times and we "
        "do not invent a tracking-derived split for players who never ran "
        f"the 40); {funnel['n_thin']} with a split but fewer than "
        f"{MIN_RUSH_PLAYS} pass-rush snaps; "
        f"{funnel['n_final']} final "
        f"({funnel['n_final_edge']} Edge / {funnel['n_final_interior']} Interior; "
        f"{year_s} by 2023/24/25)."
    )


def write_named_players(M: pd.DataFrame) -> Path:
    """Every official-sample rusher, sorted by 10-yard split (faster first)."""
    d = M[
        M["official_ten_yd"].notna()
        & (M["n_rush_plays"].fillna(0) >= MIN_RUSH_PLAYS)
    ].copy()
    d = d.sort_values(["official_ten_yd", "display_name"], kind="mergesort")
    out = pd.DataFrame({
        "player": d["display_name"],
        "subtype": d["subtype"],
        "draft_year": d["draft_year"].astype(int),
        "official_ten_yd": d["official_ten_yd"],
        "speed_1s_mph": d["speed_1s_mph"],
        "pressure_rate": d["pressure_rate"],
        "sack_rate": d["sack_rate"],
        "pass_rush_snaps": d["n_rush_plays"].astype(int),
        "college_name": d["college_name"] if "college_name" in d.columns else "",
        "nfl_id": d["nfl_id"],
        "nfl_position": d["nfl_position"],
    })
    path = OUT / "dl_players_named.csv"
    out.to_csv(path, index=False)
    log(f"  wrote {path} ({len(out)} rows, sorted by official 10-yard split)")
    return path


def write_dl_players_md(M: pd.DataFrame, funnel: dict) -> Path:
    d = pd.read_csv(OUT / "dl_players_named.csv")
    y = funnel["by_year"]
    year_s = "/".join(str(y.get(yr, 0)) for yr in (2023, 2024, 2025))

    def row_md(r):
        return (
            f"| {r['player']} | {r['subtype']} | {int(r['draft_year'])} | "
            f"{r['official_ten_yd']:.2f} | {r['speed_1s_mph']:.2f} | "
            f"{100 * r['pressure_rate']:.1f}% | {100 * r['sack_rate']:.1f}% | "
            f"{int(r['pass_rush_snaps'])} |"
        )

    header = (
        "| Player | Subtype | Year | 10-yd | Speed 1.0s (mph) | "
        "Pressure | Sack | Pass-rush snaps |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"
    )
    top = "\n".join(row_md(r) for _, r in d.head(10).iterrows())
    bot = "\n".join(row_md(r) for _, r in d.tail(10).iterrows())
    lines = [
        "# Named defensive linemen — official 10-yard sample",
        "",
        "The headline DL analysis uses **one combined group**: every defensive lineman in the 2023–2025 rookie classes with an official Combine 10-yard split and at least 20 regular-season pass-rush snaps that stood. Edge vs Interior is a breakout in every table and chart, not a second headline sample.",
        "",
        "## Sample funnel",
        "",
        f"- **{funnel['n_total']} DL** in the roster ({funnel['n_edge']} Edge = DE + OLB who tested in the DL Combine group; {funnel['n_interior']} Interior = DT + NT).",
        f"- **{funnel['n_no_split']}** have no official 10-yard split. They skipped the Combine 40. This file has no pro-day times, and we do not invent a tracking-derived split for players who never ran the 40 (they still have other DL drills).",
        f"- **{funnel['n_thin']}** have a split but fewer than 20 pass-rush snaps, so they do not get a pressure or sack rate.",
        f"- **{funnel['n_final']} final** ({funnel['n_final_edge']} Edge / {funnel['n_final_interior']} Interior; {year_s} by the 2023 / 2024 / 2025 classes).",
        "",
        "The official named table is `out/dl_players_named.csv` (all "
        f"{funnel['n_final']} players, sorted by official 10-yard split, faster first).",
        "",
        "## How to read the all-DL result",
        "",
        "Edges as a group run faster 10-yard splits and post higher pressure rates than interior players, because they rush in more space. That composition is part of the pooled all-DL 10-yard-to-pressure link. **Within Edge alone, or Interior alone, the same link is weaker and does not survive Holm correction.** Trust the all-DL number as a pooled scouting fact; do not treat it as a within-position rule until a larger sample says so. We still have no blocker or QB tracks.",
        "",
        "## Fastest official 10-yard splits (top 10 of the 72)",
        "",
        header,
        top,
        "",
        "## Slowest official 10-yard splits (bottom 10 of the 72)",
        "",
        header,
        bot,
        "",
        "Times are official Combine 10-yard splits in seconds (faster is smaller). Speed at 1.0s is the tracking get-off process metric, in mph. Pressure and sack rates are on regular-season pass-rush snaps that stood.",
        "",
    ]
    path = ROOT / "DL_PLAYERS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log(f"  wrote {path}")
    return path


def _rho_cell(tests: pd.DataFrame, family: str, group: str, feature: str, outcome: str):
    sub = tests[
        (tests["family"] == family)
        & (tests["group"] == group)
        & (tests["feature"] == feature)
        & (tests["outcome"] == outcome)
    ]
    return sub.iloc[0] if len(sub) else None


def make_figure(M: pd.DataFrame, tests: pd.DataFrame) -> Path:
    """Headline view: all DL, 10-yard split vs get-off, colored by Edge / Interior."""
    _style()
    feat_sign = {f: s for f, _l, s in PRIMARY_FEATURES}
    prim = tests[(tests["family"] == "primary")].copy()
    prim["rho_oriented"] = prim.apply(
        lambda r: r["rho"] * feat_sign.get(r["feature"], 1),
        axis=1,
    )

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.6), gridspec_kw={"width_ratios": [1.15, 1.0]})
    ax0, ax1 = axes

    d = M.dropna(subset=["official_ten_yd", "speed_1s_mph", "subtype"]).copy()
    d = d[d["n_rush_plays"].fillna(0) >= MIN_RUSH_PLAYS]
    for grp, color, marker in (
        ("Edge", SUBTYPE_COLOR["Edge"], "o"),
        ("Interior", SUBTYPE_COLOR["Interior"], "s"),
    ):
        sub = d[d["subtype"] == grp]
        ax0.scatter(
            sub["official_ten_yd"], sub["speed_1s_mph"],
            color=color, marker=marker, s=42, alpha=0.88, zorder=3,
            label=f"{grp} (n={len(sub)})",
            edgecolor="white", linewidth=0.4,
        )
        if len(sub) >= 8:
            x = sub["official_ten_yd"].to_numpy()
            y = sub["speed_1s_mph"].to_numpy()
            xs = np.linspace(x.min(), x.max(), 50)
            ax0.plot(xs, np.poly1d(np.polyfit(x, y, 1))(xs), color=color, lw=1.2, ls="--", zorder=2)
    if len(d) >= 8:
        x = d["official_ten_yd"].to_numpy()
        y = d["speed_1s_mph"].to_numpy()
        xs = np.linspace(x.min(), x.max(), 50)
        ax0.plot(xs, np.poly1d(np.polyfit(x, y, 1))(xs), color="#222222", lw=2.1, zorder=2, label=f"All DL (n={len(d)})")

    # Legend annotations: year-partial / raw ρ for 10-yard vs speed_1s
    bits = []
    for gname in ("All DL", "Edge", "Interior"):
        r = _rho_cell(tests, "primary", gname, "official_ten_yd", "speed_1s_mph")
        if r is None:
            continue
        # orient: faster split, faster get-off => flip raw rho
        rho = -float(r["partial_rho"]) if np.isfinite(r.get("partial_rho", np.nan)) else -float(r["rho"])
        star = " ★" if bool(r.get("sig_holm_05", False)) else ""
        bits.append(f"{gname} ρ={rho:+.2f}{star}")
    ax0.legend(frameon=False, loc="upper right", fontsize=8.5)
    ax0.set_xlabel("Official Combine 10-yard split (seconds, faster is left)")
    ax0.set_ylabel("Get-off: speed 1.0s after the snap (mph)")
    ax0.set_title("All DL: 10-yard split vs get-off", loc="left", fontweight="bold")
    if bits:
        ax0.text(
            0.02, 0.02, "  ·  ".join(bits),
            transform=ax0.transAxes, fontsize=7.5, color="#333333", va="bottom",
        )

    # Right: 4 Combine features, grouped bars All DL / Edge / Interior
    pretty = {
        "official_ten_yd": "Faster\n10-yard split",
        "c_40_accel": "Higher 40-yard\npeak accel",
        "c_t15": "Faster 40\ntime to 15 mph",
        "dl_pass_rush_accel": "Higher pass-rush\ndrill accel",
    }
    labels_order = [f for f, _l, _s in PRIMARY_FEATURES]
    groups_order = ["All DL", "Edge", "Interior"]
    bar_colors = [SUBTYPE_COLOR[g] for g in groups_order]
    width = 0.26
    x = np.arange(len(labels_order))
    for i, gname in enumerate(groups_order):
        sub = prim[prim["group"] == gname].copy()
        sub["_ord"] = sub["feature"].map({f: j for j, f in enumerate(labels_order)})
        sub = sub.dropna(subset=["_ord"]).sort_values("_ord")
        # align to labels_order
        vals = []
        ns = []
        sigs = []
        for feat in labels_order:
            row = sub[sub["feature"] == feat]
            if len(row):
                vals.append(float(row["rho_oriented"].iloc[0]))
                ns.append(int(row["n"].iloc[0]))
                sigs.append(bool(row["sig_holm_05"].fillna(False).iloc[0]))
            else:
                vals.append(0.0)
                ns.append(0)
                sigs.append(False)
        offset = (i - 1) * width
        # All DL slightly taller / more opaque
        alpha = 0.95 if gname == "All DL" else 0.72
        ax1.bar(
            x + offset, vals, width=width, color=bar_colors[i],
            edgecolor="white", zorder=3, alpha=alpha, label=gname,
        )
        for xi, val, sig in zip(x + offset, vals, sigs):
            if not np.isfinite(val):
                continue
            mark = "★" if sig else ""
            ax1.text(
                xi, val + (0.03 if val >= 0 else -0.03),
                f"{val:+.2f}{mark}",
                ha="center", va="bottom" if val >= 0 else "top", fontsize=6.5,
                fontweight="bold" if gname == "All DL" else "normal",
            )
    ax1.axhline(0, color="#888888", lw=0.8)
    ax1.set_xticks(x, [pretty[f] for f in labels_order], fontsize=8)
    ax1.set_ylabel("Correlation with get-off\n(right = expected football direction)")
    ax1.set_ylim(-0.55, 1.05)
    ax1.set_title("Burst features vs get-off, by group", loc="left", fontweight="bold")
    ax1.legend(frameon=False, loc="upper right", fontsize=8)

    fig.suptitle(
        "The official 10-yard split shows up as get-off — headline is all DL",
        x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.02,
    )
    fig.text(
        0.01, -0.08,
        "Left: every rusher with an official 10-yard split and ≥20 pass-rush snaps (n=72). Solid line is the all-DL fit; dashed lines are Edge and Interior. "
        "ρ values are year-controlled Spearman, oriented so faster split / faster get-off is positive. "
        "Right: the four pre-declared Combine burst features vs speed 1.0s after the snap. All-DL bars are the headline; Edge and Interior are breakouts. "
        "★ survives Holm across the 12 get-off tests (4 features × All DL / Edge / Interior). "
        "Times are flipped so 'faster' points right. Game tracking covers only the 510 rookies; there are no blocker or QB tracks. "
        "The 10-yard-to-get-off link also survives Holm inside Edge and inside Interior. The 10-yard-to-pressure link does not — that caveat lives in Figure 6.",
        fontsize=7.6, color="#555555", ha="left",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    path = FIGS / "fig5_dl_burst.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def make_figure6(M: pd.DataFrame, tests: pd.DataFrame) -> Path:
    """Coach-readable chain: 10-yard split → get-off → pressure, plus the direct link."""
    _style()
    fam = tests[tests["family"] == "combine_success_primary"].copy()
    go = tests[tests["family"] == "getoff_success_ci"].copy()
    # Prefer year partials for the annotation numbers.
    def _cell(frame, group, feature, outcome):
        sub = frame[(frame["group"] == group) & (frame["feature"] == feature) & (frame["outcome"] == outcome)]
        return sub.iloc[0] if len(sub) else None

    all_p = _cell(fam, "All DL", "official_ten_yd", "pressure_rate")
    all_s = _cell(fam, "All DL", "official_ten_yd", "sack_rate")
    go_p = _cell(go, "All DL", "speed_1s_mph", "pressure_rate")

    # Title follows the All-DL 10-yard → pressure result after year and Holm.
    if all_p is not None and bool(all_p.get("sig_holm_05", False)):
        title = "A faster Combine 10-yard split shows up as more pressure on Sunday"
    elif all_p is not None and np.isfinite(all_p.get("official_partial_rho", np.nan)) and all_p["official_partial_rho"] < -0.2:
        title = "A faster 10-yard split leans toward more pressure — check the fine print"
    else:
        title = "The 10-yard split is real get-off information; the pressure link is the one to judge carefully"

    fig = plt.figure(figsize=(12.6, 6.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.15], wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])

    # Left: chain of three All-DL links, oriented so "better 10-yard / faster get-off / more pressure" is to the right.
    # 10-yd is a time (lower=better) so flip sign; speed_1s is already higher=better.
    chain = []
    ten_go = tests[
        (tests["family"] == "primary")
        & (tests["group"] == "All DL")
        & (tests["feature"] == "official_ten_yd")
        & (tests["outcome"] == "speed_1s_mph")
    ]
    if len(ten_go):
        r = ten_go.iloc[0]
        chain.append({
            "label": "Faster 10-yard split\n→ faster get-off",
            "rho": -float(r["partial_rho"]) if np.isfinite(r.get("partial_rho", np.nan)) else -float(r["rho"]),
            "n": int(r["n"]),
            "sig": bool(r.get("sig_holm_05", False)),
        })
    if go_p is not None:
        chain.append({
            "label": "Faster get-off\n→ higher pressure rate",
            "rho": float(go_p["official_partial_rho"]),
            "n": int(go_p["n"]),
            "lo": go_p.get("partial_ci_low", np.nan),
            "hi": go_p.get("partial_ci_high", np.nan),
            "sig": np.isfinite(go_p.get("official_partial_p", np.nan)) and go_p["official_partial_p"] < 0.05,
        })
    if all_p is not None:
        # 10-yd time: flip so "faster split, more pressure" is positive.
        chain.append({
            "label": "Faster 10-yard split\n→ higher pressure rate",
            "rho": -float(all_p["official_partial_rho"]) if np.isfinite(all_p["official_partial_rho"]) else np.nan,
            "n": int(all_p["n"]),
            "lo": -float(all_p["partial_ci_high"]) if np.isfinite(all_p.get("partial_ci_high", np.nan)) else np.nan,
            "hi": -float(all_p["partial_ci_low"]) if np.isfinite(all_p.get("partial_ci_low", np.nan)) else np.nan,
            "sig": bool(all_p.get("sig_holm_05", False)),
        })

    ys = np.arange(len(chain))[::-1]
    colors = ["#0072B2" if c["sig"] else "#7A7A7A" for c in chain]
    rhos = [c["rho"] if np.isfinite(c["rho"]) else 0.0 for c in chain]
    ax0.barh(ys, rhos, color=colors, height=0.62, zorder=3, edgecolor="white")
    ax0.axvline(0, color="#888888", lw=0.8)
    for y, c in zip(ys, chain):
        x = c["rho"] if np.isfinite(c["rho"]) else 0.0
        star = " ★" if c["sig"] else ""
        ci = ""
        if np.isfinite(c.get("lo", np.nan)) and np.isfinite(c.get("hi", np.nan)):
            ci = f"\nCI {c['lo']:+.2f}–{c['hi']:+.2f}"
        ax0.text(
            x + (0.03 if x >= 0 else -0.03), y,
            f"{x:+.2f}{star}\nn={c['n']}{ci}",
            ha="left" if x >= 0 else "right", va="center", fontsize=8,
        )
    ax0.set_yticks(ys, [c["label"] for c in chain], fontsize=9)
    ax0.set_xlabel("Correlation after draft year\n(right = the expected football direction)")
    ax0.set_xlim(-0.2, 1.05)
    ax0.set_title("The chain, in numbers", loc="left", fontweight="bold")

    # Right: scatter, 10-yard split vs pressure rate. Headline is all DL;
    # points and dashed fits are Edge vs Interior breakouts.
    d = M.dropna(subset=["official_ten_yd", "pressure_rate", "subtype"]).copy()
    d = d[d["n_rush_plays"] >= MIN_RUSH_PLAYS]

    def _leg(group, n):
        r = _cell(fam, group, "official_ten_yd", "pressure_rate")
        if r is None or not np.isfinite(r.get("official_partial_rho", np.nan)):
            return f"{group} (n={n})"
        star = " ★" if bool(r.get("sig_holm_05", False)) else ""
        return f"{group} (n={n}, ρ={r['official_partial_rho']:+.2f}{star})"

    if len(d) >= 8:
        x = d["official_ten_yd"].to_numpy()
        y = 100 * d["pressure_rate"].to_numpy()
        xs = np.linspace(x.min(), x.max(), 50)
        ax1.plot(
            xs, np.poly1d(np.polyfit(x, y, 1))(xs),
            color="#222222", lw=2.2, zorder=2, label=_leg("All DL", len(d)),
        )
    for grp, color, marker in (
        ("Edge", SUBTYPE_COLOR["Edge"], "o"),
        ("Interior", SUBTYPE_COLOR["Interior"], "s"),
    ):
        sub = d[d["subtype"] == grp]
        ax1.scatter(
            sub["official_ten_yd"], 100 * sub["pressure_rate"],
            color=color, marker=marker, s=38, alpha=0.85, zorder=3,
            label=_leg(grp, len(sub)),
            edgecolor="white", linewidth=0.4,
        )
        if len(sub) >= 8:
            x = sub["official_ten_yd"].to_numpy()
            y = 100 * sub["pressure_rate"].to_numpy()
            xs = np.linspace(x.min(), x.max(), 50)
            ax1.plot(xs, np.poly1d(np.polyfit(x, y, 1))(xs), color=color, lw=1.3, ls="--", zorder=2)
    ax1.set_xlabel("Official Combine 10-yard split (seconds, faster is left)")
    ax1.set_ylabel("Pressure rate on pass-rush snaps (%)")
    ax1.legend(frameon=False, loc="upper right", fontsize=8)
    ax1.set_title("Each rusher, 10-yard split vs pressure rate", loc="left", fontweight="bold")
    # Invert x so faster (lower time) is to the left — coaches already read a 10-yard
    # split that way. (Do not invert: standard split axis already has faster on the left
    # if we leave it as elapsed time increasing to the right... wait, increasing to the
    # right means slower on the right, faster on the left. That is what we want. No invert.)

    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.04)
    caption_bits = []
    if all_p is not None:
        star = " (survives Holm)" if bool(all_p.get("sig_holm_05", False)) else " (does not survive Holm)"
        caption_bits.append(
            f"All-DL 10-yard split vs pressure rate: year ρ={all_p['official_partial_rho']:+.2f}, "
            f"n={int(all_p['n'])}, Holm p={all_p['holm_p']:.3f}{star}."
        )
    if all_s is not None:
        star = " *" if bool(all_s.get("sig_holm_05", False)) else ""
        caption_bits.append(
            f"Same split vs sack rate: year ρ={all_s['official_partial_rho']:+.2f}, "
            f"Holm p={all_s['holm_p']:.3f}{star}."
        )
    caption_bits.append(
        "Pressure rate is the share of regular-season pass-rush snaps (EDGE or interior, plays that stood, ≥20 snaps) "
        "where time_to_pressure is recorded. Sack rate credits shared sacks as 0.5. "
        "★ / colored bars mark results that clear their own pre-declared bar (get-off family or the 6-test Combine-to-success family). "
        "We do not have blocker or QB tracking, so a rusher who is already free can also look 'faster' at 1.0s — association, not proof. "
        "Headline is the all-DL sample (n=72, 2023–2025 pooled). The all-DL 10-yard-to-pressure link survives Holm; the same test inside Edge and inside Interior does not. Part of the pooled effect comes from edges being both faster and better rushers. "
        "Playing time (snaps, start rate) is a secondary context metric, not the success definition."
    )
    import textwrap
    caption = textwrap.fill("  ".join(caption_bits), width=165)
    fig.suptitle(title, x=0.02, ha="left", fontweight="bold", fontsize=13, y=0.98)
    fig.text(0.02, 0.01, caption, fontsize=7.5, color="#555555", ha="left", va="bottom")
    fig.subplots_adjust(left=0.20, right=0.98, top=0.82, bottom=0.26, wspace=0.32)
    path = FIGS / "fig6_combine_to_pressure.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Rebuild cached play-level get-off from game tracking.")
    args = parser.parse_args()
    FIGS.mkdir(parents=True, exist_ok=True)

    roster = load_roster()
    combine = build_combine_features(roster["nfl_id"])
    rush = load_pass_rush_plays(roster["nfl_id"])
    getoff = build_tracking_getoff(rush, rebuild=args.rebuild)
    M = build_player_table(roster, combine, rush, getoff)

    # Keep a coach-readable player csv (no parquet in git).
    keep = [
        "nfl_id", "display_name", "nfl_position", "subtype", "college_name",
        "draft_year",
        "official_ten_yd", "official_forty", "c_top_mph", "c_t15", "c_t18",
        "c_t90", "c_t10_derived", "c_40_accel", "c_40_accel_first",
        "dl_pass_rush_accel", "dl_pass_rush_accel_first", "dl_pass_rush_max_s",
        "n_rush_plays", "n_getoff", "n_speed_1s",
        "player_get_off", "speed_1s_mph", "speed_15s_mph", "time_to_5yd",
        "time_to_10yd", "accel_first", "dist_1s",
        "sack_rate", "pressure_rate", "hurry_rate", "pressure_rate_blocked",
        "start_rate", "snaps_per_game",
        "career_defensive_snaps", "career_games_active", "career_games_started",
    ]
    keep = [c for c in keep if c in M.columns]
    players_csv = OUT / "dl_burst_players.csv"
    M[keep].to_csv(players_csv, index=False)
    log(f"  wrote {players_csv} ({len(M)} rows)")

    funnel = sample_funnel(M)
    log_funnel(funnel)
    write_named_players(M)
    write_dl_players_md(M, funnel)

    tests = run_tests(M)
    tests_csv = OUT / "dl_burst_tests.csv"
    tests.to_csv(tests_csv, index=False)
    log(f"  wrote {tests_csv}")
    make_figure(M, tests)
    make_figure6(M, tests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
