#!/usr/bin/env python3
"""Sunday Speed pipeline for NFL Big Data Bowl 2027.

Builds one row per WR / CB / S prospect with Combine tracking features,
game Sunday Speed, draft slot, and career outcomes. Reproduces the
headline Spearman correlations, runs the Phase 2 drill comparison, and
writes coach-readable draft figures.

Usage (from anywhere):
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/build_dataset.py
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/build_dataset.py --rebuild-game

Outputs:
    out/sunday_speed_players.parquet
    out/sunday_speed_players.csv
    out/game_play_speed.parquet          (intermediate, cached)
    out/phase2_tests.csv
    out/verification.txt
    out/figs/fig1_translation_scatter.png
    out/figs/fig2_exchange_rate.png
    out/figs/fig3_phase2_drills.png
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score
from statsmodels.stats.multitest import multipletests

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

MPH = 2.0455  # yd/s -> mph
UDFA_PICK = 260
MIN_DEEP_PLAYS = 20
MIN_COV_PLAYS = 30
MIN_TOTAL_PLAYS_LEGACY = 100  # explore.py test() filter, needed to reproduce rhos
GAME_YEARS = (2023, 2024, 2025)
CHUNKSIZE = 2_000_000
ACCEL_CLIP = 12.0  # |Δs/Δt| above this is treated as a tracking glitch
N_BOOT = 2000
RNG_SEED = 2027

DEEP_ROUTES = frozenset({"GO", "POST", "CORNER", "WHEEL"})
POS_MAP = {"WR": "WR", "CB": "CB", "FS": "S", "SS": "S"}
POS_ORDER = ["WR", "CB", "S"]

# Okabe-Ito colorblind-safe palette
POS_COLOR = {"WR": "#0072B2", "CB": "#D55E00", "S": "#009E73"}
POS_LABEL = {"WR": "Wide receivers", "CB": "Cornerbacks", "S": "Safeties"}

DRILL_NAME_NORM = {
    "LINE": "LINE_DRILL",
    "SPEED_OUT_LEFT": "SPEED_OUT_ROUTE_LEFT",
}

# Phase 2 drills of interest. Keys are normalized drill_name values.
DB_DRILLS = {
    "BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION": "bp45",
    "BACK_PEDAL_AND_90_DEGREE_BREAK_TO_BALL": "bp90",
    "W_DRILL": "w",
    "BOX_DRILL": "box",
    "GAUNTLET_DRILL": "gauntlet",
}
WR_DRILLS = {
    "GO_ROUTE_RIGHT": "go",
    "POST_CORNER_ROUTE_RIGHT": "post_corner",
    "SLANT_ROUTE_LEFT": "slant",
    "DAGGER_ROUTE_LEFT": "dagger",
}

# Pretty names for figures and the results writeup
DRILL_PRETTY = {
    "c_top": "40-yard tracked speed",
    "official_forty": "Official 40 time",
    "official_ten_yd": "Official 10-yard split",
    "c_t90": "40 burst (time to 90% top speed)",
    "c_t10_derived": "Derived 10-yard split",
    "wr_go_max_s": "WR go-route drill speed",
    "wr_post_corner_max_s": "WR post-corner drill speed",
    "wr_slant_max_s": "WR slant drill speed",
    "wr_dagger_max_s": "WR dagger drill speed",
    "db_bp45_max_s": "DB 45° transition drill speed",
    "db_bp90_max_s": "DB 90° break-to-ball drill speed",
    "db_w_max_s": "DB W-drill speed",
    "db_box_max_s": "DB box-drill speed",
    "db_gauntlet_max_s": "DB gauntlet drill speed",
    "db_bp45_brake": "DB 45° transition braking",
    "db_bp90_brake": "DB 90° break braking",
    "db_w_brake": "DB W-drill braking",
    "db_box_brake": "DB box-drill braking",
    "db_bp45_trans": "DB 45° transition time",
    "db_bp90_trans": "DB 90° break transition time",
    "db_w_trans": "DB W-drill transition time",
    "db_box_trans": "DB box-drill transition time",
}

TERMINAL_EVENTS = frozenset({
    "pass_arrived",
    "tackle",
    "out_of_bounds",
    "touchdown",
    "qb_sack",
    "qb_spike",
    "lateral",
    "fumble",
    "pass_outcome_touchdown",
    "safety",
})
SNAP_EVENTS = frozenset({"ball_snap", "autoevent_ballsnap"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def coerce_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.map({True: True, False: False, "TRUE": True, "FALSE": False, "True": True, "False": False, 1: True, 0: False, 1.0: True, 0.0: False}).fillna(False)


def spearman_with_partial(x: pd.Series, y: pd.Series, pick: pd.Series) -> dict:
    """Spearman ρ and a pick-controlled 'partial' ρ (residualize on log pick, then Spearman).

    Matches the method in explore.py so headline numbers can be reproduced.
    """
    d = pd.DataFrame({"x": x, "y": y, "pick": pick}).dropna()
    n = len(d)
    out = {"n": n, "rho": np.nan, "p": np.nan, "partial_rho": np.nan, "partial_p": np.nan}
    if n < 8:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    lp = np.log(d["pick"].astype(float))
    # Guard against a constant log-pick (shouldn't happen, but don't crash).
    if lp.nunique() >= 2 and d["x"].nunique() >= 2 and d["y"].nunique() >= 2:
        rx = d["x"] - np.poly1d(np.polyfit(lp, d["x"], 1))(lp)
        ry = d["y"] - np.poly1d(np.polyfit(lp, d["y"], 1))(lp)
        pr, pp = stats.spearmanr(rx, ry)
        out["partial_rho"], out["partial_p"] = float(pr), float(pp)
    return out


def loo_r2(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float)
    if len(y) < 8 or np.unique(x).size < 2:
        return np.nan
    preds = np.empty_like(y, dtype=float)
    for train, test in LeaveOneOut().split(x):
        preds[test] = LinearRegression().fit(x[train], y[train]).predict(x[test])
    return float(r2_score(y, preds))


def bootstrap_slope(x: np.ndarray, y: np.ndarray, n_boot: int = N_BOOT, seed: int = RNG_SEED) -> tuple[float, float, float]:
    """OLS slope of y ~ x with a player-level bootstrap 95% CI."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 8:
        return np.nan, np.nan, np.nan
    slope = float(np.polyfit(x, y, 1)[0])
    rng = np.random.default_rng(seed)
    n = len(x)
    boots = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        if np.unique(x[idx]).size < 2:
            boots[i] = np.nan
            continue
        boots[i] = np.polyfit(x[idx], y[idx], 1)[0]
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return slope, float(lo), float(hi)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


# ---------------------------------------------------------------------------
# Combine tracking features
# ---------------------------------------------------------------------------
def _attempt_features(g: pd.DataFrame) -> dict:
    """Peak speed, burst, signed accel/brake, transition time, optional 40 splits."""
    g = g.sort_values("time")
    s = g["s"].to_numpy(dtype=float)
    x = g["x"].to_numpy(dtype=float)
    ds = g["ds"].to_numpy(dtype=float)
    n = len(g)
    out = {
        "max_s": np.nan,
        "t90": np.nan,
        "accel": np.nan,
        "brake": np.nan,
        "trans": np.nan,
        "t10": np.nan,
        "t20": np.nan,
        "t40": np.nan,
        "n_frames": n,
    }
    if n == 0 or not np.isfinite(s).any():
        return out
    i_max = int(np.nanargmax(s))
    max_s = float(s[i_max])
    out["max_s"] = max_s
    if max_s > 0:
        # Time from first tracked frame to first frame at 90% of this attempt's top speed.
        # This matches explore.py (index / 10 Hz), kept for consistency.
        hit = np.where(s >= 0.9 * max_s)[0]
        out["t90"] = float(hit[0] / 10.0) if len(hit) else np.nan
    finite_ds = ds[np.isfinite(ds)]
    if finite_ds.size:
        out["accel"] = float(np.nanmax(finite_ds))
        out["brake"] = float(-np.nanmin(finite_ds))
        # Transition time: peak brake -> first later frame at 80% of subsequent peak re-accel.
        i_brake = int(np.nanargmin(ds))
        after = ds[i_brake + 1 :]
        if after.size and np.isfinite(after).any():
            peak_re = float(np.nanmax(after))
            if peak_re > 0:
                rel = np.where(after >= 0.8 * peak_re)[0]
                if len(rel):
                    out["trans"] = float((rel[0] + 1) / 10.0)  # +1 because after starts at i_brake+1

    # 10 / 20 / 40-yard splits for the 40-yard dash only.
    # Tracking usually starts after first movement, so we set the start line
    # as (max x - 40) — players run in +x — and interpolate crossing times.
    # Official laser times remain the preferred split columns; these are a
    # tracking-derived companion and do not match official times closely.
    if g["drill_type"].iloc[0] == "FORTY_YARD_DASH" and n >= 8 and np.isfinite(x).sum() >= 8:
        t0 = pd.to_datetime(g["time"].iloc[0])
        t = (pd.to_datetime(g["time"]) - t0).dt.total_seconds().to_numpy()
        start_x = float(np.nanmax(x) - 40.0)
        n_fit = min(8, n)

        def t_cross(target: float) -> float:
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

        t_start = t_cross(start_x)
        if np.isfinite(t_start):
            for yd, key in ((10, "t10"), (20, "t20"), (40, "t40")):
                tc = t_cross(start_x + yd)
                if np.isfinite(tc):
                    out[key] = float(tc - t_start)
    return out


def build_combine_features(ids: pd.Index) -> pd.DataFrame:
    log("Loading combine_tracking.csv (PLAYER rows for WR/CB/S)...")
    usecols = [
        "event_id", "nfl_id", "entity_type", "time", "drill_type", "drill_name",
        "attempt", "x", "y", "s",
    ]
    ct = pd.read_csv(DATA / "combine_tracking.csv", usecols=usecols)
    ct = ct[(ct["entity_type"] == "PLAYER") & ct["nfl_id"].isin(ids)].copy()
    ct["drill_name"] = ct["drill_name"].replace(DRILL_NAME_NORM)
    ct = ct.sort_values(["event_id", "time"])
    ct["ds"] = ct.groupby("event_id")["s"].diff() * 10.0
    ct.loc[ct["ds"].abs() > ACCEL_CLIP, "ds"] = np.nan
    log(f"  {len(ct):,} frames, {ct['event_id'].nunique():,} attempts, {ct['nfl_id'].nunique()} players")

    rows = []
    grouped = ct.groupby(["event_id", "nfl_id", "drill_type", "drill_name"], sort=False)
    for (event_id, nfl_id, drill_type, drill_name), g in grouped:
        feat = _attempt_features(g)
        feat.update({
            "event_id": event_id,
            "nfl_id": nfl_id,
            "drill_type": drill_type,
            "drill_name": drill_name,
        })
        rows.append(feat)
    att = pd.DataFrame(rows)
    att.to_parquet(OUT / "combine_attempts_features.parquet", index=False)
    log(f"  wrote {len(att):,} attempt rows -> out/combine_attempts_features.parquet")
    del ct
    gc.collect()

    # 40-yard dash player features
    f40 = att[att["drill_type"] == "FORTY_YARD_DASH"].copy()
    if f40.empty:
        raise RuntimeError("No FORTY_YARD_DASH attempts found for WR/CB/S.")
    # Splits from the same attempt that produced the player's top speed.
    idx = f40.groupby("nfl_id")["max_s"].idxmax()
    best = f40.loc[idx, ["nfl_id", "t10", "t20", "t40", "accel", "brake"]].set_index("nfl_id")
    best = best.rename(columns={
        "t10": "c_t10_derived", "t20": "c_t20_derived", "t40": "c_t40_derived",
        "accel": "c_40_accel", "brake": "c_40_brake",
    })
    c40 = f40.groupby("nfl_id").agg(c_top=("max_s", "max"), c_t90=("t90", "min"))
    C = c40.join(best)

    def _drill_player(frame: pd.DataFrame, name_map: dict[str, str], prefix: str) -> pd.DataFrame:
        parts = []
        for raw_name, short in name_map.items():
            sub = frame[frame["drill_name"] == raw_name]
            if sub.empty:
                continue
            agg = sub.groupby("nfl_id").agg(
                max_s=("max_s", "max"),
                brake=("brake", "max"),
                trans=("trans", "median"),
                accel=("accel", "max"),
                n_att=("max_s", "size"),
            )
            agg.columns = [f"{prefix}_{short}_{c}" for c in agg.columns]
            parts.append(agg)
        if not parts:
            return pd.DataFrame(index=pd.Index([], name="nfl_id"))
        out = parts[0]
        for p in parts[1:]:
            out = out.join(p, how="outer")
        return out

    db = _drill_player(att[att["drill_type"] == "SKILL_DRILLS_DB"], DB_DRILLS, "db")
    wr = _drill_player(att[att["drill_type"] == "SKILL_DRILLS_WR"], WR_DRILLS, "wr")
    C = C.join(db, how="outer").join(wr, how="outer")
    log(f"  combine feature table: {len(C)} players, {C.shape[1]} columns")
    return C


# ---------------------------------------------------------------------------
# Game tracking -> per-play max speed
# ---------------------------------------------------------------------------
def build_game_play_speeds(ids: pd.Index, rebuild: bool = False) -> pd.DataFrame:
    cache = OUT / "game_play_speed.parquet"
    if cache.exists() and not rebuild:
        log(f"Loading cached play speeds from {cache}")
        return pd.read_parquet(cache)

    log("Streaming game tracking (this is the slow step)...")
    t0 = time.time()
    parts: list[pd.DataFrame] = []
    id_set = set(ids.tolist())
    usecols = ["game_id", "play_id", "nfl_id", "time", "s", "event"]
    dtypes = {"game_id": "int64", "play_id": "int64", "nfl_id": "int32", "s": "float32"}
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
            n_kept += len(chunk)
            chunk = chunk.sort_values(["game_id", "play_id", "nfl_id", "time"])
            # Signed accel for a robustness column; primary Sunday Speed uses max s only.
            chunk["ds"] = chunk.groupby(["game_id", "play_id", "nfl_id"], sort=False)["s"].diff() * 10.0
            chunk.loc[chunk["ds"].abs() > ACCEL_CLIP, "ds"] = np.nan

            ev = chunk["event"].astype("string")
            is_snap = ev.isin(SNAP_EVENTS)
            is_end = ev.isin(TERMINAL_EVENTS)
            # Vectorized aggregations + a compact window pass (no per-play Python apply).
            base = chunk.groupby(["game_id", "play_id", "nfl_id"], sort=False).agg(
                max_s=("s", "max"),
                brake=("ds", "min"),
            )
            # Window: first snap / first terminal time per play-player, then max s in range.
            snap = chunk.loc[is_snap, ["game_id", "play_id", "nfl_id", "time"]].groupby(
                ["game_id", "play_id", "nfl_id"], sort=False
            )["time"].min().rename("snap_time")
            end = chunk.loc[is_end, ["game_id", "play_id", "nfl_id", "time"]].groupby(
                ["game_id", "play_id", "nfl_id"], sort=False
            )["time"].min().rename("end_time")
            bounds = pd.concat([snap, end], axis=1)
            if len(bounds):
                tmp = chunk[["game_id", "play_id", "nfl_id", "time", "s"]].merge(
                    bounds, on=["game_id", "play_id", "nfl_id"], how="inner"
                )
                in_win = tmp["snap_time"].notna() & tmp["end_time"].notna()
                in_win &= tmp["time"] >= tmp["snap_time"]
                in_win &= tmp["time"] <= tmp["end_time"]
                win = tmp.loc[in_win].groupby(["game_id", "play_id", "nfl_id"], sort=False)["s"].max().rename("max_s_window")
                base = base.join(win)
            else:
                base["max_s_window"] = np.nan
            base["brake"] = -base["brake"]
            parts.append(base.reset_index())
            if n_chunks % 4 == 0:
                log(f"    chunks={n_chunks}, kept frames={n_kept:,}, plays so far={sum(len(p) for p in parts):,}")
            del chunk, base
            gc.collect()

    G = pd.concat(parts, ignore_index=True)
    del parts
    gc.collect()
    # A play can straddle a chunk boundary: take the max of per-chunk maxima.
    G = G.groupby(["game_id", "play_id", "nfl_id"], sort=False).agg(
        max_s=("max_s", "max"),
        max_s_window=("max_s_window", "max"),
        brake=("brake", "max"),
    ).reset_index()
    G.to_parquet(cache, index=False)
    log(f"  {len(G):,} play-player rows written to {cache} in {time.time()-t0:.1f}s")
    return G


# ---------------------------------------------------------------------------
# Player-level Sunday Speed table
# ---------------------------------------------------------------------------
def build_player_table(combine: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    log("Building player table...")
    pl = pd.read_csv(DATA / "players.csv")
    pl = pl[pl["nfl_position"].isin(POS_MAP)].copy()
    pl["pos_group"] = pl["nfl_position"].map(POS_MAP)
    pl["pick"] = pl["draft_overall_pick"].fillna(UDFA_PICK)
    cs = pd.read_csv(DATA / "player_career_successes.csv")
    cr = pd.read_csv(DATA / "combine_results.csv")
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season", "season_type", "week"])

    slim_cols = [
        "game_id", "play_id", "nfl_id", "quarter", "route_ran", "coverage_assignment",
        "separation_at_pass_forward", "target", "yards_after_catch",
        "expected_yards_after_catch", "play_nullified_by_penalty", "pass_result",
        "tackle", "assist",
    ]
    pp = pd.read_csv(DATA / "player_play.csv", usecols=slim_cols)
    pp = pp[pp["nfl_id"].isin(pl["nfl_id"])]
    pp["target"] = coerce_bool(pp["target"])
    for col in ("tackle", "assist"):
        pp[col] = pd.to_numeric(pp[col], errors="coerce").fillna(0.0)

    G = plays.merge(pp, on=["game_id", "play_id", "nfl_id"], how="left")
    G = G.merge(games, on="game_id", how="left")
    # Official opportunity filter: regular season, play stands.
    G["is_reg_clean"] = (G["season_type"] == "REG") & (G["play_nullified_by_penalty"] == "N")
    G["is_deep"] = G["route_ran"].isin(DEEP_ROUTES)
    cov = G["coverage_assignment"].astype("string")
    G["is_cov"] = cov.str.contains("DEEP|MAN", na=False) & G["pass_result"].notna()
    # Legacy coverage flag matches explore.py (no pass_result requirement).
    G["is_cov_legacy"] = cov.str.contains("DEEP|MAN", na=False)

    def p90(s: pd.Series, min_n: int) -> float:
        return float(s.quantile(0.90)) if len(s) >= min_n else np.nan

    def player_game_metrics(g: pd.DataFrame) -> pd.Series:
        deep = g[g["is_deep"]]
        deep_r = g[g["is_deep"] & g["is_reg_clean"]]
        covp = g[g["is_cov"]]
        cov_r = g[g["is_cov"] & g["is_reg_clean"]]
        cov_leg = g[g["is_cov_legacy"]]
        q1, q4 = g[g["quarter"] == 1], g[g["quarter"] == 4]
        yoe = g["yards_after_catch"] - g["expected_yards_after_catch"]
        # Odd/even game split-half (stability), on official opportunity plays.
        # Position is not known here; compute both deep and cov halves.
        odd_deep = deep_r[deep_r["game_id"] % 2 == 1]["max_s"]
        even_deep = deep_r[deep_r["game_id"] % 2 == 0]["max_s"]
        odd_cov = cov_r[cov_r["game_id"] % 2 == 1]["max_s"]
        even_cov = cov_r[cov_r["game_id"] % 2 == 0]["max_s"]
        return pd.Series({
            "n_plays": len(g),
            "n_plays_reg": int(g["is_reg_clean"].sum()),
            "n_deep": len(deep),
            "n_deep_reg": len(deep_r),
            "n_cov": len(covp),
            "n_cov_reg": len(cov_r),
            "n_cov_legacy": len(cov_leg),
            "g_p95": float(g["max_s"].quantile(0.95)) if len(g) else np.nan,
            # Legacy (all games, no penalty/REG filter) — used to verify headline rhos.
            "g_deep_p90": p90(deep["max_s"], MIN_DEEP_PLAYS),
            "g_cov_p90": p90(cov_leg["max_s"], MIN_COV_PLAYS),
            # Official Sunday Speed ingredients (REG, play stands).
            "g_deep_p90_reg": p90(deep_r["max_s"], MIN_DEEP_PLAYS),
            "g_cov_p90_reg": p90(cov_r["max_s"], MIN_COV_PLAYS),
            "g_deep_p90_reg_window": p90(deep_r["max_s_window"].dropna(), MIN_DEEP_PLAYS),
            "g_cov_p90_reg_window": p90(cov_r["max_s_window"].dropna(), MIN_COV_PLAYS),
            "sep_deep": float(deep_r["separation_at_pass_forward"].mean())
                if deep_r["separation_at_pass_forward"].notna().sum() >= MIN_DEEP_PLAYS else np.nan,
            "yac_oe": float(yoe.mean()) if yoe.notna().any() else np.nan,
            "tgt_rate": float(g["target"].mean()) if "target" in g else np.nan,
            "tk_rate": float((g["tackle"] + g["assist"]).mean()),
            "q4_ret": (
                float(q4["max_s"].quantile(0.90) / q1["max_s"].quantile(0.90))
                if min(len(q4), len(q1)) >= 30 and q1["max_s"].quantile(0.90) > 0
                else np.nan
            ),
            "ss_odd_deep": p90(odd_deep, 15),
            "ss_even_deep": p90(even_deep, 15),
            "ss_odd_cov": p90(odd_cov, 15),
            "ss_even_cov": p90(even_cov, 15),
        })

    gp = G.groupby("nfl_id", sort=False).apply(player_game_metrics, include_groups=False)

    M = (
        pl.set_index("nfl_id")[
            ["display_name", "draft_year", "nfl_position", "pos_group", "birth_date",
             "college_name", "college_conference", "draft_round",
             "draft_pick_within_round", "draft_overall_pick", "pick"]
        ]
        .join(cr.set_index("nfl_id")[[
            "combine_position", "combine_height", "combine_weight",
            "ten_yd_split", "forty", "vertical", "broad_jump",
            "three_cone", "short_shuttle", "bench_reps",
            "ngs_athleticism_score", "ngs_college_production_score", "ngs_final_score",
        ]], how="left")
        .join(cs.set_index("nfl_id"), how="left")
        .join(combine, how="left")
        .join(gp, how="left")
    )
    M = M.rename(columns={"ten_yd_split": "official_ten_yd", "forty": "official_forty"})

    M["n_plays"] = M["n_plays"].fillna(0)
    M["start_rate"] = M["career_games_started"] / M["career_games_active"].replace(0, np.nan)
    M["snap_share"] = (
        (M["career_offensive_snaps"] + M["career_defensive_snaps"])
        / M["career_games_active"].replace(0, np.nan)
    )
    # Position-appropriate Sunday Speed (official definition).
    M["sunday_speed"] = np.where(M["pos_group"] == "WR", M["g_deep_p90_reg"], M["g_cov_p90_reg"])
    M["sunday_speed_window"] = np.where(
        M["pos_group"] == "WR", M["g_deep_p90_reg_window"], M["g_cov_p90_reg_window"]
    )
    # Legacy column used to reproduce the published headline (all games).
    M["sunday_speed_legacy"] = np.where(M["pos_group"] == "WR", M["g_deep_p90"], M["g_cov_p90"])

    for col in ("c_top", "sunday_speed", "sunday_speed_legacy", "sunday_speed_window"):
        M[f"{col}_mph"] = M[col] * MPH

    M["realization"] = M["sunday_speed"] / M["c_top"]
    M["realization_legacy"] = M["sunday_speed_legacy"] / M["c_top"]

    # Speed Translation Rate and SSOE, fit on official sample (min plays already baked into SS).
    slope_rows = []
    M["ssoe"] = np.nan
    M["ssoe_mph"] = np.nan
    M["translation_slope"] = np.nan
    for pos in POS_ORDER:
        # Official sample: has c_top, has Sunday Speed, plus the legacy total-play floor
        # is NOT required here — official SS already has opportunity-play floors.
        d = M[(M["pos_group"] == pos) & M["c_top"].notna() & M["sunday_speed"].notna()]
        if len(d) < 8:
            log(f"  {pos}: official sample too small (n={len(d)})")
            continue
        intercept, slope = np.polyfit(d["c_top"], d["sunday_speed"], 1)[1], np.polyfit(d["c_top"], d["sunday_speed"], 1)[0]
        # np.polyfit returns [slope, intercept]
        coef = np.polyfit(d["c_top"], d["sunday_speed"], 1)
        slope, intercept = float(coef[0]), float(coef[1])
        b_slope, b_lo, b_hi = bootstrap_slope(d["c_top"].to_numpy(), d["sunday_speed"].to_numpy())
        resid = d["sunday_speed"] - (intercept + slope * d["c_top"])
        M.loc[d.index, "ssoe"] = resid
        M.loc[d.index, "ssoe_mph"] = resid * MPH
        M.loc[d.index, "translation_slope"] = slope
        slope_rows.append({
            "pos_group": pos,
            "n": int(len(d)),
            "slope": slope,
            "slope_ci_lo": b_lo,
            "slope_ci_hi": b_hi,
            "intercept": intercept,
            "median_realization": float(d["realization"].median()),
        })
        log(f"  {pos} official translation: n={len(d)} slope={slope:.3f} (95% CI {b_lo:.3f}–{b_hi:.3f})")

    # Legacy slopes (all-games SS, plays>=100) for headline verification.
    for pos in POS_ORDER:
        col = "g_deep_p90" if pos == "WR" else "g_cov_p90"
        d = M[(M["pos_group"] == pos) & (M["n_plays"] >= MIN_TOTAL_PLAYS_LEGACY) & M["c_top"].notna() & M[col].notna()]
        if len(d) < 8:
            continue
        coef = np.polyfit(d["c_top"], d[col], 1)
        log(f"  {pos} legacy translation (plays>=100): n={len(d)} slope={coef[0]:.3f}")
        for row in slope_rows:
            if row["pos_group"] == pos:
                row["legacy_n"] = int(len(d))
                row["legacy_slope"] = float(coef[0])

    pd.DataFrame(slope_rows).to_csv(OUT / "translation_slopes.csv", index=False)
    with open(OUT / "translation_slopes.json", "w") as f:
        json.dump(slope_rows, f, indent=2)

    M["c_top_mph"] = M["c_top"] * MPH
    return M.reset_index()


# ---------------------------------------------------------------------------
# Headline verification + Phase 2
# ---------------------------------------------------------------------------
def verify_headlines(M: pd.DataFrame) -> pd.DataFrame:
    log("\n==== Headline verification (legacy definition, to match STRATEGY.md) ====")
    rows = []
    expected = {"WR": (68, 0.64, 0.62), "CB": (33, 0.06, 0.05), "S": (27, 0.19, 0.15)}
    for pos in POS_ORDER:
        col = "g_deep_p90" if pos == "WR" else "g_cov_p90"
        d = M[(M["pos_group"] == pos) & (M["n_plays"] >= MIN_TOTAL_PLAYS_LEGACY)]
        res = spearman_with_partial(d["c_top"], d[col], d["pick"])
        exp_n, exp_rho, exp_part = expected[pos]
        ok_n = res["n"] == exp_n
        ok_rho = np.isfinite(res["rho"]) and abs(res["rho"] - exp_rho) < 0.015
        ok_part = np.isfinite(res["partial_rho"]) and abs(res["partial_rho"] - exp_part) < 0.02
        status = "MATCH" if (ok_n and ok_rho) else "CHECK"
        log(
            f"  {pos:3s} n={res['n']:3d} (exp {exp_n})  rho={res['rho']:+.2f} (exp {exp_rho:+.2f})  "
            f"partial={res['partial_rho']:+.2f} (exp {exp_part:+.2f})  p={fmt_p(res['p'])}  [{status}]"
        )
        rows.append({
            "family": "headline_legacy", "pos_group": pos, "feature": "c_top",
            "outcome": col, **res, "expected_n": exp_n, "expected_rho": exp_rho,
            "match": ok_n and ok_rho,
        })

    log("\n==== Official definition (REG, play stands, no 100-play floor) ====")
    for pos in POS_ORDER:
        d = M[M["pos_group"] == pos]
        res = spearman_with_partial(d["c_top"], d["sunday_speed"], d["pick"])
        log(
            f"  {pos:3s} n={res['n']:3d}  rho={res['rho']:+.2f} p={fmt_p(res['p'])}  "
            f"partial={res['partial_rho']:+.2f} p={fmt_p(res['partial_p'])}"
        )
        rows.append({
            "family": "headline_official", "pos_group": pos, "feature": "c_top",
            "outcome": "sunday_speed", **res,
        })

    # Stability (split-half Pearson r), official opportunity plays.
    log("\n==== Split-half stability (odd vs even games, official SS) ====")
    for pos, odd_col, even_col in (
        ("WR", "ss_odd_deep", "ss_even_deep"),
        ("CB", "ss_odd_cov", "ss_even_cov"),
        ("S", "ss_odd_cov", "ss_even_cov"),
        ("DB", "ss_odd_cov", "ss_even_cov"),
    ):
        if pos == "DB":
            d = M[M["pos_group"].isin(["CB", "S"])][[odd_col, even_col]].dropna()
        else:
            d = M[M["pos_group"] == pos][[odd_col, even_col]].dropna()
        if len(d) < 8:
            log(f"  {pos}: n={len(d)} too thin")
            continue
        r = float(d[odd_col].corr(d[even_col]))
        log(f"  {pos}: n={len(d)} r={r:.2f}")
        rows.append({
            "family": "stability", "pos_group": pos, "feature": "split_half",
            "outcome": "sunday_speed", "n": int(len(d)), "rho": r, "p": np.nan,
            "partial_rho": np.nan, "partial_p": np.nan,
        })
    return pd.DataFrame(rows)


def phase2_tests(M: pd.DataFrame) -> pd.DataFrame:
    """Does skill-drill tracking predict Sunday Speed better than the 40?"""
    log("\n==== Phase 2: drill features vs 40-yard tracked speed ====")
    # Primary family: peak-speed features only (the direct 'which drill' question).
    # Secondary family: braking and transition times.
    primary_by_pos = {
        "WR": [
            "c_top", "official_forty", "official_ten_yd", "c_t90",
            "wr_go_max_s", "wr_post_corner_max_s", "wr_slant_max_s", "wr_dagger_max_s",
        ],
        "CB": [
            "c_top", "official_forty", "official_ten_yd", "c_t90",
            "db_bp45_max_s", "db_bp90_max_s", "db_w_max_s", "db_box_max_s", "db_gauntlet_max_s",
        ],
        "S": [
            "c_top", "official_forty", "official_ten_yd", "c_t90",
            "db_bp45_max_s", "db_bp90_max_s", "db_w_max_s", "db_box_max_s", "db_gauntlet_max_s",
        ],
    }
    secondary_by_pos = {
        "WR": ["wr_go_brake", "wr_go_trans"],
        "CB": [
            "db_bp45_brake", "db_bp90_brake", "db_w_brake", "db_box_brake",
            "db_bp45_trans", "db_bp90_trans", "db_w_trans", "db_box_trans",
        ],
        "S": [
            "db_bp45_brake", "db_bp90_brake", "db_w_brake", "db_box_brake",
            "db_bp45_trans", "db_bp90_trans", "db_w_trans", "db_box_trans",
        ],
    }

    rows = []
    for pos in POS_ORDER:
        dpos = M[M["pos_group"] == pos]
        for family, feat_list in (("primary", primary_by_pos[pos]), ("secondary", secondary_by_pos[pos])):
            for feat in feat_list:
                if feat not in dpos.columns:
                    continue
                res = spearman_with_partial(dpos[feat], dpos["sunday_speed"], dpos["pick"])
                # Leave-one-out R² on the same complete cases as the Spearman.
                sub = dpos[[feat, "sunday_speed"]].dropna()
                r2 = loo_r2(sub[feat].to_numpy(), sub["sunday_speed"].to_numpy()) if len(sub) >= 8 else np.nan
                # Incremental: drill vs Sunday Speed after residualizing on c_top (and pick already in partial).
                inc = {"inc_rho": np.nan, "inc_p": np.nan}
                if feat != "c_top" and "c_top" in dpos.columns:
                    sub2 = dpos[[feat, "sunday_speed", "c_top"]].dropna()
                    if len(sub2) >= 8 and sub2["c_top"].nunique() >= 2:
                        rx = sub2[feat] - np.poly1d(np.polyfit(sub2["c_top"], sub2[feat], 1))(sub2["c_top"])
                        ry = sub2["sunday_speed"] - np.poly1d(np.polyfit(sub2["c_top"], sub2["sunday_speed"], 1))(sub2["c_top"])
                        ir, ip = stats.spearmanr(rx, ry)
                        inc = {"inc_rho": float(ir), "inc_p": float(ip)}
                rec = {
                    "family": family, "pos_group": pos, "feature": feat,
                    "feature_label": DRILL_PRETTY.get(feat, feat),
                    "outcome": "sunday_speed",
                    **res, "loo_r2": r2, **inc,
                }
                rows.append(rec)
                log(
                    f"  [{family:9s}] {pos:3s} {DRILL_PRETTY.get(feat, feat):40s}  "
                    f"n={res['n']:3d}  rho={res['rho']:+.2f} p={fmt_p(res['p'])}  "
                    f"partial={res['partial_rho']:+.2f}  LOO R²={r2:+.3f}"
                    + (f"  inc|c_top rho={inc['inc_rho']:+.2f} p={fmt_p(inc['inc_p'])}" if np.isfinite(inc["inc_rho"]) else "")
                )

    T = pd.DataFrame(rows)
    # Holm correction within the pre-specified primary family (all positions, peak-speed tests).
    prim = T["family"] == "primary"
    if prim.any():
        reject, p_adj, _, _ = multipletests(T.loc[prim, "p"].fillna(1.0).to_numpy(), method="holm")
        T.loc[prim, "p_holm"] = p_adj
        T.loc[prim, "sig_holm_05"] = reject
        # Also Holm within each position (smaller family; slightly more power, still honest).
        T["p_holm_within_pos"] = np.nan
        for pos in POS_ORDER:
            m = prim & (T["pos_group"] == pos)
            if m.sum() == 0:
                continue
            _, p_adj_w, _, _ = multipletests(T.loc[m, "p"].fillna(1.0).to_numpy(), method="holm")
            T.loc[m, "p_holm_within_pos"] = p_adj_w
    sec = T["family"] == "secondary"
    if sec.any():
        _, p_adj_s, _, _ = multipletests(T.loc[sec, "p"].fillna(1.0).to_numpy(), method="holm")
        T.loc[sec, "p_holm"] = p_adj_s

    log("\n  Holm-adjusted p (primary family, all positions together):")
    show = T[prim].sort_values(["pos_group", "p"])
    for _, r in show.iterrows():
        flag = "*" if bool(r.get("sig_holm_05")) else " "
        log(
            f"  {flag} {r['pos_group']:3s} {r['feature_label']:40s}  "
            f"p_raw={fmt_p(r['p'])}  p_holm={fmt_p(r['p_holm'])}"
        )
    return T


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def _style():
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


def make_figures(M: pd.DataFrame, phase2: pd.DataFrame, slopes: list[dict]) -> list[Path]:
    _style()
    paths = []
    slope_map = {s["pos_group"]: s for s in slopes}

    # Fig 1: translation scatter, faceted WR / CB / S, mph units.
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.6), sharex=False, sharey=False)
    for ax, pos in zip(axes, POS_ORDER):
        d = M[(M["pos_group"] == pos) & M["c_top_mph"].notna() & M["sunday_speed_mph"].notna()]
        ax.scatter(
            d["c_top_mph"], d["sunday_speed_mph"],
            c=POS_COLOR[pos], s=36, alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3,
        )
        if len(d) >= 8:
            coef = np.polyfit(d["c_top_mph"], d["sunday_speed_mph"], 1)
            xs = np.linspace(d["c_top_mph"].min(), d["c_top_mph"].max(), 50)
            ax.plot(xs, np.poly1d(coef)(xs), color=POS_COLOR[pos], lw=2.0, zorder=4)
            sl = slope_map.get(pos, {})
            ci = ""
            if sl and np.isfinite(sl.get("slope_ci_lo", np.nan)):
                ci = f"\n95% CI {sl['slope_ci_lo']:.2f}–{sl['slope_ci_hi']:.2f}"
            ax.text(
                0.05, 0.95,
                f"n={len(d)}\n+{coef[0]:.2f} mph Sunday\nper Combine mph{ci}",
                transform=ax.transAxes, va="top", ha="left",
                fontsize=9, color=POS_COLOR[pos],
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#CCCCCC", alpha=0.9),
            )
        ax.set_title(POS_LABEL[pos], loc="left", fontweight="bold", color=POS_COLOR[pos])
        ax.set_xlabel("Combine 40-yard top speed (mph)")
        if pos == "WR":
            ax.set_ylabel("Sunday Speed (mph)")
        else:
            ax.set_ylabel("Sunday Speed (mph)")
    fig.suptitle(
        "For receivers, Combine speed shows up on Sunday. For corners, it barely does.",
        x=0.01, ha="left", fontweight="bold", fontsize=14, y=1.02,
    )
    fig.text(
        0.01, -0.02,
        "Sunday Speed is a player's 90th-percentile play top speed on go/post/corner/wheel routes (WR) "
        "or man/deep coverage (CB, S), regular season, plays that stood. Speed in mph (yd/s × 2.0455).",
        fontsize=8, color="#555555", ha="left",
    )
    fig.tight_layout()
    p1 = FIGS / "fig1_translation_scatter.png"
    fig.savefig(p1, dpi=200, bbox_inches="tight")
    plt.close(fig)
    paths.append(p1)
    log(f"  wrote {p1}")

    # Fig 2: exchange-rate bars with bootstrap CIs.
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    labels, vals, los, his, colors, ns = [], [], [], [], [], []
    for pos in POS_ORDER:
        sl = slope_map.get(pos)
        if not sl:
            continue
        labels.append(POS_LABEL[pos])
        vals.append(sl["slope"])
        los.append(sl["slope"] - sl["slope_ci_lo"])
        his.append(sl["slope_ci_hi"] - sl["slope"])
        colors.append(POS_COLOR[pos])
        ns.append(sl["n"])
    x = np.arange(len(labels))
    ax.bar(x, vals, color=colors, width=0.62, zorder=3, edgecolor="white")
    ax.errorbar(x, vals, yerr=[los, his], fmt="none", ecolor="#222222", capsize=5, lw=1.2, zorder=4)
    for i, (v, n) in enumerate(zip(vals, ns)):
        ax.text(i, v + his[i] + 0.03, f"{v:.2f}\nn={n}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.axhline(0, color="#888888", lw=0.8)
    ax.axhline(1.0, color="#AAAAAA", lw=0.8, ls="--")
    ax.set_xticks(x, labels)
    ax.set_ylabel("mph on Sunday per 1 mph at the Combine")
    ax.set_ylim(min(0, min(vals) - 0.15), max(vals) + max(his) + 0.25)
    ax.set_title(
        "The exchange rate: how much Combine speed is real on Sunday",
        loc="left", fontweight="bold",
    )
    ax.text(
        0.0, -0.18,
        "Dashed line at 1.0 would mean every Combine mph shows up on Sunday. "
        "Error bars are 95% bootstrap confidence intervals (2,000 player resamples).",
        transform=ax.transAxes, fontsize=8, color="#555555", ha="left",
    )
    fig.tight_layout()
    p2 = FIGS / "fig2_exchange_rate.png"
    fig.savefig(p2, dpi=200, bbox_inches="tight")
    plt.close(fig)
    paths.append(p2)
    log(f"  wrote {p2}")

    # Fig 3: Phase 2 comparison — Spearman ρ of 40 vs each drill, by position.
    # Show the headline 40 plus the skill drills (drop official times / burst from the figure
    # so the comparison stays readable). Annotate Holm-significant bars.
    keep_feats = {
        "WR": ["c_top", "wr_go_max_s", "wr_post_corner_max_s", "wr_slant_max_s", "wr_dagger_max_s"],
        "CB": ["c_top", "db_bp45_max_s", "db_bp90_max_s", "db_w_max_s", "db_box_max_s", "db_gauntlet_max_s"],
        "S": ["c_top", "db_bp45_max_s", "db_bp90_max_s", "db_w_max_s", "db_box_max_s", "db_gauntlet_max_s"],
    }
    short_label = {
        "c_top": "40-yard\ntracked speed",
        "wr_go_max_s": "Go-route\ndrill",
        "wr_post_corner_max_s": "Post-corner\ndrill",
        "wr_slant_max_s": "Slant\ndrill",
        "wr_dagger_max_s": "Dagger\ndrill",
        "db_bp45_max_s": "45°\ntrans.",
        "db_bp90_max_s": "90°\nbreak",
        "db_w_max_s": "W-drill",
        "db_box_max_s": "Box",
        "db_gauntlet_max_s": "Gauntlet",
    }
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 5.1), sharey=True)
    for ax, pos in zip(axes, POS_ORDER):
        sub = phase2[(phase2["pos_group"] == pos) & (phase2["family"] == "primary")]
        sub = sub[sub["feature"].isin(keep_feats[pos])].copy()
        # Preserve the planned order.
        sub["_ord"] = sub["feature"].map({f: i for i, f in enumerate(keep_feats[pos])})
        sub = sub.dropna(subset=["_ord", "rho"]).sort_values("_ord")
        colors = [POS_COLOR[pos] if f == "c_top" else "#7A7A7A" for f in sub["feature"]]
        # Highlight 40 in the position color; drills in gray unless they beat it clearly.
        colors = []
        for _, r in sub.iterrows():
            if r["feature"] == "c_top":
                colors.append(POS_COLOR[pos])
            else:
                colors.append("#4C4C4C")
        xs = np.arange(len(sub))
        ax.bar(xs, sub["rho"], color=colors, width=0.72, zorder=3, edgecolor="white")
        ax.axhline(0, color="#888888", lw=0.8)
        for i, r in enumerate(sub.itertuples()):
            star = " ★" if (pd.notna(getattr(r, "sig_holm_05", np.nan)) and r.sig_holm_05) else ""
            y = r.rho
            ax.text(
                i, y + (0.03 if y >= 0 else -0.03),
                f"{y:+.2f}{star}\nn={int(r.n)}",
                ha="center", va="bottom" if y >= 0 else "top", fontsize=8,
            )
        ax.set_xticks(xs, [short_label.get(f, f) for f in sub["feature"]], fontsize=8)
        ax.set_title(POS_LABEL[pos], loc="left", fontweight="bold", color=POS_COLOR[pos])
        if pos == "WR":
            ax.set_ylabel("Spearman correlation with Sunday Speed")
        ax.set_ylim(-0.45, 0.95)
    fig.suptitle(
        "Which Combine drill predicts Sunday Speed? The 40 still leads for receivers.\n"
        "No DB skill drill clearly beats the 40 — and none of them transfer like WR speed does.",
        x=0.01, ha="left", fontweight="bold", fontsize=13, y=1.04,
    )
    fig.text(
        0.01, -0.06,
        "Bars show Spearman ρ between each Combine tracking feature and Sunday Speed (official definition). "
        "★ marks tests that remain significant after Holm correction across the primary family. "
        "The 40-yard bar is in color; skill drills are in gray.",
        fontsize=8, color="#555555", ha="left",
    )
    fig.tight_layout()
    p3 = FIGS / "fig3_phase2_drills.png"
    fig.savefig(p3, dpi=200, bbox_inches="tight")
    plt.close(fig)
    paths.append(p3)
    log(f"  wrote {p3}")
    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Sunday Speed player dataset and Phase 2 figures.")
    parser.add_argument("--rebuild-game", action="store_true", help="Re-stream game tracking even if a cache exists.")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    t_all = time.time()

    pl = pd.read_csv(DATA / "players.csv")
    roster = pl[pl["nfl_position"].isin(POS_MAP)].copy()
    ids = roster["nfl_id"]
    log(f"Roster: {len(roster)} WR/CB/FS/SS players "
        f"({(roster.nfl_position=='WR').sum()} WR, {(roster.nfl_position=='CB').sum()} CB, "
        f"{roster.nfl_position.isin(['FS','SS']).sum()} S)")

    combine = build_combine_features(ids)
    plays = build_game_play_speeds(ids, rebuild=args.rebuild_game)
    M = build_player_table(combine, plays)

    # Column order: identity, draft, combine official, 40 tracking, drills, game, outcomes.
    front = [
        "nfl_id", "display_name", "nfl_position", "pos_group", "draft_year",
        "draft_round", "draft_overall_pick", "pick", "college_name", "college_conference",
        "combine_height", "combine_weight", "official_ten_yd", "official_forty",
        "vertical", "broad_jump", "three_cone", "short_shuttle", "bench_reps",
        "ngs_athleticism_score", "ngs_college_production_score", "ngs_final_score",
        "c_top", "c_top_mph", "c_t90", "c_t10_derived", "c_t20_derived", "c_t40_derived",
        "c_40_accel", "c_40_brake",
        "sunday_speed", "sunday_speed_mph", "sunday_speed_window", "sunday_speed_legacy",
        "realization", "ssoe", "ssoe_mph", "translation_slope",
        "g_deep_p90", "g_deep_p90_reg", "g_cov_p90", "g_cov_p90_reg", "g_p95",
        "n_plays", "n_plays_reg", "n_deep", "n_deep_reg", "n_cov", "n_cov_reg",
        "sep_deep", "yac_oe", "tgt_rate", "tk_rate", "q4_ret",
        "start_rate", "snap_share",
        "career_games_active", "career_games_started",
        "career_offensive_snaps", "career_defensive_snaps", "career_special_teams_snaps",
        "ap_all_pro_1st_team", "ap_all_pro_2nd_team", "pro_bowl_original_ballot",
    ]
    front = [c for c in front if c in M.columns]
    rest = [c for c in M.columns if c not in front]
    M = M[front + rest]

    out_parq = OUT / "sunday_speed_players.parquet"
    out_csv = OUT / "sunday_speed_players.csv"
    M.to_parquet(out_parq, index=False)
    M.to_csv(out_csv, index=False)
    log(f"\nWrote {len(M)} player rows, {M.shape[1]} columns")
    log(f"  {out_parq}")
    log(f"  {out_csv}")
    # Sanity asserts
    assert len(M) == 219, f"expected 219 WR/CB/S rows, got {len(M)}"
    assert M["nfl_id"].is_unique
    assert set(M["pos_group"]) <= {"WR", "CB", "S"}
    log("  asserts passed (219 unique WR/CB/S rows)")

    ver = verify_headlines(M)
    phase2 = phase2_tests(M)
    results = pd.concat([ver, phase2], ignore_index=True, sort=False)
    results.to_csv(OUT / "phase2_tests.csv", index=False)

    with open(OUT / "translation_slopes.json") as f:
        slopes = json.load(f)

    log("\n==== Figures ====")
    make_figures(M, phase2, slopes)

    # Also dump a short verification text file for the writeup.
    with open(OUT / "verification.txt", "w") as f:
        f.write("Sunday Speed pipeline verification\n")
        f.write(f"rows={len(M)} cols={M.shape[1]}\n\n")
        f.write(results.to_string(index=False))
        f.write("\n")
    log(f"\nDone in {time.time()-t_all:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
