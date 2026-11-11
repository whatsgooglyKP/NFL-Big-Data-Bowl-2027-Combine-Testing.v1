#!/usr/bin/env python3
"""DL burst vs. Sunday get-off — a quick, honest check for BDB 2027.

Question: does Combine burst (10-yard split, early acceleration from the
tracked 40, and DL skill-drill explosiveness) show up as get-off on
pass-rush snaps? Split by Edge (DE + OLB who tested in the DL Combine
group) vs Interior (DT + NT). Offensive linemen are out of scope.

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
UDFA_PICK = 260
ACCEL_CLIP = 12.0
GAME_YEARS = (2023, 2024, 2025)
CHUNKSIZE = 2_000_000
MIN_RUSH_PLAYS = 20
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

# Primary career outcomes: opportunity, not just starts.
# career_defensive_snaps is cumulative, so 2023 rookies have a head start
# (three seasons vs one for 2025). snaps_per_game already adjusts for
# career length; we still control both for draft year and draft slot.
CAREER_PRIMARY = [
    ("career_defensive_snaps", "Career defensive snaps"),
    ("snaps_per_game", "Defensive snaps per game active"),
]
CAREER_SECONDARY = [
    ("start_rate", "Start rate (starts / games active)"),
    ("sack_rate", "Sack rate on pass-rush plays"),
    ("pressure_rate", "Pressure rate on pass-rush plays"),
]

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


def spearman_partial(x: pd.Series, y: pd.Series, pick: pd.Series) -> dict:
    d = pd.DataFrame({"x": x, "y": y, "pick": pick}).dropna()
    out = {"n": int(len(d)), "rho": np.nan, "p": np.nan, "partial_rho": np.nan, "partial_p": np.nan}
    if len(d) < 8:
        return out
    if d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    lp = np.log(d["pick"].astype(float))
    if lp.nunique() >= 2:
        rx = d["x"] - np.poly1d(np.polyfit(lp, d["x"], 1))(lp)
        ry = d["y"] - np.poly1d(np.polyfit(lp, d["y"], 1))(lp)
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


def spearman_controlled(x: pd.Series, y: pd.Series, df: pd.DataFrame, control_kind: str) -> dict:
    """Spearman ρ after residualizing both sides on the requested controls.

    control_kind:
      'pick'      — log draft pick (UDFA = 260)
      'year'      — draft-year dummies (2023 rookies have had more seasons)
      'year+pick' — both; this is the official control for DL career tests
    """
    d = pd.DataFrame({"x": x, "y": y, "pick": df["pick"], "draft_year": df["draft_year"]}).dropna()
    out = {
        "n": int(len(d)), "rho": np.nan, "p": np.nan,
        "partial_rho": np.nan, "partial_p": np.nan,
        "partial_year_rho": np.nan, "partial_year_p": np.nan,
        "partial_year_pick_rho": np.nan, "partial_year_pick_p": np.nan,
        "control": control_kind,
    }
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)

    def _partial(cols: pd.DataFrame) -> tuple[float, float]:
        X = cols.to_numpy(dtype=float)
        if np.unique(X, axis=0).shape[0] < 2:
            return np.nan, np.nan
        rx = _residualize(d["x"].to_numpy(dtype=float), X)
        ry = _residualize(d["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size < 2 or np.unique(ry).size < 2:
            return np.nan, np.nan
        pr, pp = stats.spearmanr(rx, ry)
        return float(pr), float(pp)

    year_dummies = pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True)
    log_pick = np.log(d["pick"].astype(float)).to_frame("log_pick")
    out["partial_rho"], out["partial_p"] = _partial(log_pick)
    if year_dummies.shape[1] >= 1:
        out["partial_year_rho"], out["partial_year_p"] = _partial(year_dummies)
        both = pd.concat([log_pick, year_dummies], axis=1)
        out["partial_year_pick_rho"], out["partial_year_pick_p"] = _partial(both)
    # Official reported partial for career tests is year+pick when available.
    if control_kind == "year+pick" and np.isfinite(out["partial_year_pick_rho"]):
        out["official_partial_rho"] = out["partial_year_pick_rho"]
        out["official_partial_p"] = out["partial_year_pick_p"]
    elif control_kind == "year":
        out["official_partial_rho"] = out["partial_year_rho"]
        out["official_partial_p"] = out["partial_year_p"]
    else:
        out["official_partial_rho"] = out["partial_rho"]
        out["official_partial_p"] = out["partial_p"]
    return out


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
    M["pick"] = M["draft_overall_pick"].fillna(UDFA_PICK)
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
        "quick_pressure", "blitzing",
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
            "sack_rate": float(g["sack_num"].sum() / n) if n else np.nan,
            "pressure_rate": float(g["got_pressure"].mean()) if n else np.nan,
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
            res = spearman_partial(g[feat], g[PRIMARY_OUTCOME], g["pick"])
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
                res = spearman_partial(g[feat], g[out_col], g["pick"])
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

    # Career-success tests: does Sunday get-off relate to defensive snaps?
    # Primary outcomes are career defensive snaps and snaps per game active.
    # Official partial residualizes on draft-year dummies (2023 rookies have
    # had more seasons) and log draft pick. Start rate, sack rate, and
    # pressure rate are secondary. Holm is on the 4 primary All-DL tests,
    # using the year+pick partial p-value.
    log("\n==== Career family (PRIMARY): get-off vs defensive snaps, All DL ====")
    log("Official partial controls for draft year and log draft pick.")
    career_rows = []
    g = groups["All DL"]
    getoff_measures = [
        ("speed_1s_mph", "Speed at 1.0s after snap (mph)", +1),
        ("player_get_off", "NFL get-off time (sec, lower=faster)", -1),
    ]

    def _career_row(family, gname, gcol, glabel, ccol, clabel, frame):
        res = spearman_controlled(frame[gcol], frame[ccol], frame, "year+pick")
        log(
            f"  {gname:9s}  {glabel:36s} vs {clabel:34s}  n={res['n']:3d}  "
            f"ρ={res['rho']:+.2f} (p={fmt_p(res['p'])})  "
            f"year+pick ρ={res['partial_year_pick_rho']:+.2f} (p={fmt_p(res['partial_year_pick_p'])})  "
            f"year-only ρ={res['partial_year_rho']:+.2f}  pick-only ρ={res['partial_rho']:+.2f}"
        )
        return {
            "family": family, "group": gname, "feature": gcol, "feature_label": glabel,
            "outcome": ccol, "outcome_label": clabel, **res,
        }

    for gcol, glabel, _gs in getoff_measures:
        for ccol, clabel in CAREER_PRIMARY:
            career_rows.append(_career_row("career_primary", "All DL", gcol, glabel, ccol, clabel, g))
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
    log("  Holm-adjusted p (4 primary All-DL tests, year+pick partial p):")
    for _, r in Cprim.iterrows():
        star = " *" if bool(r["sig_holm_05"]) else ""
        log(
            f"    {r['feature_label']:36s} vs {r['outcome_label']:34s}  "
            f"p={fmt_p(r['official_partial_p'])} → Holm p={fmt_p(r['holm_p'])}{star}"
        )

    log("\n==== Career family (SECONDARY): start rate, sack rate, pressure rate ====")
    sec_rows = []
    for gcol, glabel, _gs in getoff_measures:
        for ccol, clabel in CAREER_SECONDARY:
            row = _career_row("career_secondary", "All DL", gcol, glabel, ccol, clabel, g)
            row["holm_p"] = np.nan
            row["sig_holm_05"] = False
            sec_rows.append(row)

    log("\n==== Career subtype (PRIMARY snaps only; not in the Holm family) ====")
    sub_rows = []
    for gname in ("Edge", "Interior"):
        frame = groups[gname]
        for gcol, glabel, _gs in getoff_measures:
            for ccol, clabel in CAREER_PRIMARY + CAREER_SECONDARY:
                row = _career_row("career_subtype", gname, gcol, glabel, ccol, clabel, frame)
                row["holm_p"] = np.nan
                row["sig_holm_05"] = False
                sub_rows.append(row)
    C = pd.concat([Cprim, pd.DataFrame(sec_rows), pd.DataFrame(sub_rows)], ignore_index=True, sort=False)

    return pd.concat([T, E, C], ignore_index=True, sort=False)


def make_figure(M: pd.DataFrame, tests: pd.DataFrame) -> Path:
    """Coach-readable fig: does Combine burst show up as get-off, Edge vs Interior?"""
    _style()
    # Oriented ρ so that a bar to the right always means "better Combine burst,
    # faster Sunday get-off (higher speed at 1.0s)".
    feat_sign = {f: s for f, _l, s in PRIMARY_FEATURES}
    prim = tests[(tests["family"] == "primary") & (tests["group"].isin(SUBTYPE_ORDER))].copy()
    prim["rho_oriented"] = prim.apply(
        lambda r: r["rho"] * feat_sign.get(r["feature"], 1) * 1,  # outcome speed_1s is already +
        axis=1,
    )

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.4), sharey=True)
    labels_order = [f for f, _l, _s in PRIMARY_FEATURES]
    pretty = {f: l.replace(" ", "\n") if False else l for f, l, _s in PRIMARY_FEATURES}
    # Shorter labels for the axis.
    pretty = {
        "official_ten_yd": "Faster\n10-yard split",
        "c_40_accel": "Higher 40-yard\npeak accel",
        "c_t15": "Faster 40\ntime to 15 mph",
        "dl_pass_rush_accel": "Higher pass-rush\ndrill accel",
    }

    # Title follows the 10-yard split, which is the feature that actually holds
    # inside both Edge and Interior (All-DL ρ is inflated by the speed gap
    # between those groups). Other primary features are mentioned only if they
    # also survive Holm within a subtype.
    ten = prim[prim["feature"] == "official_ten_yd"]
    ten_sig = bool(ten["sig_holm_05"].fillna(False).any())
    other_sig = bool(
        prim[prim["feature"] != "official_ten_yd"]["sig_holm_05"].fillna(False).any()
    )
    if ten_sig:
        # Keep this to one line so it does not clip. Interior time-to-15-mph
        # also barely survives Holm; that lives in the caption, not the title.
        title = "The 10-yard split is the Combine burst that shows up as get-off"
    elif other_sig:
        title = "A few Combine burst numbers track get-off — most do not survive a hard look"
    else:
        title = "Combine burst does not reliably show up as get-off on Sunday pass-rush snaps"

    for ax, group in zip(axes, SUBTYPE_ORDER):
        sub = prim[prim["group"] == group].copy()
        sub["_ord"] = sub["feature"].map({f: i for i, f in enumerate(labels_order)})
        sub = sub.dropna(subset=["_ord"]).sort_values("_ord")
        xs = np.arange(len(sub))
        colors = [SUBTYPE_COLOR[group] if bool(s) else "#7A7A7A" for s in sub["sig_holm_05"].fillna(False)]
        ax.bar(xs, sub["rho_oriented"], color=colors, width=0.72, zorder=3, edgecolor="white")
        ax.axhline(0, color="#888888", lw=0.8)
        for i, r in enumerate(sub.itertuples()):
            y = r.rho_oriented if np.isfinite(r.rho_oriented) else 0.0
            star = " ★" if bool(getattr(r, "sig_holm_05", False)) else ""
            ax.text(
                i, y + (0.04 if y >= 0 else -0.04),
                f"{y:+.2f}{star}\nn={int(r.n)}",
                ha="center", va="bottom" if y >= 0 else "top", fontsize=8,
            )
        ax.set_xticks(xs, [pretty.get(f, f) for f in sub["feature"]], fontsize=8.5)
        n_players = int((M["subtype"] == group).sum())
        n_used = int(sub["n"].max()) if len(sub) else 0
        ax.set_title(f"{group}  ({n_used} of {n_players} with enough snaps)", loc="left",
                     fontweight="bold", color=SUBTYPE_COLOR[group])
        if group == "Edge":
            ax.set_ylabel("Correlation with get-off\n(speed 1 second after the snap)")
        ax.set_ylim(-0.55, 0.75)

    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.08)
    fig.text(
        0.01, -0.12,
        "A bar to the right means a more explosive Combine number comes with a faster first second on pass-rush snaps.  "
        "Get-off is the player's median speed 1.0s after the snap, regular-season pass plays, lined up as EDGE or interior DL, plays that stood, at least 20 snaps.  "
        "Times (10-yard split, time to 15 mph) are flipped so 'faster' points right.  "
        "★ would mark a result that survives Holm correction across the 12 primary tests (4 features × Edge/Interior/All DL).  "
        "Grey bars did not.  Offensive linemen are not in this chart.  Game tracking covers only the 510 rookies.",
        fontsize=8, color="#555555", ha="left",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    path = FIGS / "fig5_dl_burst.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
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
        "draft_year", "draft_round", "draft_overall_pick", "pick",
        "official_ten_yd", "official_forty", "c_top_mph", "c_t15", "c_t18",
        "c_t90", "c_t10_derived", "c_40_accel", "c_40_accel_first",
        "dl_pass_rush_accel", "dl_pass_rush_accel_first", "dl_pass_rush_max_s",
        "n_rush_plays", "n_getoff", "n_speed_1s",
        "player_get_off", "speed_1s_mph", "speed_15s_mph", "time_to_5yd",
        "time_to_10yd", "accel_first", "dist_1s",
        "sack_rate", "pressure_rate", "start_rate", "snaps_per_game",
        "career_defensive_snaps", "career_games_active", "career_games_started",
    ]
    keep = [c for c in keep if c in M.columns]
    players_csv = OUT / "dl_burst_players.csv"
    M[keep].to_csv(players_csv, index=False)
    log(f"  wrote {players_csv} ({len(M)} rows)")

    tests = run_tests(M)
    tests_csv = OUT / "dl_burst_tests.csv"
    tests.to_csv(tests_csv, index=False)
    log(f"  wrote {tests_csv}")
    make_figure(M, tests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
