#!/usr/bin/env python3
"""Late-round Combine overperformers — BDB 2027.

Question: among later-round picks (rounds 4–7; UDFA reported separately),
who tested in the top third of their position on the Combine measure that
best relates to that group's on-field gameplay, and then outplayed their
draft slot?

The primary Combine measure is chosen from a *pre-declared shortlist* for
each group, using the early-round (R1–3) sample so the selection step is
separated from the late-round contrast. All shortlist correlations are
reported. This is a selection step: do not treat the winning correlation
as an independent confirmatory test.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/late_round_gems.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

UDFA_PICK = 260
MIN_WR_ROUTES = 20
MIN_DB_SNAPS = 50
MIN_DL_RUSH = 20
MIN_N_SELECT = 12
MIN_N_REPORT = 8
MIN_N_GROUP_CELL = 5
N_BOOT = 2000
BOOT_SEED = 2027
MPH = 2.0455
YDS_SPEED_MEASURES = {"db_gauntlet_max_s", "db_bp45_max_s", "db_w_max_s", "wr_go_max_s"}

# Draft-slot residual is the official "overperformed" definition.
# Playing time is context only.

GROUPS = ["WR", "CB", "S", "Edge", "Interior"]
GROUP_COLOR = {
    "WR": "#0072B2",
    "CB": "#D55E00",
    "S": "#009E73",
    "Edge": "#D55E00",
    "Interior": "#0072B2",
}
GROUP_OUTCOME = {
    "WR": ("yards_per_route", "Yards per route"),
    "CB": ("tackle_rate", "Tackle involvement rate"),
    "S": ("tackle_rate", "Tackle involvement rate"),
    "Edge": ("pressure_rate", "Pressure rate"),
    "Interior": ("pressure_rate", "Pressure rate"),
}
# Companion outcomes shown on the card, not used to pick the measure.
GROUP_COMPANIONS = {
    "WR": [
        ("deep_yards_per_deep_route", "Deep yards / deep route"),
        ("deep_target_share", "Deep target share"),
        ("sunday_speed_mph", "Sunday Speed (mph)"),
        ("ssoe_mph", "SSOE (mph)"),
    ],
    "CB": [
        ("tfl_rate", "TFL rate"),
        ("ssoe_mph", "SSOE (mph)"),
        ("sunday_speed_mph", "Sunday Speed (mph)"),
    ],
    "S": [
        ("tfl_rate", "TFL rate"),
        ("ssoe_mph", "SSOE (mph)"),
        ("sunday_speed_mph", "Sunday Speed (mph)"),
    ],
    "Edge": [
        ("sack_rate", "Sack rate"),
        ("speed_1s_mph", "Get-off: speed at 1.0s (mph)"),
        ("snaps_per_game", "Defensive snaps / game"),
    ],
    "Interior": [
        ("sack_rate", "Sack rate"),
        ("speed_1s_mph", "Get-off: speed at 1.0s (mph)"),
        ("snaps_per_game", "Defensive snaps / game"),
    ],
}

# Pre-declared shortlists. direction = sign of a *good* raw number
# (−1 = lower is better, e.g. times).
# WR: speed tests. Sunday Speed is a *game* measure, not a Combine input,
# so it is a companion on the card, not a candidate for "strong Combine."
# CB/S: COD, explosiveness, burst, and the standard DB drills that have
# enough attempts. Shuttle and 3-cone are included but will often fail
# the n floor (many players skip them).
# DL: 10-yard split is the prior primary; 3-cone, broad, and bench are
# the requested checks. official_forty is a close cousin of the 10-yard
# and is listed so the choice is visible, not so it can quietly win.
WR_SHORTLIST = [
    ("c_top_mph", "40-yard tracked top speed", +1),
    ("official_forty", "Official 40 time", -1),
    ("official_ten_yd", "Official 10-yard split", -1),
]
DB_SHORTLIST = [
    ("short_shuttle", "20-yard shuttle", -1),
    ("three_cone", "3-cone drill", -1),
    ("vertical", "Vertical jump", +1),
    ("broad_jump", "Broad jump", +1),
    ("official_ten_yd", "Official 10-yard split", -1),
    ("c_top_mph", "40-yard tracked top speed", +1),
    ("official_forty", "Official 40 time", -1),
    ("db_gauntlet_max_s", "Gauntlet drill top speed", +1),
    ("db_bp45_max_s", "Backpedal 45° drill top speed", +1),
]
DL_SHORTLIST = [
    ("official_ten_yd", "Official 10-yard split", -1),
    ("three_cone", "3-cone drill", -1),
    ("broad_jump", "Broad jump", +1),
    ("bench_reps", "Bench press reps", +1),
    ("official_forty", "Official 40 time", -1),
]
# If an alternate is only barely ahead of the 10-yard split on the
# early-round sample, keep the 10-yard. It is already the established
# DL burst measure; we will not let a noisy small-n coin flip replace it.
# official_forty is reported on the shortlist (it is a cousin of the
# 10-yard) but cannot be selected — Kevin asked us to check 3-cone,
# broad, and bench against the 10-yard, not to let the laser 40
# quietly take its place.
DL_PREFERRED = "official_ten_yd"
DL_TIE_MARGIN = 0.10
DL_NOT_SELECTABLE = {"official_forty"}
WEAK_LINK_RHO = 0.20
WEAK_LINK_P = 0.10

GROUP_SHORTLIST = {
    "WR": WR_SHORTLIST,
    "CB": DB_SHORTLIST,
    "S": DB_SHORTLIST,
    "Edge": DL_SHORTLIST,
    "Interior": DL_SHORTLIST,
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def fmt_rho(r: float) -> str:
    if not np.isfinite(r):
        return "NA"
    return f"{r:+.2f}"


def fmt_ci(lo: float, hi: float) -> str:
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "NA"
    return f"{lo:+.2f} – {hi:+.2f}"


def _residualize(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    keep = [0]
    for j in range(1, A.shape[1]):
        cand = A[:, keep + [j]]
        if np.linalg.matrix_rank(cand) > len(keep):
            keep.append(j)
    A = A[:, keep]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def year_pick_controls(d: pd.DataFrame) -> pd.DataFrame:
    year_dummies = pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True)
    log_pick = np.log(d["pick"].astype(float)).to_frame("log_pick")
    if year_dummies.shape[1] >= 1:
        return pd.concat([log_pick, year_dummies], axis=1)
    return log_pick


def spearman_controlled(x: pd.Series, y: pd.Series, df: pd.DataFrame) -> dict:
    d = pd.DataFrame({
        "x": x, "y": y, "pick": df["pick"], "draft_year": df["draft_year"],
    }).dropna()
    out = {
        "n": int(len(d)), "rho": np.nan, "p": np.nan,
        "partial_rho": np.nan, "partial_p": np.nan,
        "partial_year_pick_rho": np.nan, "partial_year_pick_p": np.nan,
    }
    if len(d) < MIN_N_REPORT or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    lp = np.log(d["pick"].astype(float))
    if lp.nunique() >= 2:
        rx = d["x"].to_numpy() - np.poly1d(np.polyfit(lp, d["x"], 1))(lp)
        ry = d["y"].to_numpy() - np.poly1d(np.polyfit(lp, d["y"], 1))(lp)
        if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
            pr, pp = stats.spearmanr(rx, ry)
            out["partial_rho"], out["partial_p"] = float(pr), float(pp)
    controls = year_pick_controls(d)
    X = controls.to_numpy(dtype=float)
    if np.unique(X, axis=0).shape[0] >= 2:
        rx = _residualize(d["x"].to_numpy(dtype=float), X)
        ry = _residualize(d["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
            pr, pp = stats.spearmanr(rx, ry)
            out["partial_year_pick_rho"], out["partial_year_pick_p"] = float(pr), float(pp)
    return out


def pick_residual(y: pd.Series, pick: pd.Series) -> pd.Series:
    """Outcome residual after a linear fit on log draft pick (UDFA = 260)."""
    d = pd.DataFrame({"y": y, "pick": pick}).dropna()
    out = pd.Series(np.nan, index=y.index, dtype=float)
    if len(d) < 8 or d["pick"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    lp = np.log(d["pick"].astype(float))
    coef = np.polyfit(lp, d["y"].to_numpy(dtype=float), 1)
    pred = np.poly1d(coef)(lp)
    out.loc[d.index] = d["y"].to_numpy(dtype=float) - pred
    return out


def draft_band(round_val) -> str:
    if pd.isna(round_val):
        return "UDFA"
    if float(round_val) <= 3:
        return "R1-3"
    return "R4-7"


def fmt_draft(row: pd.Series) -> str:
    year = row.get("draft_year")
    rnd = row.get("draft_round")
    overall = row.get("draft_overall_pick")
    year_s = f"{int(year)} " if pd.notna(year) else ""
    if pd.isna(rnd):
        return f"{year_s}UDFA".strip()
    pick_s = f" #{int(overall)}" if pd.notna(overall) else ""
    return f"{year_s}R{int(rnd)}{pick_s}".strip()


def oriented_value(series: pd.Series, direction: int) -> pd.Series:
    return series.astype(float) * (1 if direction > 0 else -1)


def add_tertiles_and_z(df: pd.DataFrame, col: str, direction: int, prefix: str) -> pd.DataFrame:
    """Position-group tertiles and z-score, oriented so higher = better."""
    out = df.copy()
    oriented = oriented_value(out[col], direction)
    mu = oriented.mean(skipna=True)
    sd = oriented.std(skipna=True, ddof=1)
    out[f"{prefix}_z"] = (oriented - mu) / sd if pd.notna(sd) and sd > 0 else np.nan
    # Rank percentile among players with a value. Top third = strong.
    ranks = oriented.rank(method="average", pct=True)
    out[f"{prefix}_pct"] = ranks
    band = pd.Series(np.nan, index=out.index, dtype=object)
    has = oriented.notna()
    band.loc[has & (ranks >= 2.0 / 3.0)] = "strong"
    band.loc[has & (ranks <= 1.0 / 3.0)] = "weak"
    band.loc[has & (ranks > 1.0 / 3.0) & (ranks < 2.0 / 3.0)] = "middle"
    out[f"{prefix}_band"] = band
    return out


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    ss = pd.read_csv(OUT / "sunday_speed_players.csv")
    gp = pd.read_csv(OUT / "gameplay_success_players.csv")
    dl = pd.read_csv(OUT / "dl_burst_players.csv")
    cr = pd.read_csv(DATA / "combine_results.csv")
    pl = pd.read_csv(DATA / "players.csv")

    drill_cols = [c for c in [
        "draft_round", "official_ten_yd", "official_forty", "vertical",
        "broad_jump", "three_cone", "short_shuttle", "bench_reps",
        "college_name", "db_gauntlet_max_s", "db_bp45_max_s", "db_w_max_s",
        "wr_go_max_s", "n_plays",
    ] if c in ss.columns]
    skill = gp.merge(ss[["nfl_id"] + drill_cols], on="nfl_id", how="left")
    # gameplay table already has pick, c_top_mph, sunday_speed, ssoe, outcomes
    if "college_name" not in skill.columns:
        skill = skill.merge(pl[["nfl_id", "college_name"]], on="nfl_id", how="left")
    skill["pick"] = skill["pick"].fillna(UDFA_PICK)
    skill["band"] = skill["draft_round"].map(draft_band)
    skill["group"] = skill["pos_group"]

    wr = skill[skill["pos_group"] == "WR"].copy()
    wr = wr[wr["n_routes"] >= MIN_WR_ROUTES].copy()
    wr["eligible"] = True
    wr["n_opps"] = wr["n_routes"]
    wr["opp_label"] = "routes"

    dbs = skill[skill["pos_group"].isin(["CB", "S"])].copy()
    dbs = dbs[dbs["n_def_snaps"] >= MIN_DB_SNAPS].copy()
    dbs["eligible"] = True
    dbs["n_opps"] = dbs["n_def_snaps"]
    dbs["opp_label"] = "def snaps"

    # DL: join official athletic tests from combine_results when missing.
    dl = dl.merge(
        cr[["nfl_id", "ten_yd_split", "forty", "vertical", "broad_jump",
            "three_cone", "short_shuttle", "bench_reps"]],
        on="nfl_id", how="left", suffixes=("", "_cr"),
    )
    if "college_name" not in dl.columns or dl["college_name"].isna().all():
        dl = dl.drop(columns=["college_name"], errors="ignore")
        dl = dl.merge(pl[["nfl_id", "college_name"]], on="nfl_id", how="left")
    if "official_forty" not in dl.columns:
        dl["official_forty"] = dl["forty"]
    else:
        dl["official_forty"] = dl["official_forty"].fillna(dl["forty"])
    for src, dst in [("ten_yd_split", "official_ten_yd"),
                     ("vertical", "vertical"),
                     ("broad_jump", "broad_jump"),
                     ("three_cone", "three_cone"),
                     ("short_shuttle", "short_shuttle"),
                     ("bench_reps", "bench_reps")]:
        if dst not in dl.columns:
            dl[dst] = dl[src]
        else:
            dl[dst] = dl[dst].fillna(dl[src])
    dl["pick"] = dl["pick"].fillna(UDFA_PICK)
    dl["band"] = dl["draft_round"].map(draft_band)
    dl = dl[dl["n_rush_plays"] >= MIN_DL_RUSH].copy()
    dl["group"] = dl["subtype"]
    dl["pos_group"] = dl["subtype"]
    dl["eligible"] = True
    dl["n_opps"] = dl["n_rush_plays"]
    dl["opp_label"] = "pass-rush snaps"
    # Harmonize name field
    if "display_name" not in dl.columns and "player_name" in dl.columns:
        dl["display_name"] = dl["player_name"]

    skill_out = pd.concat([wr, dbs], ignore_index=True)
    # Shared column set for later stacking in the gems table
    return skill_out, dl


def selection_score(row: dict) -> float:
    """Prefer pick-partial ρ; fall back to raw ρ. Already oriented."""
    if np.isfinite(row.get("oriented_partial_rho", np.nan)):
        return float(row["oriented_partial_rho"])
    if np.isfinite(row.get("oriented_rho", np.nan)):
        return float(row["oriented_rho"])
    return np.nan


def evaluate_shortlist(df: pd.DataFrame, group: str) -> pd.DataFrame:
    outcome_col, outcome_label = GROUP_OUTCOME[group]
    shortlist = GROUP_SHORTLIST[group]
    g = df[df["group"] == group].copy()
    early = g[g["band"] == "R1-3"]
    rows = []
    for col, label, direction in shortlist:
        if col not in g.columns:
            continue
        # Early-round selection sample
        early_s = spearman_controlled(early[col], early[outcome_col], early)
        # Full eligible sample, reported for transparency, not used to pick
        full_s = spearman_controlled(g[col], g[outcome_col], g)
        n_early = int(early[[col, outcome_col]].dropna().shape[0])
        n_full = int(g[[col, outcome_col]].dropna().shape[0])
        # Selection uses the early-round sample only. Full-sample
        # correlations are reported for transparency and cannot win.
        if n_early >= MIN_N_SELECT:
            used = "early_round"
        elif n_early >= MIN_N_REPORT or n_full >= MIN_N_REPORT:
            used = "reported_only"
        else:
            used = "insufficient_n"
        sign = 1 if direction > 0 else -1
        row = {
            "group": group,
            "outcome": outcome_col,
            "outcome_label": outcome_label,
            "measure": col,
            "measure_label": label,
            "direction": direction,
            "n_early": n_early,
            "n_full": n_full,
            "selection_sample": used,
            "raw_rho_early": early_s["rho"],
            "raw_p_early": early_s["p"],
            "partial_rho_early": early_s["partial_rho"],
            "partial_p_early": early_s["partial_p"],
            "yearpick_rho_early": early_s["partial_year_pick_rho"],
            "yearpick_p_early": early_s["partial_year_pick_p"],
            "raw_rho_full": full_s["rho"],
            "raw_p_full": full_s["p"],
            "partial_rho_full": full_s["partial_rho"],
            "partial_p_full": full_s["partial_p"],
            "yearpick_rho_full": full_s["partial_year_pick_rho"],
            "yearpick_p_full": full_s["partial_year_pick_p"],
        }
        # Oriented scores always come from early-round when available.
        row["oriented_rho"] = sign * early_s["rho"]
        row["oriented_partial_rho"] = sign * early_s["partial_rho"]
        row["oriented_p"] = early_s["partial_p"] if np.isfinite(early_s["partial_p"]) else early_s["p"]
        not_selectable = group in ("Edge", "Interior") and col in DL_NOT_SELECTABLE
        row["eligible_to_select"] = (
            used == "early_round"
            and (not not_selectable)
            and np.isfinite(selection_score(row))
        )
        rows.append(row)
    return pd.DataFrame(rows)


def choose_primary(short_df: pd.DataFrame, group: str) -> dict:
    cand = short_df[(short_df["group"] == group) & (short_df["eligible_to_select"])].copy()
    if cand.empty:
        # Fall back to the pre-declared first measure even if n is short,
        # and flag it.
        fallback = short_df[short_df["group"] == group].iloc[0].to_dict()
        fallback["chosen"] = True
        fallback["choice_reason"] = (
            "No shortlist measure cleared the n floor; defaulted to the "
            "first pre-declared measure. Treat as descriptive only."
        )
        fallback["weak_link"] = True
        return fallback
    cand = cand.copy()
    cand["score"] = cand.apply(selection_score, axis=1)
    cand = cand.sort_values("score", ascending=False)
    winner = cand.iloc[0].to_dict()
    # DL tie-break: keep the 10-yard split if it is close.
    if group in ("Edge", "Interior") and DL_PREFERRED in set(cand["measure"]):
        ten = cand[cand["measure"] == DL_PREFERRED].iloc[0]
        if np.isfinite(ten["score"]) and (winner["score"] - ten["score"]) <= DL_TIE_MARGIN:
            winner = ten.to_dict()
            winner["choice_reason"] = (
                f"Official 10-yard split kept as primary: it is the established "
                f"DL burst measure, and the early-round lead of any alternate "
                f"was at most {DL_TIE_MARGIN:.2f} Spearman ρ (small-n buffer)."
            )
        else:
            winner["choice_reason"] = (
                "Highest oriented pick-partial Spearman ρ on the early-round "
                "sample among the pre-declared shortlist (cleared the 10-yard tie-break)."
            )
    else:
        winner["choice_reason"] = (
            "Highest oriented pick-partial Spearman ρ on the early-round "
            "sample among the pre-declared shortlist."
        )
    winner["chosen"] = True
    score = winner.get("score", selection_score(winner))
    pval = winner.get("oriented_p", np.nan)
    winner["weak_link"] = (
        (not np.isfinite(score)) or (score < WEAK_LINK_RHO)
        or (np.isfinite(pval) and pval >= WEAK_LINK_P)
    )
    if winner["weak_link"]:
        winner["choice_reason"] += (
            " FLAG: the chosen measure is only weakly (or not clearly) related "
            "to the gameplay outcome on the early-round sample. Late-round 'gems' "
            "on this measure are a named shortlist, not evidence that the test "
            "identifies overperformers as a group."
        )
    return winner


def tag_group(df: pd.DataFrame, group: str, choice: dict) -> pd.DataFrame:
    outcome_col, outcome_label = GROUP_OUTCOME[group]
    g = df[df["group"] == group].copy()
    measure = choice["measure"]
    direction = int(choice["direction"])
    g = add_tertiles_and_z(g, measure, direction, "combine")
    g["outcome"] = g[outcome_col]
    g["outcome_label"] = outcome_label
    g["measure"] = measure
    g["measure_label"] = choice["measure_label"]
    g["measure_value"] = g[measure] if measure in g.columns else np.nan
    g["outcome_resid"] = pick_residual(g["outcome"], g["pick"])
    early_med = g.loc[g["band"] == "R1-3", "outcome"].median()
    g["early_median"] = early_med
    g["above_early_median"] = g["outcome"] > early_med
    g["over_slot"] = g["outcome_resid"] > 0
    g["is_late"] = g["band"] == "R4-7"
    g["is_udfa"] = g["band"] == "UDFA"
    g["is_gem"] = (
        (g["band"] == "R4-7")
        & (g["combine_band"] == "strong")
        & g["over_slot"]
        & g["outcome"].notna()
        & g["measure_value"].notna()
    )
    g["is_udfa_gem"] = (
        (g["band"] == "UDFA")
        & (g["combine_band"] == "strong")
        & g["over_slot"]
        & g["outcome"].notna()
        & g["measure_value"].notna()
    )
    g["draft_info"] = g.apply(fmt_draft, axis=1)
    g["choice_weak_link"] = bool(choice.get("weak_link", False))
    return g


def group_contrast(g: pd.DataFrame, group: str, choice: dict) -> dict:
    """Late-round strong vs weak on the chosen measure."""
    late = g[(g["band"] == "R4-7") & g["measure_value"].notna() & g["outcome"].notna()].copy()
    strong = late[late["combine_band"] == "strong"]["outcome"]
    weak = late[late["combine_band"] == "weak"]["outcome"]
    mid = late[late["combine_band"] == "middle"]["outcome"]
    out = {
        "group": group,
        "measure": choice["measure"],
        "measure_label": choice["measure_label"],
        "outcome": GROUP_OUTCOME[group][0],
        "outcome_label": GROUP_OUTCOME[group][1],
        "n_late": int(len(late)),
        "n_strong": int(len(strong)),
        "n_weak": int(len(weak)),
        "n_middle": int(len(mid)),
        "median_strong": float(strong.median()) if len(strong) else np.nan,
        "median_weak": float(weak.median()) if len(weak) else np.nan,
        "median_middle": float(mid.median()) if len(mid) else np.nan,
        "median_resid_strong": float(late.loc[late["combine_band"] == "strong", "outcome_resid"].median())
        if (late["combine_band"] == "strong").any() else np.nan,
        "median_resid_weak": float(late.loc[late["combine_band"] == "weak", "outcome_resid"].median())
        if (late["combine_band"] == "weak").any() else np.nan,
        "mw_u": np.nan, "mw_p": np.nan, "mw_note": "",
        "spearman_rho": np.nan, "spearman_p": np.nan,
        "spearman_partial_rho": np.nan, "spearman_partial_p": np.nan,
        "underpowered": False,
        "weak_link_flag": bool(choice.get("weak_link", False)),
    }
    if len(strong) < MIN_N_GROUP_CELL or len(weak) < MIN_N_GROUP_CELL:
        out["underpowered"] = True
        out["mw_note"] = (
            f"Underpowered: n_strong={len(strong)}, n_weak={len(weak)} "
            f"(need ≥{MIN_N_GROUP_CELL} in each tail)."
        )
    if len(strong) >= 3 and len(weak) >= 3:
        try:
            u, p = stats.mannwhitneyu(strong, weak, alternative="greater")
            out["mw_u"], out["mw_p"] = float(u), float(p)
        except ValueError:
            out["mw_note"] = (out["mw_note"] + " Mann-Whitney could not be computed.").strip()
    if len(late) >= MIN_N_REPORT:
        s = spearman_controlled(late["combine_z"], late["outcome"], late)
        out["spearman_rho"] = s["rho"]
        out["spearman_p"] = s["p"]
        out["spearman_partial_rho"] = s["partial_rho"]
        out["spearman_partial_p"] = s["partial_p"]
    # Sensitivity including UDFA
    late_u = g[g["band"].isin(["R4-7", "UDFA"]) & g["measure_value"].notna() & g["outcome"].notna()]
    st = late_u[late_u["combine_band"] == "strong"]["outcome"]
    wk = late_u[late_u["combine_band"] == "weak"]["outcome"]
    out["n_late_plus_udfa"] = int(len(late_u))
    out["n_strong_plus_udfa"] = int(len(st))
    out["n_weak_plus_udfa"] = int(len(wk))
    out["median_strong_plus_udfa"] = float(st.median()) if len(st) else np.nan
    out["median_weak_plus_udfa"] = float(wk.median()) if len(wk) else np.nan
    if len(st) >= 3 and len(wk) >= 3:
        try:
            u, p = stats.mannwhitneyu(st, wk, alternative="greater")
            out["mw_p_plus_udfa"] = float(p)
        except ValueError:
            out["mw_p_plus_udfa"] = np.nan
    else:
        out["mw_p_plus_udfa"] = np.nan
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
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "figure.titlesize": 14,
        "font.family": "DejaVu Sans",
    })


def annotate_names(ax, sub: pd.DataFrame, xcol: str, ycol: str, color: str) -> None:
    sub = sub.dropna(subset=[xcol, ycol]).sort_values(ycol, ascending=False)
    # Alternate offsets so stacked names (Cowing / Franklin / Lane) stay readable.
    offsets = [(6, 5), (6, -10), (-6, 5), (-6, -10), (8, 12), (8, -14)]
    for i, (_, r) in enumerate(sub.iterrows()):
        last = str(r["display_name"]).split()[-1]
        dx, dy = offsets[i % len(offsets)]
        ha = "left" if dx >= 0 else "right"
        ax.annotate(
            last, (r[xcol], r[ycol]),
            textcoords="offset points", xytext=(dx, dy),
            fontsize=7.5, color=color, fontweight="bold", ha=ha,
        )


def draw_figure(tagged: dict[str, pd.DataFrame], choices: dict[str, dict],
                contrasts: list[dict], path: Path) -> None:
    _style()
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.8))
    axes = axes.ravel()
    # 5 group panels + 1 summary bar panel
    for i, group in enumerate(GROUPS):
        ax = axes[i]
        g = tagged[group]
        color = GROUP_COLOR[group]
        late = g[g["band"] == "R4-7"]
        udfa = g[g["band"] == "UDFA"]
        early = g[g["band"] == "R1-3"]
        ax.scatter(
            early["combine_z"], early["outcome_resid"],
            s=22, c="#BBBBBB", alpha=0.55, zorder=2, label="R1–3 (context)",
            edgecolors="none",
        )
        ax.scatter(
            late["combine_z"], late["outcome_resid"],
            s=42, c=color, alpha=0.85, zorder=3, label="R4–7",
            edgecolors="white", linewidths=0.4,
        )
        ax.scatter(
            udfa["combine_z"], udfa["outcome_resid"],
            s=42, facecolors="none", edgecolors=color, linewidths=1.1,
            zorder=4, label="UDFA",
        )
        gems = g[g["is_gem"] | g["is_udfa_gem"]]
        if len(gems):
            ax.scatter(
                gems["combine_z"], gems["outcome_resid"],
                s=86, facecolors="none", edgecolors="#111111", linewidths=1.4,
                zorder=5, label="Gem",
            )
            annotate_names(ax, gems, "combine_z", "outcome_resid", "#111111")
        # Top-third threshold: z at the 2/3 percentile of oriented values
        z_cut = g.loc[g["combine_band"] == "strong", "combine_z"].min()
        if np.isfinite(z_cut):
            ax.axvline(z_cut, color="#888888", ls="--", lw=0.9, zorder=1)
        ax.axhline(0, color="#888888", ls=":", lw=0.9, zorder=1)
        meas = choice_label = choices[group]["measure_label"]
        out_lab = GROUP_OUTCOME[group][1]
        flag = "  ·  weak link" if choices[group].get("weak_link") else ""
        ax.set_title(f"{group}: {meas}{flag}", loc="left", pad=6)
        ax.set_xlabel("Combine z (higher = better)")
        ax.set_ylabel(f"{out_lab}\nvs draft slot")
        if i == 0:
            ax.legend(loc="lower left", fontsize=7, frameon=False)
    # Summary panel: group-test read-out (native units; no mixed-scale bars)
    ax = axes[5]
    ax.axis("off")
    ax.set_title("R4–7 strong vs weak, group test", loc="left", pad=6)
    header = ["Group", "Strong", "Weak", "n s/w", "MW p", "Flag"]
    rows = [header]
    for c in contrasts:
        ok = outcome_kind(c["group"])
        flag = []
        if c["weak_link_flag"]:
            flag.append("weak link")
        if c["underpowered"]:
            flag.append("n small")
        rows.append([
            c["group"],
            fmt_num(c["median_strong"], ok),
            fmt_num(c["median_weak"], ok),
            f"{c['n_strong']}/{c['n_weak']}",
            fmt_p(c["mw_p"]),
            ", ".join(flag) if flag else "—",
        ])
    table = ax.table(
        cellText=rows[1:], colLabels=rows[0],
        loc="upper center", cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    table.scale(1.05, 1.45)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#CCCCCC")
        if row == 0:
            cell.set_facecolor("#F2F2F2")
            cell.set_text_props(fontweight="bold")
        else:
            grp = rows[row][0]
            if col == 0:
                cell.set_text_props(fontweight="bold", color=GROUP_COLOR.get(grp, "#222222"))
    ax.text(
        0.0, 0.08,
        "Medians are the raw gameplay outcome\n"
        "(yards/route or a rate), rounds 4-7 only.\n"
        "MW is one-sided (strong > weak).\n"
        "Circled names at left made the shortlist:\n"
        "top-third tester and over their draft slot.",
        transform=ax.transAxes, fontsize=7.2, color="#444444", va="bottom",
    )
    fig.suptitle(
        "Late-round gems: top-third Combine testers who outplayed their draft slot",
        x=0.01, ha="left", fontsize=14, fontweight="bold",
    )
    fig.text(
        0.01, 0.008,
        "Strong = top third of the position (or Edge / Interior) on the chosen Combine measure, "
        "not the top third of late-round only.  Over slot = residual vs log draft pick (UDFA = 260).  "
        "Open circles are UDFAs.  Grey points are early-round context.  "
        "‘Weak link’ means the chosen measure is not clearly related to the gameplay outcome "
        "on the early-round sample — those shortlists are names, not a group-level finding.  "
        "CB/S outcomes are tackle / TFL rates only; this file has no targets or completions allowed.",
        fontsize=7.0, color="#444444", va="bottom", wrap=True,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    log(f"Wrote {path}")


def fmt_num(v, kind: str) -> str:
    if not pd.notna(v) or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    if kind == "rate":
        return f"{100 * float(v):.1f}%"
    if kind == "ypR":
        return f"{float(v):.2f}"
    if kind == "mph":
        return f"{float(v):.2f}"
    if kind == "time":
        return f"{float(v):.2f}"
    if kind == "int":
        return f"{int(round(float(v)))}"
    if kind == "resid":
        # rate residuals as percentage points when the outcome looks like a rate
        return f"{float(v):+.3f}"
    return f"{float(v):.3f}"


def outcome_kind(group: str) -> str:
    return {"WR": "ypR", "CB": "rate", "S": "rate", "Edge": "rate", "Interior": "rate"}[group]


def article_for(label: str) -> str:
    first = label.strip().split()[0].lower()
    return "an" if first[:1] in "aeiou" else "a"


def display_measure_value(measure: str, value):
    if measure in YDS_SPEED_MEASURES and pd.notna(value) and np.isfinite(float(value)):
        return float(value) * MPH
    return value


def measure_kind(measure: str) -> str:
    if measure in {"official_ten_yd", "official_forty", "three_cone", "short_shuttle"}:
        return "time"
    if measure in {"c_top_mph", "sunday_speed_mph", "ssoe_mph", "speed_1s_mph"} | YDS_SPEED_MEASURES:
        return "mph"
    if measure in {"bench_reps", "broad_jump", "vertical"}:
        return "int" if measure == "bench_reps" else "ypR"
    return "ypR"


def shortlist_table_md(g: pd.DataFrame, udfa: bool = False) -> str:
    flag = "is_udfa_gem" if udfa else "is_gem"
    gems = g[g[flag]].sort_values("outcome_resid", ascending=False)
    if gems.empty:
        return "_None in this sample._\n"
    group = gems["group"].iloc[0]
    okind = outcome_kind(group)
    meas_name = gems["measure"].iloc[0]
    mkind = measure_kind(meas_name)
    out_lab = gems["outcome_label"].iloc[0]
    meas_lab = gems["measure_label"].iloc[0]
    if meas_name in YDS_SPEED_MEASURES and not str(meas_lab).endswith("(mph)"):
        meas_lab = f"{meas_lab} (mph)"
    lines = [
        f"| Player | Draft | College | {meas_lab} | z | {out_lab} | vs slot | Opps | Above R1–3 median? |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in gems.iterrows():
        college = r["college_name"] if pd.notna(r.get("college_name")) else "—"
        above = "Yes" if bool(r["above_early_median"]) else "No"
        lines.append(
            f"| {r['display_name']} | {r['draft_info']} | {college} | "
            f"{fmt_num(display_measure_value(r['measure'], r['measure_value']), mkind)} | {fmt_num(r['combine_z'], 'resid')} | "
            f"{fmt_num(r['outcome'], okind)} | {fmt_num(r['outcome_resid'], 'resid')} | "
            f"{fmt_num(r['n_opps'], 'int')} | {above} |"
        )
    return "\n".join(lines) + "\n"


def companion_bits(r: pd.Series, group: str) -> str:
    bits = []
    for col, lab in GROUP_COMPANIONS[group]:
        if col not in r.index or not pd.notna(r[col]):
            continue
        if col in {"pressure_rate", "sack_rate", "tackle_rate", "tfl_rate", "deep_target_share"}:
            bits.append(f"{lab} {fmt_num(r[col], 'rate')}")
        elif col in {"sunday_speed_mph", "ssoe_mph", "speed_1s_mph"}:
            bits.append(f"{lab} {fmt_num(r[col], 'mph')}")
        else:
            bits.append(f"{lab} {fmt_num(r[col], 'ypR')}")
    return "; ".join(bits)


def write_markdown(path: Path, choices: dict, short_df: pd.DataFrame,
                   tagged: dict, contrasts: list[dict]) -> None:
    lines = []
    a = lines.append
    a("# Late-round gems — strong Combine testers who outplayed their draft slot")
    a("")
    a("Working note for the NFL Big Data Bowl 2027 Open Track entry. Official metric definitions live in `METRICS.md`. This page is a named shortlist plus an honest group-level check, not a new official metric.")
    a("")
    a("**Question.** Among later-round picks (rounds 4–7; undrafted players listed separately), who tested in the top third of their position on the Combine measure that best relates to that group's on-field gameplay, and then produced more than their draft slot predicted?")
    a("")
    a("**Definitions.**")
    a("")
    a("- **Later-round** means drafted in rounds 4–7. UDFAs (pick 260) are reported on their own, not mixed into the headline contrast.")
    a("- **Strong Combine** means the top third of *the whole position group* (Edge and Interior are split) on the chosen measure, not the top third of late-round players only. A late-round tester in the top third of his position is the interesting case.")
    a("- **Overperformed** means a positive residual after a linear fit of the group's primary gameplay outcome on log draft pick, fit on every eligible player at that group (UDFA = 260). Beating the rounds 1–3 median at the position is a second, stricter badge; it is not required to make the shortlist.")
    a("- **Primary outcomes** are on-field gameplay, not playing time: yards per route for receivers (≥20 regular-season routes that stood); pressure rate for Edge and Interior (≥20 pass-rush snaps); tackle involvement rate for corners and safeties (≥50 defensive snaps). CB/S coverage outcomes (targets or completions allowed, PBUs, INTs) are not in this file and were not invented. Playing time is context only.")
    a("")
    a("## 1. How the Combine measure was chosen")
    a("")
    a("Each group had a **pre-declared shortlist**. The primary measure is the shortlist entry with the highest *oriented* pick-partial Spearman ρ (better Combine number ↔ better gameplay) on the **early-round (R1–3)** sample, and only if that sample has at least 12 players with both the test and the outcome. That keeps the selection step off the late-round contrast we then test. Measures that miss the early-round n floor are still shown in the correlation table; they cannot be chosen. Full-sample correlations are for transparency only — they cannot win, because they would peek at the late-round players we then test.")
    a("")
    a("For Edge and Interior, the official 10-yard split is the established burst measure from the earlier get-off work. An alternate (3-cone, broad jump, or bench) had to beat it by more than 0.10 ρ on the early-round sample to take its place — a small-n buffer, not a claim that the measures are equal. The official 40 time is listed because it is a cousin of the 10-yard split; it is not allowed to replace it.")
    a("")
    a("**This is a selection step.** The winning correlation was chosen after looking at a shortlist. Do not read it as an independent confirmatory test. The late-round strong-vs-weak contrast is the check that uses a held-out draft band; even that is a small-sample descriptive test, not a new official finding.")
    a("")
    a("Sunday Speed and SSOE are game measures, not Combine inputs. They appear on the receiver and DB cards as companions. They were not candidates for “strong Combine.”")
    a("")

    a("### Chosen measure, by group")
    a("")
    a("| Group | Primary outcome | Chosen measure | Selection sample | n | Oriented pick-partial ρ | p | Why | Weak link? |")
    a("|---|---|---|---|---:|---:|---:|---|---|")
    for group in GROUPS:
        ch = choices[group]
        n = ch["n_early"] if ch.get("selection_sample") == "early_round" else ch["n_full"]
        a(
            f"| {group} | {ch['outcome_label']} | **{ch['measure_label']}** | "
            f"{ch.get('selection_sample', '—')} | {n} | "
            f"{fmt_rho(ch.get('oriented_partial_rho', np.nan))} | "
            f"{fmt_p(ch.get('oriented_p', np.nan)) if np.isfinite(ch.get('oriented_p', np.nan)) else 'NA'} | "
            f"{ch.get('choice_reason', '').split('FLAG:')[0].strip()} | "
            f"{'Yes' if ch.get('weak_link') else 'No'} |"
        )
    a("")

    a("### Full shortlist correlations")
    a("")
    a("Oriented ρ is flipped so that a positive number always means “better Combine test, better gameplay.” Early-round columns are the selection sample. Full-sample columns are for transparency only.")
    a("")
    a("| Group | Measure | n early | Early raw ρ | Early pick-partial ρ (p) | n full | Full pick-partial ρ (p) | Eligible to select | Chosen? |")
    a("|---|---|---:|---:|---|---:|---|---|---|")
    for _, r in short_df.iterrows():
        sign = 1 if int(r["direction"]) > 0 else -1
        early_part = sign * r["partial_rho_early"] if np.isfinite(r["partial_rho_early"]) else np.nan
        full_part = sign * r["partial_rho_full"] if np.isfinite(r["partial_rho_full"]) else np.nan
        chosen = "Yes" if (
            r["measure"] == choices[r["group"]]["measure"] and r["group"] in choices
        ) else ""
        a(
            f"| {r['group']} | {r['measure_label']} | {int(r['n_early'])} | "
            f"{fmt_rho(sign * r['raw_rho_early'] if np.isfinite(r['raw_rho_early']) else np.nan)} | "
            f"{fmt_rho(early_part)} ({fmt_p(r['partial_p_early'])}) | {int(r['n_full'])} | "
            f"{fmt_rho(full_part)} ({fmt_p(r['partial_p_full'])}) | "
            f"{'Yes' if r['eligible_to_select'] else 'No'} | {chosen} |"
        )
    a("")

    a("## 2. Do late-round strong testers outperform late-round weak testers as a group?")
    a("")
    a("Sample: rounds 4–7 only, eligible gameplay floor, with a value on the chosen measure. Strong = top third of the *position*, weak = bottom third of the position. Mann-Whitney is one-sided (strong > weak). Spearman is the chosen measure's oriented z vs the raw outcome, also inside rounds 4–7, with a pick-partial column. Cells with fewer than 5 players in either tail are marked underpowered. A “weak link” group is one where the measure itself barely relates to the outcome — a null or noisy contrast is the expected result, not a surprise.")
    a("")
    a("| Group | Measure | n late (strong / mid / weak) | Median strong | Median weak | MW p (strong > weak) | Late Spearman ρ (p) | Late pick-partial ρ (p) | Notes |")
    a("|---|---|---|---:|---:|---:|---|---|---|")
    for c in contrasts:
        notes = []
        if c["underpowered"]:
            notes.append("underpowered")
        if c["weak_link_flag"]:
            notes.append("weak link")
        if c.get("mw_note") and not c["underpowered"]:
            notes.append(c["mw_note"])
        a(
            f"| {c['group']} | {c['measure_label']} | {c['n_late']} "
            f"({c['n_strong']} / {c['n_middle']} / {c['n_weak']}) | "
            f"{fmt_num(c['median_strong'], outcome_kind(c['group']))} | "
            f"{fmt_num(c['median_weak'], outcome_kind(c['group']))} | "
            f"{fmt_p(c['mw_p'])} | "
            f"{fmt_rho(c['spearman_rho'])} ({fmt_p(c['spearman_p'])}) | "
            f"{fmt_rho(c['spearman_partial_rho'])} ({fmt_p(c['spearman_partial_p'])}) | "
            f"{'; '.join(notes) if notes else '—'} |"
        )
    a("")
    a("The late-round receiver contrast leans the expected way (median yards per route 0.99 for strong official-40 testers vs 0.74 for weak, one-sided Mann-Whitney p=0.086) but we will not promote it. Official 40 time was a weak-link pick from a null shortlist, the early-round relationship was ρ=+0.10 (p=0.61), and p=0.086 on 11 vs 9 players is still a lean, not a finding.")
    a("")
    a("One reported-only lead: Interior 3-cone vs pressure rate is ρ=+0.64 (p=0.007) on the full eligible sample (n=16), but only seven early-round interior players ran the 3-cone, so it could not be selected. That is a lead for a later look, not a chosen primary.")
    a("")
    a("Sensitivity including UDFAs is in `out/late_round_gems_tests.csv`. Do not overclaim a group effect when n is small, when the p-value is modest, or when the selection step already flagged a weak link.")
    a("")

    a("## 3. Named shortlists (rounds 4–7)")
    a("")
    a("A player makes this list if he was drafted in rounds 4–7, tested in the top third of his position on the chosen measure, and posted a positive draft-slot residual on the primary gameplay outcome. Names are ordered by residual, not by Combine z. Limited opportunity counts (just-cleared floors) should be read as early looks, not finished grades.")
    a("")
    for group in GROUPS:
        ch = choices[group]
        a(f"### {group} — {ch['measure_label']}")
        a("")
        if ch.get("weak_link"):
            a(f"*The {group} measure is only weakly related to {ch['outcome_label']} on the selection sample. These are named over-slot testers, not a group-level recommendation.*")
            a("")
        a(shortlist_table_md(tagged[group], udfa=False))
        gems = tagged[group][tagged[group]["is_gem"]].sort_values("outcome_resid", ascending=False)
        strong_late = tagged[group][
            (tagged[group]["band"] == "R4-7") & (tagged[group]["combine_band"] == "strong")
            & tagged[group]["measure_value"].notna()
        ].sort_values("outcome_resid", ascending=False)
        if gems.empty and len(strong_late):
            names = []
            for _, r in strong_late.iterrows():
                names.append(
                    f"{r['display_name']} ({r['draft_info']}, "
                    f"{fmt_num(r['outcome'], outcome_kind(group))} "
                    f"{GROUP_OUTCOME[group][1].lower()}, residual "
                    f"{fmt_num(r['outcome_resid'], 'resid')})"
                )
            a(
                "No late-round player in this group cleared both cuts. "
                "Top-third testers who did not beat their draft-slot expectation: "
                + "; ".join(names) + "."
            )
            a("")
        if len(gems):
            a("Why they stand out:")
            a("")
            for _, r in gems.head(5).iterrows():
                extra = companion_bits(r, group)
                extra_s = f" Companions: {extra}." if extra else ""
                early_badge = " Also above the rounds 1–3 median at the position." if r["above_early_median"] else ""
                a(
                    f"- **{r['display_name']}** ({r['draft_info']}) posted "
                    f"{fmt_num(r['outcome'], outcome_kind(group))} {GROUP_OUTCOME[group][1].lower()} "
                    f"against a draft-slot expectation, residual {fmt_num(r['outcome_resid'], 'resid')}, "
                    f"with {article_for(ch['measure_label'])} {ch['measure_label'].lower()} of {fmt_num(display_measure_value(ch['measure'], r['measure_value']), measure_kind(ch['measure']))} "
                    f"(z {fmt_num(r['combine_z'], 'resid')}) on {fmt_num(r['n_opps'], 'int')} {r['opp_label']}."
                    f"{early_badge}{extra_s}"
                )
            a("")

    a("## 4. Undrafted players (separate list)")
    a("")
    a("Same rules as above, but UDFA only. These names are not in the rounds 4–7 group test.")
    a("")
    any_udfa = False
    for group in GROUPS:
        gems = tagged[group][tagged[group]["is_udfa_gem"]]
        if gems.empty:
            continue
        any_udfa = True
        ch = choices[group]
        a(f"### {group} UDFAs — {ch['measure_label']}")
        a("")
        a(shortlist_table_md(tagged[group], udfa=True))
        for _, r in gems.sort_values("outcome_resid", ascending=False).iterrows():
            extra = companion_bits(r, group)
            extra_s = f" Companions: {extra}." if extra else ""
            a(
                f"- **{r['display_name']}** (UDFA) posted "
                f"{fmt_num(r['outcome'], outcome_kind(group))} {GROUP_OUTCOME[group][1].lower()}, "
                f"residual {fmt_num(r['outcome_resid'], 'resid')}, "
                f"{ch['measure_label'].lower()} {fmt_num(display_measure_value(ch['measure'], r['measure_value']), measure_kind(ch['measure']))} "
                f"(z {fmt_num(r['combine_z'], 'resid')}) on {fmt_num(r['n_opps'], 'int')} {r['opp_label']}."
                f"{extra_s}"
            )
        a("")
    if not any_udfa:
        a("No UDFA in this sample cleared both the top-third Combine cut and a positive draft-slot residual at the gameplay floor.")
        a("")

    a("## 5. Limits")
    a("")
    a("- Sample sizes in a single draft band, at a single position, are small. A one-or-two-player shortlist can move with one more season of snaps or one more Combine time.")
    a("- The measure was chosen from a shortlist. That inflates the apparent relationship on the selection sample. The late-round contrast is the cleaner check, and even that is modest n.")
    a("- Shuttle and 3-cone are missing for most corners and safeties in this cohort, so those classic COD tests usually cannot be the primary measure here.")
    a("- Receiver production still has the same honest limit as the main writeup: even the best speed test in this file has not been a reliable yards-per-route predictor after draft slot and Holm correction. A late-round receiver gem is a named over-slot player who also tested well, not proof that paying for that test finds producers.")
    a("- Corner and safety 'success' here is tackle involvement and tackles for loss. That is what the file gives us. It is not a coverage grade.")
    a("- Defensive-line pressure has no blocker or QB track. Get-off and pressure are still associations.")
    a("- Career length differs by draft year (2023 rookies have three seasons, 2025 rookies have one). Rate outcomes and the draft-pick residual do not fully remove that.")
    a("")
    a("Figure: `out/figs/fig8_late_round_gems.png`. Player-level table: `out/late_round_gems.csv`. Selection and group tests: `out/late_round_gems_tests.csv`.")
    a("")
    path.write_text("\n".join(lines), encoding="utf-8")
    log(f"Wrote {path}")


def player_row(r: pd.Series) -> dict:
    out = {
        "nfl_id": r.get("nfl_id"),
        "display_name": r.get("display_name"),
        "group": r.get("group"),
        "college_name": r.get("college_name"),
        "draft_year": r.get("draft_year"),
        "draft_round": r.get("draft_round"),
        "draft_overall_pick": r.get("draft_overall_pick"),
        "pick": r.get("pick"),
        "draft_info": r.get("draft_info"),
        "band": r.get("band"),
        "measure": r.get("measure"),
        "measure_label": r.get("measure_label"),
        "measure_value": r.get("measure_value"),
        "combine_z": r.get("combine_z"),
        "combine_pct": r.get("combine_pct"),
        "combine_band": r.get("combine_band"),
        "outcome": r.get("outcome"),
        "outcome_label": r.get("outcome_label"),
        "outcome_resid": r.get("outcome_resid"),
        "early_median": r.get("early_median"),
        "above_early_median": r.get("above_early_median"),
        "over_slot": r.get("over_slot"),
        "is_gem": bool(r.get("is_gem", False)),
        "is_udfa_gem": bool(r.get("is_udfa_gem", False)),
        "n_opps": r.get("n_opps"),
        "opp_label": r.get("opp_label"),
        "choice_weak_link": r.get("choice_weak_link"),
    }
    for col in [
        "yards_per_route", "deep_yards_per_deep_route", "deep_target_share",
        "sunday_speed_mph", "ssoe_mph", "tackle_rate", "tfl_rate",
        "pressure_rate", "sack_rate", "speed_1s_mph", "snaps_per_game",
        "start_rate", "n_routes", "n_deep_routes", "n_def_snaps", "n_rush_plays",
        "official_ten_yd", "official_forty", "c_top_mph", "vertical",
        "broad_jump", "three_cone", "short_shuttle", "bench_reps",
        "db_gauntlet_max_s", "db_bp45_max_s",
    ]:
        if col in r.index:
            out[col] = r[col]
    return out


def main() -> None:
    skill, dl = load_tables()
    log(f"Eligible skill players: {len(skill)} "
        f"({skill.groupby('group').size().to_dict()})")
    log(f"Eligible DL: {len(dl)} ({dl.groupby('group').size().to_dict()})")

    frames = {
        "WR": skill, "CB": skill, "S": skill,
        "Edge": dl, "Interior": dl,
    }

    short_parts = []
    choices: dict[str, dict] = {}
    tagged: dict[str, pd.DataFrame] = {}
    contrasts: list[dict] = []

    for group in GROUPS:
        sdf = evaluate_shortlist(frames[group], group)
        short_parts.append(sdf)
        ch = choose_primary(sdf, group)
        choices[group] = ch
        log(
            f"{group}: chose {ch['measure_label']} "
            f"(sample={ch.get('selection_sample')}, "
            f"oriented partial ρ={fmt_rho(ch.get('oriented_partial_rho', np.nan))}, "
            f"weak_link={ch.get('weak_link')})"
        )
        g = tag_group(frames[group], group, ch)
        tagged[group] = g
        c = group_contrast(g, group, ch)
        contrasts.append(c)
        n_gems = int(g["is_gem"].sum())
        n_udfa = int(g["is_udfa_gem"].sum())
        log(
            f"  late n={c['n_late']} strong/weak={c['n_strong']}/{c['n_weak']} "
            f"MW p={fmt_p(c['mw_p'])}  gems={n_gems} udfa_gems={n_udfa}"
        )

    short_df = pd.concat(short_parts, ignore_index=True)
    # Mark chosen on the shortlist table
    short_df["chosen"] = False
    for group, ch in choices.items():
        short_df.loc[
            (short_df["group"] == group) & (short_df["measure"] == ch["measure"]),
            "chosen",
        ] = True

    player_rows = [player_row(r) for g in tagged.values() for _, r in g.iterrows()]
    players = pd.DataFrame(player_rows).sort_values(
        ["group", "is_gem", "is_udfa_gem", "outcome_resid"],
        ascending=[True, False, False, False],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    players_path = OUT / "late_round_gems.csv"
    players.to_csv(players_path, index=False)
    log(f"Wrote {players_path} ({len(players)} rows, "
        f"{int(players.is_gem.sum())} R4-7 gems, "
        f"{int(players.is_udfa_gem.sum())} UDFA gems)")

    # Tests file: shortlist rows + contrast rows in one tidy frame with a section column
    t1 = short_df.copy()
    t1.insert(0, "section", "measure_selection")
    t2 = pd.DataFrame(contrasts)
    t2.insert(0, "section", "late_round_contrast")
    tests = pd.concat([t1, t2], ignore_index=True, sort=False)
    tests_path = OUT / "late_round_gems_tests.csv"
    tests.to_csv(tests_path, index=False)
    log(f"Wrote {tests_path}")

    fig_path = FIGS / "fig8_late_round_gems.png"
    draw_figure(tagged, choices, contrasts, fig_path)
    write_markdown(ROOT / "LATE_ROUND_GEMS.md", choices, short_df, tagged, contrasts)
    log("Done.")


if __name__ == "__main__":
    main()
