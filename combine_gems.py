#!/usr/bin/env python3
"""Combine Gems — BDB 2027.

Named overperformers at every draft slot: players who tested in the top
third of their position on a pre-declared Combine measure and then beat
the gameplay residual expected from their draft pick.

This replaces the earlier late-round-only (R4–7) shortlist. Rounds are
no longer split. Every eligible drafted player (rounds 1–7) and every
eligible UDFA is in the same list. UDFAs are flagged in a column, not
held out as a separate tier. UDFA draft-slot value is pick 260, the
slot after a seven-round draft, used consistently in the residual fit.

Pre-declared measures (not re-selected on this sample):
    DL  official 10-yard split   (within-subtype z / tertiles)
    WR  official 40 time
    CB  broad jump
    S   gauntlet drill top speed

These match the measures used in the earlier late-round writeup. Full-
sample correlations are reported for transparency. That is a selection
caveat, not a confirmatory test: we did not hold out a draft band, and
we did not fish a new winner here.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/combine_gems.py
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
MIN_N_REPORT = 8
MIN_N_GROUP_CELL = 5
MPH = 2.0455
YDS_SPEED_MEASURES = {"db_gauntlet_max_s", "db_bp45_max_s", "db_w_max_s", "wr_go_max_s"}

# Residual flag for a "weak" pre-declared link (descriptive, does not
# change the measure).
WEAK_LINK_RHO = 0.20
WEAK_LINK_P = 0.10

GROUPS = ["WR", "CB", "S", "DL"]
GROUP_COLOR = {
    "WR": "#0072B2",
    "CB": "#D55E00",
    "S": "#009E73",
    "DL": "#333333",
}
DL_SUBTYPE_COLOR = {"Edge": "#D55E00", "Interior": "#0072B2"}
GROUP_OUTCOME = {
    "WR": ("yards_per_route", "Yards per route"),
    "CB": ("tackle_rate", "Tackle involvement rate"),
    "S": ("tackle_rate", "Tackle involvement rate"),
    "DL": ("pressure_rate", "Pressure rate"),
}
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
    "DL": [
        ("sack_rate", "Sack rate"),
        ("speed_1s_mph", "Get-off: speed at 1.0s (mph)"),
        ("snaps_per_game", "Defensive snaps / game"),
    ],
}

# Pre-declared primary per group. direction = sign of a *good* raw number
# (−1 = lower is better).
GROUP_PRIMARY = {
    "WR": ("official_forty", "Official 40 time", -1),
    "CB": ("broad_jump", "Broad jump", +1),
    "S": ("db_gauntlet_max_s", "Gauntlet drill top speed", +1),
    "DL": ("official_ten_yd", "Official 10-yard split", -1),
}

# Companion Combine tests reported for transparency only.
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
GROUP_SHORTLIST = {
    "WR": WR_SHORTLIST,
    "CB": DB_SHORTLIST,
    "S": DB_SHORTLIST,
    "DL": DL_SHORTLIST,
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


def year_pick_residual(y: pd.Series, pick: pd.Series, draft_year: pd.Series) -> pd.Series:
    """Outcome residual after year + log draft pick (UDFA = 260)."""
    d = pd.DataFrame({"y": y, "pick": pick, "draft_year": draft_year}).dropna()
    out = pd.Series(np.nan, index=y.index, dtype=float)
    if len(d) < 8 or d["pick"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    controls = year_pick_controls(d)
    X = controls.to_numpy(dtype=float)
    if np.unique(X, axis=0).shape[0] < 2:
        return out
    out.loc[d.index] = _residualize(d["y"].to_numpy(dtype=float), X)
    return out


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


def add_tertiles_and_z(df: pd.DataFrame, col: str, direction: int, prefix: str,
                       by: str | None = None) -> pd.DataFrame:
    """Tertiles and z-score, oriented so higher = better.

    If `by` is set (for DL: subtype), z-scores and top/bottom thirds are
    computed *within* that column. That keeps interior rushers from being
    graded against edges on a raw 10-yard time.
    """
    out = df.copy()
    oriented = oriented_value(out[col], direction)
    z = pd.Series(np.nan, index=out.index, dtype=float)
    ranks = pd.Series(np.nan, index=out.index, dtype=float)
    if by and by in out.columns:
        for _, idx in out.groupby(by, dropna=False).groups.items():
            ix = list(idx)
            sub = oriented.loc[ix]
            mu = sub.mean(skipna=True)
            sd = sub.std(skipna=True, ddof=1)
            if pd.notna(sd) and sd > 0:
                z.loc[ix] = (sub - mu) / sd
            ranks.loc[ix] = sub.rank(method="average", pct=True)
    else:
        mu = oriented.mean(skipna=True)
        sd = oriented.std(skipna=True, ddof=1)
        if pd.notna(sd) and sd > 0:
            z = (oriented - mu) / sd
        ranks = oriented.rank(method="average", pct=True)
    out[f"{prefix}_z"] = z
    out[f"{prefix}_pct"] = ranks
    band = pd.Series(np.nan, index=out.index, dtype=object)
    has = oriented.notna() & ranks.notna()
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
    if "college_name" not in skill.columns:
        skill = skill.merge(pl[["nfl_id", "college_name"]], on="nfl_id", how="left")
    skill["pick"] = skill["pick"].fillna(UDFA_PICK)
    skill["is_udfa"] = skill["draft_round"].isna()
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
    dl["is_udfa"] = dl["draft_round"].isna()
    dl = dl[dl["n_rush_plays"] >= MIN_DL_RUSH].copy()
    dl["group"] = "DL"
    dl["pos_group"] = "DL"
    dl["eligible"] = True
    dl["n_opps"] = dl["n_rush_plays"]
    dl["opp_label"] = "pass-rush snaps"
    if "display_name" not in dl.columns and "player_name" in dl.columns:
        dl["display_name"] = dl["player_name"]

    skill_out = pd.concat([wr, dbs], ignore_index=True)
    return skill_out, dl


def evaluate_shortlist(df: pd.DataFrame, group: str) -> pd.DataFrame:
    """Full-sample correlations for the pre-declared shortlist (transparency)."""
    outcome_col, outcome_label = GROUP_OUTCOME[group]
    shortlist = GROUP_SHORTLIST[group]
    primary = GROUP_PRIMARY[group][0]
    g = df[df["group"] == group].copy()
    rows = []
    for col, label, direction in shortlist:
        if col not in g.columns:
            continue
        full_s = spearman_controlled(g[col], g[outcome_col], g)
        n_full = int(g[[col, outcome_col]].dropna().shape[0])
        sign = 1 if direction > 0 else -1
        row = {
            "section": "measure_correlations",
            "group": group,
            "outcome": outcome_col,
            "outcome_label": outcome_label,
            "measure": col,
            "measure_label": label,
            "direction": direction,
            "n_full": n_full,
            "raw_rho_full": full_s["rho"],
            "raw_p_full": full_s["p"],
            "partial_rho_full": full_s["partial_rho"],
            "partial_p_full": full_s["partial_p"],
            "yearpick_rho_full": full_s["partial_year_pick_rho"],
            "yearpick_p_full": full_s["partial_year_pick_p"],
            "oriented_rho": sign * full_s["rho"],
            "oriented_partial_rho": sign * full_s["partial_rho"],
            "oriented_yearpick_rho": sign * full_s["partial_year_pick_rho"],
            "oriented_p": (
                full_s["partial_year_pick_p"]
                if np.isfinite(full_s["partial_year_pick_p"])
                else full_s["partial_p"] if np.isfinite(full_s["partial_p"])
                else full_s["p"]
            ),
            "predeclared": col == primary,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def primary_choice(short_df: pd.DataFrame, group: str) -> dict:
    col, label, direction = GROUP_PRIMARY[group]
    sub = short_df[short_df["measure"] == col]
    if len(sub):
        winner = sub.iloc[0].to_dict()
    else:
        winner = {
            "group": group,
            "measure": col,
            "measure_label": label,
            "direction": direction,
            "n_full": 0,
            "oriented_yearpick_rho": np.nan,
            "oriented_partial_rho": np.nan,
            "oriented_p": np.nan,
        }
    winner["chosen"] = True
    winner["measure"] = col
    winner["measure_label"] = label
    winner["direction"] = direction
    score = winner.get("oriented_yearpick_rho", np.nan)
    if not np.isfinite(score):
        score = winner.get("oriented_partial_rho", np.nan)
    pval = winner.get("oriented_p", np.nan)
    winner["weak_link"] = (
        (not np.isfinite(score)) or (score < WEAK_LINK_RHO)
        or (np.isfinite(pval) and pval >= WEAK_LINK_P)
    )
    winner["choice_reason"] = (
        f"Pre-declared primary for {group}: {label}. Not re-selected on this "
        f"sample. Full-sample correlations are reported for transparency."
    )
    if winner["weak_link"]:
        winner["choice_reason"] += (
            " FLAG: on the full eligible sample this measure is only weakly "
            "(or not clearly) related to the gameplay outcome. Names on this "
            "list are a named shortlist, not evidence that the test identifies "
            "overperformers as a group."
        )
    return winner


def tag_group(df: pd.DataFrame, group: str, choice: dict) -> pd.DataFrame:
    outcome_col, outcome_label = GROUP_OUTCOME[group]
    g = df[df["group"] == group].copy()
    measure = choice["measure"]
    direction = int(choice["direction"])
    by = "subtype" if group == "DL" and "subtype" in g.columns else None
    g = add_tertiles_and_z(g, measure, direction, "combine", by=by)
    g["outcome"] = g[outcome_col]
    g["outcome_label"] = outcome_label
    g["measure"] = measure
    g["measure_label"] = choice["measure_label"]
    g["measure_value"] = g[measure] if measure in g.columns else np.nan
    # Draft-slot expectation: residual vs log pick, fit on every eligible
    # player in the group, including UDFAs at pick 260.
    g["outcome_resid"] = pick_residual(g["outcome"], g["pick"])
    g["outcome_resid_yearpick"] = year_pick_residual(
        g["outcome"], g["pick"], g["draft_year"]
    )
    g["over_slot"] = g["outcome_resid"] > 0
    g["is_udfa"] = g["draft_round"].isna() if "is_udfa" not in g.columns else g["is_udfa"]
    g["is_gem"] = (
        (g["combine_band"] == "strong")
        & g["over_slot"]
        & g["outcome"].notna()
        & g["measure_value"].notna()
    )
    g["draft_info"] = g.apply(fmt_draft, axis=1)
    g["choice_weak_link"] = bool(choice.get("weak_link", False))
    return g


def _mw(strong: pd.Series, weak: pd.Series) -> tuple[float, float, str]:
    if len(strong) < MIN_N_GROUP_CELL or len(weak) < MIN_N_GROUP_CELL:
        note = (
            f"Underpowered: n_strong={len(strong)}, n_weak={len(weak)} "
            f"(need ≥{MIN_N_GROUP_CELL} in each tail)."
        )
        return np.nan, np.nan, note
    try:
        u, p = stats.mannwhitneyu(
            strong.to_numpy(dtype=float),
            weak.to_numpy(dtype=float),
            alternative="greater",
        )
        return float(u), float(p), ""
    except ValueError:
        return np.nan, np.nan, "Mann-Whitney failed."


def group_contrast(g: pd.DataFrame, group: str, choice: dict,
                   subtype: str | None = None) -> dict:
    """Strong vs weak testers across all eligible players (including UDFA).

    Mann-Whitney is one-sided (strong > weak) on the year+pick residual.
    Raw-outcome medians are reported as a companion.
    """
    frame = g[g["measure_value"].notna() & g["outcome"].notna()].copy()
    if subtype and "subtype" in frame.columns:
        frame = frame[frame["subtype"] == subtype]
    strong = frame[frame["combine_band"] == "strong"]
    weak = frame[frame["combine_band"] == "weak"]
    mid = frame[frame["combine_band"] == "middle"]

    mw_u, mw_p, mw_note = _mw(strong["outcome_resid_yearpick"], weak["outcome_resid_yearpick"])
    # Companion MW on the raw outcome, for the log.
    _, mw_p_raw, _ = _mw(strong["outcome"], weak["outcome"])

    def _med(s: pd.Series) -> float:
        return float(s.median()) if len(s) else np.nan

    # Spearman of oriented combine z vs outcome, and vs year+pick residual.
    spear = {"rho": np.nan, "p": np.nan}
    if len(frame) >= MIN_N_REPORT and frame["combine_z"].nunique() >= 2:
        rho, p = stats.spearmanr(frame["combine_z"], frame["outcome"])
        spear = {"rho": float(rho), "p": float(p)}
    spear_r = {"rho": np.nan, "p": np.nan}
    dres = frame[["combine_z", "outcome_resid_yearpick"]].dropna()
    if len(dres) >= MIN_N_REPORT and dres["combine_z"].nunique() >= 2:
        rho, p = stats.spearmanr(dres["combine_z"], dres["outcome_resid_yearpick"])
        spear_r = {"rho": float(rho), "p": float(p)}

    n_udfa = int(frame["is_udfa"].sum()) if "is_udfa" in frame.columns else 0
    return {
        "section": "group_contrast",
        "group": group,
        "subgroup": subtype or group,
        "measure": choice["measure"],
        "measure_label": choice["measure_label"],
        "outcome": GROUP_OUTCOME[group][0],
        "outcome_label": GROUP_OUTCOME[group][1],
        "n": int(len(frame)),
        "n_strong": int(len(strong)),
        "n_weak": int(len(weak)),
        "n_middle": int(len(mid)),
        "n_udfa": n_udfa,
        "median_strong": _med(strong["outcome"]),
        "median_weak": _med(weak["outcome"]),
        "median_middle": _med(mid["outcome"]),
        "median_resid_strong": _med(strong["outcome_resid"]),
        "median_resid_weak": _med(weak["outcome_resid"]),
        "median_yearpick_resid_strong": _med(strong["outcome_resid_yearpick"]),
        "median_yearpick_resid_weak": _med(weak["outcome_resid_yearpick"]),
        "mw_u": mw_u,
        "mw_p": mw_p,
        "mw_p_raw": mw_p_raw,
        "mw_note": mw_note,
        "spearman_rho": spear["rho"],
        "spearman_p": spear["p"],
        "spearman_yearpick_resid_rho": spear_r["rho"],
        "spearman_yearpick_resid_p": spear_r["p"],
        "underpowered": len(strong) < MIN_N_GROUP_CELL or len(weak) < MIN_N_GROUP_CELL,
        "weak_link_flag": bool(choice.get("weak_link", False)),
    }


def measure_kind(measure: str) -> str:
    if measure in YDS_SPEED_MEASURES:
        return "mph"
    if measure in {"official_forty", "official_ten_yd", "three_cone", "short_shuttle"}:
        return "time"
    if measure == "broad_jump":
        return "int"
    if measure == "vertical":
        return "vert"
    if measure == "bench_reps":
        return "int"
    return "num"


def display_measure_value(measure: str, value) -> float:
    if pd.isna(value):
        return np.nan
    v = float(value)
    if measure in YDS_SPEED_MEASURES:
        return v * MPH
    return v


def fmt_num(v, kind: str) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    if kind == "time":
        return f"{v:.2f}"
    if kind == "mph":
        return f"{v:.2f}"
    if kind == "int":
        return f"{int(round(v))}"
    if kind == "vert":
        return f"{v:.1f}"
    if kind == "rate":
        return f"{v:.1%}"
    if kind == "resid":
        return f"{v:+.3f}"
    if kind == "ypr":
        return f"{v:.2f}"
    return f"{v:.2f}"


def outcome_kind(group: str) -> str:
    return "ypr" if group == "WR" else "rate"


def article_for(label: str) -> str:
    return "an" if label[:1].lower() in "aeiou" else "a"


def companion_bits(r: pd.Series, group: str) -> str:
    parts = []
    for col, lab in GROUP_COMPANIONS[group]:
        if col not in r.index or pd.isna(r[col]):
            continue
        val = r[col]
        if col in {"sack_rate", "tfl_rate", "deep_target_share"}:
            parts.append(f"{lab} {fmt_num(val, 'rate')}")
        else:
            parts.append(f"{lab} {fmt_num(val, 'num')}")
    return "; ".join(parts)


def chop_placement(dl: pd.DataFrame) -> dict:
    """Always report where Chop Robinson lands, gem or not."""
    hit = dl[dl["display_name"].str.fullmatch(r"Chop Robinson", case=False, na=False)]
    if hit.empty:
        hit = dl[dl["display_name"].str.contains("Chop Robinson", case=False, na=False)]
    if hit.empty:
        return {"found": False, "note": "Chop Robinson was not in the eligible DL table."}
    r = hit.iloc[0]
    band = r.get("combine_band")
    resid = r.get("outcome_resid")
    is_gem = bool(r.get("is_gem"))
    if is_gem:
        status = "GEM — top-third (within Edge) official 10-yard split and a positive draft-slot residual."
    elif band == "strong" and pd.notna(resid) and resid <= 0:
        status = "Strong split (top third within Edge) but did not beat his draft-slot expectation."
    elif band == "strong":
        status = "Strong split (top third within Edge); residual could not be computed."
    elif band == "middle":
        status = "Official 10-yard split is in the middle third within Edge."
    elif band == "weak":
        status = "Official 10-yard split is in the bottom third within Edge."
    else:
        status = "No official 10-yard split, or not in the tertile sample."
    return {
        "found": True,
        "display_name": r["display_name"],
        "subtype": r.get("subtype"),
        "draft_info": r.get("draft_info"),
        "official_ten_yd": r.get("measure_value", r.get("official_ten_yd")),
        "combine_z": r.get("combine_z"),
        "combine_band": band,
        "pressure_rate": r.get("outcome", r.get("pressure_rate")),
        "outcome_resid": resid,
        "outcome_resid_yearpick": r.get("outcome_resid_yearpick"),
        "n_opps": r.get("n_opps"),
        "is_gem": is_gem,
        "is_udfa": bool(r.get("is_udfa")),
        "status": status,
        "rank_among_gems": None,
    }


def shortlist_table_md(g: pd.DataFrame, group: str, measure: str,
                       measure_label: str, gems: pd.DataFrame) -> str:
    mkind = measure_kind(measure)
    okind = outcome_kind(group)
    meas_lab = measure_label
    if measure in YDS_SPEED_MEASURES:
        meas_lab = f"{measure_label} (mph)"
    out_lab = GROUP_OUTCOME[group][1]
    show_sub = group == "DL" and "subtype" in gems.columns
    if show_sub:
        lines = [
            f"| Player | Subtype | Draft | UDFA | College | {meas_lab} | z | {out_lab} | vs slot | Opps |",
            "|---|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
    else:
        lines = [
            f"| Player | Draft | UDFA | College | {meas_lab} | z | {out_lab} | vs slot | Opps |",
            "|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
    for _, r in gems.iterrows():
        college = r["college_name"] if pd.notna(r.get("college_name")) else "—"
        udfa = "Yes" if bool(r.get("is_udfa")) else ""
        core = (
            f"{udfa} | {college} | "
            f"{fmt_num(display_measure_value(r['measure'], r['measure_value']), mkind)} | "
            f"{fmt_num(r['combine_z'], 'resid')} | "
            f"{fmt_num(r['outcome'], okind)} | {fmt_num(r['outcome_resid'], 'resid')} | "
            f"{fmt_num(r['n_opps'], 'int')} |"
        )
        if show_sub:
            typ = r["subtype"] if pd.notna(r.get("subtype")) else "—"
            lines.append(f"| {r['display_name']} | {typ} | {r['draft_info']} | {core}")
        else:
            lines.append(f"| {r['display_name']} | {r['draft_info']} | {core}")
    return "\n".join(lines)


def draw_figure(tagged: dict, choices: dict, contrasts: list[dict],
                chop: dict) -> Path:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(13.4, 8.6))
    axes = axes.ravel()

    for i, group in enumerate(GROUPS):
        ax = axes[i]
        g = tagged[group]
        color = GROUP_COLOR[group]
        drafted = g[~g["is_udfa"]]
        udfa = g[g["is_udfa"]]
        if group == "DL" and "subtype" in g.columns:
            for typ, typ_color, typ_marker in (
                ("Edge", DL_SUBTYPE_COLOR["Edge"], "o"),
                ("Interior", DL_SUBTYPE_COLOR["Interior"], "s"),
            ):
                d = drafted[drafted["subtype"] == typ]
                ax.scatter(
                    d["combine_z"], d["outcome_resid"],
                    s=36, c=typ_color, marker=typ_marker, alpha=0.8, zorder=3,
                    label=typ, edgecolors="white", linewidths=0.4,
                )
                u = udfa[udfa["subtype"] == typ]
                ax.scatter(
                    u["combine_z"], u["outcome_resid"],
                    s=42, marker=typ_marker, facecolors="none",
                    edgecolors=typ_color, linewidths=1.15, zorder=4,
                    label=f"UDFA {typ}",
                )
        else:
            ax.scatter(
                drafted["combine_z"], drafted["outcome_resid"],
                s=36, c=color, alpha=0.8, zorder=3, label="Drafted",
                edgecolors="white", linewidths=0.4,
            )
            ax.scatter(
                udfa["combine_z"], udfa["outcome_resid"],
                s=42, facecolors="none", edgecolors=color, linewidths=1.15,
                zorder=4, label="UDFA",
            )
        gems = g[g["is_gem"]].sort_values("outcome_resid", ascending=False)
        # Ring the gems; label the top 8 by residual so the panel stays readable.
        if len(gems):
            ax.scatter(
                gems["combine_z"], gems["outcome_resid"],
                s=90, facecolors="none", edgecolors="black", linewidths=1.0,
                zorder=5, label="Gem",
            )
        for _, r in gems.head(8).iterrows():
            last = str(r["display_name"]).split()[-1]
            ax.annotate(
                last, (r["combine_z"], r["outcome_resid"]),
                textcoords="offset points", xytext=(4, 3),
                fontsize=7, color="#111111", zorder=6,
            )
        ax.axvline(0, color="#AAAAAA", lw=0.6, zorder=1)
        # Approximate top-third cut at z of the lowest strong player
        strong = g[g["combine_band"] == "strong"]
        if len(strong) and strong["combine_z"].notna().any():
            ax.axvline(strong["combine_z"].min(), color="#888888", lw=0.6,
                       ls=":", zorder=1)
        ax.axhline(0, color="#AAAAAA", lw=0.6, zorder=1)
        ax.set_xlabel(
            "Within-subtype Combine z (higher = better)" if group == "DL"
            else "Combine z (higher = better)"
        )
        ax.set_ylabel(f"{GROUP_OUTCOME[group][1]} vs draft slot")
        flag = "  ·  weak link" if choices[group].get("weak_link") else ""
        ax.set_title(f"{group}: {choices[group]['measure_label']}{flag}", fontsize=10)
        ax.legend(loc="best", fontsize=6, frameon=False, markerscale=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Summary table of the all-rounds strong vs weak contrast.
    ax = axes[4]
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    headline = [c for c in contrasts if c.get("subgroup", c["group"]) == c["group"]]
    rows_txt = [
        "Strong vs weak, all eligible players",
        "",
        "Group   Med resid s/w    n s/w    MW p    Flag",
        "-----------------------------------------------",
    ]
    for c in headline:
        flag = "weak link" if c["weak_link_flag"] else ("n small" if c["underpowered"] else "—")
        ms = c["median_yearpick_resid_strong"]
        mw = c["median_yearpick_resid_weak"]
        ms_s = f"{ms:+.3f}" if np.isfinite(ms) else "NA"
        mw_s = f"{mw:+.3f}" if np.isfinite(mw) else "NA"
        p_s = fmt_p(c["mw_p"])
        rows_txt.append(
            f"{c['group']:<6} {ms_s}/{mw_s:<8} {c['n_strong']}/{c['n_weak']:<6} {p_s:<7} {flag}"
        )
    rows_txt.append("")
    rows_txt.append("Medians are year+pick residuals.")
    rows_txt.append("MW is one-sided (strong > weak).")
    rows_txt.append("Open circles are UDFAs (pick = 260).")
    rows_txt.append("Circled names (top 8 residual) are gems:")
    rows_txt.append("top-third tester and over their draft slot.")
    ax.text(0.02, 0.98, "\n".join(rows_txt), va="top", ha="left",
            fontsize=7.5, family="monospace", color="#222222",
            transform=ax.transAxes)

    # Chop Robinson callout.
    ax = axes[5]
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    if chop.get("found"):
        chop_lines = [
            "Chop Robinson (requested check)",
            "",
            f"{chop['draft_info']}  ·  {chop.get('subtype') or 'DL'}",
            f"Official 10-yard split  {fmt_num(chop.get('official_ten_yd'), 'time')}"
            f"   z {fmt_num(chop.get('combine_z'), 'resid')}",
            f"Band: {chop.get('combine_band') or '—'}",
            f"Pressure rate  {fmt_num(chop.get('pressure_rate'), 'rate')}"
            f"   vs slot  {fmt_num(chop.get('outcome_resid'), 'resid')}",
            f"Pass-rush snaps  {fmt_num(chop.get('n_opps'), 'int')}",
            "",
            chop.get("status", ""),
        ]
        if chop.get("is_gem") and chop.get("rank_among_gems"):
            chop_lines.append(f"Rank among DL gems (by residual): {chop['rank_among_gems']}")
    else:
        chop_lines = ["Chop Robinson (requested check)", "", chop.get("note", "Not found.")]
    ax.text(0.02, 0.98, "\n".join(chop_lines), va="top", ha="left",
            fontsize=8, color="#222222", transform=ax.transAxes,
            wrap=True)

    fig.suptitle(
        "Combine gems: top-third testers who outplayed their draft slot",
        x=0.01, ha="left", fontweight="bold", fontsize=13, y=0.98,
    )
    import textwrap
    caption = (
        "Strong = top third of the position on the pre-declared Combine measure.  "
        "For DL, strong is the top third within Edge and within Interior on the "
        "official 10-yard split (within-subtype z), so interior rushers are not "
        "graded against edges on raw time.  Over slot = residual vs log draft pick, "
        "fit on every eligible player in the group (UDFA = 260, the slot after a "
        "seven-round draft).  Open circles are UDFAs, in the same list, not a "
        "separate tier.  Rounds are not split: first-rounders and seventh-rounders "
        "use the same cuts.  “Weak link” means the pre-declared measure is only "
        "weakly related to the gameplay outcome on the full sample — those "
        "shortlists are names, not a group-level finding.  CB/S outcomes are "
        "tackle / TFL rates only; this file has no targets or completions allowed."
    )
    fig.text(0.01, 0.01, textwrap.fill(caption, width=165), fontsize=7.2,
             color="#555555", ha="left", va="bottom")
    fig.subplots_adjust(left=0.06, right=0.99, top=0.90, bottom=0.14,
                        wspace=0.35, hspace=0.38)
    path = FIGS / "fig8_combine_gems.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    log(f"Wrote {path}")
    return path


def player_row(r: pd.Series) -> dict:
    keep = [
        "nfl_id", "display_name", "group", "subtype", "college_name",
        "draft_year", "draft_round", "draft_overall_pick", "pick",
        "draft_info", "is_udfa", "measure", "measure_label", "measure_value",
        "combine_z", "combine_pct", "combine_band", "outcome", "outcome_label",
        "outcome_resid", "outcome_resid_yearpick", "over_slot", "is_gem",
        "n_opps", "opp_label", "choice_weak_link",
        "yards_per_route", "deep_yards_per_deep_route", "deep_target_share",
        "sunday_speed_mph", "ssoe_mph", "tackle_rate", "tfl_rate", "start_rate",
        "n_routes", "n_deep_routes", "n_def_snaps",
        "official_ten_yd", "official_forty", "c_top_mph", "vertical",
        "broad_jump", "three_cone", "short_shuttle", "bench_reps",
        "db_gauntlet_max_s", "db_bp45_max_s",
        "pressure_rate", "sack_rate", "speed_1s_mph", "snaps_per_game",
        "n_rush_plays",
    ]
    return {k: r[k] if k in r.index else np.nan for k in keep}


def write_markdown(choices: dict, short_tabs: dict, contrasts: list[dict],
                   tagged: dict, chop: dict) -> Path:
    lines: list[str] = []
    a = lines.append

    a("# Combine gems — strong testers who outplayed their draft slot")
    a("")
    a("A **Combine gem** is a player who tested in the top third of his position on a pre-declared Combine measure and then posted a better gameplay number than his draft slot predicted. Rounds are **not** split: first-rounders, seventh-rounders, and undrafted players are in the same list. UDFAs are flagged in a column, not held out as a separate tier.")
    a("")
    a("## Definitions")
    a("")
    a("- **Eligible** means the same gameplay floors as the main writeup: receivers with ≥20 regular-season routes that stood; corners and safeties with ≥50 defensive snaps; defensive linemen with ≥20 pass-rush snaps (lined up EDGE or interior, plays that stood).")
    a("- **Strong Combine** means the top third of the whole position group on the pre-declared measure. **For DL, strong is the top third within Edge and within Interior** (a within-subtype z-score of the official 10-yard split). We do not take the top third of raw 10-yard times among all DL, because that list would be almost all edges.")
    a(f"- **Overperformed** means a positive residual after a linear fit of the group's primary gameplay outcome on log draft pick, fit on every eligible player at that group. **UDFA = pick {UDFA_PICK}**, the slot after a seven-round draft, used consistently in that fit. For DL the residual is fit on the combined all-DL sample. A year+pick residual is used for the group-level Mann-Whitney (below) as a second, year-adjusted view; it is not the gem cut.")
    a("- **Primary outcomes** are on-field gameplay, not playing time: yards per route for receivers; pressure rate for the combined DL group, with Edge vs Interior shown as a breakout; tackle involvement rate for corners and safeties. CB/S coverage outcomes (targets or completions allowed, PBUs, INTs) are not in this file and were not invented. Playing time is context only.")
    a("")
    a("## 1. Pre-declared Combine measures")
    a("")
    a("Each group has a **pre-declared** primary measure, locked to the measure used in the earlier late-round writeup: official 40 time for receivers, broad jump for corners, gauntlet drill top speed for safeties, and the official 10-yard split for the combined DL group. We did not re-select a winner on this sample, and we no longer use an early-round hold-out, because rounds are not split.")
    a("")
    a("**Selection caveat.** These measures were chosen with knowledge of the earlier shortlist exercise. The full-sample correlations below are descriptive, for transparency. They are not an independent confirmatory test, and they were not used to pick a different primary here.")
    a("")
    a("A “weak link” flag means the pre-declared measure’s oriented year+pick Spearman ρ is below 0.20, or its p-value is ≥ 0.10, on the full eligible sample. Names on a weak-link list are still listed; they are not a group-level recommendation.")
    a("")
    a("### Pre-declared measure, by group")
    a("")
    a("| Group | Outcome | Pre-declared measure | n | Oriented year+pick ρ | p | Weak link? |")
    a("|---|---|---|---:|---:|---:|---|")
    for group in GROUPS:
        ch = choices[group]
        a(
            f"| {group} | {ch.get('outcome_label', GROUP_OUTCOME[group][1])} | "
            f"{ch['measure_label']} | {ch.get('n_full', '—')} | "
            f"{fmt_rho(ch.get('oriented_yearpick_rho', np.nan))} | "
            f"{fmt_p(ch.get('oriented_p', np.nan))} | "
            f"{'Yes' if ch.get('weak_link') else 'No'} |"
        )
    a("")
    a("### Full-sample shortlist correlations (transparency)")
    a("")
    a("Oriented ρ is signed so that a positive number means “better test, better gameplay.” Year+pick is the partial Spearman after residualizing both sides on draft year and log pick.")
    a("")
    a("| Group | Measure | n | Oriented raw ρ (p) | Oriented pick-partial ρ (p) | Oriented year+pick ρ (p) | Pre-declared? |")
    a("|---|---|---:|---|---|---|---|")
    for group in GROUPS:
        tab = short_tabs[group]
        for _, r in tab.iterrows():
            a(
                f"| {group} | {r['measure_label']} | {int(r['n_full'])} | "
                f"{fmt_rho(r['oriented_rho'])} ({fmt_p(r['raw_p_full'])}) | "
                f"{fmt_rho(r['oriented_partial_rho'])} ({fmt_p(r['partial_p_full'])}) | "
                f"{fmt_rho(r['oriented_yearpick_rho'])} ({fmt_p(r['yearpick_p_full'])}) | "
                f"{'Yes' if r['predeclared'] else ''} |"
            )
    a("")

    a("## 2. Do strong testers outperform weak testers as a group?")
    a("")
    a("Sample: every eligible player with a value on the pre-declared measure, including UDFAs. Strong = top third of the *position* (for DL, within subtype). Mann-Whitney is one-sided (strong > weak) on the **year+pick residual**. Raw-outcome medians are shown as a companion. Cells with fewer than 5 players in either tail are marked underpowered. A “weak link” group is one where the measure itself barely relates to the outcome — a null or noisy contrast is the expected result, not a surprise.")
    a("")
    a("| Group | Subgroup | Measure | n (strong / mid / weak) | Median outcome strong | Median outcome weak | Median year+pick residual strong / weak | MW p (resid, strong > weak) | Notes |")
    a("|---|---|---|---|---:|---:|---|---:|---|")
    for c in contrasts:
        notes = []
        if c["weak_link_flag"]:
            notes.append("weak link")
        if c["underpowered"]:
            notes.append("underpowered")
        if c.get("mw_note") and "Underpowered" not in (c.get("mw_note") or ""):
            notes.append(c["mw_note"])
        okind = outcome_kind(c["group"])
        a(
            f"| {c['group']} | {c.get('subgroup', c['group'])} | {c['measure_label']} | "
            f"{c['n']} ({c['n_strong']} / {c['n_middle']} / {c['n_weak']}) | "
            f"{fmt_num(c['median_strong'], okind)} | {fmt_num(c['median_weak'], okind)} | "
            f"{fmt_num(c['median_yearpick_resid_strong'], 'resid')} / {fmt_num(c['median_yearpick_resid_weak'], 'resid')} | "
            f"{fmt_p(c['mw_p'])} | {', '.join(notes) if notes else '—'} |"
        )
    a("")
    a("Do not overclaim a group effect when n is small, when the p-value is modest, or when the pre-declared measure is already a weak link. The names are the deliverable; a significant group test would be a bonus, not the requirement.")
    a("")

    a("## 3. Named shortlists")
    a("")
    a("A player makes this list if he is eligible, tested in the top third of his position on the pre-declared measure, and posted a positive draft-slot residual on the primary gameplay outcome. Names are ordered by residual, not by Combine z. UDFAs (pick 260) can make the same list; they are marked in the UDFA column. Limited opportunity counts (just-cleared floors) should be read as early looks, not finished grades. The tables below show every gem; the “why they stand out” notes cover the top eight by residual.")
    a("")

    for group in GROUPS:
        ch = choices[group]
        a(f"### {group} — {ch['measure_label']}")
        a("")
        if ch.get("weak_link"):
            a(f"*The {group} measure is only weakly related to {ch.get('outcome_label', GROUP_OUTCOME[group][1])} on the full sample. These are named over-slot testers, not a group-level recommendation.*")
            a("")
        if group == "DL":
            a("*One combined DL shortlist. Strong is the top third of the official 10-yard split **within Edge** and **within Interior** (the z column is a within-subtype z-score), so interior rushers are not graded against edges on raw time. The draft-slot residual is fit on the combined all-DL sample.*")
            a("")
        gems = tagged[group][tagged[group]["is_gem"]].sort_values("outcome_resid", ascending=False)
        if gems.empty:
            a("_None in this sample._")
            a("")
            strong = tagged[group][
                (tagged[group]["combine_band"] == "strong")
                & tagged[group]["measure_value"].notna()
            ].sort_values("outcome_resid", ascending=False)
            if len(strong):
                names = []
                for _, r in strong.iterrows():
                    typ = f"{r['subtype']}, " if group == "DL" and pd.notna(r.get("subtype")) else ""
                    names.append(
                        f"{r['display_name']} ({typ}{r['draft_info']}, "
                        f"{fmt_num(r['outcome'], outcome_kind(group))} "
                        f"{GROUP_OUTCOME[group][1].lower()}, residual "
                        f"{fmt_num(r['outcome_resid'], 'resid')})"
                    )
                a(
                    "No player in this group cleared both cuts. "
                    "Top-third testers who did not beat their draft-slot expectation: "
                    + "; ".join(names) + "."
                )
                a("")
            continue
        a(shortlist_table_md(tagged[group], group, ch["measure"], ch["measure_label"], gems))
        a("")
        a("Why they stand out (top 8 by residual):")
        a("")
        for _, r in gems.head(8).iterrows():
            extra = companion_bits(r, group)
            extra_s = f" Companions: {extra}." if extra else ""
            typ = ""
            if group == "DL" and pd.notna(r.get("subtype")):
                typ = f"{r['subtype']}, "
            udfa_flag = " [UDFA]" if bool(r.get("is_udfa")) else ""
            a(
                f"- **{r['display_name']}** ({typ}{r['draft_info']}{udfa_flag}) posted "
                f"{fmt_num(r['outcome'], outcome_kind(group))} {GROUP_OUTCOME[group][1].lower()} "
                f"against a draft-slot expectation, residual {fmt_num(r['outcome_resid'], 'resid')}, "
                f"with {article_for(ch['measure_label'])} {ch['measure_label'].lower()} of "
                f"{fmt_num(display_measure_value(ch['measure'], r['measure_value']), measure_kind(ch['measure']))} "
                f"(z {fmt_num(r['combine_z'], 'resid')}) on {fmt_num(r['n_opps'], 'int')} {r['opp_label']}."
                f"{extra_s}"
            )
        a("")

    a("## 4. Chop Robinson")
    a("")
    if chop.get("found"):
        a(
            f"**{chop['display_name']}** ({chop.get('subtype') or 'DL'}, {chop['draft_info']}) "
            f"ran a {fmt_num(chop.get('official_ten_yd'), 'time')} official 10-yard split "
            f"(within-subtype z {fmt_num(chop.get('combine_z'), 'resid')}, band: "
            f"{chop.get('combine_band') or '—'}) and posted "
            f"{fmt_num(chop.get('pressure_rate'), 'rate')} pressure rate "
            f"(draft-slot residual {fmt_num(chop.get('outcome_resid'), 'resid')}; "
            f"year+pick residual {fmt_num(chop.get('outcome_resid_yearpick'), 'resid')}) "
            f"on {fmt_num(chop.get('n_opps'), 'int')} pass-rush snaps."
        )
        a("")
        a(chop["status"])
        if chop.get("is_gem") and chop.get("rank_among_gems"):
            a("")
            a(f"He is **#{chop['rank_among_gems']}** on the combined DL gem list, ordered by draft-slot residual.")
    else:
        a(chop.get("note", "Chop Robinson was not found in the eligible DL table."))
    a("")

    a("## 5. Limits")
    a("")
    a("- The measures were pre-declared after an earlier shortlist exercise. That is a selection caveat. Full-sample correlations are shown for honesty, not as a second chance to pick a winner.")
    a("- Sample sizes at a single position are still modest. A one-or-two-player swing can move a residual or a tertile cut.")
    a("- Shuttle and 3-cone are missing for most corners and safeties in this cohort, so those classic COD tests are not the pre-declared measure here.")
    a("- Receiver production still has the same honest limit as the main writeup: even the best speed test in this file has not been a reliable yards-per-route predictor after draft slot. A receiver gem is a named over-slot player who also tested well, not proof that paying for that test finds producers.")
    a("- Corner and safety “success” here is tackle involvement and tackles for loss. That is what the file gives us. It is not a coverage grade.")
    a("- Defensive-line pressure has no blocker or QB track. Get-off and pressure are still associations. The all-DL 10-yard → pressure link is a pooled result; within Edge or Interior alone it is weaker and not significant.")
    a("- Career length differs by draft year (2023 rookies have three seasons, 2025 rookies have one). Rate outcomes and the year+pick residual do not fully remove that.")
    a(f"- UDFA pick value is {UDFA_PICK}. That is a convention (the next slot after pick 259), not a market price. Changing it would move UDFA residuals.")
    a("")
    a("Figure: `out/figs/fig8_combine_gems.png`. Player-level table: `out/combine_gems.csv`. Measure correlations and group tests: `out/combine_gems_tests.csv`.")
    a("")

    path = ROOT / "COMBINE_GEMS.md"
    path.write_text("\n".join(lines) + "\n")
    log(f"Wrote {path}")
    return path


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    skill, dl = load_tables()
    log(f"Eligible skill players: {len(skill)} ({skill['group'].value_counts().to_dict()})")
    log(f"Eligible DL: {len(dl)} ({dl['group'].value_counts().to_dict()})")

    frames = {"WR": skill, "CB": skill, "S": skill, "DL": dl}
    short_tabs = {}
    choices = {}
    tagged = {}
    contrasts = []

    for group in GROUPS:
        tab = evaluate_shortlist(frames[group], group)
        short_tabs[group] = tab
        ch = primary_choice(tab, group)
        choices[group] = ch
        log(
            f"{group}: pre-declared {ch['measure_label']} "
            f"(n={ch.get('n_full')}, oriented year+pick ρ={fmt_rho(ch.get('oriented_yearpick_rho', np.nan))}, "
            f"weak_link={ch.get('weak_link')})"
        )
        g = tag_group(frames[group], group, ch)
        tagged[group] = g
        c = group_contrast(g, group, ch)
        contrasts.append(c)
        n_gems = int(g["is_gem"].sum())
        n_udfa_gems = int((g["is_gem"] & g["is_udfa"]).sum())
        log(
            f"  n={c['n']} strong/weak={c['n_strong']}/{c['n_weak']} "
            f"MW p (year+pick resid)={fmt_p(c['mw_p'])}  gems={n_gems} (UDFA gems={n_udfa_gems})"
        )
        if group == "DL":
            for typ in ("Edge", "Interior"):
                br = group_contrast(g, group, ch, subtype=typ)
                contrasts.append(br)
                log(
                    f"    breakout {typ}: n={br['n']} strong/weak={br['n_strong']}/{br['n_weak']} "
                    f"MW p={fmt_p(br['mw_p'])}"
                )

    chop = chop_placement(tagged["DL"])
    if chop.get("found") and chop.get("is_gem"):
        gems = tagged["DL"][tagged["DL"]["is_gem"]].sort_values("outcome_resid", ascending=False)
        names = list(gems["display_name"])
        if chop["display_name"] in names:
            chop["rank_among_gems"] = names.index(chop["display_name"]) + 1
    if chop.get("found"):
        log(
            f"Chop Robinson: {chop['draft_info']}, split={chop.get('official_ten_yd')}, "
            f"band={chop.get('combine_band')}, pressure={chop.get('pressure_rate')}, "
            f"resid={chop.get('outcome_resid')}, gem={chop.get('is_gem')} "
            f"rank={chop.get('rank_among_gems')} — {chop['status']}"
        )
    else:
        log(f"Chop Robinson: {chop.get('note')}")

    rows = []
    for group in GROUPS:
        for _, r in tagged[group].iterrows():
            rows.append(player_row(r))
    gems_tbl = pd.DataFrame(rows)
    gems_path = OUT / "combine_gems.csv"
    gems_tbl.to_csv(gems_path, index=False)
    n_gems = int(gems_tbl["is_gem"].sum())
    n_udfa_gems = int((gems_tbl["is_gem"] & gems_tbl["is_udfa"]).sum())
    log(f"Wrote {gems_path} ({len(gems_tbl)} rows, {n_gems} gems, {n_udfa_gems} of them UDFA)")

    test_rows = []
    for group in GROUPS:
        t = short_tabs[group].copy()
        test_rows.append(t)
    test_rows.append(pd.DataFrame(contrasts))
    tests = pd.concat(test_rows, ignore_index=True, sort=False)
    tests_path = OUT / "combine_gems_tests.csv"
    tests.to_csv(tests_path, index=False)
    log(f"Wrote {tests_path}")

    draw_figure(tagged, choices, contrasts, chop)
    write_markdown(choices, short_tabs, contrasts, tagged, chop)
    log("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
