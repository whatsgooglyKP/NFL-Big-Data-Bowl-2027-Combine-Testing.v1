#!/usr/bin/env python3
"""Which Combine tests translate to in-game success, by position.

Kevin's framing (11/2026): draft slot is out of this analysis entirely —
not as a covariate, not as a baseline, not as a sensitivity. For each
group (WR, TE, CB, S, and one combined DL; RB excluded) we ask which
Combine metric maps to coach-relevant Sunday outcomes.

  1. Pairwise Spearman matrix: every available Combine test × each
     group's in-game metrics, residualized on draft year only, with
     bootstrap CIs and Holm / BH-FDR adjustment within the group.
  2. Model comparison on the group's key success metric, year-only
     baseline: L2 logistic, Firth, L1 lasso, elastic net, shallow
     trees, Gaussian naive Bayes, and a Bayesian hierarchical
     logistic that partially pools Combine slopes across the five
     groups. Ridge / lasso / EN on the continuous outcome.

Usage, from the repo root with the venv:

    .venv/bin/python combine_to_game.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from scipy import stats
from sklearn.linear_model import (
    ElasticNetCV,
    LassoCV,
    LogisticRegression,
    LogisticRegressionCV,
    RidgeCV,
)
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import KFold, RepeatedKFold, RepeatedStratifiedKFold, StratifiedKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from statsmodels.stats.multitest import multipletests

import multi_test_models as mtm
from multi_test_models import (
    add_intercept,
    fit_firth,
    firth_predict_proba,
    n_splits_for,
)

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

N_BOOT = 2000
BOOT_SEED = 2027
CV_REPEATS = 20
CV_SEED = 2027
MIN_SPEARMAN_N = 12
MIN_WR_ROUTES = 20
MIN_TE_ROUTES = 20
MIN_DB_SNAPS = 50
MIN_DL_RUSH = 20
DEEP_ROUTES = frozenset({"GO", "POST", "CORNER", "WHEEL"})
MPH = 2.0455
NONZERO = 1e-5

# ---------------------------------------------------------------------------
# Combine tests and in-game outcomes
# ---------------------------------------------------------------------------
# expected_sign: -1 = lower (faster time) should help a higher-better outcome;
# +1 = higher should help; 0 = no pre-declared direction.

COMBINE_TESTS = [
    ("official_forty", "Official 40", -1, "s"),
    ("official_ten_yd", "Official 10-yard", -1, "s"),
    ("c_t20_derived", "20-yard (tracking)", -1, "s"),
    ("vertical", "Vertical", +1, "in"),
    ("broad_jump", "Broad jump", +1, "in"),
    ("three_cone", "3-cone", -1, "s"),
    ("short_shuttle", "Short shuttle", -1, "s"),
    ("combine_height", "Height", 0, "in"),
    ("combine_weight", "Weight", 0, "lb"),
    ("c_top_mph", "Combine top speed", +1, "mph"),
    ("c_40_accel", "40-yard peak accel", +1, "yd/s²"),
]
TEST_LABELS = {k: lab for k, lab, *_ in COMBINE_TESTS}
TEST_SIGN = {k: sgn for k, _, sgn, _ in COMBINE_TESTS}
TEST_ORDER = [k for k, *_ in COMBINE_TESTS]

# Joint models drop 3-cone and shuttle (too sparse). Draft pick is never a
# predictor. Year is the only control.
# Joint models: official times, jumps, size, and Combine top speed.
# 3-cone, shuttle, 20-yard (tracking), and 40-yard accel stay in the
# pairwise Spearman matrix only — the last two are near-collinear with
# the official 40 / Combine top speed, and 3-cone / shuttle are sparse.
MODEL_TESTS = [
    "official_forty", "official_ten_yd",
    "vertical", "broad_jump", "combine_height", "combine_weight",
    "c_top_mph",
]

# higher_better is for the outcome itself (used in binary "success" and in
# P(direction) combined with the Combine-test expected sign).
# key=True marks the group's primary success metric.
OUTCOMES = {
    "WR": [
        dict(col="yards_per_route", label="Yards per route", short="YPR",
             higher_better=True, key=True, min_col="n_routes", min_n=MIN_WR_ROUTES,
             min_label="≥20 regular-season routes"),
        dict(col="sunday_speed_mph", label="Deep-route game speed", short="Sunday Speed",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="official Sunday Speed sample"),
        dict(col="sep_deep", label="Deep-route separation", short="Deep sep",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="already floored in gameplay table"),
        dict(col="yac_oe", label="YAC over expected", short="YAC-OE",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="already floored in gameplay table"),
        dict(col="target_rate", label="Target rate", short="Target rate",
             higher_better=True, key=False, min_col="n_routes", min_n=MIN_WR_ROUTES,
             min_label="≥20 regular-season routes"),
        dict(col="deep_yards_per_deep_route", label="Deep yards per deep route", short="Deep YPR",
             higher_better=True, key=False, min_col="n_deep_routes", min_n=8,
             min_label="≥8 regular-season deep routes"),
    ],
    "TE": [
        dict(col="yards_per_route", label="Yards per route", short="YPR",
             higher_better=True, key=True, min_col="n_routes", min_n=MIN_TE_ROUTES,
             min_label="≥20 regular-season routes"),
        dict(col="target_rate", label="Target rate", short="Target rate",
             higher_better=True, key=False, min_col="n_routes", min_n=MIN_TE_ROUTES,
             min_label="≥20 regular-season routes"),
        dict(col="sep_deep", label="Deep-route separation", short="Deep sep",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="≥8 deep routes with a recorded separation"),
        dict(col="yac_oe", label="YAC over expected", short="YAC-OE",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="≥5 catches with YAC-over-expected"),
        dict(col="deep_yards_per_deep_route", label="Deep yards per deep route", short="Deep YPR",
             higher_better=True, key=False, min_col="n_deep_routes", min_n=8,
             min_label="≥8 regular-season deep routes"),
    ],
    "CB": [
        dict(col="tackle_rate", label="Tackle involvement rate", short="Tackle rate",
             higher_better=True, key=True, min_col="n_def_snaps", min_n=MIN_DB_SNAPS,
             min_label="≥50 regular-season defensive snaps"),
        dict(col="tfl_rate", label="Tackle-for-loss rate", short="TFL rate",
             higher_better=True, key=False, min_col="n_def_snaps", min_n=MIN_DB_SNAPS,
             min_label="≥50 regular-season defensive snaps"),
        dict(col="sunday_speed_mph", label="Game top speed (coverage)", short="Sunday Speed",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="official Sunday Speed sample"),
    ],
    "S": [
        dict(col="tackle_rate", label="Tackle involvement rate", short="Tackle rate",
             higher_better=True, key=True, min_col="n_def_snaps", min_n=MIN_DB_SNAPS,
             min_label="≥50 regular-season defensive snaps"),
        dict(col="tfl_rate", label="Tackle-for-loss rate", short="TFL rate",
             higher_better=True, key=False, min_col="n_def_snaps", min_n=MIN_DB_SNAPS,
             min_label="≥50 regular-season defensive snaps"),
        dict(col="sunday_speed_mph", label="Game top speed (coverage)", short="Sunday Speed",
             higher_better=True, key=False, min_col=None, min_n=0,
             min_label="official Sunday Speed sample"),
    ],
    "DL": [
        dict(col="pressure_rate", label="Pressure rate", short="Pressure",
             higher_better=True, key=True, min_col="n_rush_plays", min_n=MIN_DL_RUSH,
             min_label="≥20 regular-season pass-rush snaps"),
        dict(col="sack_rate", label="Sack rate", short="Sack",
             higher_better=True, key=False, min_col="n_rush_plays", min_n=MIN_DL_RUSH,
             min_label="≥20 regular-season pass-rush snaps"),
        dict(col="speed_1s_mph", label="Get-off (speed at 1.0s)", short="Get-off mph",
             higher_better=True, key=False, min_col="n_rush_plays", min_n=MIN_DL_RUSH,
             min_label="≥20 regular-season pass-rush snaps"),
        dict(col="player_get_off", label="NFL get-off time", short="Get-off sec",
             higher_better=False, key=False, min_col="n_rush_plays", min_n=MIN_DL_RUSH,
             min_label="≥20 regular-season pass-rush snaps (lower is faster)"),
    ],
}

POS_ORDER = ["WR", "TE", "CB", "S", "DL"]
POS_COLOR = {
    "WR": "#0072B2", "TE": "#CC79A7", "CB": "#D55E00",
    "S": "#009E73", "DL": "#6A3D9A",
}
KEY_OUTCOME = {g: next(o["col"] for o in outs if o["key"]) for g, outs in OUTCOMES.items()}
KEY_LABEL = {g: next(o["label"] for o in outs if o["key"]) for g, outs in OUTCOMES.items()}

MODEL_LABELS = {
    "baseline_year": "Year only",
    "logistic_l2": "L2 logistic (tests + year)",
    "firth": "Firth logistic (tests + year)",
    "lasso": "Lasso L1 logistic (tests + year)",
    "elastic_net": "Elastic-net logistic (tests + year)",
    "tree_d2": "Decision tree (depth 2)",
    "tree_d3": "Decision tree (depth 3)",
    "gaussian_nb": "Gaussian naive Bayes",
    "bayes_loo": "Bayesian hierarchical (PSIS-LOO)",
    "bayes_5fold": "Bayesian hierarchical (5-fold CV)",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def fmt_rho(x: float) -> str:
    if not np.isfinite(x):
        return "NA"
    return f"{x:+.2f}"


def coerce_bool(s: pd.Series) -> pd.Series:
    return s.map({
        True: True, False: False, "TRUE": True, "FALSE": False,
        "True": True, "False": False, 1: True, 0: False, 1.0: True, 0.0: False,
    })


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
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "figure.titlesize": 15,
        "font.family": "DejaVu Sans",
    })


# ---------------------------------------------------------------------------
# Year-only residualization (NO draft pick)
# ---------------------------------------------------------------------------
def year_controls(d: pd.DataFrame) -> np.ndarray:
    """Year dummies, drop_first. Empty array if a single year is present."""
    dum = pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True)
    if dum.shape[1] == 0:
        return np.zeros((len(d), 0), dtype=float)
    return dum.to_numpy(dtype=float)


def residualize(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    if X.size == 0 or X.shape[1] == 0:
        return y - np.mean(y)
    A = np.column_stack([np.ones(len(X)), X])
    keep = [0]
    for j in range(1, A.shape[1]):
        cand = A[:, keep + [j]]
        if np.linalg.matrix_rank(cand, tol=1e-9) > len(keep):
            keep.append(j)
    A = A[:, keep]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def spearman_year(x: pd.Series, y: pd.Series, year: pd.Series) -> dict:
    d = pd.DataFrame({"x": x, "y": y, "draft_year": year}).dropna()
    out = {"n": int(len(d)), "rho_raw": np.nan, "p_raw": np.nan,
           "rho": np.nan, "p": np.nan}
    if len(d) < MIN_SPEARMAN_N or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho_raw"], out["p_raw"] = float(rho), float(p)
    X = year_controls(d)
    rx = residualize(d["x"].to_numpy(dtype=float), X)
    ry = residualize(d["y"].to_numpy(dtype=float), X)
    if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
        pr, pp = stats.spearmanr(rx, ry)
        out["rho"], out["p"] = float(pr), float(pp)
    return out


def bootstrap_year_ci(x: pd.Series, y: pd.Series, year: pd.Series,
                      n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple[float, float, int]:
    base = pd.DataFrame({"x": x, "y": y, "draft_year": year}).dropna().reset_index(drop=True)
    if len(base) < MIN_SPEARMAN_N:
        return np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    rhos: list[float] = []
    n = len(base)
    x_arr = base["x"].to_numpy(dtype=float)
    y_arr = base["y"].to_numpy(dtype=float)
    yr = base["draft_year"].to_numpy()
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        xb, yb, yrb = x_arr[idx], y_arr[idx], yr[idx]
        if np.unique(xb).size < 2 or np.unique(yb).size < 2:
            continue
        dtmp = pd.DataFrame({"draft_year": yrb})
        X = year_controls(dtmp)
        rx = residualize(xb, X)
        ry = residualize(yb, X)
        if np.unique(rx).size < 2 or np.unique(ry).size < 2:
            continue
        rho, _ = stats.spearmanr(rx, ry)
        if np.isfinite(rho):
            rhos.append(float(rho))
    if len(rhos) < max(50, n_boot // 20):
        return np.nan, np.nan, len(rhos)
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return float(lo), float(hi), len(rhos)



# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------
def forty_tracking_for(ids: set[int], cache: Path) -> pd.DataFrame:
    """Tracking-derived 40 features (top speed, 10/20 splits, accel) for a set of IDs.

    Does not overwrite the WR/CB/S combine_attempts_features.parquet.
    Official laser times remain the preferred 40 and 10-yard columns;
    these are companions, and the 20-yard split exists only as tracking.
    """
    if cache.exists():
        out = pd.read_parquet(cache)
        have = set(out["nfl_id"].tolist())
        if ids.issubset(have) or len(have) >= len(ids) * 0.9:
            return out[out["nfl_id"].isin(ids)].copy()
    from build_dataset import ACCEL_CLIP, _attempt_features
    log(f"  Deriving 40-yard tracking features for {len(ids)} players...")
    usecols = ["event_id", "nfl_id", "entity_type", "time", "drill_type", "x", "s"]
    ct = pd.read_csv(DATA / "combine_tracking.csv", usecols=usecols)
    ct = ct[
        (ct["entity_type"] == "PLAYER")
        & (ct["drill_type"] == "FORTY_YARD_DASH")
        & ct["nfl_id"].isin(ids)
    ].copy()
    if ct.empty:
        return pd.DataFrame(columns=[
            "nfl_id", "c_top_mph", "c_t10_derived", "c_t20_derived",
            "c_t40_derived", "c_40_accel", "c_t90",
        ])
    ct = ct.sort_values(["event_id", "time"])
    ct["ds"] = ct.groupby("event_id")["s"].diff() * 10.0
    ct.loc[ct["ds"].abs() > ACCEL_CLIP, "ds"] = np.nan
    ct["drill_name"] = "FORTY_YARD_DASH"
    rows = []
    for (event_id, nfl_id), g in ct.groupby(["event_id", "nfl_id"], sort=False):
        feat = _attempt_features(g)
        feat["nfl_id"] = nfl_id
        rows.append(feat)
    att = pd.DataFrame(rows)
    idx = att.groupby("nfl_id")["max_s"].idxmax()
    best = att.loc[idx, ["nfl_id", "t10", "t20", "t40", "accel", "max_s"]].copy()
    t90 = att.groupby("nfl_id")["t90"].min()
    best["c_t90"] = best["nfl_id"].map(t90)
    best = best.rename(columns={
        "t10": "c_t10_derived", "t20": "c_t20_derived", "t40": "c_t40_derived",
        "accel": "c_40_accel", "max_s": "c_top",
    })
    best["c_top_mph"] = best["c_top"] * MPH
    keep = ["nfl_id", "c_top_mph", "c_t10_derived", "c_t20_derived",
            "c_t40_derived", "c_40_accel", "c_t90"]
    out = best[keep].reset_index(drop=True)
    out.to_parquet(cache, index=False)
    log(f"    {len(out)} players with 40 tracking -> {cache.name}")
    return out


def build_te_outcomes() -> pd.DataFrame:
    """Yards per route and companion receiving metrics for tight ends."""
    log("Building TE gameplay outcomes from player_play...")
    usecols = [
        "game_id", "play_id", "nfl_id", "play_nullified_by_penalty",
        "route_ran", "target", "rec_yards", "separation_at_pass_forward",
        "yards_after_catch", "expected_yards_after_catch",
    ]
    te_ids = set(
        pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "nfl_position"])
        .query("nfl_position == 'TE'")["nfl_id"]
    )
    parts = []
    for ch in pd.read_csv(DATA / "player_play.csv", usecols=usecols, chunksize=150_000):
        sub = ch[ch["nfl_id"].isin(te_ids)]
        if len(sub):
            parts.append(sub)
    pp = pd.concat(parts, ignore_index=True)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp[(pp["season_type"] == "REG") & (pp["play_nullified_by_penalty"] == "N")].copy()
    pp["target"] = coerce_bool(pp["target"]).fillna(False).astype(bool)
    pp["is_route"] = pp["route_ran"].notna()
    pp["is_deep"] = pp["route_ran"].isin(DEEP_ROUTES)
    pp["rec_yds"] = pd.to_numeric(pp["rec_yards"], errors="coerce")
    pp["sep"] = pd.to_numeric(pp["separation_at_pass_forward"], errors="coerce")
    pp["yac"] = pd.to_numeric(pp["yards_after_catch"], errors="coerce")
    pp["eyac"] = pd.to_numeric(pp["expected_yards_after_catch"], errors="coerce")
    pp["yac_oe"] = pp["yac"] - pp["eyac"]
    pp["caught"] = pp["rec_yds"].notna()

    def agg(g: pd.DataFrame) -> pd.Series:
        routes = g[g["is_route"]]
        n_routes = int(len(routes))
        n_tgt = int(routes["target"].sum())
        rec_yds = float(routes["rec_yds"].fillna(0).sum())
        deep = g[g["is_deep"]]
        n_deep = int(len(deep))
        deep_yds = float(deep["rec_yds"].fillna(0).sum())
        sep_vals = deep["sep"].dropna()
        yoe = g.loc[g["caught"], "yac_oe"].dropna()
        return pd.Series({
            "n_routes": n_routes,
            "n_targets": n_tgt,
            "rec_yards": rec_yds,
            "yards_per_route": rec_yds / n_routes if n_routes else np.nan,
            "target_rate": n_tgt / n_routes if n_routes else np.nan,
            "n_deep_routes": n_deep,
            "deep_yards_per_deep_route": deep_yds / n_deep if n_deep else np.nan,
            "sep_deep": float(sep_vals.mean()) if len(sep_vals) >= 8 else np.nan,
            "yac_oe": float(yoe.mean()) if len(yoe) >= 5 else np.nan,
        })

    out = pp.groupby("nfl_id", sort=False).apply(agg, include_groups=False).reset_index()
    log(f"  TE outcomes for {len(out)} players; "
        f"{int((out.n_routes >= MIN_TE_ROUTES).sum())} with ≥{MIN_TE_ROUTES} routes; "
        f"sep_deep {out.sep_deep.notna().sum()}, yac_oe {out.yac_oe.notna().sum()}, "
        f"deep YPR {int((out.n_deep_routes >= 8).sum())}")
    return out


def _combine_from_players() -> pd.DataFrame:
    players = pd.read_csv(DATA / "players.csv")
    comb = pd.read_csv(DATA / "combine_results.csv")
    M = players.merge(comb, on=["nfl_id", "draft_year"], how="left")
    M["official_forty"] = pd.to_numeric(M["forty"], errors="coerce")
    M["official_ten_yd"] = pd.to_numeric(M["ten_yd_split"], errors="coerce")
    M["pos_group"] = M["nfl_position"].map({
        "WR": "WR", "TE": "TE", "RB": "RB", "FB": "FB",
        "CB": "CB", "FS": "S", "SS": "S", "DB": "S",
        "DE": "DL", "DT": "DL", "NT": "DL", "OLB": "DL",
    })
    M["year_idx"] = M["draft_year"] - 2023
    return M


def assemble() -> pd.DataFrame:
    """One row per WR / TE / CB / S / DL with Combine tests and in-game metrics.

    Draft pick is loaded nowhere into this frame's analysis columns.
    """
    log("Assembling player table (year only; no draft pick)...")
    M = _combine_from_players()
    ss = pd.read_csv(OUT / "sunday_speed_players.csv")
    gp = pd.read_csv(OUT / "gameplay_success_players.csv")
    dl = pd.read_csv(OUT / "dl_burst_players.csv")
    te = build_te_outcomes()

    # Tracking-derived 40 features: WR/CB/S already in sunday_speed; TE/DL need a pass.
    te_ids = set(M.loc[M["pos_group"] == "TE", "nfl_id"])
    dl_ids = set(dl["nfl_id"])
    extra40 = forty_tracking_for(te_ids | dl_ids, OUT / "te_dl_forty_features.parquet")

    # --- WR / CB / S ---
    skill = gp.merge(
        ss[["nfl_id", "official_forty", "official_ten_yd", "vertical", "broad_jump",
            "three_cone", "short_shuttle", "combine_height", "combine_weight",
            "c_top_mph", "c_t10_derived", "c_t20_derived", "c_t40_derived",
            "c_40_accel", "c_t90", "sunday_speed_mph", "g_deep_p90_reg", "g_cov_p90_reg"]],
        on="nfl_id", how="left", suffixes=("", "_ss"),
    )
    # Prefer gameplay sunday_speed if present; otherwise sunday_speed table.
    if "sunday_speed_mph_ss" in skill.columns:
        skill["sunday_speed_mph"] = skill["sunday_speed_mph"].combine_first(
            skill["sunday_speed_mph_ss"]
        )
    # Combine tests: prefer sunday_speed official columns, fill from M.
    for c in TEST_ORDER:
        if c not in skill.columns:
            skill[c] = np.nan
    m_sub = M[["nfl_id"] + [c for c in TEST_ORDER if c in M.columns] + ["draft_year", "display_name", "nfl_position", "pos_group", "year_idx"]]
    skill = skill.drop(columns=[c for c in ["display_name", "nfl_position", "pos_group", "draft_year"]
                                if c in skill.columns and c != "nfl_id"], errors="ignore")
    # gp already has display_name, pos_group, draft_year — re-read cleanly
    # Rebuild skill more carefully.
    gp_keep = [
        "nfl_id", "display_name", "nfl_position", "pos_group", "draft_year",
        "n_routes", "n_deep_routes", "n_targets", "rec_yards",
        "yards_per_route", "deep_yards_per_deep_route", "target_rate",
        "deep_target_rate", "deep_target_share", "catch_rate",
        "sep_deep", "yac_oe",
        "n_def_snaps", "n_pass_snaps", "n_tackles", "tackle_rate",
        "tfl_rate", "solo_tackle_rate",
        "sunday_speed_mph", "c_top_mph",
    ]
    gp_keep = [c for c in gp_keep if c in gp.columns]
    skill = gp[gp_keep].copy()
    ss_keep = [
        "nfl_id", "official_forty", "official_ten_yd", "vertical", "broad_jump",
        "three_cone", "short_shuttle", "combine_height", "combine_weight",
        "c_top_mph", "c_t10_derived", "c_t20_derived", "c_t40_derived",
        "c_40_accel", "c_t90", "sunday_speed_mph",
    ]
    ss_keep = [c for c in ss_keep if c in ss.columns]
    skill = skill.merge(ss[ss_keep], on="nfl_id", how="outer", suffixes=("", "_ss"))
    if "sunday_speed_mph_ss" in skill.columns:
        skill["sunday_speed_mph"] = skill["sunday_speed_mph"].combine_first(skill["sunday_speed_mph_ss"])
        skill = skill.drop(columns=["sunday_speed_mph_ss"])
    if "c_top_mph_ss" in skill.columns:
        skill["c_top_mph"] = skill["c_top_mph"].combine_first(skill["c_top_mph_ss"])
        skill = skill.drop(columns=["c_top_mph_ss"])
    # Fill identity / official tests from M
    fill_cols = ["display_name", "nfl_position", "pos_group", "draft_year",
                 "official_forty", "official_ten_yd", "vertical", "broad_jump",
                 "three_cone", "short_shuttle", "combine_height", "combine_weight"]
    mfill = M[["nfl_id"] + [c for c in fill_cols if c in M.columns] + ["year_idx"]].copy()
    skill = skill.merge(mfill, on="nfl_id", how="left", suffixes=("", "_m"))
    for c in fill_cols + ["year_idx"]:
        cm = c + "_m"
        if cm in skill.columns:
            if c not in skill.columns:
                skill[c] = skill[cm]
            else:
                skill[c] = skill[c].combine_first(skill[cm])
            skill = skill.drop(columns=[cm])
    skill = skill[skill["pos_group"].isin(["WR", "CB", "S"])].copy()

    # --- TE ---
    te_m = M[M["pos_group"] == "TE"].copy()
    te_m = te_m.merge(te, on="nfl_id", how="left")
    te_m = te_m.merge(extra40, on="nfl_id", how="left")
    # If sunday_speed ever exists for a TE, pick it up (it shouldn't).
    if "sunday_speed_mph" not in te_m.columns:
        te_m["sunday_speed_mph"] = np.nan

    # --- DL (ONE combined group) ---
    dl_m = dl.merge(
        M[["nfl_id", "official_forty", "official_ten_yd", "vertical", "broad_jump",
           "three_cone", "short_shuttle", "combine_height", "combine_weight",
           "pos_group", "year_idx", "display_name", "nfl_position", "draft_year"]],
        on="nfl_id", how="left", suffixes=("", "_m"),
    )
    # official times already on dl; prefer those
    if "official_forty_m" in dl_m.columns:
        dl_m["official_forty"] = dl_m["official_forty"].combine_first(dl_m["official_forty_m"])
    if "official_ten_yd_m" in dl_m.columns:
        dl_m["official_ten_yd"] = dl_m["official_ten_yd"].combine_first(dl_m["official_ten_yd_m"])
    for c in ["vertical", "broad_jump", "three_cone", "short_shuttle",
              "combine_height", "combine_weight", "display_name", "nfl_position",
              "draft_year", "year_idx"]:
        cm = c + "_m"
        if cm in dl_m.columns:
            if c not in dl_m.columns:
                dl_m[c] = dl_m[cm]
            else:
                dl_m[c] = dl_m[c].combine_first(dl_m[cm])
    dl_m = dl_m.merge(extra40, on="nfl_id", how="left", suffixes=("", "_x"))
    # Keep existing DL c_top_mph / c_40_accel; fill 20-yd from extra40
    for c in ["c_top_mph", "c_t10_derived", "c_t20_derived", "c_t40_derived", "c_40_accel", "c_t90"]:
        cx = c + "_x"
        if cx in dl_m.columns:
            if c not in dl_m.columns:
                dl_m[c] = dl_m[cx]
            else:
                dl_m[c] = dl_m[c].combine_first(dl_m[cx])
            dl_m = dl_m.drop(columns=[cx], errors="ignore")
    dl_m["pos_group"] = "DL"
    # Keep subtype only for the appendix
    if "subtype" not in dl_m.columns:
        dl_m["subtype"] = np.nan

    frames = [skill, te_m, dl_m]
    # Harmonize columns
    all_cols = set()
    for f in frames:
        all_cols |= set(f.columns)
    identity = [
        "nfl_id", "display_name", "nfl_position", "pos_group", "subtype",
        "draft_year", "year_idx", "college_name",
    ]
    tests = list(TEST_ORDER) + ["c_t10_derived", "c_t40_derived", "c_t90"]
    outcomes = [
        "n_routes", "n_deep_routes", "n_targets", "rec_yards",
        "yards_per_route", "deep_yards_per_deep_route", "target_rate",
        "sep_deep", "yac_oe",
        "n_def_snaps", "n_pass_snaps", "n_tackles", "tackle_rate", "tfl_rate",
        "sunday_speed_mph",
        "n_rush_plays", "pressure_rate", "sack_rate", "hurry_rate",
        "speed_1s_mph", "player_get_off", "n_getoff", "n_speed_1s",
    ]
    keep = [c for c in identity + tests + outcomes if c in all_cols]
    aligned = []
    for f in frames:
        sub = f.copy()
        for c in keep:
            if c not in sub.columns:
                sub[c] = np.nan
        aligned.append(sub[keep])
    table = pd.concat(aligned, ignore_index=True)
    # One row per player (WR/CB/S outer merge could theoretically dup)
    table = table.drop_duplicates(subset=["nfl_id"], keep="first")
    table = table[table["pos_group"].isin(POS_ORDER)].copy()
    table["year_idx"] = table["draft_year"] - 2023
    log(f"  Assembled {len(table)} players: "
        + ", ".join(f"{g} {int((table.pos_group==g).sum())}" for g in POS_ORDER))
    return table


def eligible_for(table: pd.DataFrame, pos: str, outcome: dict) -> pd.DataFrame:
    d = table[table["pos_group"] == pos].copy()
    if outcome.get("min_col") and outcome["min_n"]:
        d = d[d[outcome["min_col"]] >= outcome["min_n"]]
    d = d[d[outcome["col"]].notna()].copy()
    return d


# ---------------------------------------------------------------------------
# Spearman matrix
# ---------------------------------------------------------------------------
def run_spearman(table: pd.DataFrame) -> pd.DataFrame:
    log("\n==== Spearman matrix (year-controlled, NO draft pick) ====")
    rows = []
    seed_i = 0
    for pos in POS_ORDER:
        for oc in OUTCOMES[pos]:
            elig = eligible_for(table, pos, oc)
            log(f"  {pos} {oc['short']}: {len(elig)} eligible ({oc['min_label']})")
            for test in TEST_ORDER:
                seed_i += 1
                if test not in elig.columns:
                    continue
                pair = elig[[test, oc["col"], "draft_year"]].dropna()
                res = spearman_year(pair[test], pair[oc["col"]], pair["draft_year"])
                lo, hi, n_ok = np.nan, np.nan, 0
                if res["n"] >= MIN_SPEARMAN_N and np.isfinite(res["rho"]):
                    lo, hi, n_ok = bootstrap_year_ci(
                        pair[test], pair[oc["col"]], pair["draft_year"],
                        seed=BOOT_SEED + seed_i,
                    )
                expected = TEST_SIGN[test]
                # For a lower-better outcome, the helpful Combine direction flips.
                if not oc["higher_better"] and expected != 0:
                    expected = -expected
                direction_ok = np.nan
                if expected != 0 and np.isfinite(res["rho"]):
                    direction_ok = float(np.sign(res["rho"]) == expected)
                rows.append({
                    "pos_group": pos,
                    "test": test,
                    "test_label": TEST_LABELS[test],
                    "expected_sign": TEST_SIGN[test],
                    "outcome": oc["col"],
                    "outcome_label": oc["label"],
                    "outcome_short": oc["short"],
                    "higher_better": oc["higher_better"],
                    "is_key": oc["key"],
                    "n_eligible": len(elig),
                    "n": res["n"],
                    "rho_raw": res["rho_raw"],
                    "p_raw": res["p_raw"],
                    "rho": res["rho"],
                    "p": res["p"],
                    "rho_lo": lo,
                    "rho_hi": hi,
                    "n_boot_ok": n_ok,
                    "direction_matches": direction_ok,
                    "min_label": oc["min_label"],
                })
    sp = pd.DataFrame(rows)
    # Holm and BH-FDR within group, across every valid (test, outcome) cell.
    sp["holm_p"] = np.nan
    sp["fdr_p"] = np.nan
    sp["sig_holm_05"] = False
    sp["sig_fdr_05"] = False
    for pos in POS_ORDER:
        mask = (sp["pos_group"] == pos) & sp["p"].notna() & np.isfinite(sp["p"])
        if mask.sum() == 0:
            continue
        pvals = sp.loc[mask, "p"].to_numpy(dtype=float)
        holm = multipletests(pvals, alpha=0.05, method="holm")
        fdr = multipletests(pvals, alpha=0.05, method="fdr_bh")
        sp.loc[mask, "holm_p"] = holm[1]
        sp.loc[mask, "fdr_p"] = fdr[1]
        sp.loc[mask, "sig_holm_05"] = holm[0]
        sp.loc[mask, "sig_fdr_05"] = fdr[0]
        n_fdr = int(sp.loc[mask, "sig_fdr_05"].sum())
        n_holm = int(sp.loc[mask, "sig_holm_05"].sum())
        log(f"  {pos}: {int(mask.sum())} cells, {n_fdr} FDR-significant, {n_holm} Holm-significant")
    return sp


def pick_best(sp: pd.DataFrame) -> pd.DataFrame:
    """Best Combine test for each group's key in-game metric."""
    rows = []
    for pos in POS_ORDER:
        sub = sp[(sp["pos_group"] == pos) & (sp["is_key"]) & sp["rho"].notna()].copy()
        if sub.empty:
            log(f"  {pos}: no valid Spearman cells for key outcome")
            continue
        sub["abs_rho"] = sub["rho"].abs()
        sub = sub.sort_values(["fdr_p", "p", "abs_rho"], ascending=[True, True, False])
        best = sub.iloc[0]
        # Also the best that matches the expected athletic direction, if different.
        signed = sub[sub["direction_matches"] == 1].sort_values(
            ["fdr_p", "p", "abs_rho"], ascending=[True, True, False]
        )
        rows.append({
            "pos_group": pos,
            "key_outcome": best["outcome"],
            "key_outcome_label": best["outcome_label"],
            "best_test": best["test"],
            "best_test_label": best["test_label"],
            "n": int(best["n"]),
            "rho": float(best["rho"]),
            "rho_lo": float(best["rho_lo"]) if np.isfinite(best["rho_lo"]) else np.nan,
            "rho_hi": float(best["rho_hi"]) if np.isfinite(best["rho_hi"]) else np.nan,
            "p": float(best["p"]),
            "holm_p": float(best["holm_p"]) if np.isfinite(best["holm_p"]) else np.nan,
            "fdr_p": float(best["fdr_p"]) if np.isfinite(best["fdr_p"]) else np.nan,
            "sig_fdr_05": bool(best["sig_fdr_05"]),
            "sig_holm_05": bool(best["sig_holm_05"]),
            "direction_matches": best["direction_matches"],
            "expected_sign": int(best["expected_sign"]),
            "n_tests_compared": int(len(sub)),
            "best_signed_test": (signed.iloc[0]["test"] if len(signed) else ""),
            "best_signed_rho": (float(signed.iloc[0]["rho"]) if len(signed) else np.nan),
            "best_signed_fdr_p": (float(signed.iloc[0]["fdr_p"]) if len(signed) else np.nan),
        })
        star = " FDR-significant" if best["sig_fdr_05"] else " (not FDR-significant)"
        log(f"  BEST {pos} {best['outcome_label']}: {best['test_label']}  "
            f"ρ={best['rho']:+.3f} [{best['rho_lo']:+.3f}, {best['rho_hi']:+.3f}]  "
            f"n={int(best['n'])}  p={fmt_p(best['p'])}  "
            f"Holm={fmt_p(best['holm_p'])}  FDR={fmt_p(best['fdr_p'])}{star}")
    return pd.DataFrame(rows)


def appendix_edge_interior(table: pd.DataFrame) -> pd.DataFrame:
    """Small appendix: year-only Spearman within Edge and Interior, key DL outcomes.

    Not used in the heatmap, the models, or the Bayesian pool.
    """
    log("\n==== Appendix: Edge vs Interior (not in headline) ====")
    d = table[table["pos_group"] == "DL"].copy()
    if "subtype" not in d.columns or d["subtype"].dropna().empty:
        log("  No subtype column; skipping appendix.")
        return pd.DataFrame()
    tests = ["official_ten_yd", "official_forty", "c_top_mph", "vertical",
             "broad_jump", "c_t20_derived", "c_40_accel"]
    outcomes = [o for o in OUTCOMES["DL"]]
    rows = []
    seed_i = 8000
    for sub in ["Edge", "Interior"]:
        for oc in outcomes:
            elig = d[d["subtype"] == sub].copy()
            if oc.get("min_col") and oc["min_n"]:
                elig = elig[elig[oc["min_col"]] >= oc["min_n"]]
            elig = elig[elig[oc["col"]].notna()]
            for test in tests:
                seed_i += 1
                if test not in elig.columns:
                    continue
                pair = elig[[test, oc["col"], "draft_year"]].dropna()
                res = spearman_year(pair[test], pair[oc["col"]], pair["draft_year"])
                lo, hi, n_ok = np.nan, np.nan, 0
                if res["n"] >= MIN_SPEARMAN_N and np.isfinite(res["rho"]):
                    lo, hi, n_ok = bootstrap_year_ci(
                        pair[test], pair[oc["col"]], pair["draft_year"],
                        seed=BOOT_SEED + seed_i,
                    )
                rows.append({
                    "subtype": sub,
                    "test": test,
                    "test_label": TEST_LABELS.get(test, test),
                    "outcome": oc["col"],
                    "outcome_label": oc["label"],
                    "n": res["n"],
                    "rho": res["rho"],
                    "p": res["p"],
                    "rho_lo": lo,
                    "rho_hi": hi,
                })
                if test == "official_ten_yd" and oc["col"] in ("pressure_rate", "speed_1s_mph"):
                    log(f"    {sub} {TEST_LABELS.get(test, test)} vs {oc['short']}: "
                        f"n={res['n']} ρ={fmt_rho(res['rho'])} p={fmt_p(res['p'])}")
    ap = pd.DataFrame(rows)
    ap["fdr_p"] = np.nan
    ap["holm_p"] = np.nan
    for sub in ["Edge", "Interior"]:
        mask = (ap["subtype"] == sub) & ap["p"].notna() & np.isfinite(ap["p"])
        if mask.sum() == 0:
            continue
        pvals = ap.loc[mask, "p"].to_numpy(dtype=float)
        holm = multipletests(pvals, alpha=0.05, method="holm")
        fdr = multipletests(pvals, alpha=0.05, method="fdr_bh")
        ap.loc[mask, "holm_p"] = holm[1]
        ap.loc[mask, "fdr_p"] = fdr[1]
    return ap


# ---------------------------------------------------------------------------
# Model comparison (year only, no pick)
# ---------------------------------------------------------------------------
def _metrics(y_true: np.ndarray, proba: np.ndarray) -> dict:
    proba = np.clip(np.asarray(proba, dtype=float), 1e-15, 1 - 1e-15)
    out = {"auc": np.nan, "brier": np.nan, "log_loss": np.nan}
    if not np.isfinite(proba).all() or len(y_true) < 2:
        return out
    if np.unique(y_true).size >= 2:
        try:
            out["auc"] = float(roc_auc_score(y_true, proba))
        except Exception:
            pass
    try:
        out["brier"] = float(brier_score_loss(y_true, proba))
        out["log_loss"] = float(log_loss(y_true, proba, labels=[0, 1]))
    except Exception:
        pass
    return out


def _inner_cv(ytr: np.ndarray) -> StratifiedKFold | None:
    counts = np.bincount(ytr.astype(int))
    if len(counts) < 2 or counts.min() < 2:
        return None
    n = min(n_splits_for(ytr), int(counts.min()))
    n = max(2, n)
    if int(counts.min()) < n:
        n = int(counts.min())
    if n < 2:
        return None
    return StratifiedKFold(n_splits=n, shuffle=True, random_state=CV_SEED)


def _lasso_en_fit(Xtr: np.ndarray, ytr: np.ndarray, kind: str):
    """Fit lasso or elastic-net logistic with inner CV on already-scaled Xtr."""
    inner = _inner_cv(ytr)
    if inner is None:
        return None
    if kind == "lasso":
        clf = LogisticRegressionCV(
            Cs=np.logspace(-2, 2, 10),
            l1_ratios=[1.0],
            cv=inner,
            solver="saga",
            scoring="roc_auc",
            max_iter=4000,
            tol=1e-3,
            refit=True,
            random_state=CV_SEED,
            n_jobs=1,
        )
    else:
        clf = LogisticRegressionCV(
            Cs=np.logspace(-2, 2, 10),
            l1_ratios=[0.15, 0.5, 0.85],
            cv=inner,
            solver="saga",
            scoring="roc_auc",
            max_iter=4000,
            tol=1e-3,
            refit=True,
            random_state=CV_SEED,
            n_jobs=1,
        )
    try:
        clf.fit(Xtr, ytr)
        return clf
    except Exception:
        return None


def model_factories(min_leaf: int) -> dict:
    return {
        "baseline_year": lambda: LogisticRegression(
            C=1.0, solver="lbfgs", max_iter=800, random_state=0,
        ),
        "logistic_l2": lambda: LogisticRegression(
            C=1.0, solver="lbfgs", max_iter=800, random_state=0,
        ),
        "firth": lambda: "firth",
        "tree_d2": lambda: DecisionTreeClassifier(
            max_depth=2, min_samples_leaf=min_leaf, random_state=CV_SEED,
        ),
        "tree_d3": lambda: DecisionTreeClassifier(
            max_depth=3, min_samples_leaf=min_leaf, random_state=CV_SEED,
        ),
        "gaussian_nb": lambda: GaussianNB(),
    }


def complete_case(table: pd.DataFrame, pos: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, list[str], dict]:
    """Eligible complete cases for the key outcome, model tests + year_idx."""
    oc = next(o for o in OUTCOMES[pos] if o["key"])
    elig = eligible_for(table, pos, oc)
    median = float(elig[oc["col"]].median())
    if oc["higher_better"]:
        elig = elig.copy()
        elig["success"] = (elig[oc["col"]] > median).astype(int)
    else:
        elig = elig.copy()
        elig["success"] = (elig[oc["col"]] < median).astype(int)
    elig["median_outcome"] = median
    preds = [c for c in MODEL_TESTS if c in elig.columns]
    cc = elig.dropna(subset=preds + ["year_idx", "success", oc["col"]]).copy().reset_index(drop=True)
    info = {
        "outcome": oc["col"], "outcome_label": oc["label"],
        "n_eligible": len(elig), "n_complete": len(cc),
        "n_success": int(cc["success"].sum()) if len(cc) else 0,
        "median": median, "preds": preds, "min_label": oc["min_label"],
        "higher_better": oc["higher_better"],
    }
    if len(cc) == 0:
        return cc, np.zeros((0, 0)), np.zeros((0, 0)), np.array([]), preds, info
    X_full = cc[preds + ["year_idx"]].to_numpy(dtype=float)
    X_base = cc[["year_idx"]].to_numpy(dtype=float)
    y = cc["success"].to_numpy(dtype=int)
    return cc, X_full, X_base, y, preds, info


def cv_fixed(X: np.ndarray, y: np.ndarray, factory, scale: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """20×5 RepeatedStratifiedKFold (seed 2027). Returns fold AUC, Brier, log loss."""
    splits = n_splits_for(y)
    cv = RepeatedStratifiedKFold(n_splits=splits, n_repeats=CV_REPEATS, random_state=CV_SEED)
    aucs, briers, lls = [], [], []
    for tr, te in cv.split(X, y):
        if np.unique(y[te]).size < 2 or np.unique(y[tr]).size < 2:
            continue
        Xtr, Xte = X[tr].copy(), X[te].copy()
        ytr, yte = y[tr], y[te]
        if scale:
            sc = StandardScaler()
            Xtr = sc.fit_transform(Xtr)
            Xte = sc.transform(Xte)
        try:
            model = factory()
            if isinstance(model, str) and model == "firth":
                beta, _pll, ok = fit_firth(add_intercept(Xtr), ytr)
                if not ok:
                    continue
                proba = firth_predict_proba(add_intercept(Xte), beta)
            else:
                model.fit(Xtr, ytr)
                proba = model.predict_proba(Xte)[:, 1]
            m = _metrics(yte, proba)
            if np.isfinite(m["auc"]):
                aucs.append(m["auc"])
                briers.append(m["brier"])
                lls.append(m["log_loss"])
        except Exception:
            continue
    return np.asarray(aucs), np.asarray(briers), np.asarray(lls)


def train_auc_fixed(X: np.ndarray, y: np.ndarray, factory) -> float:
    sc = StandardScaler()
    Xs = sc.fit_transform(X)
    try:
        model = factory()
        if isinstance(model, str) and model == "firth":
            beta, _pll, ok = fit_firth(add_intercept(Xs), y)
            if not ok:
                return np.nan
            proba = firth_predict_proba(add_intercept(Xs), beta)
        else:
            model.fit(Xs, y)
            proba = model.predict_proba(Xs)[:, 1]
        return float(roc_auc_score(y, proba))
    except Exception:
        return np.nan


def cv_nested_penalized(X: np.ndarray, y: np.ndarray, kind: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Nested CV for lasso / elastic net. Returns fold metrics, stability, train AUC.

    Stability is a (n_features,) array: share of outer folds with |coef| > NONZERO.
    Train AUC is a full-sample inner-CV fit.
    """
    splits = n_splits_for(y)
    cv = RepeatedStratifiedKFold(n_splits=splits, n_repeats=CV_REPEATS, random_state=CV_SEED)
    aucs, briers, lls = [], [], []
    nz_counts = np.zeros(X.shape[1], dtype=float)
    n_ok = 0
    for tr, te in cv.split(X, y):
        if np.unique(y[te]).size < 2 or np.unique(y[tr]).size < 2:
            continue
        sc = StandardScaler()
        Xtr = sc.fit_transform(X[tr])
        Xte = sc.transform(X[te])
        clf = _lasso_en_fit(Xtr, y[tr], kind)
        if clf is None:
            continue
        proba = clf.predict_proba(Xte)[:, 1]
        m = _metrics(y[te], proba)
        if not np.isfinite(m["auc"]):
            continue
        aucs.append(m["auc"])
        briers.append(m["brier"])
        lls.append(m["log_loss"])
        coef = np.asarray(clf.coef_).ravel()
        nz_counts += (np.abs(coef) > NONZERO).astype(float)
        n_ok += 1
    stability = nz_counts / n_ok if n_ok else np.full(X.shape[1], np.nan)
    # Full-sample train AUC with inner CV on all data
    sc = StandardScaler()
    Xs = sc.fit_transform(X)
    clf = _lasso_en_fit(Xs, y, kind)
    tr_auc = np.nan
    full_coef = np.full(X.shape[1], np.nan)
    full_C = np.nan
    full_l1 = np.nan
    if clf is not None:
        try:
            proba = clf.predict_proba(Xs)[:, 1]
            tr_auc = float(roc_auc_score(y, proba))
            full_coef = np.asarray(clf.coef_).ravel()
            full_C = float(np.ravel(clf.C_)[0])
            if hasattr(clf, "l1_ratio_") and clf.l1_ratio_ is not None:
                full_l1 = float(np.ravel(clf.l1_ratio_)[0])
        except Exception:
            pass
    return (
        np.asarray(aucs), np.asarray(briers), np.asarray(lls),
        stability, tr_auc, full_coef, full_C, full_l1,
    )


def _auc_row(pos, model, n, splits, aucs, briers, lls, train_auc, extra=None) -> dict:
    row = {
        "pos_group": pos,
        "model": model,
        "model_label": MODEL_LABELS.get(model, model),
        "n": n,
        "n_splits": splits,
        "n_repeats": CV_REPEATS if model not in ("bayes_loo", "bayes_5fold") else (
            1 if model == "bayes_5fold" else np.nan
        ),
        "n_fold_aucs": int(len(aucs)),
        "cv_auc_mean": float(np.mean(aucs)) if len(aucs) else np.nan,
        "cv_auc_sd": float(np.std(aucs, ddof=1)) if len(aucs) > 1 else np.nan,
        "cv_auc_lo": float(np.percentile(aucs, 2.5)) if len(aucs) >= 20 else np.nan,
        "cv_auc_hi": float(np.percentile(aucs, 97.5)) if len(aucs) >= 20 else np.nan,
        "cv_brier_mean": float(np.mean(briers)) if len(briers) else np.nan,
        "cv_logloss_mean": float(np.mean(lls)) if len(lls) else np.nan,
        "train_auc": float(train_auc) if np.isfinite(train_auc) else np.nan,
        "overfit_gap": (
            float(train_auc) - float(np.mean(aucs))
            if len(aucs) and np.isfinite(train_auc) else np.nan
        ),
        "protocol": (
            "20x5 RepeatedStratifiedKFold seed 2027"
            if model not in ("bayes_loo", "bayes_5fold")
            else ("PSIS-LOO" if model == "bayes_loo" else "5-fold CV, one pass, seed 2027")
        ),
    }
    if extra:
        row.update(extra)
    return row


def vs_baseline(auc_df: pd.DataFrame, draws: dict) -> pd.DataFrame:
    base = draws.get("baseline_year", np.array([]))
    for mname, arr in draws.items():
        if mname == "baseline_year" or len(arr) == 0 or len(base) == 0:
            continue
        k = min(len(arr), len(base))
        delta = arr[:k] - base[:k]
        mask = auc_df["model"] == mname
        auc_df.loc[mask, "delta_vs_baseline_mean"] = float(np.mean(delta))
        auc_df.loc[mask, "delta_vs_baseline_sd"] = (
            float(np.std(delta, ddof=1)) if k > 1 else np.nan
        )
        auc_df.loc[mask, "pct_folds_better"] = float((delta > 0).mean() * 100)
        if k >= 20 and np.unique(np.sign(delta[delta != 0])).size:
            try:
                w = stats.wilcoxon(delta, alternative="greater", zero_method="wilcox")
                auc_df.loc[mask, "wilcoxon_p_better"] = float(w.pvalue)
            except Exception:
                auc_df.loc[mask, "wilcoxon_p_better"] = np.nan
    return auc_df


def run_models(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    log("\n==== Model comparison (year only, no draft pick) ====")
    auc_rows = []
    stab_rows = []
    coef_rows = []
    draws_all = {}
    cc_all = {}
    for pos in POS_ORDER:
        cc, X_full, X_base, y, preds, info = complete_case(table, pos)
        log(f"  {pos}: eligible {info['n_eligible']}, complete {info['n_complete']} "
            f"(success {info['n_success']})  key={info['outcome_label']}")
        if info["n_complete"] < 15 or np.unique(y).size < 2:
            log(f"    INFEASIBLE (n={info['n_complete']})")
            continue
        names = preds + ["year_idx"]
        cc_all[pos] = (cc, X_full, X_base, y, preds, info)
        min_leaf = max(3, len(cc) // 10)
        factories = model_factories(min_leaf)
        draws = {}
        splits = n_splits_for(y)
        for mname, fac in factories.items():
            Xuse = X_base if mname == "baseline_year" else X_full
            aucs, briers, lls = cv_fixed(Xuse, y, fac)
            tr = train_auc_fixed(Xuse, y, fac)
            draws[mname] = aucs
            auc_rows.append(_auc_row(pos, mname, len(cc), splits, aucs, briers, lls, tr))
            log(f"    {mname:16s}  CV AUC {np.mean(aucs):.3f} ± {np.std(aucs, ddof=1):.3f}  "
                f"train {tr:.3f}" if len(aucs) else f"    {mname} failed")
        for kind in ("lasso", "elastic_net"):
            aucs, briers, lls, stab, tr, full_coef, full_C, full_l1 = cv_nested_penalized(
                X_full, y, kind
            )
            draws[kind] = aucs
            auc_rows.append(_auc_row(
                pos, kind, len(cc), splits, aucs, briers, lls, tr,
                extra={"chosen_C": full_C, "chosen_l1_ratio": full_l1},
            ))
            log(f"    {kind:16s}  CV AUC {np.mean(aucs):.3f} ± {np.std(aucs, ddof=1):.3f}  "
                f"train {tr:.3f}  C={full_C:.3g}  l1={full_l1:.2g}" if len(aucs)
                else f"    {kind} failed")
            for i, feat in enumerate(names):
                stab_rows.append({
                    "pos_group": pos,
                    "model": kind,
                    "feature": feat,
                    "feature_label": TEST_LABELS.get(feat, "Year" if feat == "year_idx" else feat),
                    "family": "combine" if feat in TEST_ORDER else "control",
                    "stability": float(stab[i]) if np.isfinite(stab[i]) else np.nan,
                    "full_sample_coef": float(full_coef[i]) if np.isfinite(full_coef[i]) else np.nan,
                    "full_sample_or": (
                        float(np.exp(full_coef[i])) if np.isfinite(full_coef[i]) else np.nan
                    ),
                    "nonzero_full": bool(np.isfinite(full_coef[i]) and abs(full_coef[i]) > NONZERO),
                    "chosen_C": full_C,
                    "chosen_l1_ratio": full_l1,
                    "n": len(cc),
                })
                if kind == "lasso":
                    coef_rows.append({
                        "pos_group": pos,
                        "feature": feat,
                        "feature_label": TEST_LABELS.get(feat, "Year" if feat == "year_idx" else feat),
                        "family": "combine" if feat in TEST_ORDER else "control",
                        "lasso_coef": float(full_coef[i]) if np.isfinite(full_coef[i]) else np.nan,
                        "lasso_or": (
                            float(np.exp(full_coef[i])) if np.isfinite(full_coef[i]) else np.nan
                        ),
                        "lasso_stability": float(stab[i]) if np.isfinite(stab[i]) else np.nan,
                        "nonzero": bool(np.isfinite(full_coef[i]) and abs(full_coef[i]) > NONZERO),
                        "n": len(cc),
                        "outcome": info["outcome"],
                    })
        # Paired vs baseline
        tmp = pd.DataFrame([r for r in auc_rows if r["pos_group"] == pos])
        tmp = vs_baseline(tmp, draws)
        # write deltas back
        for _, r in tmp.iterrows():
            for j, row in enumerate(auc_rows):
                if row["pos_group"] == pos and row["model"] == r["model"]:
                    for k in ("delta_vs_baseline_mean", "delta_vs_baseline_sd",
                              "pct_folds_better", "wilcoxon_p_better"):
                        if k in r.index and pd.notna(r[k]):
                            auc_rows[j][k] = r[k]
        draws_all[pos] = draws

        # Surviving lasso tests
        surviving = [
            TEST_LABELS.get(r["feature"], r["feature"])
            for r in coef_rows
            if r["pos_group"] == pos and r["family"] == "combine" and r["nonzero"]
        ]
        log(f"    lasso surviving Combine tests: {', '.join(surviving) if surviving else '(none)'}")

    return (
        pd.DataFrame(auc_rows),
        pd.DataFrame(stab_rows),
        pd.DataFrame(coef_rows),
        cc_all,
    )


def run_continuous(table: pd.DataFrame) -> pd.DataFrame:
    """Ridge, lasso, and elastic-net on the continuous key outcome, year only."""
    log("\n==== Continuous ridge / lasso / EN (year only) ====")
    rows = []
    for pos in POS_ORDER:
        oc = next(o for o in OUTCOMES[pos] if o["key"])
        elig = eligible_for(table, pos, oc)
        preds = [c for c in MODEL_TESTS if c in elig.columns]
        cc = elig.dropna(subset=preds + ["year_idx", oc["col"]]).copy()
        if len(cc) < 15:
            log(f"  {pos}: n={len(cc)} too small")
            continue
        X = cc[preds + ["year_idx"]].to_numpy(dtype=float)
        y = cc[oc["col"]].to_numpy(dtype=float)
        names = preds + ["year_idx"]
        n_splits = 5 if len(cc) >= 25 else 3
        outer = RepeatedKFold(n_splits=n_splits, n_repeats=CV_REPEATS, random_state=CV_SEED)
        inner_k = 5 if len(cc) >= 30 else 3
        r2 = {"ridge": [], "lasso": [], "elastic_net": []}
        for tr, te in outer.split(X):
            sc = StandardScaler()
            Xtr, Xte = sc.fit_transform(X[tr]), sc.transform(X[te])
            ytr, yte = y[tr], y[te]
            inner = KFold(n_splits=inner_k, shuffle=True, random_state=CV_SEED)
            try:
                ridge = RidgeCV(alphas=np.logspace(-2, 3, 12), cv=inner).fit(Xtr, ytr)
                r2["ridge"].append(r2_score(yte, ridge.predict(Xte)))
            except Exception:
                pass
            try:
                las = LassoCV(cv=inner, max_iter=8000, random_state=CV_SEED, alphas=np.logspace(-3, 1, 16)).fit(Xtr, ytr)
                r2["lasso"].append(r2_score(yte, las.predict(Xte)))
            except Exception:
                pass
            try:
                en = ElasticNetCV(
                    l1_ratio=[0.15, 0.5, 0.85], cv=inner, max_iter=8000,
                    random_state=CV_SEED, alphas=np.logspace(-3, 1, 16),
                ).fit(Xtr, ytr)
                r2["elastic_net"].append(r2_score(yte, en.predict(Xte)))
            except Exception:
                pass
        # Full-sample coefficients (per 1 SD)
        sc = StandardScaler()
        Xs = sc.fit_transform(X)
        inner = KFold(n_splits=inner_k, shuffle=True, random_state=CV_SEED)
        fits = {
            "ridge": RidgeCV(alphas=np.logspace(-2, 3, 12), cv=inner).fit(Xs, y),
            "lasso": LassoCV(cv=inner, max_iter=8000, random_state=CV_SEED,
                             alphas=np.logspace(-3, 1, 16)).fit(Xs, y),
            "elastic_net": ElasticNetCV(
                l1_ratio=[0.15, 0.5, 0.85], cv=inner, max_iter=8000,
                random_state=CV_SEED, alphas=np.logspace(-3, 1, 16),
            ).fit(Xs, y),
        }
        for kind, model in fits.items():
            arr = np.asarray(r2[kind], dtype=float)
            coef = np.asarray(model.coef_).ravel()
            log(f"  {pos} {kind:12s}  CV R² {np.mean(arr):+.3f} ± {np.std(arr, ddof=1):.3f}  n={len(cc)}"
                if len(arr) > 1 else f"  {pos} {kind} failed")
            for i, feat in enumerate(names):
                rows.append({
                    "pos_group": pos,
                    "model": kind,
                    "feature": feat,
                    "feature_label": TEST_LABELS.get(feat, "Year" if feat == "year_idx" else feat),
                    "coef_per_sd": float(coef[i]),
                    "cv_r2_mean": float(np.mean(arr)) if len(arr) else np.nan,
                    "cv_r2_sd": float(np.std(arr, ddof=1)) if len(arr) > 1 else np.nan,
                    "n": len(cc),
                    "outcome": oc["col"],
                    "alpha": float(getattr(model, "alpha_", np.nan)),
                    "l1_ratio": float(getattr(model, "l1_ratio_", np.nan)) if hasattr(model, "l1_ratio_") else np.nan,
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Bayesian hierarchical logistic (partial pooling across 5 groups)
# ---------------------------------------------------------------------------
def _zscore_within(df: pd.DataFrame, cols: list[str], group: str = "pos_group") -> tuple[pd.DataFrame, dict]:
    """Z-score Combine tests within group; return scaled copy and (mean, sd) maps."""
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").astype(float)
    stats_map = {}
    for g, sub in out.groupby(group):
        for c in cols:
            mu = float(sub[c].mean())
            sd = float(sub[c].std(ddof=1))
            stats_map[(g, c)] = (mu, sd)
            if sd < 1e-12 or not np.isfinite(sd):
                out.loc[sub.index, c] = 0.0
            else:
                out.loc[sub.index, c] = (sub[c] - mu) / sd
    return out, stats_map


def _build_bayes_model(Z, year_z, g_idx, y, groups, tests):
    import pymc as pm
    import pytensor.tensor as pt
    n = len(y)
    coords = {
        "group": list(groups),
        "test": list(tests),
        "obs": np.arange(n),
    }
    with pm.Model(coords=coords) as model:
        mu_beta = pm.Normal("mu_beta", 0.0, 1.0, dims="test")
        sigma_beta = pm.HalfNormal("sigma_beta", 0.5, dims="test")
        beta_off = pm.Normal("beta_off", 0.0, 1.0, dims=("group", "test"))
        beta = pm.Deterministic("beta", mu_beta + beta_off * sigma_beta, dims=("group", "test"))

        mu_a = pm.Normal("mu_a", 0.0, 1.5)
        sigma_a = pm.HalfNormal("sigma_a", 1.0)
        a_off = pm.Normal("a_off", 0.0, 1.0, dims="group")
        a = pm.Deterministic("a", mu_a + a_off * sigma_a, dims="group")

        # Year is global (three seasons; group-specific year slopes are under-identified).
        b_year = pm.Normal("b_year", 0.0, 1.0)

        eta = a[g_idx] + pt.sum(beta[g_idx] * Z, axis=1) + b_year * year_z
        p = pm.Deterministic("p", pm.math.sigmoid(eta), dims="obs")
        pm.Bernoulli("y", p=p, observed=y, dims="obs")
    return model


def _sample(model, draws=2000, tune=2000, chains=4, seed=CV_SEED, progress=False):
    import pymc as pm
    with model:
        idata = pm.sample(
            draws=draws, tune=tune, chains=chains, target_accept=0.9,
            random_seed=seed, nuts_sampler="nutpie",
            progressbar=progress, compute_convergence_checks=True,
        )
        pm.compute_log_likelihood(idata, progressbar=False)
    return idata


def run_bayes(cc_all: dict) -> tuple[pd.DataFrame, dict, dict]:
    """Partial-pooling hierarchical logistic. No draft pick. Year is the only control.

    Returns posterior OR table, a bag of diagnostics, and the idata.
    """
    import arviz as az
    from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss as sk_ll

    log("\n==== Bayesian hierarchical logistic (partial pooling, year only) ====")
    frames = []
    for pos, (cc, X_full, X_base, y, preds, info) in cc_all.items():
        tmp = cc.copy()
        tmp["pos_group"] = pos
        tmp["_y"] = y
        tmp["_outcome"] = info["outcome"]
        frames.append(tmp)
    if not frames:
        return pd.DataFrame(), {}, {}
    df = pd.concat(frames, ignore_index=True)
    # Use the intersection of model tests actually present for every group.
    tests = [t for t in MODEL_TESTS if t in df.columns and df.groupby("pos_group")[t].apply(lambda s: s.notna().all()).all()]
    # After complete_case, they should all be present. Still drop any all-nan.
    tests = [t for t in tests if df[t].notna().all()]
    groups = [g for g in POS_ORDER if g in set(df["pos_group"])]
    log(f"  Pooled n={len(df)} across {groups}; tests: {', '.join(tests)}")
    log(f"  Outcome is above-median { {g: KEY_LABEL[g] for g in groups} }")

    scaled, _mu = _zscore_within(df, tests)
    year_mu, year_sd = float(df["year_idx"].mean()), float(df["year_idx"].std(ddof=1))
    year_z = ((df["year_idx"] - year_mu) / year_sd).to_numpy(dtype=float) if year_sd > 0 else np.zeros(len(df))
    Z = scaled[tests].to_numpy(dtype=float)
    g_idx = df["pos_group"].map({g: i for i, g in enumerate(groups)}).to_numpy(dtype=int)
    y = df["_y"].to_numpy(dtype=int)

    model = _build_bayes_model(Z, year_z, g_idx, y, groups, tests)
    log("  Sampling (nutpie, 4×2000+2000)...")
    idata = _sample(model, draws=2000, tune=2000, chains=4, seed=CV_SEED, progress=False)

    # Diagnostics
    import arviz as az
    rhat = az.rhat(idata, var_names=["mu_beta", "sigma_beta", "mu_a", "sigma_a", "b_year"])
    rhat_max = float(max(np.max(np.asarray(rhat[v].values)) for v in rhat.data_vars))
    diverg = 0
    try:
        diverg = int(np.asarray(idata["sample_stats"]["diverging"]).sum())
    except Exception:
        pass
    log(f"  max R̂={rhat_max:.3f}, divergences={diverg}")

    loo = az.loo(idata, pointwise=True)
    elpd = float(getattr(loo, "elpd", getattr(loo, "elpd_loo", np.nan)))
    elpd_se = float(getattr(loo, "se", getattr(loo, "se_elpd_loo", np.nan)))
    # Pareto k
    try:
        k = np.asarray(loo.pareto_k)
        n_bad = int((np.asarray(k, dtype=float) > 0.7).sum())
    except Exception:
        k, n_bad = np.array([]), 0
    log(f"  PSIS-LOO elpd={elpd:.1f} (SE {elpd_se:.1f}); Pareto k>0.7: {n_bad}/{len(y)}")

    # LOO probabilities -> AUC overall and per group
    p_loo, _se = az.loo_expectations(idata, var_name="p", group="posterior", kind="mean")
    p_loo = np.asarray(p_loo.values).ravel()
    loo_auc = float(roc_auc_score(y, p_loo)) if np.unique(y).size > 1 else np.nan
    loo_brier = float(brier_score_loss(y, np.clip(p_loo, 1e-15, 1-1e-15)))
    log(f"  PSIS-LOO AUC (pooled)={loo_auc:.3f}, Brier={loo_brier:.3f}")
    per_group_loo = {}
    for i, g in enumerate(groups):
        m = g_idx == i
        if m.sum() >= 8 and np.unique(y[m]).size > 1:
            per_group_loo[g] = {
                "auc": float(roc_auc_score(y[m], p_loo[m])),
                "brier": float(brier_score_loss(y[m], np.clip(p_loo[m], 1e-15, 1-1e-15))),
                "n": int(m.sum()),
            }
            log(f"    {g} LOO AUC={per_group_loo[g]['auc']:.3f} n={int(m.sum())}")

    # 5-fold CV (one pass) for a more familiar AUC
    from sklearn.model_selection import StratifiedKFold
    fold_aucs = []
    fold_pred = np.full(len(y), np.nan)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=CV_SEED)
    log("  5-fold CV (one pass, nutpie 2×1000+1000)...")
    for fold_i, (tr, te) in enumerate(skf.split(Z, y), 1):
        # Re-standardize on train only
        tr_df = df.iloc[tr].copy()
        te_df = df.iloc[te].copy()
        tr_sc, mu_map = _zscore_within(tr_df, tests)
        te_sc = te_df.copy()
        for c in tests:
            te_sc[c] = pd.to_numeric(te_sc[c], errors="coerce").astype(float)
        for g, sub in te_df.groupby("pos_group"):
            for c in tests:
                mu, sd = mu_map.get((g, c), (tr_df[c].mean(), tr_df[c].std(ddof=1)))
                if sd is None or not np.isfinite(sd) or sd < 1e-12:
                    te_sc.loc[sub.index, c] = 0.0
                else:
                    te_sc.loc[sub.index, c] = (sub[c] - mu) / sd
        y_mu, y_sd = float(tr_df["year_idx"].mean()), float(tr_df["year_idx"].std(ddof=1))
        year_tr = ((tr_df["year_idx"] - y_mu) / y_sd).to_numpy() if y_sd > 0 else np.zeros(len(tr_df))
        year_te = ((te_df["year_idx"] - y_mu) / y_sd).to_numpy() if y_sd > 0 else np.zeros(len(te_df))
        Ztr = tr_sc[tests].to_numpy(dtype=float)
        Zte = te_sc[tests].to_numpy(dtype=float)
        gtr = tr_df["pos_group"].map({g: i for i, g in enumerate(groups)}).to_numpy(dtype=int)
        gte = te_df["pos_group"].map({g: i for i, g in enumerate(groups)}).to_numpy(dtype=int)
        ytr = y[tr]
        # Groups missing from train: shouldn't happen
        mfold = _build_bayes_model(Ztr, year_tr, gtr, ytr, groups, tests)
        try:
            idf = _sample(mfold, draws=1000, tune=1000, chains=2, seed=CV_SEED + fold_i, progress=False)
        except Exception as e:
            log(f"    fold {fold_i} failed: {e}")
            continue
        beta = np.asarray(idf["posterior"]["beta"])  # chain, draw, group, test
        a = np.asarray(idf["posterior"]["a"])        # chain, draw, group
        by = np.asarray(idf["posterior"]["b_year"])  # chain, draw
        # Flatten samples
        n_s = beta.shape[0] * beta.shape[1]
        beta_s = beta.reshape(n_s, len(groups), len(tests))
        a_s = a.reshape(n_s, len(groups))
        by_s = by.reshape(n_s)
        # eta for each test player, mean sigmoid over posterior
        eta = a_s[:, gte] + np.einsum("sgt,nt->sn", beta_s[:, gte, :], Zte) + by_s[:, None] * year_te[None, :]
        # Wait: beta_s[:, gte, :] is (n_s, n_te, n_tests); Zte is (n_te, n_tests)
        # einsum 'sgt,nt->sn' would need matching. Better:
        # (n_s, n_te, n_tests) * (n_te, n_tests) -> sum tests
        bt = beta_s[:, gte, :]  # (n_s, n_te, T)
        eta = a_s[:, gte] + (bt * Zte[None, :, :]).sum(axis=2) + by_s[:, None] * year_te[None, :]
        p_te = 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
        p_mean = p_te.mean(axis=0)
        fold_pred[te] = p_mean
        if np.unique(y[te]).size > 1:
            fa = float(roc_auc_score(y[te], p_mean))
            fold_aucs.append(fa)
            log(f"    fold {fold_i} AUC={fa:.3f} n_te={len(te)}")
        del idf

    cv5_auc = float(np.mean(fold_aucs)) if fold_aucs else np.nan
    cv5_sd = float(np.std(fold_aucs, ddof=1)) if len(fold_aucs) > 1 else np.nan
    # Per-group 5-fold (each player in one test fold)
    per_group_5 = {}
    if np.isfinite(fold_pred).any():
        for i, g in enumerate(groups):
            m = (g_idx == i) & np.isfinite(fold_pred)
            if m.sum() >= 8 and np.unique(y[m]).size > 1:
                per_group_5[g] = float(roc_auc_score(y[m], fold_pred[m]))
                log(f"    {g} 5-fold AUC={per_group_5[g]:.3f}")
    log(f"  5-fold mean AUC={cv5_auc:.3f} ± {cv5_sd:.3f} (not 20×5)")

    # Posterior OR per 1 SD, 90% equal-tail CI, P(direction)
    beta_da = idata["posterior"]["beta"]  # dims chain, draw, group, test
    mu_da = idata["posterior"]["mu_beta"]
    rows = []

    def _or_row(arr, pos, test, kind):
        """arr is 1-d samples of the coefficient."""
        ors = np.exp(arr)
        mean_or = float(np.mean(ors))
        lo, hi = np.percentile(ors, [5, 95])
        p_gt = float((ors > 1).mean())
        p_lt = float((ors < 1).mean())
        expected = TEST_SIGN.get(test, 0)
        if expected < 0:
            p_dir = p_lt
        elif expected > 0:
            p_dir = p_gt
        else:
            p_dir = np.nan
        return {
            "pos_group": pos,
            "test": test,
            "test_label": TEST_LABELS.get(test, test) if test != "_year" else "Year",
            "kind": kind,
            "or_mean": mean_or,
            "or_median": float(np.median(ors)),
            "or_lo90": float(lo),
            "or_hi90": float(hi),
            "p_gt_1": p_gt,
            "p_lt_1": p_lt,
            "p_direction": p_dir,
            "expected_sign": expected,
            "coef_mean": float(np.mean(arr)),
        }

    # Group-specific
    beta_vals = beta_da.stack(sample=("chain", "draw"))
    # dims: group, test, sample
    for gi, g in enumerate(groups):
        for ti, t in enumerate(tests):
            try:
                arr = np.asarray(beta_vals.sel(group=g, test=t).values).ravel()
            except Exception:
                # positional
                arr = np.asarray(beta_vals.values)
                # guess shape
                if arr.ndim == 3:
                    # (group, test, sample) or similar
                    # Use isel
                    arr = np.asarray(beta_da.isel(group=gi, test=ti)).ravel()
                else:
                    arr = np.asarray(beta_da).reshape(-1, len(groups), len(tests))[:, gi, ti]
            rows.append(_or_row(arr, g, t, "group"))
    # Population (mu_beta)
    for ti, t in enumerate(tests):
        try:
            arr = np.asarray(mu_da.sel(test=t).values).ravel()
        except Exception:
            arr = np.asarray(mu_da).reshape(-1, len(tests))[:, ti]
        rows.append(_or_row(arr, "Pooled", t, "population"))

    post = pd.DataFrame(rows)
    # Headlines
    log("  Posterior OR per 1 SD (90% CI), P(direction):")
    for g in groups + ["Pooled"]:
        sub = post[post["pos_group"] == g]
        # highlight strongest P(direction)
        if sub.empty:
            continue
        top = sub.dropna(subset=["p_direction"]).sort_values("p_direction", ascending=False)
        if len(top):
            r = top.iloc[0]
            log(f"    {g}: strongest P(dir) {r['test_label']}  "
                f"OR {r['or_mean']:.2f} (90% {r['or_lo90']:.2f}–{r['or_hi90']:.2f})  "
                f"P(dir)={r['p_direction']:.2f}")
        # any with P(dir)>=0.90
        strong = sub[sub["p_direction"] >= 0.90]
        for _, r in strong.iterrows():
            if len(top) and r["test"] == top.iloc[0]["test"]:
                continue
            log(f"    {g}: {r['test_label']}  OR {r['or_mean']:.2f} "
                f"(90% {r['or_lo90']:.2f}–{r['or_hi90']:.2f})  P(dir)={r['p_direction']:.2f}")

    bag = {
        "groups": groups,
        "tests": tests,
        "loo_auc": loo_auc,
        "loo_brier": loo_brier,
        "elpd": elpd,
        "elpd_se": elpd_se,
        "n_bad_k": n_bad,
        "rhat_max": rhat_max,
        "divergences": diverg,
        "per_group_loo": per_group_loo,
        "cv5_auc": cv5_auc,
        "cv5_sd": cv5_sd,
        "cv5_folds": fold_aucs,
        "per_group_5": per_group_5,
        "n": len(df),
        "p_loo": p_loo,
        "y": y,
        "g_idx": g_idx,
    }
    return post, bag, {"idata": idata, "df": df, "tests": tests, "groups": groups}


def recommend(auc: pd.DataFrame, stab: pd.DataFrame, best: pd.DataFrame) -> pd.DataFrame:
    """Recommended model per position, flagged for Kevin to decide.

    Kevin leans toward lasso as safest. We recommend lasso when it is
    within 0.03 CV AUC of the best honest model (overfit gap < 0.20 and
    not a 20×5-incompatible Bayesian-only row). Year-only baseline wins
    when Combine tests add nothing.
    """
    rows = []
    honest = {"baseline_year", "logistic_l2", "firth", "lasso", "elastic_net"}
    for pos in POS_ORDER:
        sub = auc[auc["pos_group"] == pos].copy()
        if sub.empty:
            continue
        # Restrict "best honest" to 20×5 models
        h = sub[sub["model"].isin(honest) & sub["cv_auc_mean"].notna()].copy()
        if h.empty:
            continue
        # Penalize large overfit: if overfit_gap > 0.20, treat as less trustworthy
        h["honest_score"] = h["cv_auc_mean"] - 0.25 * np.clip(h["overfit_gap"].fillna(0) - 0.15, 0, None)
        h = h.sort_values("honest_score", ascending=False)
        top = h.iloc[0]
        las = h[h["model"] == "lasso"]
        base = h[h["model"] == "baseline_year"]
        las_auc = float(las["cv_auc_mean"].iloc[0]) if len(las) else np.nan
        base_auc = float(base["cv_auc_mean"].iloc[0]) if len(base) else np.nan
        top_auc = float(top["cv_auc_mean"])
        # Surviving lasso tests
        surv = stab[
            (stab["pos_group"] == pos) & (stab["model"] == "lasso")
            & (stab["family"] == "combine") & (stab["nonzero_full"])
        ]
        surv_names = ", ".join(surv["feature_label"].tolist()) if len(surv) else "none"
        if np.isfinite(las_auc) and (top["model"] == "lasso" or (top_auc - las_auc) <= 0.03):
            if np.isfinite(base_auc) and las_auc < base_auc - 0.02 and len(surv) == 0:
                rec, reason = "baseline_year", (
                    "Lasso shrinks every Combine test to zero and does not beat "
                    "the year-only baseline. Recommendation: year-only. Lasso is "
                    "a close, equally safe alternative because it recovers the baseline."
                )
            else:
                rec, reason = "lasso", (
                    f"Lasso CV AUC {las_auc:.3f} is within 0.03 of the best honest "
                    f"model ({top['model_label']}, {top_auc:.3f}). Kevin leans lasso "
                    f"as safest; surviving tests: {surv_names}."
                )
        elif np.isfinite(base_auc) and base_auc >= top_auc - 0.02:
            rec, reason = "baseline_year", (
                f"Year-only CV AUC {base_auc:.3f} matches or beats models that add "
                f"Combine tests. Do not use a multi-test rule at this position."
            )
        else:
            rec, reason = top["model"], (
                f"Best honest CV AUC is {top['model_label']} at {top_auc:.3f}. "
                f"Lasso is at {las_auc:.3f}. Flagged for Kevin: he leans lasso as safest."
            )
        b = best[best["pos_group"] == pos]
        rows.append({
            "pos_group": pos,
            "recommended_model": rec,
            "recommended_label": MODEL_LABELS.get(rec, rec),
            "reason": reason,
            "lasso_cv_auc": las_auc,
            "baseline_cv_auc": base_auc,
            "best_honest_model": top["model"],
            "best_honest_auc": top_auc,
            "lasso_surviving": surv_names,
            "flag": "Recommendation for Kevin to decide. Kevin leans toward lasso as safest.",
        })
        log(f"  REC {pos}: {MODEL_LABELS.get(rec, rec)} — {reason}")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def make_heatmap(sp: pd.DataFrame) -> Path:
    """Headline heatmap: Combine test × in-game metric, ρ, starred if FDR-significant."""
    _style()
    n_pos = len(POS_ORDER)
    # Width scales with the busiest group
    max_cols = max(len(OUTCOMES[g]) for g in POS_ORDER)
    fig_w = max(16.5, 3.2 * max_cols + 2.2)
    fig_h = 3.15 * n_pos + 1.6
    fig, axes = plt.subplots(n_pos, 1, figsize=(fig_w, fig_h), constrained_layout=False)
    if n_pos == 1:
        axes = [axes]
    cmap = plt.cm.RdBu_r
    norm = TwoSlopeNorm(vmin=-0.65, vcenter=0.0, vmax=0.65)
    last_im = None
    for ax, pos in zip(axes, POS_ORDER):
        outs = OUTCOMES[pos]
        col_order = [o["col"] for o in outs]
        col_labs = [o["short"] for o in outs]
        mat = np.full((len(TEST_ORDER), len(col_order)), np.nan)
        star = np.zeros_like(mat, dtype=bool)
        nmat = np.full_like(mat, np.nan)
        sub = sp[sp["pos_group"] == pos]
        for i, t in enumerate(TEST_ORDER):
            for j, oc in enumerate(col_order):
                r = sub[(sub["test"] == t) & (sub["outcome"] == oc)]
                if r.empty:
                    continue
                rr = r.iloc[0]
                if np.isfinite(rr["rho"]) and rr["n"] >= MIN_SPEARMAN_N:
                    mat[i, j] = rr["rho"]
                    star[i, j] = bool(rr["sig_fdr_05"])
                    nmat[i, j] = rr["n"]
        last_im = ax.imshow(mat, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
        ax.set_yticks(range(len(TEST_ORDER)))
        ax.set_yticklabels([TEST_LABELS[t] for t in TEST_ORDER], fontsize=9)
        ax.set_xticks(range(len(col_labs)))
        # Mark the key outcome
        xt_labels = []
        for o in outs:
            lab = o["short"]
            if o["key"]:
                lab = f"★ {lab}"
            if not o["higher_better"]:
                lab = f"{lab} ↓"
            xt_labels.append(lab)
        ax.set_xticklabels(xt_labels, fontsize=9, rotation=25, ha="right")
        ax.set_ylabel(pos, fontsize=13, fontweight="bold", color=POS_COLOR[pos], labelpad=8)
        ax.tick_params(length=0)
        ax.grid(False)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                if not np.isfinite(mat[i, j]):
                    ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                               facecolor="#EEEEEE", edgecolor="white", lw=0.6))
                    ax.text(j, i, "·", ha="center", va="center", color="#AAAAAA", fontsize=8)
                    continue
                val = mat[i, j]
                txt = f"{val:+.2f}"
                if star[i, j]:
                    txt += "*"
                # Contrast
                color = "white" if abs(val) >= 0.38 else "#111111"
                weight = "bold" if star[i, j] else "normal"
                ax.text(j, i, txt, ha="center", va="center", color=color,
                        fontsize=8.2, fontweight=weight)
        # Thin grid lines
        ax.set_xticks(np.arange(-0.5, len(col_labs), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(TEST_ORDER), 1), minor=True)
        ax.grid(which="minor", color="white", linestyle="-", linewidth=1.2)
        ax.tick_params(which="minor", length=0)
        ax.set_xlim(-0.5, len(col_labs) - 0.5)
        ax.set_ylim(len(TEST_ORDER) - 0.5, -0.5)
        # Key-outcome column highlight
        key_j = next(j for j, o in enumerate(outs) if o["key"])
        ax.axvline(key_j - 0.5, color="#333333", lw=1.1, alpha=0.55)
        ax.axvline(key_j + 0.5, color="#333333", lw=1.1, alpha=0.55)

    fig.subplots_adjust(left=0.16, right=0.86, top=0.90, bottom=0.10, hspace=0.55)
    cax = fig.add_axes([0.88, 0.18, 0.015, 0.62])
    cb = fig.colorbar(last_im, cax=cax)
    cb.set_label("Spearman ρ  (year-controlled)", fontsize=10)
    fig.suptitle(
        "Which Combine tests translate to Sunday?\n"
        "Spearman ρ, residualized on draft year only  ·  no draft pick  ·  "
        "* BH-FDR < 0.05 within group",
        fontsize=15, fontweight="bold", y=0.98, va="top",
    )
    fig.text(
        0.16, 0.035,
        "★ column is the group’s key success metric.  Grey cells: n < 12 or a missing test.  "
        "↓ = lower is better.  "
        "20-yard split and Combine top speed / accel are tracking-derived from the 40-yard dash "
        "(there is no official 20-yard time).  "
        "Closing speed and defender yards-allowed are not in this file.  "
        "DL is one combined group.  RB is excluded.  "
        "Family for FDR/Holm = every valid (test × outcome) cell at that position.",
        fontsize=8.2, color="#333333", va="center", wrap=True,
    )
    path = FIGS / "fig10_combine_gameplay_heatmap.png"
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  Wrote {path}")
    return path


def make_forest(post: pd.DataFrame, bag: dict) -> Path:
    """Bayesian hierarchical forest: OR per 1 SD, 90% credible intervals."""
    _style()
    groups = bag["groups"] + (["Pooled"] if "Pooled" in set(post["pos_group"]) else [])
    tests = bag["tests"]
    n_g = len(groups)
    ncols = 3
    nrows = int(np.ceil(n_g / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14.8, 4.4 * nrows + 1.0), sharex=False)
    axes = np.atleast_2d(axes)
    colors = {**POS_COLOR, "Pooled": "#222222"}
    for k, g in enumerate(groups):
        ax = axes[k // ncols, k % ncols]
        sub = post[(post["pos_group"] == g)].copy()
        sub["_ord"] = sub["test"].map({t: i for i, t in enumerate(tests)})
        sub = sub.dropna(subset=["_ord"]).sort_values("_ord", ascending=False)
        y = np.arange(len(sub))
        for i, (_, r) in enumerate(sub.iterrows()):
            color = colors.get(g, "#333333")
            strong = np.isfinite(r["p_direction"]) and r["p_direction"] >= 0.90
            ax.hlines(i, r["or_lo90"], r["or_hi90"], color=color, lw=2.0, alpha=0.9)
            ax.plot(
                r["or_mean"], i,
                "o" if strong else "o",
                color=color, markersize=8 if strong else 6,
                markerfacecolor=color if strong else "white",
                markeredgecolor=color, markeredgewidth=1.6, zorder=3,
            )
            # Numeric label to the right of the CI
            ax.text(
                max(r["or_hi90"], 1.02) * 1.04, i,
                f"{r['or_mean']:.2f}  ({r['or_lo90']:.2f}–{r['or_hi90']:.2f})"
                + (f"  P={r['p_direction']:.2f}" if np.isfinite(r["p_direction"]) else ""),
                va="center", ha="left", fontsize=7.6, color="#222222",
            )
        ax.axvline(1.0, color="#555555", lw=1.0, ls="--")
        ax.set_yticks(y)
        ax.set_yticklabels([TEST_LABELS.get(t, t) for t in sub["test"]], fontsize=9)
        ax.set_title(g, fontsize=13, fontweight="bold", color=colors.get(g, "#222"), loc="left")
        # log-ish x if needed
        xs = np.concatenate([sub["or_lo90"].to_numpy(), sub["or_hi90"].to_numpy(), [0.5, 2.0]])
        xs = xs[np.isfinite(xs) & (xs > 0)]
        lo, hi = max(0.15, float(np.min(xs)) * 0.8), min(6.0, float(np.max(xs)) * 1.55)
        ax.set_xlim(lo, hi)
        ax.set_ylim(-0.6, len(sub) - 0.4)
        ax.set_xlabel("Odds ratio per 1 SD  (90% credible interval)", fontsize=9)
        ax.grid(axis="x", which="major")
        ax.grid(axis="y", visible=False)
    # Hide unused axes
    for k in range(n_g, nrows * ncols):
        axes[k // ncols, k % ncols].set_visible(False)
    fig.suptitle(
        "Bayesian hierarchical logistic: Combine-test odds ratios\n"
        "Partial pooling across WR, TE, CB, S, and one combined DL  ·  "
        "year only, no draft pick",
        fontsize=15, fontweight="bold", y=0.99, va="top",
    )
    fig.text(
        0.06, 0.015,
        "Filled markers: P(direction) ≥ 0.90 (posterior share on the pre-declared athletic side: "
        "faster times OR < 1, higher jumps / top speed / accel OR > 1).  "
        "Height and weight have no pre-declared side; P(direction) is omitted.  "
        f"Pooled n={bag['n']}.  PSIS-LOO AUC={bag['loo_auc']:.3f}.  "
        f"5-fold CV AUC={bag['cv5_auc']:.3f} (one pass, not 20×5).  "
        f"max R̂={bag['rhat_max']:.3f}, divergences={bag['divergences']}.  "
        "Binary outcome is above-median key success at each position "
        "(WR/TE yards per route, CB/S tackle rate, DL pressure rate).  "
        "RB is excluded.  DL is one combined group.",
        fontsize=8.0, color="#333333", va="bottom",
    )
    fig.subplots_adjust(left=0.12, right=0.97, top=0.86, bottom=0.13, wspace=0.45, hspace=0.38)
    path = FIGS / "fig11_bayes_hierarchical.png"
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  Wrote {path}")
    return path


def make_auc_chart(auc: pd.DataFrame) -> Path:
    """All-models CV AUC vs the year-only baseline, by position."""
    _style()
    order = [
        "baseline_year", "logistic_l2", "firth", "lasso", "elastic_net",
        "tree_d2", "tree_d3", "gaussian_nb", "bayes_loo", "bayes_5fold",
    ]
    labels = [MODEL_LABELS.get(m, m) for m in order]
    positions = [p for p in POS_ORDER if p in set(auc["pos_group"])]
    fig, axes = plt.subplots(1, len(positions), figsize=(3.15 * len(positions) + 1.6, 6.4), sharey=True)
    if len(positions) == 1:
        axes = [axes]
    for ax, pos in zip(axes, positions):
        sub = auc[auc["pos_group"] == pos]
        ys = []
        means = []
        sds = []
        labs = []
        colors = []
        for m, lab in zip(order, labels):
            r = sub[sub["model"] == m]
            if r.empty or not np.isfinite(r["cv_auc_mean"].iloc[0]):
                continue
            ys.append(len(ys))
            means.append(float(r["cv_auc_mean"].iloc[0]))
            sds.append(float(r["cv_auc_sd"].iloc[0]) if np.isfinite(r["cv_auc_sd"].iloc[0]) else 0)
            # Mark non-20×5
            proto = str(r["protocol"].iloc[0]) if "protocol" in r.columns else ""
            if m.startswith("bayes"):
                labs.append(lab + " †")
                colors.append("#6A3D9A")
            else:
                labs.append(lab)
                colors.append(POS_COLOR[pos] if m in ("lasso", "elastic_net", "firth", "logistic_l2") else "#555555")
        ys = np.arange(len(means))
        ax.axvline(0.5, color="#AAAAAA", lw=0.8, ls=":")
        base = sub[sub["model"] == "baseline_year"]
        if len(base) and np.isfinite(base["cv_auc_mean"].iloc[0]):
            ax.axvline(float(base["cv_auc_mean"].iloc[0]), color="#888888", lw=1.1, ls="--")
        ax.hlines(ys, np.array(means) - np.array(sds), np.array(means) + np.array(sds),
                  color="#AAAAAA", lw=1.5)
        for y, m, c in zip(ys, means, colors):
            ax.plot(m, y, "o", color=c, markersize=7, zorder=3)
            ax.text(m + 0.02, y, f"{m:.2f}", va="center", fontsize=7.5, color="#222")
        ax.set_yticks(ys)
        ax.set_yticklabels(labs, fontsize=8)
        ax.set_title(pos, fontweight="bold", color=POS_COLOR[pos])
        ax.set_xlim(0.25, 1.02)
        ax.set_xlabel("CV AUC")
        ax.grid(axis="y", visible=False)
        ax.invert_yaxis()
    fig.suptitle(
        "Model comparison: predicting above-median key success\n"
        "20×5 RepeatedStratifiedKFold, seed 2027  ·  year only, no draft pick",
        fontsize=14, fontweight="bold",
    )
    fig.text(
        0.06, 0.02,
        "Dashed line is the year-only baseline.  Error bars are the SD of fold AUCs.  "
        "† Bayesian AUCs are PSIS-LOO or a single 5-fold pass, not 20×5, and are not "
        "directly comparable.  Trees often overfit (see train AUC in the table).  "
        "DL is one combined group.  RB is excluded.",
        fontsize=8, color="#333",
    )
    fig.subplots_adjust(left=0.22, right=0.98, top=0.84, bottom=0.14, wspace=0.12)
    # first axis already has labels; that's the point of sharey
    path = FIGS / "fig12_model_comparison.png"
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  Wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _attach_bayes_auc(auc: pd.DataFrame, bag: dict, cc_all: dict) -> pd.DataFrame:
    if not bag:
        return auc
    extra = []
    for pos, info in bag.get("per_group_loo", {}).items():
        extra.append(_auc_row(
            pos, "bayes_loo", info["n"], np.nan,
            np.array([info["auc"]]), np.array([info["brier"]]), np.array([np.nan]),
            np.nan,
            extra={"protocol": "PSIS-LOO (hierarchical, pooled fit; not 20×5)"},
        ))
    for pos, a in bag.get("per_group_5", {}).items():
        extra.append(_auc_row(
            pos, "bayes_5fold", int(cc_all[pos][5]["n_complete"]), 5,
            np.array([a]), np.array([np.nan]), np.array([np.nan]),
            np.nan,
            extra={"protocol": "5-fold CV, one pass, seed 2027 (hierarchical; not 20×5)"},
        ))
    if extra:
        auc = pd.concat([auc, pd.DataFrame(extra)], ignore_index=True)
    return auc


def _rebuild_cc_all(table: pd.DataFrame) -> dict:
    cc_all = {}
    for pos in POS_ORDER:
        cc, X_full, X_base, y, preds, info = complete_case(table, pos)
        log(f"  {pos}: complete {info['n_complete']} (success {info['n_success']})")
        if info["n_complete"] >= 15 and np.unique(y).size >= 2:
            cc_all[pos] = (cc, X_full, X_base, y, preds, info)
    return cc_all


def _finish(table, sp, best, auc, stab, coef, cont, appendix, post, bag, rec, cc_all):
    table.to_csv(OUT / "combine_to_game_players.csv", index=False)
    sp.to_csv(OUT / "combine_to_game_spearman.csv", index=False)
    best.to_csv(OUT / "combine_to_game_best.csv", index=False)
    auc.to_csv(OUT / "combine_to_game_auc.csv", index=False)
    stab.to_csv(OUT / "combine_to_game_lasso_stability.csv", index=False)
    coef.to_csv(OUT / "combine_to_game_coefficients.csv", index=False)
    if len(cont):
        cont.to_csv(OUT / "combine_to_game_continuous.csv", index=False)
    if len(post):
        post.to_csv(OUT / "combine_to_game_bayes.csv", index=False)
    if len(appendix):
        appendix.to_csv(OUT / "combine_to_game_appendix_edge_interior.csv", index=False)
    rec.to_csv(OUT / "combine_to_game_recommendations.csv", index=False)
    log("\nWrote CSVs under out/combine_to_game_*.csv")
    fig10 = make_heatmap(sp)
    fig11 = make_forest(post, bag) if len(post) else None
    fig12 = make_auc_chart(auc) if len(auc) else None
    log("\n==== HEADLINE: best Combine test for each group's key metric ====")
    if len(best):
        print(best[[
            "pos_group", "key_outcome_label", "best_test_label", "n",
            "rho", "rho_lo", "rho_hi", "p", "holm_p", "fdr_p", "sig_fdr_05",
        ]].to_string(index=False))
    log("\n==== Recommendations (for Kevin to decide; he leans lasso) ====")
    if len(rec):
        for _, r in rec.iterrows():
            log(f"  {r['pos_group']}: {r['recommended_label']}")
            log(f"      {r['reason']}")
    log("\nFigures:")
    log(f"  {fig10}")
    if fig11:
        log(f"  {fig11}")
    if fig12:
        log(f"  {fig12}")
    log("Done.")
    return 0


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    log("combine_to_game.py  —  Combine → Sunday, year only, no draft pick")
    log("Groups: WR, TE, CB, S, DL (one combined group).  RB excluded.")

    if "--bayes-only" in sys.argv:
        log("Resuming from checkpoint (Spearman and 20×5 models already on disk).")
        table = pd.read_csv(OUT / "combine_to_game_players.csv")
        sp = pd.read_csv(OUT / "combine_to_game_spearman.csv")
        best = pd.read_csv(OUT / "combine_to_game_best.csv")
        auc = pd.read_csv(OUT / "combine_to_game_auc.csv")
        # Drop any leftover Bayesian rows from a partial write
        auc = auc[~auc["model"].isin(["bayes_loo", "bayes_5fold"])].copy()
        stab = pd.read_csv(OUT / "combine_to_game_lasso_stability.csv")
        coef = pd.read_csv(OUT / "combine_to_game_coefficients.csv")
        cont_p = OUT / "combine_to_game_continuous.csv"
        cont = pd.read_csv(cont_p) if cont_p.exists() else pd.DataFrame()
        ap_p = OUT / "combine_to_game_appendix_edge_interior.csv"
        appendix = pd.read_csv(ap_p) if ap_p.exists() else pd.DataFrame()
        cc_all = _rebuild_cc_all(table)
        post, bag, _extra = run_bayes(cc_all)
        auc = _attach_bayes_auc(auc, bag, cc_all)
        rec = recommend(auc, stab, best)
        return _finish(table, sp, best, auc, stab, coef, cont, appendix, post, bag, rec, cc_all)

    table = assemble()
    # Never carry a pick column into the analysis outputs.
    drop_pick = [c for c in table.columns if "pick" in c.lower() or c in ("is_udfa", "draft_round")]
    if drop_pick:
        table = table.drop(columns=drop_pick, errors="ignore")

    sp = run_spearman(table)
    best = pick_best(sp)
    appendix = appendix_edge_interior(table)

    auc, stab, coef, cc_all = run_models(table)
    cont = run_continuous(table)

    # Checkpoint before the Bayesian step so a later failure does not
    # throw away the Spearman matrix and the 20×5 model comparison.
    table.to_csv(OUT / "combine_to_game_players.csv", index=False)
    sp.to_csv(OUT / "combine_to_game_spearman.csv", index=False)
    best.to_csv(OUT / "combine_to_game_best.csv", index=False)
    auc.to_csv(OUT / "combine_to_game_auc.csv", index=False)
    stab.to_csv(OUT / "combine_to_game_lasso_stability.csv", index=False)
    coef.to_csv(OUT / "combine_to_game_coefficients.csv", index=False)
    if len(cont):
        cont.to_csv(OUT / "combine_to_game_continuous.csv", index=False)
    if len(appendix):
        appendix.to_csv(OUT / "combine_to_game_appendix_edge_interior.csv", index=False)
    log("  Checkpointed Spearman and model CSVs.")

    post, bag, _extra = run_bayes(cc_all)
    # Attach Bayesian AUCs to the comparison table
    if bag:
        for pos, info in bag.get("per_group_loo", {}).items():
            auc = pd.concat([auc, pd.DataFrame([_auc_row(
                pos, "bayes_loo", info["n"], np.nan,
                np.array([info["auc"]]), np.array([info["brier"]]), np.array([np.nan]),
                np.nan,
                extra={"protocol": "PSIS-LOO (hierarchical, pooled fit; not 20×5)"},
            )])], ignore_index=True)
        for pos, a in bag.get("per_group_5", {}).items():
            folds = np.array(bag.get("cv5_folds", [a]), dtype=float)
            auc = pd.concat([auc, pd.DataFrame([_auc_row(
                pos, "bayes_5fold", int(cc_all[pos][5]["n_complete"]), 5,
                np.array([a]), np.array([np.nan]), np.array([np.nan]),
                np.nan,
                extra={"protocol": "5-fold CV, one pass, seed 2027 (hierarchical; not 20×5)"},
            )])], ignore_index=True)

    rec = recommend(auc, stab, best)

    # Write CSVs
    table.to_csv(OUT / "combine_to_game_players.csv", index=False)
    sp.to_csv(OUT / "combine_to_game_spearman.csv", index=False)
    best.to_csv(OUT / "combine_to_game_best.csv", index=False)
    auc.to_csv(OUT / "combine_to_game_auc.csv", index=False)
    stab.to_csv(OUT / "combine_to_game_lasso_stability.csv", index=False)
    coef.to_csv(OUT / "combine_to_game_coefficients.csv", index=False)
    if len(cont):
        cont.to_csv(OUT / "combine_to_game_continuous.csv", index=False)
    if len(post):
        post.to_csv(OUT / "combine_to_game_bayes.csv", index=False)
    if len(appendix):
        appendix.to_csv(OUT / "combine_to_game_appendix_edge_interior.csv", index=False)
    rec.to_csv(OUT / "combine_to_game_recommendations.csv", index=False)
    log("\nWrote CSVs under out/combine_to_game_*.csv")

    fig10 = make_heatmap(sp)
    fig11 = make_forest(post, bag) if len(post) else None
    fig12 = make_auc_chart(auc) if len(auc) else None

    log("\n==== HEADLINE: best Combine test for each group's key metric ====")
    if len(best):
        print(best[[
            "pos_group", "key_outcome_label", "best_test_label", "n",
            "rho", "rho_lo", "rho_hi", "p", "holm_p", "fdr_p", "sig_fdr_05",
        ]].to_string(index=False))
    log("\n==== Recommendations (for Kevin to decide; he leans lasso) ====")
    if len(rec):
        for _, r in rec.iterrows():
            log(f"  {r['pos_group']}: {r['recommended_label']}")
            log(f"      {r['reason']}")
    log("\nFigures:")
    log(f"  {fig10}")
    if fig11:
        log(f"  {fig11}")
    if fig12:
        log(f"  {fig12}")
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
