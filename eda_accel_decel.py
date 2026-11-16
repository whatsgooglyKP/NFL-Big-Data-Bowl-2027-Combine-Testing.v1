#!/usr/bin/env python3
"""Exploratory analysis of acceleration and deceleration for speed positions.

Build on explore_route_cod.py. Asks whether Combine start/stop profiles show
up on Sunday, whether those traits are stable, and whether a coach-readable
Brakes / Re-Burst score is worth carrying forward.

Speed positions: WR, CB, S (FS+SS). TE is a comparison group. RB is Sione
Vaki only (n=1) and is reported as an anecdote, not a sample.

Everything here is exploratory. Small official-agility samples are labeled.
This script does not push to git or Drive and does not touch Kaggle tokens.

Outputs under out/:
  eda_accel_players.csv
  eda_accel_translation.csv
  eda_accel_reliability.csv
  eda_accel_position.csv
  eda_accel_clusters.csv
  eda_accel_cluster_members.csv
  eda_accel_leaderboard.csv
  eda_accel_outcomes.csv
  eda_accel_vaki.csv
  figs/fig14_accel_decel_profiles.png
  figs/fig15_combine_vs_game_cod.png
  figs/fig16_archetypes.png
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"
FIGS.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT))
from explore_route_cod import (  # noqa: E402
    ACCEL_CLIP,
    BREAKING_ROUTES,
    DB_COD_DRILLS,
    WR_BREAK_DRILLS,
    detect_cuts,
    prepare_track,
)

YD_S_TO_MPH = 2.0455
YD_S2_TO_MPH_S = 2.0455  # 1 yd/s² = 2.0455 mph/s

SPEED_POS = {"WR", "CB", "FS", "SS", "TE", "RB"}
POS_GROUP = {"WR": "WR", "TE": "TE", "CB": "CB", "FS": "S", "SS": "S", "RB": "RB"}
LEAD_GROUPS = ["WR", "CB", "S"]
ALL_GROUPS = ["WR", "CB", "S", "TE"]

# Opportunity floors for a "usable Sunday profile"
FLOOR = {"WR": 20, "TE": 20, "CB": 30, "S": 30, "RB": 20}

POS_COLORS = {
    "WR": "#2C6EAB",
    "CB": "#2A9D6A",
    "S": "#E07B2A",
    "TE": "#7A7A7A",
    "RB": "#8B5A8B",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def spearman_safe(x, y) -> tuple[int, float, float]:
    m = pd.DataFrame({"x": x, "y": y}).dropna()
    n = int(len(m))
    if n < 5:
        return n, np.nan, np.nan
    rho, p = spearmanr(m["x"], m["y"])
    if not np.isfinite(rho):
        return n, np.nan, np.nan
    return n, float(rho), float(p)


def spearman_brown(r: float) -> float:
    if not np.isfinite(r) or r <= -0.999:
        return np.nan
    return float(2.0 * r / (1.0 + r))


def pct_rank(s: pd.Series) -> pd.Series:
    """0-100 percentile within the series; ties get the average rank."""
    return s.rank(method="average", pct=True) * 100.0


def style() -> None:
    plt.rcParams.update(
        {
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
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "figure.titlesize": 15,
            "font.family": "DejaVu Sans",
        }
    )


# ---------------------------------------------------------------------------
# Roster, outcomes, 40-yard burst, Combine cut distances
# ---------------------------------------------------------------------------
def load_players() -> pd.DataFrame:
    p = pd.read_csv(DATA / "players.csv")
    p["pos_group"] = p["nfl_position"].map(POS_GROUP)
    return p


def load_outcomes(players: pd.DataFrame) -> pd.DataFrame:
    """Yards per route, target rate, from regular-season standing plays."""
    log("Computing receiver outcomes from player_play …")
    usecols = [
        "game_id",
        "play_id",
        "nfl_id",
        "route_ran",
        "target",
        "rec_yards",
        "play_nullified_by_penalty",
        "separation_at_pass_forward",
        "cushion",
        "coverage_assignment",
    ]
    pp = pd.read_csv(DATA / "player_play.csv", usecols=usecols)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pen = pp["play_nullified_by_penalty"].astype(str).str.strip().str.upper()
    pp = pp[pen.eq("N") & pp["season_type"].eq("REG")]
    if pd.api.types.is_bool_dtype(pp["target"]):
        pp["is_target"] = pp["target"].fillna(False).astype(bool)
    else:
        pp["is_target"] = pp["target"].astype(str).str.upper().isin(["TRUE", "1", "T", "YES"])
    rec = pp[pp["route_ran"].notna()].copy()
    rec["rec_yards"] = pd.to_numeric(rec["rec_yards"], errors="coerce")
    out = (
        rec.groupby("nfl_id")
        .agg(
            n_routes=("play_id", "size"),
            n_targets=("is_target", "sum"),
            rec_yards=("rec_yards", "sum"),
        )
        .reset_index()
    )
    out["yards_per_route"] = out["rec_yards"] / out["n_routes"]
    out["target_rate"] = out["n_targets"] / out["n_routes"]
    return out


def forty_features() -> pd.DataFrame:
    """Time to 90% of top speed and peak accel, from the fastest 40 attempt."""
    log("Computing 40-yard burst features from combine_tracking …")
    ct = pd.read_csv(
        DATA / "combine_tracking.csv",
        usecols=["event_id", "nfl_id", "entity_type", "time", "drill_name", "s"],
    )
    f40 = ct[(ct.entity_type == "PLAYER") & (ct.drill_name == "FORTY_YARD_DASH")].copy()
    recs = []
    for (eid, nid), g in f40.groupby(["event_id", "nfl_id"], sort=False):
        g = prepare_track(g)
        s = g["s"].to_numpy(dtype=float)
        if len(s) < 8 or not np.isfinite(s).any():
            continue
        max_s = float(np.nanmax(s))
        hit = np.where(s >= 0.9 * max_s)[0]
        t90 = float(hit[0] / 10.0) if len(hit) else np.nan
        sa = g["signed_a"].to_numpy(dtype=float)
        finite = sa[np.isfinite(sa)]
        recs.append(
            {
                "event_id": eid,
                "nfl_id": int(nid),
                "c_40_max_s": max_s,
                "c_40_t90": t90,
                "c_40_peak_accel": float(np.nanmax(finite)) if finite.size else np.nan,
            }
        )
    att = pd.DataFrame(recs)
    # Fastest attempt (same convention as official Combine top speed)
    idx = att.groupby("nfl_id")["c_40_max_s"].idxmax()
    best = att.loc[idx].drop(columns=["event_id"])
    log(f"  40-yard burst for {len(best)} players")
    return best


def combine_cut_distance() -> pd.DataFrame:
    """Median decel distance (yards) into cuts, by role-drill family."""
    log("Computing Combine cut distances from tracking …")
    ct = pd.read_csv(
        DATA / "combine_tracking.csv",
        usecols=[
            "event_id",
            "nfl_id",
            "entity_type",
            "time",
            "drill_name",
            "x",
            "y",
            "s",
            "dir",
            "dis",
        ],
    )
    wanted = WR_BREAK_DRILLS | DB_COD_DRILLS | {"THREE_CONE_DRILL", "SHORT_SHUTTLE"}
    pl = ct[(ct.entity_type == "PLAYER") & (ct.drill_name.isin(wanted))].copy()
    recs = []
    for (eid, nid, dname), g in pl.groupby(["event_id", "nfl_id", "drill_name"], sort=False):
        min_entry = 1.5 if dname in {"THREE_CONE_DRILL", "SHORT_SHUTTLE"} else 2.5
        cuts = detect_cuts(g, min_entry_speed=min_entry)
        if not cuts:
            continue
        # Path length into each cut from a prepared track
        g2 = prepare_track(g)
        t0 = g2["_t"].iloc[0]
        trel = (g2["_t"] - t0).dt.total_seconds().to_numpy()
        x = g2["x"].to_numpy(dtype=float)
        y = g2["y"].to_numpy(dtype=float)
        dists = []
        for c in cuts:
            i1 = int(np.searchsorted(trel, c["t_break"] - 0.8))
            i2 = int(np.searchsorted(trel, c["t_break"]))
            if i2 <= i1 + 1:
                continue
            # Distance from the speed peak in that window to the break
            s = g2["s"].to_numpy(dtype=float)
            win = s[i1 : i2 + 1]
            if not np.isfinite(win).any():
                continue
            entry = i1 + int(np.nanargmax(win))
            dx = np.diff(x[entry : i2 + 1])
            dy = np.diff(y[entry : i2 + 1])
            if dx.size:
                dists.append(float(np.nansum(np.hypot(dx, dy))))
        if not dists:
            continue
        recs.append(
            {
                "nfl_id": int(nid),
                "drill_name": dname,
                "event_id": eid,
                "decel_dist": float(np.median(dists)),
            }
        )
    att = pd.DataFrame(recs)
    if att.empty:
        return pd.DataFrame({"nfl_id": pd.Series(dtype=int)})

    def pool(names, prefix):
        sub = att[att.drill_name.isin(names)]
        if sub.empty:
            return pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
        return (
            sub.groupby("nfl_id")
            .agg(**{f"{prefix}decel_dist": ("decel_dist", "median")})
            .reset_index()
        )

    out = pool(WR_BREAK_DRILLS, "wr_route_")
    out = out.merge(pool(DB_COD_DRILLS, "db_cod_"), on="nfl_id", how="outer")
    out = out.merge(pool({"THREE_CONE_DRILL"}, "tc_"), on="nfl_id", how="outer")
    out = out.merge(pool({"SHORT_SHUTTLE"}, "ss_"), on="nfl_id", how="outer")
    log(f"  cut distances for {out.nfl_id.nunique()} players")
    return out


# ---------------------------------------------------------------------------
# Game play-level peak accel / decel for split-half reliability
# ---------------------------------------------------------------------------
def game_play_peaks(pp_keys: pd.DataFrame) -> pd.DataFrame:
    """Per-play peak signed accel and decel on opportunity snaps."""
    cache = OUT / "eda_accel_game_plays.parquet"
    keys = pp_keys.drop_duplicates(["game_id", "play_id", "nfl_id"]).copy()
    log(f"Loading game tracking for {len(keys):,} opportunity play-players …")
    keys["_k"] = (
        keys["game_id"].astype("int64") * 10**12
        + keys["play_id"].astype("int64") * 10**6
        + keys["nfl_id"].astype("int64")
    )
    want = set(keys["_k"].tolist())
    usecols = ["game_id", "play_id", "nfl_id", "time", "s", "event"]
    parts = []
    n_in = 0
    for year in (2023, 2024, 2025):
        path = DATA / f"game_tracking_{year}.csv"
        log(f"  scanning {path.name} …")
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=750_000):
            n_in += len(chunk)
            kk = (
                chunk["game_id"].astype("int64") * 10**12
                + chunk["play_id"].astype("int64") * 10**6
                + chunk["nfl_id"].astype("int64")
            )
            keep = chunk.loc[kk.isin(want)]
            if len(keep):
                parts.append(keep)
        log(f"    kept so far {sum(len(p) for p in parts):,}")
    if not parts:
        return pd.DataFrame()
    tr = pd.concat(parts, ignore_index=True)
    log(f"  {len(tr):,} / {n_in:,} frames; aggregating play peaks …")
    tr = tr.sort_values(["game_id", "play_id", "nfl_id", "time"])
    tr["_t"] = pd.to_datetime(tr["time"], utc=True, format="ISO8601")
    dt = tr.groupby(["game_id", "play_id", "nfl_id"])["_t"].diff().dt.total_seconds()
    sa = tr["s"].diff() / dt
    tr["signed_a"] = sa.where(sa.abs() <= ACCEL_CLIP)
    ev = tr["event"].astype(str)
    tr["_event"] = ev.where(~ev.isin(["NA", "nan", "None", ""]), other=np.nan)

    # t90 from first frame (or ball_snap if present) to 90% of play max s
    recs = []
    for (gid, pid, nid), g in tr.groupby(["game_id", "play_id", "nfl_id"], sort=False):
        sa_v = g["signed_a"].to_numpy(dtype=float)
        s = g["s"].to_numpy(dtype=float)
        finite = sa_v[np.isfinite(sa_v)]
        peak_accel = float(np.nanmax(finite)) if finite.size else np.nan
        peak_decel = float(np.nanmin(finite)) if finite.size else np.nan
        max_s = float(np.nanmax(s)) if np.isfinite(s).any() else np.nan
        # start at snap if we have it
        snap = g["_event"].eq("ball_snap")
        if snap.any():
            g2 = g.loc[snap.idxmax() :]  # from snap onward
            s2 = g2["s"].to_numpy(dtype=float)
        else:
            s2 = s
        t90 = np.nan
        if np.isfinite(s2).any():
            mx = float(np.nanmax(s2))
            if mx >= 5.0:
                hit = np.where(s2 >= 0.9 * mx)[0]
                if len(hit):
                    t90 = float(hit[0] / 10.0)
        recs.append(
            {
                "game_id": gid,
                "play_id": pid,
                "nfl_id": nid,
                "play_peak_accel": peak_accel,
                "play_peak_decel": peak_decel,
                "play_peak_decel_mag": -peak_decel if np.isfinite(peak_decel) else np.nan,
                "play_max_s": max_s,
                "play_t90": t90,
                "n_frames": int(len(g)),
            }
        )
    plays = pd.DataFrame(recs)
    plays = plays.merge(keys.drop(columns=["_k"], errors="ignore"), on=["game_id", "play_id", "nfl_id"], how="left")
    plays.to_parquet(cache, index=False)
    log(f"  wrote {cache.name} ({len(plays):,} plays, {plays.nfl_id.nunique()} players)")
    return plays


def opportunity_keys(players: pd.DataFrame) -> pd.DataFrame:
    usecols = [
        "game_id",
        "play_id",
        "nfl_id",
        "route_ran",
        "play_nullified_by_penalty",
        "coverage_assignment",
    ]
    pp = pd.read_csv(DATA / "player_play.csv", usecols=usecols)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp.merge(players[["nfl_id", "nfl_position", "pos_group"]], on="nfl_id", how="left")
    pen = pp["play_nullified_by_penalty"].astype(str).str.strip().str.upper()
    pp = pp[pen.eq("N") & pp["season_type"].eq("REG")]
    cov = pp["coverage_assignment"].astype(str)
    in_cov = pp["coverage_assignment"].notna() & ~cov.isin(["nan", "NA", "NO_ASSIGNMENT", ""])
    wr = pp[pp["pos_group"].isin(["WR", "TE", "RB"]) & pp["route_ran"].notna()].copy()
    wr["opp_type"] = np.where(wr["route_ran"].isin(BREAKING_ROUTES), "break", "route")
    db = pp[pp["pos_group"].isin(["CB", "S"]) & in_cov].copy()
    db["opp_type"] = "coverage"
    keys = pd.concat(
        [
            wr[["game_id", "play_id", "nfl_id", "nfl_position", "pos_group", "opp_type", "route_ran"]],
            db[["game_id", "play_id", "nfl_id", "nfl_position", "pos_group", "opp_type"]],
        ],
        ignore_index=True,
    )
    # Vaki (RB) routes already included if present
    log(f"  opportunity keys: {len(keys):,}  WR/TE/RB routes={int((keys.opp_type!='coverage').sum()):,}  DB cov={int((keys.opp_type=='coverage').sum()):,}")
    return keys


def split_half(plays: pd.DataFrame, col: str, group_col: str = "pos_group") -> pd.DataFrame:
    rows = []
    use = plays.dropna(subset=[col]).copy()
    use = use.sort_values(["nfl_id", "game_id", "play_id"])
    use["half"] = use.groupby("nfl_id").cumcount() % 2
    # Also keep a breaking-route-only slice for WR/TE
    for label, sub in (
        ("all_opportunity", use),
        ("breaking_or_coverage", use[use["opp_type"].isin(["break", "coverage"])]),
    ):
        for grp, g in sub.groupby(group_col):
            floor = FLOOR.get(grp, 20)
            halves = (
                g.groupby(["nfl_id", "half"])[col]
                .median()
                .unstack("half")
            )
            halves = halves.rename(columns={0: "a", 1: "b"})
            for need in ("a", "b"):
                if need not in halves.columns:
                    halves[need] = np.nan
            counts = g.groupby("nfl_id").size()
            halves = halves.join(counts.rename("n_plays"), how="left")
            halves = halves[halves["n_plays"] >= floor]
            n, rho, p = spearman_safe(halves["a"], halves["b"])
            rows.append(
                {
                    "metric": col,
                    "slice": label,
                    "group": grp,
                    "n_players": n,
                    "min_plays": floor,
                    "rho": rho,
                    "p": p,
                    "spearman_brown": spearman_brown(rho),
                    "note": "even/odd play split; exploratory",
                }
            )
        # pooled speed positions (WR+CB+S) on this slice
        speed = sub[sub[group_col].isin(LEAD_GROUPS)]
        # per-player floor by their own group
        halves = (
            speed.groupby(["nfl_id", "half", group_col], observed=True)[col]
            .median()
            .reset_index()
        )
        # rebuild
        h = (
            speed.assign(_pg=speed[group_col])
            .merge(
                speed.groupby("nfl_id").size().rename("n_plays").reset_index(),
                on="nfl_id",
            )
        )
        # filter by own-group floor
        keep_ids = []
        for nid, gg in h.groupby("nfl_id"):
            pg = gg[group_col].iloc[0]
            if len(gg) >= FLOOR.get(pg, 20):
                keep_ids.append(nid)
        hs = (
            speed[speed.nfl_id.isin(keep_ids)]
            .groupby(["nfl_id", "half"])[col]
            .median()
            .unstack("half")
            .rename(columns={0: "a", 1: "b"})
        )
        for need in ("a", "b"):
            if need not in hs.columns:
                hs[need] = np.nan
        n, rho, p = spearman_safe(hs["a"], hs["b"])
        rows.append(
            {
                "metric": col,
                "slice": label,
                "group": "WR+CB+S",
                "n_players": n,
                "min_plays": "pos floor (20 WR / 30 DB)",
                "rho": rho,
                "p": p,
                "spearman_brown": spearman_brown(rho),
                "note": "even/odd play split; exploratory",
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Player profile table
# ---------------------------------------------------------------------------
def build_players(players, forty, dist, outcomes, comb, game, play_peaks) -> pd.DataFrame:
    d = players[players["pos_group"].isin(["WR", "CB", "S", "TE", "RB"])].copy()
    d = d.merge(comb, on="nfl_id", how="left", suffixes=("", "_c"))
    # comb already has display_name, position — drop dups
    drop_c = [c for c in d.columns if c.endswith("_c")]
    d = d.drop(columns=drop_c, errors="ignore")
    gdrop = [c for c in ["display_name", "draft_year", "nfl_position", "pos_group"] if c in game.columns]
    d = d.merge(game.drop(columns=gdrop), on="nfl_id", how="left")
    d = d.merge(forty, on="nfl_id", how="left")
    d = d.merge(dist, on="nfl_id", how="left")
    d = d.merge(outcomes, on="nfl_id", how="left")

    # Role-specific primary Combine / Sunday cut profiles
    is_off = d["pos_group"].isin(["WR", "TE"])
    is_db = d["pos_group"].isin(["CB", "S"])
    is_rb = d["pos_group"].eq("RB")

    def pick(mask, col_a, col_b):
        out = pd.Series(np.nan, index=d.index, dtype=float)
        if col_a in d.columns:
            out.loc[mask] = pd.to_numeric(d.loc[mask, col_a], errors="coerce")
        if col_b in d.columns:
            out.loc[~mask] = pd.to_numeric(d.loc[~mask, col_b], errors="coerce")
        return out

    d["c_decel"] = pick(is_off | is_rb, "wr_route_peak_decel_mag", "db_cod_peak_decel_mag")
    # RB tested in DB drills
    d.loc[is_rb, "c_decel"] = pd.to_numeric(d.loc[is_rb, "db_cod_peak_decel_mag"], errors="coerce")
    d["c_accel"] = pick(is_off, "wr_route_peak_accel", "db_cod_peak_accel")
    d.loc[is_rb, "c_accel"] = pd.to_numeric(d.loc[is_rb, "db_cod_peak_accel"], errors="coerce")
    d["c_speed_lost"] = pick(is_off, "wr_route_speed_lost", "db_cod_speed_lost")
    d.loc[is_rb, "c_speed_lost"] = pd.to_numeric(d.loc[is_rb, "db_cod_speed_lost"], errors="coerce")
    d["c_time_through"] = pick(is_off, "wr_route_time_through", "db_cod_time_through")
    d.loc[is_rb, "c_time_through"] = pd.to_numeric(d.loc[is_rb, "db_cod_time_through"], errors="coerce")
    d["c_decel_dist"] = pick(is_off, "wr_route_decel_dist", "db_cod_decel_dist")
    d.loc[is_rb, "c_decel_dist"] = pd.to_numeric(d.loc[is_rb, "db_cod_decel_dist"], errors="coerce")
    d["c_n_attempts"] = pick(is_off, "wr_route_n_attempts", "db_cod_n_attempts")
    d.loc[is_rb, "c_n_attempts"] = pd.to_numeric(d.loc[is_rb, "db_cod_n_attempts"], errors="coerce")
    d["c_n_cuts"] = pick(is_off, "wr_route_n_cuts", "db_cod_n_cuts")
    d.loc[is_rb, "c_n_cuts"] = pd.to_numeric(d.loc[is_rb, "db_cod_n_cuts"], errors="coerce")

    d["g_decel"] = pick(is_off, "game_brk_peak_decel_mag", "game_db_peak_decel_mag")
    d["g_accel"] = pick(is_off, "game_brk_peak_accel", "game_db_peak_accel")
    d["g_speed_lost"] = pick(is_off, "game_brk_speed_lost", "game_db_speed_lost")
    d["g_time_through"] = pick(is_off, "game_brk_time_through", "game_db_time_through")
    d["g_n_plays"] = pick(is_off, "game_brk_n_plays", "game_db_n_plays")
    d["g_n_cuts"] = pick(is_off, "game_brk_n_cuts", "game_db_n_cuts")

    d["c_brakes_gas"] = d["c_decel"] / d["c_accel"]
    d["g_brakes_gas"] = d["g_decel"] / d["g_accel"]

    # Play-level peaks (whole-play, for reliability and a companion trait)
    if play_peaks is not None and len(play_peaks):
        # Use breaking routes for WR/TE, coverage for DBs
        off_pl = play_peaks[play_peaks["opp_type"].isin(["break", "route"])]
        # Prefer breaking when the player has enough of them
        def player_play_agg(peaks: pd.DataFrame) -> pd.DataFrame:
            rows = []
            for nid, g in peaks.groupby("nfl_id"):
                br = g[g["opp_type"].eq("break")]
                cv = g[g["opp_type"].eq("coverage")]
                rt = g[g["opp_type"].isin(["break", "route"])]
                # choose slice
                pos = g["pos_group"].iloc[0] if "pos_group" in g.columns else None
                if pos in {"WR", "TE", "RB"}:
                    use = br if len(br) >= 10 else rt
                    slice_name = "break" if len(br) >= 10 else "route"
                else:
                    use = cv if len(cv) else g
                    slice_name = "coverage"
                rows.append(
                    {
                        "nfl_id": nid,
                        "g_play_decel": float(use["play_peak_decel_mag"].median()),
                        "g_play_accel": float(use["play_peak_accel"].median()),
                        "g_play_max_s": float(use["play_max_s"].median()),
                        "g_play_t90": float(use["play_t90"].median()) if use["play_t90"].notna().any() else np.nan,
                        "g_play_n": int(len(use)),
                        "g_play_slice": slice_name,
                    }
                )
            return pd.DataFrame(rows)

        pagg = player_play_agg(play_peaks)
        d = d.merge(pagg, on="nfl_id", how="left")

    d["g_floor"] = d["pos_group"].map(FLOOR)
    d["usable_sunday"] = d["g_n_plays"].fillna(0) >= d["g_floor"].fillna(20)
    d["has_combine_cod"] = d["c_decel"].notna() & d["c_accel"].notna()

    # 0-100 percentiles within position (Combine and Sunday separately)
    for grp, g in d.groupby("pos_group"):
        ix = g.index
        for src, cols, better_high in (
            (
                "c",
                {
                    "brakes": ("c_decel", True),
                    "reburst": ("c_accel", True),
                    "time": ("c_time_through", False),  # shorter is snappier
                    "burst40": ("c_40_t90", False),
                },
                None,
            ),
        ):
            pass
        # Combine scores: everyone with the feature
        d.loc[ix, "combine_brakes"] = pct_rank(g["c_decel"])
        d.loc[ix, "combine_reburst"] = pct_rank(g["c_accel"])
        d.loc[ix, "combine_snap"] = 100.0 - pct_rank(g["c_time_through"])  # higher = snappier turn
        d.loc[ix, "combine_burst"] = 100.0 - pct_rank(g["c_40_t90"])
        # Sunday scores: only players meeting the play floor, else NA
        usable = g[g["usable_sunday"]]
        if len(usable):
            d.loc[usable.index, "sunday_brakes"] = pct_rank(usable["g_decel"])
            d.loc[usable.index, "sunday_reburst"] = pct_rank(usable["g_accel"])
            d.loc[usable.index, "sunday_snap"] = 100.0 - pct_rank(usable["g_time_through"])
        # Play-peak companions
        if "g_play_decel" in g.columns:
            u2 = g[g["g_play_n"].fillna(0) >= FLOOR.get(grp, 20)]
            if len(u2):
                d.loc[u2.index, "sunday_play_brakes"] = pct_rank(u2["g_play_decel"])
                d.loc[u2.index, "sunday_play_reburst"] = pct_rank(u2["g_play_accel"])

    # mph/s companions for display
    for col in ["c_decel", "c_accel", "g_decel", "g_accel", "c_40_peak_accel"]:
        if col in d.columns:
            d[col + "_mphs"] = d[col] * YD_S2_TO_MPH_S
    if "c_40_max_s" in d.columns:
        d["c_40_max_s_mph"] = d["c_40_max_s"] * YD_S_TO_MPH
    if "c_speed_lost" in d.columns:
        d["c_speed_lost_mph"] = d["c_speed_lost"] * YD_S_TO_MPH
    if "g_speed_lost" in d.columns:
        d["g_speed_lost_mph"] = d["g_speed_lost"] * YD_S_TO_MPH

    return d


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------
def translation_table(d: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("c_decel", "g_decel", "Brakes (peak decel mag)"),
        ("c_accel", "g_accel", "Re-Burst (peak accel out of cuts)"),
        ("c_speed_lost", "g_speed_lost", "Speed lost through the cut"),
        ("c_time_through", "g_time_through", "Time through the turn"),
        ("c_brakes_gas", "g_brakes_gas", "Brakes-to-gas ratio"),
        ("c_40_t90", "g_play_t90", "Time to 90% top speed"),
        ("c_40_peak_accel", "g_play_accel", "Peak accel (40 vs play peak)"),
        ("c_decel", "g_play_decel", "Combine cut brakes vs Sunday play-peak brakes"),
        ("c_accel", "g_play_accel", "Combine cut Re-Burst vs Sunday play-peak accel"),
    ]
    rows = []
    for grp in ALL_GROUPS + ["WR+CB+S"]:
        if grp == "WR+CB+S":
            sub = d[d.pos_group.isin(LEAD_GROUPS) & d.usable_sunday]
        else:
            sub = d[(d.pos_group == grp) & (d.usable_sunday if grp != "TE" else d.usable_sunday)]
        for x, y, label in pairs:
            if x not in sub.columns or y not in sub.columns:
                continue
            n, rho, p = spearman_safe(sub[x], sub[y])
            rows.append(
                {
                    "group": grp,
                    "x": x,
                    "y": y,
                    "label": label,
                    "n": n,
                    "rho": rho,
                    "p": p,
                    "note": "exploratory; unadjusted; Sunday side uses players meeting the play floor",
                }
            )
    return pd.DataFrame(rows)


def position_table(d: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        ("c_decel", "Combine peak decel (yd/s²)"),
        ("c_accel", "Combine peak accel (yd/s²)"),
        ("c_brakes_gas", "Combine brakes/gas"),
        ("c_time_through", "Combine time through turn (s)"),
        ("c_speed_lost", "Combine speed lost (yd/s)"),
        ("c_decel_dist", "Combine decel distance (yd)"),
        ("c_40_t90", "40-yard time to 90% top speed (s)"),
        ("c_40_peak_accel", "40-yard peak accel (yd/s²)"),
        ("g_decel", "Sunday peak decel (yd/s²)"),
        ("g_accel", "Sunday peak accel (yd/s²)"),
        ("g_brakes_gas", "Sunday brakes/gas"),
        ("g_time_through", "Sunday time through turn (s)"),
        ("g_speed_lost", "Sunday speed lost (yd/s)"),
        ("g_play_decel", "Sunday play-peak decel (yd/s²)"),
        ("g_play_accel", "Sunday play-peak accel (yd/s²)"),
        ("g_play_t90", "Sunday time to 90% play top speed (s)"),
    ]
    rows = []
    for grp in ALL_GROUPS:
        sub = d[d.pos_group == grp]
        sun = sub[sub.usable_sunday]
        for col, label in metrics:
            if col not in d.columns:
                continue
            src = sun if col.startswith("g_") else sub
            s = pd.to_numeric(src[col], errors="coerce").dropna()
            rows.append(
                {
                    "group": grp,
                    "metric": col,
                    "label": label,
                    "n": int(len(s)),
                    "mean": float(s.mean()) if len(s) else np.nan,
                    "sd": float(s.std()) if len(s) else np.nan,
                    "p25": float(s.quantile(0.25)) if len(s) else np.nan,
                    "median": float(s.median()) if len(s) else np.nan,
                    "p75": float(s.quantile(0.75)) if len(s) else np.nan,
                    "p10": float(s.quantile(0.10)) if len(s) else np.nan,
                    "p90": float(s.quantile(0.90)) if len(s) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def cluster_players(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """K-means on within-position z-scores of Combine cut + 40 burst features."""
    feats = ["c_decel", "c_accel", "c_time_through", "c_brakes_gas", "c_40_t90"]
    feat_labels = {
        "c_decel": "Brakes",
        "c_accel": "Re-Burst",
        "c_time_through": "Time through turn",
        "c_brakes_gas": "Brakes/gas",
        "c_40_t90": "40 burst (t90)",
    }
    use = d[d.pos_group.isin(LEAD_GROUPS) & d[feats].notna().all(axis=1)].copy()
    # Within-position z so we cluster movement style, not position
    Z = pd.DataFrame(index=use.index)
    for f in feats:
        Z[f] = use.groupby("pos_group")[f].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    X = Z[feats].to_numpy()
    # Choose k by silhouette, 2–4
    best_k, best_sc, best_lab = 3, -1, None
    for k in (2, 3, 4):
        km = KMeans(n_clusters=k, random_state=2027, n_init=25)
        lab = km.fit_predict(X)
        sc = float(silhouette_score(X, lab))
        log(f"  k={k} silhouette={sc:.3f}")
        if sc > best_sc:
            best_k, best_sc, best_lab = k, sc, lab
    # Prefer k=3 if it is close (more readable archetypes)
    km3 = KMeans(n_clusters=3, random_state=2027, n_init=25)
    lab3 = km3.fit_predict(X)
    sc3 = float(silhouette_score(X, lab3))
    if best_k != 3 and (best_sc - sc3) < 0.03:
        best_k, best_sc, best_lab = 3, sc3, lab3
        log(f"  preferring k=3 (silhouette {sc3:.3f}, close to best)")
    use["cluster"] = best_lab

    # Centroids in z-space
    cents = Z[feats].copy()
    cents["cluster"] = use["cluster"].to_numpy()
    cent = cents.groupby("cluster")[feats].mean()

    def auto_label(row) -> str:
        # row is z-score centroid
        decel, accel, tthru, ratio, t90 = row[feats].to_numpy()
        tags = []
        if decel >= 0.45 and accel <= -0.25:
            tags.append("heavy brakes, slow restart")
        elif accel >= 0.45 and decel <= -0.25:
            tags.append("gas-first re-accelerators")
        elif decel >= 0.35 and accel >= 0.35:
            tags.append("explosive two-way cutters")
        elif tthru >= 0.45:
            tags.append("long, gradual turns")
        elif tthru <= -0.45:
            tags.append("snappy, short turns")
        if t90 <= -0.45:
            tags.append("fast 40 burst")
        elif t90 >= 0.45:
            tags.append("slower to top speed")
        if ratio >= 0.45 and "heavy brakes" not in " ".join(tags):
            tags.append("brake-dominant")
        if ratio <= -0.45 and "gas-first" not in " ".join(tags):
            tags.append("gas-dominant")
        if not tags:
            tags.append("balanced cutters")
        # unique-ify
        seen = []
        for t in tags:
            if t not in seen:
                seen.append(t)
        return "; ".join(seen[:2])

    labels = {int(i): auto_label(cent.loc[i]) for i in cent.index}
    # Ensure unique labels
    used = {}
    for i, lab in labels.items():
        if lab in used:
            labels[i] = f"{lab} ({i})"
        used[labels[i]] = i
    use["archetype"] = use["cluster"].map(labels)

    # Example players: 3 closest to each centroid (Euclidean in z-space), plus the most extreme
    members_rows = []
    for cid, lab in labels.items():
        idx = use.index[use.cluster == cid]
        z = Z.loc[idx, feats].to_numpy()
        cvec = cent.loc[cid, feats].to_numpy()
        dist = np.linalg.norm(z - cvec, axis=1)
        order = np.argsort(dist)
        close_idx = idx.to_numpy()[order[:3]]
        # also the most extreme on the cluster's signature feature
        sig = cent.loc[cid, feats].abs().idxmax()
        direction = 1 if cent.loc[cid, sig] >= 0 else -1
        extreme_id = (Z.loc[idx, sig] * direction).idxmax()
        picks = list(close_idx)
        if extreme_id not in picks:
            picks.append(extreme_id)
        for rank, ix in enumerate(picks, start=1):
            r = use.loc[ix]
            members_rows.append(
                {
                    "cluster": int(cid),
                    "archetype": lab,
                    "role": "centroid-near" if rank <= 3 else "signature-extreme",
                    "rank": rank,
                    "nfl_id": int(r.nfl_id),
                    "display_name": r.display_name,
                    "pos_group": r.pos_group,
                    "draft_year": int(r.draft_year) if pd.notna(r.draft_year) else np.nan,
                    "c_decel": r.c_decel,
                    "c_accel": r.c_accel,
                    "c_time_through": r.c_time_through,
                    "c_brakes_gas": r.c_brakes_gas,
                    "c_40_t90": r.c_40_t90,
                    "combine_brakes": r.get("combine_brakes", np.nan),
                    "combine_reburst": r.get("combine_reburst", np.nan),
                }
            )

    cluster_info = []
    for cid, lab in labels.items():
        sub = use[use.cluster == cid]
        row = {
            "cluster": int(cid),
            "archetype": lab,
            "n": int(len(sub)),
            "silhouette_k": best_k,
            "silhouette": best_sc,
            "n_WR": int((sub.pos_group == "WR").sum()),
            "n_CB": int((sub.pos_group == "CB").sum()),
            "n_S": int((sub.pos_group == "S").sum()),
            "example_players": ", ".join(
                use.loc[
                    [r["nfl_id"] for r in members_rows if r["cluster"] == cid][:3]
                    and use.nfl_id.isin([m["nfl_id"] for m in members_rows if m["cluster"] == cid][:3]),
                    "display_name",
                ].tolist()
            )
            if False
            else ", ".join(
                [
                    f"{m['display_name']} ({m['pos_group']})"
                    for m in members_rows
                    if m["cluster"] == cid and m["role"] == "centroid-near"
                ][:3]
            ),
        }
        for f in feats:
            row[f"z_{f}"] = float(cent.loc[cid, f])
            row[f"mean_{f}"] = float(sub[f].mean())
        cluster_info.append(row)

    # Attach to a slim member table of everyone
    everyone = use[
        [
            "nfl_id",
            "display_name",
            "pos_group",
            "draft_year",
            "cluster",
            "archetype",
            "c_decel",
            "c_accel",
            "c_time_through",
            "c_brakes_gas",
            "c_40_t90",
        ]
    ].copy()
    # PCA coords for the figure
    pca = PCA(n_components=2, random_state=2027)
    xy = pca.fit_transform(X)
    everyone["pc1"] = xy[:, 0]
    everyone["pc2"] = xy[:, 1]
    everyone.attrs["explained"] = pca.explained_variance_ratio_.tolist()

    info = pd.DataFrame(cluster_info)
    members = pd.DataFrame(members_rows)
    log(f"  clustered {len(use)} players into k={best_k} (silhouette {best_sc:.3f})")
    for _, r in info.iterrows():
        log(f"    cluster {r.cluster} n={r.n}  {r.archetype}  e.g. {r.example_players}")
    return everyone, info, members, pca.explained_variance_ratio_


def outcome_links(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    wr = d[(d.pos_group == "WR") & d.usable_sunday]
    te = d[(d.pos_group == "TE") & d.usable_sunday]
    cb = d[(d.pos_group == "CB") & d.usable_sunday]
    s = d[(d.pos_group == "S") & d.usable_sunday]
    tests = [
        (wr, "WR", ["combine_brakes", "combine_reburst", "combine_snap", "sunday_brakes", "sunday_reburst", "sunday_snap", "c_decel", "c_accel", "g_decel", "g_accel"],
         ["sep_all_mean", "sep_tgt_mean", "sep_brk_mean", "yards_per_route", "target_rate"]),
        (te, "TE", ["combine_brakes", "combine_reburst", "sunday_brakes", "sunday_reburst", "c_decel", "g_decel"],
         ["sep_all_mean", "sep_tgt_mean", "yards_per_route", "target_rate"]),
        (cb, "CB", ["combine_brakes", "combine_reburst", "sunday_brakes", "sunday_reburst", "c_decel", "c_accel", "g_decel", "g_accel"],
         ["cushion_mean"]),
        (s, "S", ["combine_brakes", "combine_reburst", "sunday_brakes", "sunday_reburst", "c_decel", "c_accel", "g_decel", "g_accel"],
         ["cushion_mean"]),
    ]
    for sub, grp, xs, ys in tests:
        for x in xs:
            for y in ys:
                if x not in sub.columns or y not in sub.columns:
                    continue
                n, rho, p = spearman_safe(sub[x], sub[y])
                rows.append(
                    {
                        "group": grp,
                        "x": x,
                        "y": y,
                        "n": n,
                        "rho": rho,
                        "p": p,
                        "note": "secondary / exploratory; unadjusted; not a success claim",
                    }
                )
    return pd.DataFrame(rows)


def leaderboard(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    score_cols = [
        ("combine_brakes", "Combine Brakes", "c_decel", "has_combine_cod"),
        ("combine_reburst", "Combine Re-Burst", "c_accel", "has_combine_cod"),
        ("sunday_brakes", "Sunday Brakes", "g_decel", "usable_sunday"),
        ("sunday_reburst", "Sunday Re-Burst", "g_accel", "usable_sunday"),
    ]
    for grp in ALL_GROUPS:
        sub = d[d.pos_group == grp]
        for scol, slabel, raw, flag in score_cols:
            ss = sub[sub[flag] & sub[scol].notna()].copy()
            if ss.empty:
                continue
            top = ss.nlargest(5, scol)
            bot = ss.nsmallest(5, scol)
            for kind, chunk in (("top", top), ("bottom", bot)):
                for rank, (_, r) in enumerate(chunk.iterrows(), start=1):
                    rows.append(
                        {
                            "group": grp,
                            "score": slabel,
                            "score_col": scol,
                            "end": kind,
                            "rank": rank,
                            "nfl_id": int(r.nfl_id),
                            "display_name": r.display_name,
                            "draft_year": int(r.draft_year) if pd.notna(r.draft_year) else np.nan,
                            "college_name": r.get("college_name", np.nan),
                            "percentile": float(r[scol]),
                            "raw_yd_s2": float(r[raw]) if pd.notna(r[raw]) else np.nan,
                            "raw_mph_s": float(r[raw] * YD_S2_TO_MPH_S) if pd.notna(r[raw]) else np.nan,
                            "g_n_plays": r.get("g_n_plays", np.nan),
                            "c_n_attempts": r.get("c_n_attempts", np.nan),
                        }
                    )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig14(d: pd.DataFrame, pos: pd.DataFrame) -> Path:
    style()
    fig, axes = plt.subplots(2, 3, figsize=(15.4, 9.4))
    fig.suptitle(
        "Exploratory — How speed positions start and stop",
        fontweight="bold",
        y=0.995,
    )
    fig.text(
        0.5,
        0.965,
        "Peak deceleration into cuts (Brakes) and peak acceleration out of them (Re-Burst). "
        "Combine skill drills vs Sunday breaking routes / coverage. Units: yd/s².",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    order = ALL_GROUPS
    palette = [POS_COLORS[g] for g in order]

    def panel(ax, col, title, sunday=False, ylabel="yd/s²"):
        if sunday:
            use = d[d.usable_sunday & d.pos_group.isin(order)].copy()
        else:
            use = d[d.has_combine_cod & d.pos_group.isin(order)].copy()
        use = use[use[col].notna()]
        sns.violinplot(
            data=use,
            x="pos_group",
            y=col,
            hue="pos_group",
            order=order,
            palette=POS_COLORS,
            inner="quartile",
            cut=0,
            ax=ax,
            legend=False,
        )
        sns.stripplot(
            data=use,
            x="pos_group",
            y=col,
            order=order,
            color="#222222",
            size=2.0,
            alpha=0.25,
            ax=ax,
            jitter=0.22,
        )
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        # n annotations
        for i, g in enumerate(order):
            n = int((use.pos_group == g).sum())
            ymin, ymax = ax.get_ylim()
            ax.text(i, ymin + 0.04 * (ymax - ymin), f"n={n}", ha="center", fontsize=8, color="#444")

    panel(axes[0, 0], "c_decel", "Combine Brakes\n(peak decel into cuts)")
    panel(axes[0, 1], "c_accel", "Combine Re-Burst\n(peak accel out of cuts)")
    panel(axes[0, 2], "c_brakes_gas", "Combine brakes / gas ratio", ylabel="ratio")
    panel(axes[1, 0], "g_decel", "Sunday Brakes\n(breaking routes / coverage)", sunday=True)
    panel(axes[1, 1], "g_accel", "Sunday Re-Burst\n(breaking routes / coverage)", sunday=True)
    panel(axes[1, 2], "g_time_through", "Sunday time through the turn", sunday=True, ylabel="seconds")

    axes[0, 2].axhline(1.0, color="#888", lw=0.8, ls="--")
    fig.text(
        0.01,
        0.01,
        "Exploratory. Sunday panels use players with ≥20 breaking-route plays (WR/TE) or ≥30 coverage plays (CB/S). "
        "Higher Brakes = harder stop; higher Re-Burst = quicker restart; ratio > 1 means the brakes are stronger than the gas.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    path = FIGS / "fig14_accel_decel_profiles.png"
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def fig15(d: pd.DataFrame, trans: pd.DataFrame) -> Path:
    style()
    fig, axes = plt.subplots(2, 3, figsize=(15.4, 9.2))
    fig.suptitle(
        "Exploratory — Do Combine start/stop profiles show up on Sunday?",
        fontweight="bold",
        y=0.995,
    )
    fig.text(
        0.5,
        0.965,
        "Each point is a player who has both a Combine skill-drill profile and enough Sunday plays. "
        "Spearman ρ is unadjusted.",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    rows = [
        ("c_decel", "g_decel", "Brakes  (peak decel, yd/s²)", "Combine Brakes", "Sunday Brakes"),
        ("c_accel", "g_accel", "Re-Burst  (peak accel, yd/s²)", "Combine Re-Burst", "Sunday Re-Burst"),
    ]
    for r, (x, y, row_title, xl, yl) in enumerate(rows):
        for c, grp in enumerate(LEAD_GROUPS):
            ax = axes[r, c]
            sub = d[(d.pos_group == grp) & d.usable_sunday].dropna(subset=[x, y])
            ax.scatter(
                sub[x],
                sub[y],
                s=28,
                c=POS_COLORS[grp],
                alpha=0.75,
                edgecolors="white",
                linewidths=0.4,
            )
            if len(sub) >= 5:
                # simple trend
                z = np.polyfit(sub[x], sub[y], 1)
                xs = np.linspace(sub[x].min(), sub[x].max(), 50)
                ax.plot(xs, np.polyval(z, xs), color="#333", lw=1.0, alpha=0.7)
            n, rho, p = spearman_safe(sub[x], sub[y])
            ptxt = "n.s." if (not np.isfinite(p) or p >= 0.05) else f"p={p:.3f}"
            if np.isfinite(p) and p < 0.001:
                ptxt = "p<0.001"
            rhotxt = "NA" if not np.isfinite(rho) else f"ρ={rho:.2f}"
            ax.set_title(f"{grp}  {row_title.split('  ')[0]}\n{rhotxt}   n={n}   {ptxt}", fontsize=11)
            ax.set_xlabel(xl)
            if c == 0:
                ax.set_ylabel(yl)
            else:
                ax.set_ylabel("")
    fig.text(
        0.01,
        0.01,
        "Exploratory, unadjusted. A shallow (or flat) cloud means the Combine cut profile does not strongly predict "
        "the same player's Sunday cut profile. Floors: ≥20 WR breaking-route plays, ≥30 CB/S coverage plays.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    path = FIGS / "fig15_combine_vs_game_cod.png"
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def fig16(everyone: pd.DataFrame, info: pd.DataFrame, members: pd.DataFrame, evr: np.ndarray) -> Path:
    style()
    fig = plt.figure(figsize=(15.6, 8.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    fig.suptitle(
        "Exploratory — Combine movement archetypes among WR, CB, and safeties",
        fontweight="bold",
        y=0.98,
    )

    cluster_colors = {0: "#2C6EAB", 1: "#E07B2A", 2: "#2A9D6A", 3: "#8B5A8B"}
    markers = {"WR": "o", "CB": "s", "S": "^"}
    for grp, m in markers.items():
        sub = everyone[everyone.pos_group == grp]
        for cid, g in sub.groupby("cluster"):
            ax0.scatter(
                g.pc1,
                g.pc2,
                s=36,
                c=cluster_colors.get(int(cid), "#555"),
                marker=m,
                alpha=0.8,
                edgecolors="white",
                linewidths=0.4,
                label=f"{g.archetype.iloc[0]} · {grp}" if False else None,
            )
    # legend: clusters + positions
    from matplotlib.lines import Line2D
    handles = []
    for _, r in info.sort_values("cluster").iterrows():
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color="white",
                markerfacecolor=cluster_colors.get(int(r.cluster), "#555"),
                markersize=9,
                label=f"{r.archetype}  (n={int(r.n)})",
            )
        )
    for grp, m in markers.items():
        handles.append(
            Line2D(
                [0],
                [0],
                marker=m,
                color="white",
                markerfacecolor="#444444",
                markersize=8,
                label=grp,
            )
        )
    ax0.legend(handles=handles, frameon=False, fontsize=8, loc="best")
    ax0.set_xlabel(f"PC1 ({100*evr[0]:.0f}% of style variance)")
    ax0.set_ylabel(f"PC2 ({100*evr[1]:.0f}%)")
    ax0.set_title("Within-position z-scores, viewed in 2-D")

    # Annotate a few peripheral / signature names so labels don't pile up.
    ev = everyone.set_index("nfl_id")
    picks = []
    for cid, g in members.drop_duplicates("nfl_id").groupby("cluster"):
        ext = g[g.role == "signature-extreme"]
        near = g[g.role == "centroid-near"].copy()
        if len(near):
            near = near[near.nfl_id.isin(ev.index)].copy()
            if len(near):
                near["r"] = [
                    abs(float(ev.loc[i, "pc1"])) + abs(float(ev.loc[i, "pc2"]))
                    for i in near.nfl_id
                ]
                picks.append(near.sort_values("r", ascending=False).iloc[0])
        if len(ext):
            picks.append(ext.iloc[0])
    # Recognizable extra names if they sit away from the origin
    famous = {
        "Jaxon Smith-Njigba",
        "Jordan Addison",
        "Ladd McConkey",
        "Brian Branch",
        "Quinyon Mitchell",
        "Cedric Tillman",
    }
    extra = everyone[everyone.display_name.isin(famous)].copy()
    extra["r"] = extra.pc1.abs() + extra.pc2.abs()
    for _, r in extra.iterrows():
        if r.r >= 0.8:
            picks.append(r)
    seen = set()
    # Stagger offsets so nearby names don't collide
    offsets = [(6, 8), (-52, 8), (6, -12), (-52, -12), (8, 16), (-60, 16), (8, -20)]
    oi = 0
    for r in picks:
        nid = int(r.nfl_id) if "nfl_id" in getattr(r, "index", []) or hasattr(r, "nfl_id") else None
        if nid is None or nid in seen or nid not in ev.index:
            continue
        seen.add(nid)
        pnt = ev.loc[nid]
        short = str(r.display_name).split(" ")[-1]
        grp = r.pos_group if hasattr(r, "pos_group") else pnt.pos_group
        dx, dy = offsets[oi % len(offsets)]
        oi += 1
        ax0.annotate(
            f"{short} ({grp})",
            (pnt.pc1, pnt.pc2),
            textcoords="offset points",
            xytext=(dx, dy),
            fontsize=7.5,
            color="#222",
            arrowprops=dict(arrowstyle="-", color="#888888", lw=0.5),
        )

    # Grouped bar of centroid z-scores
    feat_order = ["c_decel", "c_accel", "c_time_through", "c_brakes_gas", "c_40_t90"]
    feat_lab = ["Brakes", "Re-Burst", "Time through\nturn (higher=\nlonger)", "Brakes/gas", "40 t90\n(higher=\nslower burst)"]
    x = np.arange(len(feat_order))
    width = 0.22 if len(info) > 3 else 0.25
    ncl = len(info)
    offsets = (np.arange(ncl) - (ncl - 1) / 2) * width
    for off, (_, r) in zip(offsets, info.sort_values("cluster").iterrows()):
        vals = [r[f"z_{f}"] for f in feat_order]
        ax1.bar(
            x + off,
            vals,
            width=width * 0.95,
            color=cluster_colors.get(int(r.cluster), "#555"),
            label=f"{r.archetype}  n={int(r.n)}",
        )
    ax1.axhline(0, color="#666", lw=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(feat_lab, fontsize=8.5)
    ax1.set_ylabel("Within-position z-score")
    ax1.set_title("What each archetype looks like")
    ax1.legend(frameon=False, fontsize=7.5, loc="best")

    fig.text(
        0.01,
        0.015,
        "Exploratory k-means on within-position z-scores of Combine cut Brakes, Re-Burst, time through the turn, "
        "brakes/gas ratio, and 40-yard time to 90% top speed. Clustering on Combine data so limited Sunday playing time "
        "does not define the groups. Labels are auto-assigned from cluster centers.",
        fontsize=8,
        color="#555555",
        wrap=True,
    )
    fig.subplots_adjust(left=0.06, right=0.99, top=0.88, bottom=0.12, wspace=0.28)
    path = FIGS / "fig16_archetypes.png"
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Vaki anecdote
# ---------------------------------------------------------------------------
def vaki_row(d: pd.DataFrame) -> pd.DataFrame:
    v = d[d.display_name.str.contains("Vaki", case=False, na=False)].copy()
    if v.empty:
        v = d[d.nfl_id == 57253].copy()
    keep = [
        "nfl_id",
        "display_name",
        "draft_year",
        "nfl_position",
        "combine_position",
        "forty",
        "ten_yd_split",
        "vertical",
        "broad_jump",
        "c_decel",
        "c_accel",
        "c_brakes_gas",
        "c_time_through",
        "c_speed_lost",
        "c_decel_dist",
        "c_n_attempts",
        "c_n_cuts",
        "c_40_t90",
        "c_40_peak_accel",
        "c_40_max_s",
        "g_n_plays",
        "n_routes",
        "n_targets",
        "yards_per_route",
    ]
    keep = [c for c in keep if c in v.columns]
    return v[keep]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    t0 = time.time()
    players = load_players()
    comb = pd.read_csv(OUT / "route_cod_combine_player.csv")
    game = pd.read_csv(OUT / "route_cod_game_player.csv")
    # college is on players
    outcomes = load_outcomes(players)
    forty = forty_features()
    dist = combine_cut_distance()

    cache = OUT / "eda_accel_game_plays.parquet"
    keys = opportunity_keys(players)
    if cache.exists():
        log(f"Loading cached {cache.name} …")
        play_peaks = pd.read_parquet(cache)
        # Rebuild if the cache is from a smaller earlier draft
        if play_peaks.nfl_id.nunique() < 50:
            play_peaks = game_play_peaks(keys)
    else:
        play_peaks = game_play_peaks(keys)

    # Split-half reliability
    log("Split-half reliability …")
    rel_parts = []
    if play_peaks is not None and len(play_peaks):
        for col in ["play_peak_decel_mag", "play_peak_accel", "play_max_s", "play_t90"]:
            if col in play_peaks.columns:
                rel_parts.append(split_half(play_peaks, col))
    rel = pd.concat(rel_parts, ignore_index=True) if rel_parts else pd.DataFrame()
    rel.to_csv(OUT / "eda_accel_reliability.csv", index=False)
    if len(rel):
        show = rel[rel.group.isin(LEAD_GROUPS + ["WR+CB+S", "TE"])]
        with pd.option_context("display.width", 160, "display.float_format", lambda v: f"{v:0.3f}"):
            print(show.to_string(index=False))

    log("Building player profiles …")
    d = build_players(players, forty, dist, outcomes, comb, game, play_peaks)
    # Draft slot is out of this analysis; do not write pick columns.
    d = d.drop(
        columns=[c for c in ("draft_round", "draft_pick_within_round", "draft_overall_pick") if c in d.columns],
        errors="ignore",
    )
    d.to_csv(OUT / "eda_accel_players.csv", index=False)
    log(f"  wrote eda_accel_players.csv ({len(d)} speed-position players)")

    trans = translation_table(d)
    trans.to_csv(OUT / "eda_accel_translation.csv", index=False)
    log("Combine-to-Sunday translation (usable Sunday sample):")
    focus = trans[trans.label.isin([
        "Brakes (peak decel mag)",
        "Re-Burst (peak accel out of cuts)",
        "Time through the turn",
        "Brakes-to-gas ratio",
        "Speed lost through the cut",
    ])]
    with pd.option_context("display.width", 160, "display.float_format", lambda v: f"{v:0.3f}"):
        print(focus.to_string(index=False))

    pos = position_table(d)
    pos.to_csv(OUT / "eda_accel_position.csv", index=False)

    log("Clustering Combine movement archetypes …")
    everyone, info, members, evr = cluster_players(d)
    info.to_csv(OUT / "eda_accel_clusters.csv", index=False)
    members.to_csv(OUT / "eda_accel_cluster_members.csv", index=False)
    # also stash PCA coords with players? keep clusters file + members

    outc = outcome_links(d)
    outc.to_csv(OUT / "eda_accel_outcomes.csv", index=False)
    sig = outc[(outc.n >= 20) & (outc.p < 0.05)]
    log(f"Secondary outcome links with n≥20 and unadjusted p<0.05: {len(sig)}")
    if len(sig):
        with pd.option_context("display.width", 160, "display.float_format", lambda v: f"{v:0.3f}"):
            print(sig.sort_values("p").to_string(index=False))

    board = leaderboard(d)
    board.to_csv(OUT / "eda_accel_leaderboard.csv", index=False)

    vaki = vaki_row(d)
    vaki.to_csv(OUT / "eda_accel_vaki.csv", index=False)
    if len(vaki):
        log("Sione Vaki (anecdote):")
        print(vaki.T.to_string())

    log("Drawing figures …")
    p14 = fig14(d, pos)
    p15 = fig15(d, trans)
    p16 = fig16(everyone, info, members, evr)

    # Brief highlights for the executor summary
    log("=== HIGHLIGHTS ===")
    for grp in LEAD_GROUPS:
        row = pos[(pos.group == grp) & (pos.metric == "c_decel")]
        rowg = pos[(pos.group == grp) & (pos.metric == "g_decel")]
        if len(row):
            log(
                f"  {grp} Combine Brakes median {row.iloc[0]['median']:.2f} yd/s² "
                f"(n={int(row.iloc[0]['n'])}); Sunday median "
                f"{rowg.iloc[0]['median']:.2f} (n={int(rowg.iloc[0]['n'])})" if len(rowg) else ""
            )
    log(f"Done in {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
