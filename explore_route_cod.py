#!/usr/bin/env python3
"""Feasibility audit: route-running / coverage COD vs in-game separation.

Competition-page example: "Route running and coverage: Measuring change of
direction, deceleration into breaks, and acceleration out of cuts for
receivers and defensive backs compared to in-game separation."

This script inventories Combine and game tracking, tests whether those COD
metrics can be computed, and writes a small exploratory (not modeled)
Spearman proof-of-concept. It does not push to git or Drive and does not
touch Kaggle credentials or raw-data uploads.

Outputs (all under out/):
  route_cod_combine_drills.csv
  route_cod_official_coverage.csv
  route_cod_combine_player.csv
  route_cod_game_inventory.csv
  route_cod_game_player.csv
  route_cod_spearman.csv
  route_cod_qc.csv
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

ACCEL_CLIP = 12.0  # |Δs/Δt| above this is treated as a tracking glitch
HZ = 10.0

# WR/TE Combine drills that include a plant-and-cut (not go/fade/gauntlet).
WR_BREAK_DRILLS = {
    "COMEBACK_ROUTE_RIGHT",
    "CURL_ROUTE_RIGHT",
    "SLANT_ROUTE_LEFT",
    "SPEED_OUT_LEFT",
    "SPEED_OUT_ROUTE_LEFT",
    "POST_CORNER_ROUTE_LEFT",
    "POST_CORNER_ROUTE_RIGHT",
    "SLOT_SAIL_ROUTE_RIGHT",
    "SLOT_STRIKE_ROUTE_LEFT",
    "DAGGER_ROUTE_LEFT",
    "CIRCUS_ROUTE_LEFT",
    "IN_ROUTE_LEFT",
    "HOOK_ROUTE_RIGHT",
    "CORNER_ROUTE",
    "FLAT_ROUTE_LEFT",
}

# DB Combine drills built around a break, plant, or change of direction.
DB_COD_DRILLS = {
    "W_DRILL",
    "BOX_DRILL",
    "BACK_PEDAL_AND_90_DEGREE_BREAK_TO_BALL",
    "BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION",
    "TERYL_AUSTIN_DRILL_1",
    "TERYL_AUSTIN_DRILL_2",
    "LINE",
    "LINE_DRILL",
}

BREAKING_ROUTES = {"HITCH", "CROSS", "IN", "OUT", "POST", "CORNER", "SLANT", "ANGLE"}
FOCUS_OFF = {"WR", "TE"}
FOCUS_DB = {"CB", "FS", "SS", "DB"}
POS_GROUP = {
    "WR": "WR",
    "TE": "TE",
    "CB": "CB",
    "FS": "S",
    "SS": "S",
    "DB": "DB",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def angdiff(series: pd.Series) -> pd.Series:
    d = series.diff()
    return ((d + 180.0) % 360.0) - 180.0


def prepare_track(g: pd.DataFrame, time_col: str = "time") -> pd.DataFrame:
    g = g.sort_values(time_col).copy()
    t = pd.to_datetime(g[time_col], utc=True, format="ISO8601")
    g["_t"] = t
    dt = t.diff().dt.total_seconds()
    g["_dt"] = dt
    sa = g["s"].diff() / dt
    g["signed_a"] = sa.where(sa.abs() <= ACCEL_CLIP)
    if "dir" in g.columns:
        g["ddir"] = angdiff(g["dir"].astype(float))
    else:
        g["ddir"] = np.nan
    return g


def detect_cuts(
    g: pd.DataFrame,
    min_heading: float = 50.0,
    min_entry_speed: float = 1.5,
    min_gap_s: float = 0.6,
    heading_window: int = 7,
    time_col: str = "time",
) -> list[dict]:
    """Detect plant-and-cut events from a single 10 Hz track.

    A cut is a local peak in rolling |heading change| of at least
    `min_heading` degrees over ~0.6 s, with entry speed of at least
    `min_entry_speed` yd/s. For each cut we record peak deceleration into
    the break, peak acceleration out, speed lost, and time through the turn.
    """
    if g is None or len(g) < 10:
        return []
    need = {"s", time_col}
    if not need.issubset(g.columns):
        return []
    g = prepare_track(g, time_col=time_col)
    if g["signed_a"].notna().sum() < 8 or g["ddir"].notna().sum() < 8:
        return []

    turn = g["ddir"].abs().rolling(heading_window, center=True, min_periods=3).sum()
    turn_v = turn.to_numpy()
    s = g["s"].to_numpy(dtype=float)
    sa = g["signed_a"].to_numpy(dtype=float)
    t0 = g["_t"].iloc[0]
    trel = (g["_t"] - t0).dt.total_seconds().to_numpy()

    cands: list[int] = []
    n = len(g)
    for i in range(2, n - 2):
        v = turn_v[i]
        if not np.isfinite(v) or v < min_heading:
            continue
        if v >= turn_v[i - 1] and v >= turn_v[i + 1]:
            cands.append(i)
    kept: list[int] = []
    for i in sorted(cands, key=lambda k: -turn_v[k]):
        if any(abs(trel[i] - trel[j]) < min_gap_s for j in kept):
            continue
        kept.append(i)
    kept.sort()

    cuts: list[dict] = []
    for i in kept:
        lo = int(np.searchsorted(trel, trel[i] - 0.4))
        hi = int(np.searchsorted(trel, trel[i] + 0.4))
        win = s[lo:hi]
        if win.size == 0 or not np.isfinite(win).any():
            continue
        break_i = lo + int(np.nanargmin(win))
        elo = int(np.searchsorted(trel, trel[break_i] - 0.8))
        entry_win = s[elo : break_i + 1]
        if entry_win.size == 0 or not np.isfinite(entry_win).any():
            continue
        entry_off = int(np.nanargmax(entry_win))
        entry_i = elo + entry_off
        entry_s = float(entry_win[entry_off])
        if entry_s < min_entry_speed:
            continue
        decel_win = sa[entry_i : break_i + 1]
        peak_decel = (
            float(np.nanmin(decel_win))
            if decel_win.size and np.isfinite(decel_win).any()
            else np.nan
        )
        min_s = float(s[break_i])
        ehi = int(np.searchsorted(trel, trel[break_i] + 0.8))
        exit_s_win = s[break_i:ehi]
        exit_a_win = sa[break_i:ehi]
        exit_s = (
            float(np.nanmax(exit_s_win))
            if exit_s_win.size and np.isfinite(exit_s_win).any()
            else np.nan
        )
        peak_accel = (
            float(np.nanmax(exit_a_win))
            if exit_a_win.size and np.isfinite(exit_a_win).any()
            else np.nan
        )
        start_i = entry_i
        for k in range(entry_i, break_i + 1):
            if np.isfinite(sa[k]) and sa[k] <= -1.0:
                start_i = k
                break
        end_i = break_i
        recover = 0.8 * entry_s
        found = False
        for k in range(break_i, min(ehi, n)):
            if np.isfinite(s[k]) and s[k] >= recover:
                end_i = k
                found = True
                break
        if not found and ehi > break_i:
            end_i = min(ehi - 1, n - 1)
        time_through = float(trel[end_i] - trel[start_i])
        if time_through < 0:
            time_through = np.nan
        cuts.append(
            {
                "t_break": float(trel[break_i]),
                "entry_s": entry_s,
                "min_s": min_s,
                "exit_s": exit_s,
                "speed_lost": float(entry_s - min_s),
                "peak_decel": peak_decel,
                "peak_accel": peak_accel,
                "time_through": time_through,
                "heading_deg": float(turn_v[i]) if np.isfinite(turn_v[i]) else np.nan,
            }
        )
    return cuts


def summarize_cuts(cuts: list[dict], prefix: str) -> dict:
    if not cuts:
        return {
            f"{prefix}n_cuts": 0,
            f"{prefix}peak_decel": np.nan,
            f"{prefix}peak_decel_mag": np.nan,
            f"{prefix}peak_accel": np.nan,
            f"{prefix}speed_lost": np.nan,
            f"{prefix}time_through": np.nan,
        }
    decel = np.array([c["peak_decel"] for c in cuts], dtype=float)
    accel = np.array([c["peak_accel"] for c in cuts], dtype=float)
    lost = np.array([c["speed_lost"] for c in cuts], dtype=float)
    tt = np.array([c["time_through"] for c in cuts], dtype=float)
    return {
        f"{prefix}n_cuts": int(len(cuts)),
        f"{prefix}peak_decel": float(np.nanmedian(decel)),
        f"{prefix}peak_decel_mag": float(np.nanmedian(np.abs(decel))),
        f"{prefix}peak_accel": float(np.nanmedian(accel)),
        f"{prefix}speed_lost": float(np.nanmedian(lost)),
        f"{prefix}time_through": float(np.nanmedian(tt)),
    }


def spearman_row(group, x_name, y_name, x, y) -> dict:
    m = pd.DataFrame({"x": x, "y": y}).dropna()
    n = int(len(m))
    if n < 5:
        return {
            "group": group,
            "x": x_name,
            "y": y_name,
            "n": n,
            "rho": np.nan,
            "p": np.nan,
            "note": "n<5; not tested",
        }
    rho, p = spearmanr(m["x"], m["y"])
    return {
        "group": group,
        "x": x_name,
        "y": y_name,
        "n": n,
        "rho": float(rho) if np.isfinite(rho) else np.nan,
        "p": float(p) if np.isfinite(p) else np.nan,
        "note": "exploratory; unadjusted",
    }


def load_players() -> pd.DataFrame:
    p = pd.read_csv(DATA / "players.csv")
    p["pos_group"] = p["nfl_position"].map(POS_GROUP)
    return p


def official_coverage(players: pd.DataFrame) -> pd.DataFrame:
    cr = pd.read_csv(DATA / "combine_results.csv")
    m = cr.merge(
        players[["nfl_id", "nfl_position", "pos_group", "display_name"]],
        on="nfl_id",
        how="left",
    )
    rows = []
    for label, col in (
        ("nfl_position", "nfl_position"),
        ("combine_position", "combine_position"),
        ("pos_group", "pos_group"),
    ):
        for pos, g in m.groupby(col, dropna=False):
            rows.append(
                {
                    "group_type": label,
                    "group": pos if pd.notna(pos) else "NA",
                    "n_players": int(len(g)),
                    "n_three_cone": int(g["three_cone"].notna().sum()),
                    "n_short_shuttle": int(g["short_shuttle"].notna().sum()),
                    "n_both": int((g["three_cone"].notna() & g["short_shuttle"].notna()).sum()),
                    "median_three_cone": float(g["three_cone"].median()) if g["three_cone"].notna().any() else np.nan,
                    "median_short_shuttle": float(g["short_shuttle"].median()) if g["short_shuttle"].notna().any() else np.nan,
                }
            )
    # Combined DB = CB+S+DB and S = FS+SS already in pos_group; add CB+S explicitly
    cbs = m[m["nfl_position"].isin(["CB", "FS", "SS", "DB"])]
    rows.append(
        {
            "group_type": "custom",
            "group": "CB+S+DB",
            "n_players": int(len(cbs)),
            "n_three_cone": int(cbs["three_cone"].notna().sum()),
            "n_short_shuttle": int(cbs["short_shuttle"].notna().sum()),
            "n_both": int((cbs["three_cone"].notna() & cbs["short_shuttle"].notna()).sum()),
            "median_three_cone": float(cbs["three_cone"].median()) if cbs["three_cone"].notna().any() else np.nan,
            "median_short_shuttle": float(cbs["short_shuttle"].median()) if cbs["short_shuttle"].notna().any() else np.nan,
        }
    )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "route_cod_official_coverage.csv", index=False)
    return m


def combine_drill_inventory(players: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log("Loading combine_tracking.csv …")
    usecols = [
        "draft_year",
        "event_id",
        "nfl_id",
        "entity_type",
        "time",
        "drill_type",
        "drill_name",
        "attempt",
        "x",
        "y",
        "s",
        "a",
        "dis",
        "dir",
    ]
    ct = pd.read_csv(DATA / "combine_tracking.csv", usecols=usecols)
    log(f"  {len(ct):,} frames, entity_type={ct.entity_type.value_counts().to_dict()}")

    # Sampling rate (PLAYER only)
    player = ct[ct["entity_type"] == "PLAYER"].copy()
    player["_t"] = pd.to_datetime(player["time"], utc=True, format="ISO8601")
    player = player.sort_values(["event_id", "_t"])
    dt = player.groupby("event_id")["_t"].diff().dt.total_seconds().dropna()
    hz_row = {
        "source": "combine_tracking",
        "n_player_frames": int((ct.entity_type == "PLAYER").sum()),
        "n_ball_frames": int((ct.entity_type == "BALL").sum()),
        "n_events": int(player.event_id.nunique()),
        "dt_min": float(dt.min()) if len(dt) else np.nan,
        "dt_max": float(dt.max()) if len(dt) else np.nan,
        "dt_median": float(dt.median()) if len(dt) else np.nan,
        "frac_exactly_0_1": float(np.mean(np.isclose(dt, 0.1))) if len(dt) else np.nan,
        "implied_hz": 10.0 if len(dt) and float(np.mean(np.isclose(dt, 0.1))) == 1.0 else (
            float(1.0 / dt.median()) if len(dt) else np.nan
        ),
    }

    pos_map = players.set_index("nfl_id")["nfl_position"]
    focus_pos = ["WR", "TE", "CB", "FS", "SS", "DB", "OLB", "ILB", "MLB"]
    rows = []
    for (dtype, dname), g in player.groupby(["drill_type", "drill_name"]):
        pids = g["nfl_id"].unique()
        pos = pos_map.reindex(pids)
        vc = pos.value_counts()
        row = {
            "drill_type": dtype,
            "drill_name": dname,
            "n_player_frames": int(len(g)),
            "n_events": int(g["event_id"].nunique()),
            "n_players": int(g["nfl_id"].nunique()),
            "has_ball": bool(((ct.drill_name == dname) & (ct.entity_type == "BALL")).any()),
            "median_frames_per_event": float(g.groupby("event_id").size().median()),
        }
        for p in focus_pos:
            row[f"n_{p}"] = int(vc.get(p, 0))
        row["n_other"] = int(sum(v for k, v in vc.items() if k not in focus_pos))
        rows.append(row)
    inv = pd.DataFrame(rows).sort_values(["drill_type", "drill_name"])
    inv.to_csv(OUT / "route_cod_combine_drills.csv", index=False)
    log(f"  wrote route_cod_combine_drills.csv ({len(inv)} drills)")
    return ct, pd.Series(hz_row)


def attempt_cod(g: pd.DataFrame, min_entry_speed: float) -> dict:
    cuts = detect_cuts(g, min_entry_speed=min_entry_speed)
    finite_sa = g["signed_a"].to_numpy() if "signed_a" in g.columns else np.array([])
    # prepare_track is called inside detect_cuts; recompute if needed
    if "signed_a" not in g.columns:
        g = prepare_track(g)
        finite_sa = g["signed_a"].to_numpy()
    finite = finite_sa[np.isfinite(finite_sa)]
    out = summarize_cuts(cuts, prefix="")
    out["attempt_peak_decel"] = float(np.nanmin(finite)) if finite.size else np.nan
    out["attempt_peak_accel"] = float(np.nanmax(finite)) if finite.size else np.nan
    out["attempt_max_s"] = float(g["s"].max()) if len(g) else np.nan
    out["n_frames"] = int(len(g))
    return out


def combine_player_cod(ct: pd.DataFrame, players: pd.DataFrame, official: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log("Computing Combine cut metrics on agility and skill drills …")
    player = ct[ct["entity_type"] == "PLAYER"].copy()
    wanted = {"THREE_CONE_DRILL", "SHORT_SHUTTLE"} | WR_BREAK_DRILLS | DB_COD_DRILLS
    player = player[player["drill_name"].isin(wanted)]
    qc_rows = []
    recs = []
    for (eid, nfl_id, dname, dtype), g in player.groupby(
        ["event_id", "nfl_id", "drill_name", "drill_type"], sort=False
    ):
        # Agility drills have slower 5-yard entries; skill drills are faster.
        min_entry = 1.5 if dname in {"THREE_CONE_DRILL", "SHORT_SHUTTLE"} else 2.5
        g2 = prepare_track(g)
        feats = attempt_cod(g2, min_entry_speed=min_entry)
        feats.update(
            {
                "event_id": eid,
                "nfl_id": int(nfl_id),
                "drill_name": dname,
                "drill_type": dtype,
            }
        )
        recs.append(feats)
        if dname in {"THREE_CONE_DRILL", "SHORT_SHUTTLE"}:
            qc_rows.append(
                {
                    "drill_name": dname,
                    "event_id": eid,
                    "nfl_id": int(nfl_id),
                    "n_cuts": feats["n_cuts"],
                    "n_frames": feats["n_frames"],
                }
            )
    attempts = pd.DataFrame(recs)
    log(f"  {len(attempts):,} drill attempts with cut features")

    # QC: cuts per 3-cone / shuttle attempt
    qc = []
    if qc_rows:
        qdf = pd.DataFrame(qc_rows)
        for dname, g in qdf.groupby("drill_name"):
            qc.append(
                {
                    "check": f"cuts_per_{dname}_attempt",
                    "n_attempts": int(len(g)),
                    "mean": float(g.n_cuts.mean()),
                    "median": float(g.n_cuts.median()),
                    "p10": float(g.n_cuts.quantile(0.10)),
                    "p90": float(g.n_cuts.quantile(0.90)),
                    "frac_ge_1": float((g.n_cuts >= 1).mean()),
                    "frac_ge_2": float((g.n_cuts >= 2).mean()),
                    "note": "3-cone typically 3–4 turns; shuttle typically 2",
                }
            )

    def pool(sub: pd.DataFrame, prefix: str) -> pd.DataFrame:
        if sub.empty:
            return pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
        # Player-level: median of attempt-level median-cut metrics; also
        # median of whole-attempt peak brake/accel.
        agg = sub.groupby("nfl_id").agg(
            **{
                f"{prefix}n_attempts": ("event_id", "nunique"),
                f"{prefix}n_cuts": ("n_cuts", "sum"),
                f"{prefix}peak_decel": ("peak_decel", "median"),
                f"{prefix}peak_decel_mag": ("peak_decel_mag", "median"),
                f"{prefix}peak_accel": ("peak_accel", "median"),
                f"{prefix}speed_lost": ("speed_lost", "median"),
                f"{prefix}time_through": ("time_through", "median"),
                f"{prefix}attempt_peak_decel": ("attempt_peak_decel", "median"),
                f"{prefix}attempt_peak_accel": ("attempt_peak_accel", "median"),
            }
        )
        return agg.reset_index()

    three = pool(attempts[attempts.drill_name == "THREE_CONE_DRILL"], "tc_")
    shut = pool(attempts[attempts.drill_name == "SHORT_SHUTTLE"], "ss_")
    wrb = pool(attempts[attempts.drill_name.isin(WR_BREAK_DRILLS)], "wr_route_")
    dbc = pool(attempts[attempts.drill_name.isin(DB_COD_DRILLS)], "db_cod_")

    off = official[
        [
            "nfl_id",
            "combine_position",
            "three_cone",
            "short_shuttle",
            "ten_yd_split",
            "forty",
            "vertical",
            "broad_jump",
        ]
    ].copy()
    out = (
        players[["nfl_id", "display_name", "draft_year", "nfl_position", "pos_group"]]
        .merge(off, on="nfl_id", how="left")
        .merge(three, on="nfl_id", how="left")
        .merge(shut, on="nfl_id", how="left")
        .merge(wrb, on="nfl_id", how="left")
        .merge(dbc, on="nfl_id", how="left")
    )
    out.to_csv(OUT / "route_cod_combine_player.csv", index=False)
    log(f"  wrote route_cod_combine_player.csv ({len(out)} players)")
    return out, pd.DataFrame(qc)


def load_player_play(players: pd.DataFrame) -> pd.DataFrame:
    log("Loading player_play.csv (selected columns) …")
    usecols = [
        "game_id",
        "play_id",
        "nfl_id",
        "lined_up_position",
        "pass_result",
        "play_nullified_by_penalty",
        "target",
        "route_ran",
        "separation_at_pass_forward",
        "cushion",
        "coverage_assignment",
        "coverage_assignment_at_snap",
        "team_coverage_man_zone",
        "team_coverage_type",
    ]
    pp = pd.read_csv(DATA / "player_play.csv", usecols=usecols)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season", "season_type", "week"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp.merge(
        players[["nfl_id", "display_name", "draft_year", "nfl_position", "pos_group"]],
        on="nfl_id",
        how="left",
    )
    # Mixed boolean / string flags. Pandas 3 may use StringDtype (not object),
    # so never use astype(bool) on the penalty flag — bool("N") is True.
    pen = pp["play_nullified_by_penalty"].astype(str).str.strip().str.upper()
    pp["stood"] = pen.eq("N")
    if pd.api.types.is_bool_dtype(pp["target"]):
        pp["is_target"] = pp["target"].fillna(False).astype(bool)
    else:
        pp["is_target"] = pp["target"].astype(str).str.upper().isin(["TRUE", "1", "T", "YES"])
    pp["is_reg"] = pp["season_type"].eq("REG")
    pp["is_breaking_route"] = pp["route_ran"].isin(BREAKING_ROUTES)
    cov = pp["coverage_assignment"].astype(str)
    pp["in_coverage"] = pp["coverage_assignment"].notna() & ~cov.isin(["nan", "NA", "NO_ASSIGNMENT", ""])
    pp["in_man"] = cov.str.contains("MAN", na=False)
    pp["usable"] = pp["is_reg"] & pp["stood"]
    log(f"  {len(pp):,} player-plays, {pp.nfl_id.nunique()} players")
    return pp


def game_inventory(pp: pd.DataFrame, tracked_ids: set[int], hz_game: dict) -> pd.DataFrame:
    rows = []
    for pos in ["WR", "TE", "CB", "FS", "SS", "DB", "S", "CB+S+DB"]:
        if pos == "S":
            g = pp[pp["nfl_position"].isin(["FS", "SS"])]
        elif pos == "CB+S+DB":
            g = pp[pp["nfl_position"].isin(["CB", "FS", "SS", "DB"])]
        else:
            g = pp[pp["nfl_position"] == pos]
        roster = g.nfl_id.nunique()
        # also count roster from the already-merged players via any row
        u = g[g["usable"]]
        has_route = u[u["route_ran"].notna()]
        has_tgt = u[u["is_target"]]
        has_sep = u[u["separation_at_pass_forward"].notna()]
        has_cush = u[u["cushion"].notna()]
        has_cov = u[u["in_coverage"]]
        has_man = u[u["in_man"]]

        def n_at_floor(sub, floor):
            if sub.empty:
                return 0
            vc = sub.groupby("nfl_id").size()
            return int((vc >= floor).sum())

        tracked = {i for i in g.nfl_id.unique() if i in tracked_ids}
        rows.append(
            {
                "group": pos,
                "n_players_in_player_play": int(roster),
                "n_with_game_tracking": int(len(tracked)),
                "n_usable_reg_stood_plays": int(len(u)),
                "n_route_plays": int(len(has_route)),
                "n_players_with_route": int(has_route.nfl_id.nunique()),
                "n_players_route_ge20": n_at_floor(has_route, 20),
                "n_players_route_ge50": n_at_floor(has_route, 50),
                "n_target_plays": int(len(has_tgt)),
                "n_players_with_target": int(has_tgt.nfl_id.nunique()),
                "n_sep_at_pass_forward": int(len(has_sep)),
                "n_players_with_sep": int(has_sep.nfl_id.nunique()),
                "n_players_sep_ge20": n_at_floor(has_sep, 20),
                "n_cushion_rows": int(len(has_cush)),
                "n_players_with_cushion": int(has_cush.nfl_id.nunique()),
                "n_coverage_plays": int(len(has_cov)),
                "n_players_with_coverage": int(has_cov.nfl_id.nunique()),
                "n_players_coverage_ge30": n_at_floor(has_cov, 30),
                "n_man_plays": int(len(has_man)),
                "n_players_with_man": int(has_man.nfl_id.nunique()),
            }
        )
    inv = pd.DataFrame(rows)
    # Attach tracking facts as comment columns on a facts row
    facts = pd.DataFrame(
        [
            {
                "group": "_TRACKING_FACTS",
                "n_players_in_player_play": hz_game.get("n_players"),
                "n_with_game_tracking": hz_game.get("n_players"),
                "n_usable_reg_stood_plays": hz_game.get("n_frames"),
                "note": (
                    f"game tracking is exactly 10 Hz; football entity present={hz_game.get('ball_present')}; "
                    f"events include {hz_game.get('event_sample')}"
                ),
            }
        ]
    )
    # keep inv clean; facts go into qc later
    inv.to_csv(OUT / "route_cod_game_inventory.csv", index=False)
    log("  wrote route_cod_game_inventory.csv")
    return inv, facts


def load_game_tracks(keys: pd.DataFrame) -> pd.DataFrame:
    """Load game tracking frames only for requested (game_id, play_id, nfl_id)."""
    log(f"Loading game tracking for {len(keys):,} play-players …")
    keys = keys.drop_duplicates(["game_id", "play_id", "nfl_id"])
    # Integer key for fast isin
    keys = keys.copy()
    keys["_k"] = (
        keys["game_id"].astype("int64") * 10**12
        + keys["play_id"].astype("int64") * 10**6
        + keys["nfl_id"].astype("int64")
    )
    want = set(keys["_k"].tolist())
    usecols = ["game_id", "play_id", "nfl_id", "time", "x", "y", "s", "a", "dir", "event"]
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
        log(f"    running kept frames: {sum(len(p) for p in parts):,}")
    if not parts:
        return pd.DataFrame(columns=usecols)
    tr = pd.concat(parts, ignore_index=True)
    log(f"  kept {len(tr):,} / {n_in:,} frames")
    return tr


def scan_game_tracking_facts(players: pd.DataFrame) -> tuple[dict, set[int]]:
    """Frame rate, events, whether a football entity exists, tracked ids."""
    log("Scanning game tracking for frame rate, events, and entity coverage …")
    player_ids = set(players.nfl_id.tolist())
    tracked = set()
    event_counts: dict[str, int] = {}
    n_frames = 0
    extra_ids = set()
    dt_ok = True
    # Sample dts from each year via a small random set is already known; we
    # re-confirm on a 200k-row sample per file plus a full nfl_id/event pass.
    import pyarrow.csv as pacsv

    for year in (2023, 2024, 2025):
        path = DATA / f"game_tracking_{year}.csv"
        log(f"  facts scan {path.name} …")
        table = pacsv.read_csv(
            str(path),
            convert_options=pacsv.ConvertOptions(include_columns=["nfl_id", "time", "event"]),
            read_options=pacsv.ReadOptions(block_size=1 << 26),
        )
        df = table.to_pandas()
        n_frames += len(df)
        ids = set(df.nfl_id.unique())
        tracked |= ids
        extra_ids |= ids - player_ids
        ev = df["event"]
        # pandas may parse 'NA' as nan; pyarrow may keep 'NA'
        ev = ev.astype(str)
        ev = ev[~ev.isin(["NA", "nan", "None", ""])]
        vc = ev.value_counts()
        for k, v in vc.items():
            event_counts[str(k)] = event_counts.get(str(k), 0) + int(v)
        # dt sample
        samp = df.sample(n=min(3000, len(df)), random_state=2027)
        # Better: sample a few tracks — use first 400 unique nfl_id times is messy.
        # We'll compute dt on a 20k consecutive slice after sorting a subsample of ids.
        del df, table, samp
    # Precise 10 Hz check: already verified in the audit pre-pass; re-check
    # one file slice with time parsing on 400 tracks from 2024 (largest mid year)
    convert = pacsv.ConvertOptions(include_columns=["game_id", "play_id", "nfl_id", "time"])
    t2024 = pacsv.read_csv(
        str(DATA / "game_tracking_2024.csv"),
        convert_options=convert,
        read_options=pacsv.ReadOptions(block_size=1 << 26),
    ).to_pandas()
    keys = (
        t2024[["game_id", "play_id", "nfl_id"]]
        .drop_duplicates()
        .sample(n=400, random_state=2027)
    )
    samp = t2024.merge(keys, on=["game_id", "play_id", "nfl_id"])
    samp = samp.sort_values(["game_id", "play_id", "nfl_id", "time"])
    samp["_t"] = pd.to_datetime(samp["time"], utc=True, format="ISO8601")
    dt = samp.groupby(["game_id", "play_id", "nfl_id"])["_t"].diff().dt.total_seconds().dropna()
    frac = float(np.mean(np.isclose(dt, 0.1))) if len(dt) else np.nan
    dt_ok = bool(frac == 1.0)
    del t2024, samp

    events_sorted = sorted(event_counts, key=lambda k: -event_counts[k])
    facts = {
        "n_frames": n_frames,
        "n_players": len(tracked),
        "ball_present": bool(len(extra_ids) > 0),  # no non-player ids means no football entity
        "n_extra_ids": len(extra_ids),
        "dt_frac_0_1": frac,
        "dt_ok_10hz": dt_ok,
        "event_sample": ", ".join(events_sorted[:15]),
        "events_all": events_sorted,
        "event_counts": event_counts,
        "has_ball_snap": "ball_snap" in event_counts,
        "has_pass_forward": "pass_forward" in event_counts,
        "has_pass_arrived": "pass_arrived" in event_counts,
    }
    log(
        f"  frames={n_frames:,} tracked_players={len(tracked)} extra_ids={len(extra_ids)} "
        f"10Hz={dt_ok} events={len(event_counts)}"
    )
    return facts, tracked


def game_player_metrics(pp: pd.DataFrame, tr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-player in-game cut metrics, charted separation, and overlap sep."""
    log("Computing in-game cut metrics and separation …")
    # Charted separation / cushion / opportunity counts (no tracking needed)
    u = pp[pp["usable"]].copy()

    def sep_stats(sub: pd.DataFrame, prefix: str) -> pd.DataFrame:
        if sub.empty:
            return pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
        return (
            sub.groupby("nfl_id")
            .agg(
                **{
                    f"{prefix}n": ("separation_at_pass_forward", "count"),
                    f"{prefix}mean": ("separation_at_pass_forward", "mean"),
                    f"{prefix}median": ("separation_at_pass_forward", "median"),
                }
            )
            .reset_index()
        )

    wr_all = u[u["nfl_position"].isin(FOCUS_OFF) & u["separation_at_pass_forward"].notna()]
    wr_tgt = wr_all[wr_all["is_target"]]
    wr_brk = wr_all[wr_all["is_breaking_route"]]
    wr_tgt_brk = wr_brk[wr_brk["is_target"]]

    sep_all = sep_stats(wr_all, "sep_all_")
    sep_tgt = sep_stats(wr_tgt, "sep_tgt_")
    sep_brk = sep_stats(wr_brk, "sep_brk_")
    sep_tgt_brk = sep_stats(wr_tgt_brk, "sep_tgt_brk_")

    cush = (
        u[u["cushion"].notna()]
        .groupby("nfl_id")
        .agg(cushion_n=("cushion", "count"), cushion_mean=("cushion", "mean"))
        .reset_index()
    )
    route_n = (
        u[u["route_ran"].notna()]
        .groupby("nfl_id")
        .size()
        .rename("n_route_plays")
        .reset_index()
    )
    cov_n = (
        u[u["in_coverage"]]
        .groupby("nfl_id")
        .size()
        .rename("n_coverage_plays")
        .reset_index()
    )
    man_n = (
        u[u["in_man"]].groupby("nfl_id").size().rename("n_man_plays").reset_index()
    )
    tgt_n = (
        u[u["is_target"]].groupby("nfl_id").size().rename("n_targets").reset_index()
    )

    # Tracking-derived cuts. Restrict each play-player to snap → arrival / end.
    if tr is None or tr.empty:
        log("  no game tracks; skipping tracking-derived cuts")
        cuts_player = pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
        overlap = pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
        close_df = pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
    else:
        tr = tr.copy()
        ev = tr["event"].astype(str)
        tr["_event"] = ev.where(~ev.isin(["NA", "nan", "None", ""]), other=np.nan)
        # Event times per play-player
        ev_rows = tr[tr["_event"].notna()][
            ["game_id", "play_id", "nfl_id", "time", "_event", "x", "y", "s"]
        ]

        def event_time(name: str) -> pd.DataFrame:
            sub = ev_rows[ev_rows["_event"] == name][
                ["game_id", "play_id", "nfl_id", "time"]
            ]
            # first occurrence if duplicated
            return sub.sort_values("time").drop_duplicates(["game_id", "play_id", "nfl_id"])

        snap_t = event_time("ball_snap").rename(columns={"time": "t_snap"})
        fwd_t = event_time("pass_forward").rename(columns={"time": "t_forward"})
        arr_t = event_time("pass_arrived").rename(columns={"time": "t_arrived"})

        windows = (
            tr[["game_id", "play_id", "nfl_id"]]
            .drop_duplicates()
            .merge(snap_t, on=["game_id", "play_id", "nfl_id"], how="left")
            .merge(fwd_t, on=["game_id", "play_id", "nfl_id"], how="left")
            .merge(arr_t, on=["game_id", "play_id", "nfl_id"], how="left")
        )

        # Join route / coverage context
        ctx = u[
            [
                "game_id",
                "play_id",
                "nfl_id",
                "nfl_position",
                "route_ran",
                "is_breaking_route",
                "is_target",
                "in_coverage",
                "in_man",
                "separation_at_pass_forward",
            ]
        ]
        windows = windows.merge(ctx, on=["game_id", "play_id", "nfl_id"], how="left")

        log("  detecting in-game cuts (this is the slow step) …")
        tr["_t"] = pd.to_datetime(tr["time"], utc=True, format="ISO8601")
        # Pre-sort once
        tr = tr.sort_values(["game_id", "play_id", "nfl_id", "_t"])

        # Build window bounds as datetimes
        for col in ("t_snap", "t_forward", "t_arrived"):
            windows[col + "_dt"] = pd.to_datetime(windows[col], utc=True, format="ISO8601")

        win_idx = windows.set_index(["game_id", "play_id", "nfl_id"])
        cut_recs = []
        close_recs = []
        n_groups = 0
        # Iterate groups — ~tens of thousands; stay vectorized inside each
        for (gid, pid, nid), g in tr.groupby(["game_id", "play_id", "nfl_id"], sort=False):
            n_groups += 1
            try:
                w = win_idx.loc[(gid, pid, nid)]
            except KeyError:
                continue
            if isinstance(w, pd.DataFrame):
                w = w.iloc[0]
            t = g["_t"]
            t0 = w["t_snap_dt"] if pd.notna(w["t_snap_dt"]) else t.iloc[0]
            t1 = w["t_arrived_dt"] if pd.notna(w["t_arrived_dt"]) else (
                w["t_forward_dt"] if pd.notna(w["t_forward_dt"]) else t.iloc[-1]
            )
            gg = g[(t >= t0) & (t <= t1)]
            if len(gg) < 10:
                continue
            min_entry = 2.5
            cuts = detect_cuts(gg, min_entry_speed=min_entry, time_col="time")
            feats = summarize_cuts(cuts, prefix="")
            feats.update(
                {
                    "game_id": gid,
                    "play_id": pid,
                    "nfl_id": nid,
                    "nfl_position": w.get("nfl_position"),
                    "is_breaking_route": bool(w.get("is_breaking_route")),
                    "is_target": bool(w.get("is_target")),
                    "in_coverage": bool(w.get("in_coverage")),
                    "route_ran": w.get("route_ran"),
                }
            )
            cut_recs.append(feats)

            # Closing-ish: speed / accel near pass arrival or throw
            t_arr = w["t_arrived_dt"] if pd.notna(w["t_arrived_dt"]) else w["t_forward_dt"]
            if pd.notna(t_arr):
                near = g[(g["_t"] >= t_arr - pd.Timedelta(seconds=0.5)) & (g["_t"] <= t_arr)]
                if len(near):
                    g2 = prepare_track(near) if "signed_a" not in near.columns else near
                    # last frame closest to event
                    last = g.iloc[(g["_t"] - t_arr).abs().argmin()]
                    close_recs.append(
                        {
                            "game_id": gid,
                            "play_id": pid,
                            "nfl_id": nid,
                            "speed_at_event": float(last["s"]),
                            "mean_signed_a_0p5": float(g2["signed_a"].mean()) if "signed_a" in g2.columns else np.nan,
                            "max_s_0p5": float(near["s"].max()),
                            "in_coverage": bool(w.get("in_coverage")),
                            "is_breaking_route": bool(w.get("is_breaking_route")),
                        }
                    )
            if n_groups % 20000 == 0:
                log(f"    processed {n_groups:,} play-player tracks …")

        log(f"  cut features on {len(cut_recs):,} play-players")
        cuts_pp = pd.DataFrame(cut_recs)
        close_pp = pd.DataFrame(close_recs)

        def pool_cuts(mask, prefix):
            sub = cuts_pp[mask] if len(cuts_pp) else cuts_pp
            if sub is None or sub.empty:
                return pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
            return (
                sub.groupby("nfl_id")
                .agg(
                    **{
                        f"{prefix}n_plays": ("play_id", "count"),
                        f"{prefix}n_cuts": ("n_cuts", "sum"),
                        f"{prefix}peak_decel": ("peak_decel", "median"),
                        f"{prefix}peak_decel_mag": ("peak_decel_mag", "median"),
                        f"{prefix}peak_accel": ("peak_accel", "median"),
                        f"{prefix}speed_lost": ("speed_lost", "median"),
                        f"{prefix}time_through": ("time_through", "median"),
                    }
                )
                .reset_index()
            )

        if len(cuts_pp):
            wr_mask = cuts_pp["nfl_position"].isin(list(FOCUS_OFF))
            wr_brk_mask = wr_mask & cuts_pp["is_breaking_route"].astype(bool)
            db_mask = cuts_pp["in_coverage"].astype(bool)
            c_wr = pool_cuts(wr_mask, "game_wr_")
            c_brk = pool_cuts(wr_brk_mask, "game_brk_")
            c_db = pool_cuts(db_mask, "game_db_")
            cuts_player = c_wr.merge(c_brk, on="nfl_id", how="outer").merge(
                c_db, on="nfl_id", how="outer"
            )
        else:
            cuts_player = pd.DataFrame({"nfl_id": pd.Series(dtype=int)})

        if len(close_pp):
            close_db = (
                close_pp[close_pp["in_coverage"].astype(bool)]
                .groupby("nfl_id")
                .agg(
                    close_n=("play_id", "count"),
                    close_speed_at_arrival=("speed_at_event", "mean"),
                    close_max_s_0p5=("max_s_0p5", "mean"),
                    close_mean_signed_a=("mean_signed_a_0p5", "mean"),
                )
                .reset_index()
            )
            close_df = close_db
        else:
            close_df = pd.DataFrame({"nfl_id": pd.Series(dtype=int)})

        # Overlap separation: targeted cohort WR/TE and cohort DB on same play,
        # distance at pass_forward / pass_arrived. This is NOT nearest-defender
        # separation; untracked veterans are invisible.
        log("  computing rookie-overlap distances (caveated) …")
        tgt_keys = u[u["is_target"] & u["nfl_position"].isin(FOCUS_OFF)][
            ["game_id", "play_id", "nfl_id"]
        ].rename(columns={"nfl_id": "wr_id"})
        db_keys = u[u["nfl_position"].isin(FOCUS_DB)][
            ["game_id", "play_id", "nfl_id"]
        ].rename(columns={"nfl_id": "db_id"})
        pairs = tgt_keys.merge(db_keys, on=["game_id", "play_id"], how="inner")
        overlap = pd.DataFrame({"nfl_id": pd.Series(dtype=int)})
        if len(pairs):
            # Positions of everyone at pass_forward / pass_arrived
            def pos_at(event_name: str) -> pd.DataFrame:
                sub = ev_rows[ev_rows["_event"] == event_name][
                    ["game_id", "play_id", "nfl_id", "x", "y", "s"]
                ]
                return sub.sort_values(["game_id", "play_id", "nfl_id"]).drop_duplicates(
                    ["game_id", "play_id", "nfl_id"]
                )

            pf = pos_at("pass_forward")
            pa = pos_at("pass_arrived")
            wr_f = pf.rename(columns={"nfl_id": "wr_id", "x": "wr_x", "y": "wr_y", "s": "wr_s"})
            db_f = pf.rename(columns={"nfl_id": "db_id", "x": "db_x", "y": "db_y", "s": "db_s"})
            wr_a = pa.rename(columns={"nfl_id": "wr_id", "x": "wr_x", "y": "wr_y", "s": "wr_s"})
            db_a = pa.rename(columns={"nfl_id": "db_id", "x": "db_x", "y": "db_y", "s": "db_s"})
            at_f = pairs.merge(wr_f, on=["game_id", "play_id", "wr_id"], how="left").merge(
                db_f, on=["game_id", "play_id", "db_id"], how="left"
            )
            at_a = pairs.merge(wr_a, on=["game_id", "play_id", "wr_id"], how="left").merge(
                db_a, on=["game_id", "play_id", "db_id"], how="left"
            )
            at_f["dist"] = np.hypot(at_f["wr_x"] - at_f["db_x"], at_f["wr_y"] - at_f["db_y"])
            at_a["dist"] = np.hypot(at_a["wr_x"] - at_a["db_x"], at_a["wr_y"] - at_a["db_y"])
            # Nearest cohort DB on the play (still not necessarily the coverer)
            near_f = (
                at_f.dropna(subset=["dist"])
                .sort_values("dist")
                .drop_duplicates(["game_id", "play_id", "wr_id"])
            )
            near_a = (
                at_a.dropna(subset=["dist"])
                .sort_values("dist")
                .drop_duplicates(["game_id", "play_id", "wr_id"])
            )
            # Only count "plausible coverage" if nearest rookie DB is within 8 yards
            near_f_c = near_f[near_f["dist"] <= 8.0]
            near_a_c = near_a[near_a["dist"] <= 8.0]
            db_sep_f = (
                near_f_c.groupby("db_id")
                .agg(overlap_fwd_n=("dist", "count"), overlap_fwd_mean=("dist", "mean"))
                .reset_index()
                .rename(columns={"db_id": "nfl_id"})
            )
            db_sep_a = (
                near_a_c.groupby("db_id")
                .agg(overlap_arr_n=("dist", "count"), overlap_arr_mean=("dist", "mean"))
                .reset_index()
                .rename(columns={"db_id": "nfl_id"})
            )
            overlap = db_sep_f.merge(db_sep_a, on="nfl_id", how="outer")
            # stash counts for QC
            overlap.attrs["n_pair_plays"] = int(pairs.drop_duplicates(["game_id", "play_id"]).shape[0])
            overlap.attrs["n_fwd_any"] = int(len(near_f))
            overlap.attrs["n_fwd_within8"] = int(len(near_f_c))
            overlap.attrs["n_arr_within8"] = int(len(near_a_c))
            overlap.attrs["n_db_within8"] = int(near_f_c.db_id.nunique()) if len(near_f_c) else 0
        else:
            overlap.attrs["n_pair_plays"] = 0

    # Assemble player table from pp players of interest
    base = (
        pp[["nfl_id", "display_name", "draft_year", "nfl_position", "pos_group"]]
        .drop_duplicates("nfl_id")
    )
    out = (
        base.merge(route_n, on="nfl_id", how="left")
        .merge(tgt_n, on="nfl_id", how="left")
        .merge(cov_n, on="nfl_id", how="left")
        .merge(man_n, on="nfl_id", how="left")
        .merge(sep_all, on="nfl_id", how="left")
        .merge(sep_tgt, on="nfl_id", how="left")
        .merge(sep_brk, on="nfl_id", how="left")
        .merge(sep_tgt_brk, on="nfl_id", how="left")
        .merge(cush, on="nfl_id", how="left")
        .merge(cuts_player, on="nfl_id", how="left")
        .merge(close_df, on="nfl_id", how="left")
        .merge(overlap, on="nfl_id", how="left")
    )
    out.to_csv(OUT / "route_cod_game_player.csv", index=False)
    log(f"  wrote route_cod_game_player.csv ({len(out)} players)")
    return out, overlap


def run_spearman(comb: pd.DataFrame, game: pd.DataFrame) -> pd.DataFrame:
    log("Running exploratory Spearman tests …")
    m = comb.merge(
        game.drop(columns=["display_name", "draft_year", "nfl_position", "pos_group"], errors="ignore"),
        on="nfl_id",
        how="inner",
    )
    rows = []

    wr = m[m["nfl_position"] == "WR"]
    te = m[m["nfl_position"] == "TE"]
    wrte = m[m["nfl_position"].isin(["WR", "TE"])]
    cb = m[m["nfl_position"] == "CB"]
    s = m[m["nfl_position"].isin(["FS", "SS"])]
    dbs = m[m["nfl_position"].isin(["CB", "FS", "SS", "DB"])]

    def add(group_name, df, xs, ys, min_opp=None, opp_col=None):
        use = df
        if min_opp and opp_col:
            use = df[df[opp_col].fillna(0) >= min_opp]
        for x in xs:
            for y in ys:
                if x not in use.columns or y not in use.columns:
                    continue
                rows.append(spearman_row(group_name, x, y, use[x], use[y]))

    wr_x = [
        "three_cone",
        "short_shuttle",
        "tc_peak_decel_mag",
        "tc_peak_accel",
        "tc_speed_lost",
        "tc_time_through",
        "ss_peak_decel_mag",
        "ss_peak_accel",
        "ss_speed_lost",
        "ss_time_through",
        "wr_route_peak_decel_mag",
        "wr_route_peak_accel",
        "wr_route_speed_lost",
        "wr_route_time_through",
        "game_brk_peak_decel_mag",
        "game_brk_peak_accel",
        "game_brk_speed_lost",
    ]
    wr_y = ["sep_all_mean", "sep_tgt_mean", "sep_brk_mean", "sep_tgt_brk_mean"]
    add("WR (sep n>=20)", wr, wr_x, wr_y, min_opp=20, opp_col="sep_all_n")
    add("TE (sep n>=20)", te, wr_x, wr_y, min_opp=20, opp_col="sep_all_n")
    add("WR+TE (sep n>=20)", wrte, wr_x, wr_y, min_opp=20, opp_col="sep_all_n")

    db_x = [
        "three_cone",
        "short_shuttle",
        "tc_peak_decel_mag",
        "tc_peak_accel",
        "ss_peak_decel_mag",
        "ss_peak_accel",
        "db_cod_peak_decel_mag",
        "db_cod_peak_accel",
        "db_cod_speed_lost",
        "db_cod_time_through",
        "game_db_peak_decel_mag",
        "game_db_peak_accel",
        "close_speed_at_arrival",
    ]
    db_y = [
        "cushion_mean",
        "overlap_fwd_mean",
        "overlap_arr_mean",
    ]
    add("CB (coverage n>=30)", cb, db_x, db_y, min_opp=30, opp_col="n_coverage_plays")
    add("S (coverage n>=30)", s, db_x, db_y, min_opp=30, opp_col="n_coverage_plays")
    add("DB group CB+S+DB (coverage n>=30)", dbs, db_x, db_y, min_opp=30, opp_col="n_coverage_plays")

    # Looser floors so thin official 3-cone samples still appear
    add("WR (any official / sep n>=10)", wr, ["three_cone", "short_shuttle"], wr_y, min_opp=10, opp_col="sep_all_n")
    add("CB (any official / cov n>=10)", cb, ["three_cone", "short_shuttle"], db_y, min_opp=10, opp_col="n_coverage_plays")
    add("S (any official / cov n>=10)", s, ["three_cone", "short_shuttle"], db_y, min_opp=10, opp_col="n_coverage_plays")
    add("DB group (any official / cov n>=10)", dbs, ["three_cone", "short_shuttle"], db_y, min_opp=10, opp_col="n_coverage_plays")

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "route_cod_spearman.csv", index=False)
    log(f"  wrote route_cod_spearman.csv ({len(out)} tests)")
    return out


def main() -> int:
    t0 = time.time()
    players = load_players()
    official = official_coverage(players)
    ct, hz_combine = combine_drill_inventory(players)
    comb, qc_comb = combine_player_cod(ct, players, official)

    # Free combine frames before the game scan
    del ct

    pp = load_player_play(players)
    hz_game, tracked_ids = scan_game_tracking_facts(players)
    inv, _facts = game_inventory(pp, tracked_ids, hz_game)

    # Keys to pull from game tracking: usable WR/TE routes and DB coverage snaps
    u = pp[pp["usable"]]
    wr_keys = u[u["nfl_position"].isin(FOCUS_OFF) & u["route_ran"].notna()][
        ["game_id", "play_id", "nfl_id"]
    ]
    db_keys = u[u["nfl_position"].isin(FOCUS_DB) & (u["in_coverage"] | u["cushion"].notna())][
        ["game_id", "play_id", "nfl_id"]
    ]
    keys = pd.concat([wr_keys, db_keys], ignore_index=True).drop_duplicates()
    log(f"Tracking key set: {len(wr_keys):,} WR/TE routes, {len(db_keys):,} DB snaps, {len(keys):,} unique")
    tr = load_game_tracks(keys)
    game, overlap = game_player_metrics(pp, tr)
    sp = run_spearman(comb, game)

    # QC / facts table
    qc = []
    if qc_comb is not None and len(qc_comb):
        qc.extend(qc_comb.to_dict("records"))
    qc.append(
        {
            "check": "combine_sample_rate",
            "n_attempts": hz_combine.get("n_events"),
            "mean": hz_combine.get("implied_hz"),
            "median": hz_combine.get("dt_median"),
            "frac_ge_1": hz_combine.get("frac_exactly_0_1"),
            "note": "PLAYER frames; dt exactly 0.1 s ⇒ 10 Hz",
        }
    )
    qc.append(
        {
            "check": "game_sample_rate",
            "n_attempts": hz_game.get("n_frames"),
            "mean": 10.0 if hz_game.get("dt_ok_10hz") else hz_game.get("dt_frac_0_1"),
            "frac_ge_1": hz_game.get("dt_frac_0_1"),
            "note": f"football entity present={hz_game.get('ball_present')}; extra_ids={hz_game.get('n_extra_ids')}",
        }
    )
    qc.append(
        {
            "check": "game_events",
            "note": (
                f"ball_snap={hz_game.get('has_ball_snap')}, "
                f"pass_forward={hz_game.get('has_pass_forward')}, "
                f"pass_arrived={hz_game.get('has_pass_arrived')}; "
                f"all={', '.join(hz_game.get('events_all', []))}"
            ),
        }
    )
    # Overlap caveats
    n_pair = getattr(overlap, "attrs", {}).get("n_pair_plays", np.nan) if overlap is not None else np.nan
    qc.append(
        {
            "check": "rookie_overlap_separation",
            "n_attempts": n_pair,
            "frac_ge_1": getattr(overlap, "attrs", {}).get("n_fwd_within8", np.nan) if overlap is not None else np.nan,
            "note": (
                f"targeted WR/TE plays with a cohort DB: pairs={n_pair}; "
                f"nearest-rookie-DB within 8 yd at throw="
                f"{getattr(overlap, 'attrs', {}).get('n_fwd_within8', 'NA')}; "
                f"unique DBs={getattr(overlap, 'attrs', {}).get('n_db_within8', 'NA')}. "
                "This is NOT true nearest-defender separation; veterans are not tracked."
            ),
        }
    )
    # How many official 3-cone WRs have game sep
    wr = comb[comb.nfl_position == "WR"].merge(
        game[["nfl_id", "sep_all_n", "sep_all_mean"]], on="nfl_id", how="left"
    )
    qc.append(
        {
            "check": "WR_three_cone_with_sep20",
            "n_attempts": int(((wr.three_cone.notna()) & (wr.sep_all_n.fillna(0) >= 20)).sum()),
            "note": (
                f"WR official 3-cone n={int(wr.three_cone.notna().sum())}; "
                f"with sep_all_n>=20 n={int(((wr.three_cone.notna()) & (wr.sep_all_n.fillna(0)>=20)).sum())}; "
                f"shuttle with sep20 n={int(((wr.short_shuttle.notna()) & (wr.sep_all_n.fillna(0)>=20)).sum())}"
            ),
        }
    )
    pd.DataFrame(qc).to_csv(OUT / "route_cod_qc.csv", index=False)

    # Brief stdout summary for the executor
    log("=== Exploratory Spearman highlights (n>=8, unadjusted) ===")
    if len(sp):
        show = sp[(sp["n"] >= 8) & sp["rho"].notna()].copy()
        show["abs_rho"] = show["rho"].abs()
        show = show.sort_values(["group", "abs_rho"], ascending=[True, False])
        cols = ["group", "x", "y", "n", "rho", "p"]
        with pd.option_context("display.max_rows", 80, "display.width", 160, "display.float_format", lambda v: f"{v:0.3f}"):
            print(show[cols].to_string(index=False))
    log(f"Done in {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
