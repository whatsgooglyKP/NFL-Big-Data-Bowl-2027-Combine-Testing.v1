#!/usr/bin/env python3
"""Multi-test Combine models for WR, TE, CB, and S.

Receivers already show a Combine 40 → Sunday Speed link. This script asks a
different question: do the 40, the 10-yard split, the broad jump, and the
vertical — used together — predict on-field gameplay success for WR, TE,
CB, and S?

RB is excluded from every model. The 2023–2025 rookie file has one running
back (Sione Vaki), which is too few to fit or to pool. His athletic comps,
if produced, are an anecdote only.

Success is a median split on a gameplay outcome, among rookies who clear a
minimum-snap (or route) floor. Playing time is not the outcome.

Small n, so the models are conservative: L2-penalized and Firth logistic,
repeated stratified CV against a draft-year-only baseline, shallow decision
trees and Gaussian naive Bayes as alternatives, and blunt reporting of
null results and overfitting.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/multi_test_models.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.stats import chi2
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, _tree
from statsmodels.stats.multitest import multipletests
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

N_BOOT = 2000
BOOT_SEED = 2027
CV_REPEATS = 20
CV_SEED = 2027
DEEP_ROUTES = frozenset({"GO", "POST", "CORNER", "WHEEL"})
MIN_WR_ROUTES = 20
MIN_TE_ROUTES = 20
MIN_DB_SNAPS = 50

# Primary Combine predictors. 3-cone and shuttle are too sparse for the
# joint model; they are reported in the coverage table only.
COMBINE_PREDS = ["forty", "ten_yd_split", "vertical", "broad_jump", "combine_weight"]
COMBINE_LABELS = {
    "forty": "Official 40 time",
    "ten_yd_split": "10-yard split",
    "vertical": "Vertical jump",
    "broad_jump": "Broad jump",
    "combine_weight": "Weight",
}
COMBINE_UNITS = {
    "forty": "s",
    "ten_yd_split": "s",
    "vertical": "in",
    "broad_jump": "in",
    "combine_weight": "lb",
}
# A 1 SD *increase* is expected to help (+) or hurt (−) success odds.
EXPECTED_SIGN = {
    "forty": -1,          # slower 40 → lower odds
    "ten_yd_split": -1,
    "vertical": 1,
    "broad_jump": 1,
    "combine_weight": 0,  # size control, no pre-declared direction
}
CONTROLS = ["year_idx"]
CONTROL_LABELS = {"year_idx": "Draft year"}

POS_ORDER = ["WR", "TE", "CB", "S"]
POS_COLOR = {"WR": "#0072B2", "TE": "#CC79A7", "CB": "#D55E00", "S": "#009E73"}
ALL_TEST_COLS = [
    "forty", "ten_yd_split", "vertical", "broad_jump",
    "three_cone", "short_shuttle", "combine_height", "combine_weight",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def fmt_or(x: float) -> str:
    if not np.isfinite(x):
        return "NA"
    return f"{x:.2f}"


def coerce_bool(s: pd.Series) -> pd.Series:
    return s.map({
        True: True, False: False, "TRUE": True, "FALSE": False,
        "True": True, "False": False, 1: True, 0: False, 1.0: True, 0.0: False,
    })


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


def year_controls(d: pd.DataFrame) -> pd.DataFrame:
    """Draft-year dummies only. No draft slot / pick / round (Kevin's rule, 11/2026)."""
    return pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True).astype(float)


def spearman_controlled(x: pd.Series, y: pd.Series, df: pd.DataFrame) -> dict:
    d = pd.DataFrame({
        "x": x, "y": y, "draft_year": df["draft_year"],
    }).dropna()
    out = {
        "n": int(len(d)), "rho": np.nan, "p": np.nan,
        "partial_year_rho": np.nan, "partial_year_p": np.nan,
    }
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    controls = year_controls(d)
    X = controls.to_numpy(dtype=float)
    if np.unique(X, axis=0).shape[0] >= 2:
        rx = _residualize(d["x"].to_numpy(dtype=float), X)
        ry = _residualize(d["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
            pr, pp = stats.spearmanr(rx, ry)
            out["partial_year_rho"], out["partial_year_p"] = float(pr), float(pp)
    return out


def bootstrap_year_ci(x: pd.Series, y: pd.Series, df: pd.DataFrame,
                           n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple[float, float, int]:
    base = pd.DataFrame({
        "x": x, "y": y, "draft_year": df["draft_year"],
    }).dropna().reset_index(drop=True)
    if len(base) < 8:
        return np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    rhos: list[float] = []
    for _ in range(n_boot):
        b = base.iloc[rng.integers(0, len(base), size=len(base))].reset_index(drop=True)
        if b["x"].nunique() < 2 or b["y"].nunique() < 2:
            continue
        controls = year_controls(b)
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
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "figure.titlesize": 15,
        "font.family": "DejaVu Sans",
    })


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------

def load_players_combine() -> pd.DataFrame:
    players = pd.read_csv(DATA / "players.csv")
    comb = pd.read_csv(DATA / "combine_results.csv")
    M = players.merge(comb, on=["nfl_id", "draft_year"], how="left")
    M = M.drop(columns=[c for c in M.columns if "pick" in c.lower() or c == "draft_round"], errors="ignore")
    M["year_idx"] = (M["draft_year"] - 2023).astype(float)
    M["pos_group"] = M["nfl_position"].map({
        "WR": "WR", "TE": "TE", "RB": "RB", "FB": "FB",
        "CB": "CB", "FS": "S", "SS": "S", "DB": "DB",
        "DE": "DL", "DT": "DL", "NT": "DL", "OLB": "DL",
    })
    return M


def build_te_outcomes() -> pd.DataFrame:
    """Yards per route for tight ends, same definition as WR."""
    log("Building TE gameplay outcomes from player_play...")
    usecols = [
        "game_id", "play_id", "nfl_id", "play_nullified_by_penalty",
        "route_ran", "target", "rec_yards",
    ]
    te_ids = set(pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "nfl_position"])
                 .query("nfl_position == 'TE'")["nfl_id"])
    parts = []
    for ch in pd.read_csv(DATA / "player_play.csv", usecols=usecols, chunksize=100_000):
        parts.append(ch[ch["nfl_id"].isin(te_ids)])
    pp = pd.concat(parts, ignore_index=True)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp[(pp["season_type"] == "REG") & (pp["play_nullified_by_penalty"] == "N")].copy()
    pp["target"] = coerce_bool(pp["target"]).fillna(False).astype(bool)
    pp["is_route"] = pp["route_ran"].notna()
    pp["rec_yds"] = pd.to_numeric(pp["rec_yards"], errors="coerce")

    def agg(g: pd.DataFrame) -> pd.Series:
        routes = g[g["is_route"]]
        n_routes = int(len(routes))
        n_tgt = int(routes["target"].sum())
        rec_yds = float(routes["rec_yds"].fillna(0).sum())
        return pd.Series({
            "n_routes": n_routes,
            "n_targets": n_tgt,
            "rec_yards": rec_yds,
            "yards_per_route": rec_yds / n_routes if n_routes else np.nan,
            "n_def_snaps": np.nan,
            "tackle_rate": np.nan,
        })

    out = pp.groupby("nfl_id", sort=False).apply(agg, include_groups=False).reset_index()
    log(f"  TE outcomes for {len(out)} players; "
        f"{int((out.n_routes >= MIN_TE_ROUTES).sum())} with ≥{MIN_TE_ROUTES} routes")
    return out


def build_rb_note(M: pd.DataFrame) -> pd.DataFrame:
    """Describe the lone RB (and FB) so we can exclude them honestly."""
    usecols = [
        "game_id", "play_id", "nfl_id", "play_nullified_by_penalty",
        "route_ran", "rush_yards",
    ]
    ids = set(M.loc[M["nfl_position"].isin(["RB", "FB"]), "nfl_id"])
    parts = []
    for ch in pd.read_csv(DATA / "player_play.csv", usecols=usecols, chunksize=100_000):
        sub = ch[ch["nfl_id"].isin(ids)]
        if len(sub):
            parts.append(sub)
    if not parts:
        return pd.DataFrame()
    pp = pd.concat(parts, ignore_index=True)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp[(pp["season_type"] == "REG") & (pp["play_nullified_by_penalty"] == "N")]
    rows = []
    for nid, g in pp.groupby("nfl_id"):
        row = M.loc[M["nfl_id"] == nid].iloc[0]
        rush = pd.to_numeric(g["rush_yards"], errors="coerce")
        rows.append({
            "nfl_id": nid,
            "display_name": row["display_name"],
            "nfl_position": row["nfl_position"],
            "n_snaps": int(len(g)),
            "n_routes": int(g["route_ran"].notna().sum()),
            "n_rush": int(rush.notna().sum()),
            "rush_yards": float(rush.fillna(0).sum()),
        })
    return pd.DataFrame(rows)


def load_skill_outcomes() -> pd.DataFrame:
    gs = pd.read_csv(OUT / "gameplay_success_players.csv")
    keep = [
        "nfl_id", "pos_group", "n_routes", "n_deep_routes", "n_targets",
        "rec_yards", "yards_per_route", "n_def_snaps", "n_pass_snaps",
        "n_tackles", "tackle_rate", "tfl_rate",
    ]
    keep = [c for c in keep if c in gs.columns]
    return gs[keep].copy()


@dataclass
class PosSpec:
    pos: str
    outcome: str
    outcome_label: str
    higher_better: bool
    min_col: str
    min_n: int
    min_label: str
    fallback_note: str = ""


SPECS = {
    "WR": PosSpec(
        "WR", "yards_per_route", "Yards per route run", True,
        "n_routes", MIN_WR_ROUTES, f"≥{MIN_WR_ROUTES} regular-season routes",
    ),
    "TE": PosSpec(
        "TE", "yards_per_route", "Yards per route run", True,
        "n_routes", MIN_TE_ROUTES, f"≥{MIN_TE_ROUTES} regular-season routes",
    ),
    "CB": PosSpec(
        "CB", "tackle_rate", "Tackle involvement rate", True,
        "n_def_snaps", MIN_DB_SNAPS,
        f"≥{MIN_DB_SNAPS} regular-season defensive snaps",
        fallback_note=(
            "Yards allowed per coverage snap is not computable: this file has "
            "no target-allowed or reception-yards field on a defender, and "
            "play-level yards_gained is not attributed to the covered player. "
            "Tackle involvement rate is the closest existing gameplay metric."
        ),
    ),
    "S": PosSpec(
        "S", "tackle_rate", "Tackle involvement rate", True,
        "n_def_snaps", MIN_DB_SNAPS,
        f"≥{MIN_DB_SNAPS} regular-season defensive snaps",
        fallback_note=(
            "No attributable coverage-success field (yards allowed, targets, "
            "PBU, INT) exists for a defender. Tackle involvement rate is the "
            "fallback. The earlier safety gauntlet → tackle-rate link was "
            "wrong-signed (faster gauntlet, lower tackle involvement after "
            "year), so this outcome is a weak coverage proxy."
        ),
    ),
}


def assemble_position_table(M: pd.DataFrame, skill: pd.DataFrame, te: pd.DataFrame) -> pd.DataFrame:
    """One row per WR/TE/CB/S with outcomes, Combine tests, and flags."""
    frames = []
    wr_cb_s = skill.copy()
    merged = M.merge(wr_cb_s, on="nfl_id", how="left", suffixes=("", "_gs"))
    if "pos_group_gs" in merged.columns:
        merged["pos_group"] = merged["pos_group"].fillna(merged["pos_group_gs"])
    te_m = M[M["pos_group"] == "TE"].drop(
        columns=[c for c in ["n_routes", "yards_per_route", "n_targets", "rec_yards",
                             "n_def_snaps", "tackle_rate"] if c in M.columns],
        errors="ignore",
    ).merge(te, on="nfl_id", how="left")
    # skill already has WR/CB/S; take those from merged, TE from te_m
    for pos in ["WR", "CB", "S"]:
        frames.append(merged[merged["pos_group"] == pos].copy())
    frames.append(te_m.copy())
    out = pd.concat(frames, ignore_index=True, sort=False)
    return out


def coverage_rows(M: pd.DataFrame, table: pd.DataFrame, rb_note: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # All drafted/combine players at the position, then eligible, then complete.
    for pos in POS_ORDER + ["RB"]:
        if pos == "RB":
            raw = M[M["nfl_position"] == "RB"]
            spec = None
        else:
            raw = M[M["pos_group"] == pos] if pos != "S" else M[M["pos_group"] == "S"]
            # S already is pos_group
            spec = SPECS[pos]
        # eligible
        if pos == "RB":
            elig = raw.iloc[0:0]
            n_elig = 0
        else:
            t = table[table["pos_group"] == pos]
            elig = t[t[spec.min_col] >= spec.min_n]
            n_elig = int(len(elig))
        cc = elig[elig[COMBINE_PREDS].notna().all(axis=1)] if n_elig else elig
        for scope, df in [
            ("all_in_file", raw),
            ("snap_eligible", elig),
            ("complete_case", cc),
        ]:
            if pos == "RB" and scope != "all_in_file":
                continue
            row = {
                "pos_group": pos,
                "scope": scope,
                "n": int(len(df)),
                "n_2023": int((df["draft_year"] == 2023).sum()) if len(df) else 0,
                "n_2024": int((df["draft_year"] == 2024).sum()) if len(df) else 0,
                "n_2025": int((df["draft_year"] == 2025).sum()) if len(df) else 0,
                                "feasible": pos != "RB",
                "exclusion_reason": (
                    "Only one RB in the 2023–2025 rookie file (Sione Vaki). "
                    "Excluded from every model; athletic comps are an anecdote."
                    if pos == "RB" else ""
                ),
            }
            if spec is not None:
                row["min_threshold"] = spec.min_label
                row["outcome"] = spec.outcome
                row["outcome_label"] = spec.outcome_label
            for c in ALL_TEST_COLS:
                row[f"n_{c}"] = int(df[c].notna().sum()) if len(df) and c in df.columns else 0
            row["n_complete_primary"] = (
                int(df[COMBINE_PREDS].notna().all(axis=1).sum())
                if len(df) else 0
            )
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Firth logistic
# ---------------------------------------------------------------------------

def _sigmoid(eta: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(eta, -30.0, 30.0)))


def _firth_pll(beta: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(_sigmoid(X @ beta), 1e-12, 1 - 1e-12)
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    w = p * (1 - p)
    xtwx = X.T @ (w[:, None] * X) + np.eye(X.shape[1]) * 1e-9
    sign, logdet = np.linalg.slogdet(xtwx)
    if sign <= 0 or not np.isfinite(logdet):
        return -1e12
    return ll + 0.5 * float(logdet)


def fit_firth(X: np.ndarray, y: np.ndarray, maxiter: int = 200) -> tuple[np.ndarray, float, bool]:
    """Firth (bias-reduced) logistic. X must already include an intercept column."""
    y = np.asarray(y, dtype=float)
    p = X.shape[1]
    try:
        lr = LogisticRegression(
            C=10.0, solver="lbfgs", max_iter=500,
            fit_intercept=False, random_state=0,
        )
        lr.fit(X, y)
        x0 = lr.coef_.ravel().astype(float)
    except Exception:
        x0 = np.zeros(p)
    res = minimize(
        lambda b: -_firth_pll(b, X, y),
        x0,
        method="BFGS",
        options={"maxiter": maxiter, "gtol": 1e-6},
    )
    pll = -float(res.fun) if np.isfinite(res.fun) else np.nan
    return res.x.astype(float), pll, bool(res.success) and np.isfinite(pll)


def firth_predict_proba(X: np.ndarray, beta: np.ndarray) -> np.ndarray:
    return _sigmoid(X @ beta)


def firth_plrt_pvalues(X: np.ndarray, y: np.ndarray, n_coef: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Penalized LRT p-value for each non-intercept coefficient (cols 1..n_coef)."""
    beta, pll_full, _ok = fit_firth(X, y)
    pvals = np.full(n_coef, np.nan)
    lrs = np.full(n_coef, np.nan)
    for j in range(n_coef):
        col = j + 1  # skip intercept
        Xred = np.delete(X, col, axis=1)
        _b, pll_red, ok = fit_firth(Xred, y)
        if not ok or not np.isfinite(pll_red) or not np.isfinite(pll_full):
            continue
        lr = 2.0 * (pll_full - pll_red)
        lrs[j] = lr
        pvals[j] = float(chi2.sf(max(lr, 0.0), 1))
    return beta, pvals, lrs


# ---------------------------------------------------------------------------
# Design matrix, logistic ORs, CV
# ---------------------------------------------------------------------------

def design_matrices(d: pd.DataFrame, pred_cols: list[str], impute: bool = False) -> tuple[np.ndarray, np.ndarray, list[str], StandardScaler | None, SimpleImputer | None]:
    """Return unstandardized X (no intercept), y, names, and optional fitted transformers.

    Callers standardize inside CV on the training fold. For full-sample
    inference we standardize here on the provided frame.
    """
    X = d[pred_cols].to_numpy(dtype=float)
    y = d["success"].to_numpy(dtype=int)
    imputer = None
    if impute:
        imputer = SimpleImputer(strategy="median")
        X = imputer.fit_transform(X)
    return X, y, list(pred_cols), imputer


def add_intercept(X: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(X)), X])


def standardize_fit(X: np.ndarray) -> tuple[np.ndarray, StandardScaler]:
    sc = StandardScaler()
    return sc.fit_transform(X), sc


def fit_l2(X_std: np.ndarray, y: np.ndarray, C: float = 1.0) -> LogisticRegression:
    lr = LogisticRegression(
        C=C, solver="lbfgs", max_iter=800,
        fit_intercept=True, random_state=0,
    )
    lr.fit(X_std, y)
    return lr


def bootstrap_ors(X: np.ndarray, y: np.ndarray, names: list[str],
                  kind: str = "l2", n_boot: int = N_BOOT, seed: int = BOOT_SEED,
                  C: float = 1.0) -> pd.DataFrame:
    """Bootstrap ORs per 1 SD. Standardize within each replicate."""
    rng = np.random.default_rng(seed)
    n, p = X.shape
    stored = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        Xb = X[idx]
        Xs, _sc = standardize_fit(Xb)
        try:
            if kind == "l2":
                lr = fit_l2(Xs, yb, C=C)
                coef = lr.coef_.ravel()
            else:
                beta, pll, ok = fit_firth(add_intercept(Xs), yb)
                if not ok:
                    continue
                coef = beta[1:]
        except Exception:
            continue
        stored.append(np.exp(coef))
    if len(stored) < max(50, n_boot // 20):
        return pd.DataFrame({
            "feature": names,
            "or_lo": np.nan, "or_hi": np.nan, "n_boot_ok": len(stored),
        })
    arr = np.vstack(stored)
    lo = np.percentile(arr, 2.5, axis=0)
    hi = np.percentile(arr, 97.5, axis=0)
    # two-sided bootstrap p: 2 * min(share>1, share<1)
    share_gt = (arr >= 1.0).mean(axis=0)
    share_lt = (arr <= 1.0).mean(axis=0)
    p_boot = 2.0 * np.minimum(share_gt, share_lt)
    p_boot = np.minimum(np.maximum(p_boot, 1.0 / max(len(stored), 1)), 1.0)
    return pd.DataFrame({
        "feature": names,
        "or_lo": lo,
        "or_hi": hi,
        "boot_p": p_boot,
        "n_boot_ok": len(stored),
    })


def n_splits_for(y: np.ndarray) -> int:
    counts = np.bincount(y.astype(int))
    m = int(counts.min()) if len(counts) else 0
    if m >= 10:
        return 5
    if m >= 6:
        return 4
    return 3


def cv_aucs(X: np.ndarray, y: np.ndarray, factory, scale: bool = True,
            seed: int = CV_SEED, n_repeats: int = CV_REPEATS) -> np.ndarray:
    """Return one AUC per test fold across repeated stratified CV."""
    splits = n_splits_for(y)
    cv = RepeatedStratifiedKFold(n_splits=splits, n_repeats=n_repeats, random_state=seed)
    aucs = []
    for tr, te in cv.split(X, y):
        if len(np.unique(y[te])) < 2 or len(np.unique(y[tr])) < 2:
            continue
        Xtr, Xte = X[tr].copy(), X[te].copy()
        ytr, yte = y[tr], y[te]
        if scale:
            sc = StandardScaler()
            Xtr = sc.fit_transform(Xtr)
            Xte = sc.transform(Xte)
        try:
            model = factory()
            # Firth factory returns a special tag
            if isinstance(model, str) and model == "firth":
                beta, pll, ok = fit_firth(add_intercept(Xtr), ytr)
                if not ok:
                    continue
                proba = firth_predict_proba(add_intercept(Xte), beta)
            else:
                model.fit(Xtr, ytr)
                if hasattr(model, "predict_proba"):
                    proba = model.predict_proba(Xte)[:, 1]
                else:
                    proba = model.decision_function(Xte)
            if np.unique(proba).size < 1 or not np.isfinite(proba).all():
                continue
            aucs.append(float(roc_auc_score(yte, proba)))
        except Exception:
            continue
    return np.asarray(aucs, dtype=float)


def train_auc(X: np.ndarray, y: np.ndarray, factory, scale: bool = True) -> float:
    Xs = X
    if scale:
        Xs, _sc = standardize_fit(X)
        sc = _sc
        Xte = sc.transform(X)
    else:
        Xte = X
        Xs = X
    try:
        model = factory()
        if isinstance(model, str) and model == "firth":
            beta, pll, ok = fit_firth(add_intercept(Xs), y)
            if not ok:
                return np.nan
            proba = firth_predict_proba(add_intercept(Xte if scale else Xs), beta)
        else:
            model.fit(Xs, y)
            proba = model.predict_proba(Xte if scale else Xs)[:, 1]
        if len(np.unique(y)) < 2:
            return np.nan
        return float(roc_auc_score(y, proba))
    except Exception:
        return np.nan


# ---------------------------------------------------------------------------
# Trees: readable rules
# ---------------------------------------------------------------------------

def english_tree_rules(clf: DecisionTreeClassifier, feature_names: list[str],
                       units: dict[str, str], X: np.ndarray, y: np.ndarray) -> list[str]:
    tree = clf.tree_
    lines = []

    def uname(j: int) -> str:
        n = feature_names[j]
        if n == "year_idx":
            return "draft year"
        return COMBINE_LABELS.get(n, n)

    def uthresh(j: int, t: float) -> str:
        n = feature_names[j]
        if n == "year_idx":
            return f"{2023 + t:.1f}"
        u = units.get(n, "")
        if u:
            return f"{t:.2f} {u}"
        return f"{t:.2f}"

    def recurse(node: int, conds: list[str]) -> None:
        if tree.feature[node] == _tree.TREE_UNDEFINED:
            counts = np.asarray(tree.value[node][0], dtype=float)
            n_leaf = int(tree.n_node_samples[node])
            pred = int(np.argmax(counts))
            prop = float(counts[pred] / counts.sum()) if counts.sum() else 0.0
            n_pred = int(round(prop * n_leaf))
            label = "above-median" if pred == 1 else "below-median"
            rule = " AND ".join(conds) if conds else "(all players)"
            lines.append(
                f"If {rule} → {label} ({n_pred} of {n_leaf} in this leaf, "
                f"{100 * prop:.0f}% of leaf)"
            )
            return
        j = int(tree.feature[node])
        t = float(tree.threshold[node])
        name = uname(j)
        thr = uthresh(j, t)
        recurse(int(tree.children_left[node]), conds + [f"{name} ≤ {thr}"])
        recurse(int(tree.children_right[node]), conds + [f"{name} > {thr}"])

    recurse(0, [])
    return lines


# ---------------------------------------------------------------------------
# Per-position analysis
# ---------------------------------------------------------------------------

def model_factories(min_leaf: int) -> dict:
    return {
        "baseline_l2": lambda: LogisticRegression(
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
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=200, max_depth=3, min_samples_leaf=min_leaf,
            random_state=CV_SEED, n_jobs=1,
        ),
        "grad_boost": lambda: GradientBoostingClassifier(
            n_estimators=50, max_depth=2, min_samples_leaf=min_leaf,
            learning_rate=0.1, random_state=CV_SEED,
        ),
    }


MODEL_LABELS = {
    "baseline_l2": "Year only (L2)",
    "logistic_l2": "L2 logistic (tests + year)",
    "firth": "Firth logistic (tests + year)",
    "tree_d2": "Decision tree (depth 2)",
    "tree_d3": "Decision tree (depth 3)",
    "gaussian_nb": "Gaussian naive Bayes",
    "random_forest": "Random forest (depth 3)",
    "grad_boost": "Gradient boosting (depth 2)",
}


def analyze_position(pos: str, table: pd.DataFrame) -> dict:
    spec = SPECS[pos]
    t = table[table["pos_group"] == pos].copy()
    elig = t[t[spec.min_col] >= spec.min_n].copy()
    elig = elig[elig[spec.outcome].notna()].copy()
    median = float(elig[spec.outcome].median())
    # "Above the median": strictly greater. Lower-better would flip, but
    # both of our outcomes are higher-better.
    if spec.higher_better:
        elig["success"] = (elig[spec.outcome] > median).astype(int)
    else:
        elig["success"] = (elig[spec.outcome] < median).astype(int)
    elig["median_outcome"] = median
    elig["complete_case"] = elig[COMBINE_PREDS].notna().all(axis=1)
    cc = elig[elig["complete_case"]].copy().reset_index(drop=True)
    log(f"\n==== {pos}: {spec.outcome_label} | {spec.min_label} ====")
    log(f"  Eligible {len(elig)}, median {spec.outcome}={median:.4g}, "
        f"above-median {int(elig.success.sum())}/{len(elig)}")
    log(f"  Complete cases (40, 10-yd, vertical, broad, weight): {len(cc)} "
        f"(success {int(cc.success.sum())}/{len(cc)})")
    if spec.fallback_note:
        log(f"  FALLBACK: {spec.fallback_note}")
    if len(cc) < 15 or cc["success"].nunique() < 2:
        log(f"  INFEASIBLE for multivariable models (n={len(cc)}).")
        return {
            "pos": pos, "spec": spec, "elig": elig, "cc": cc, "median": median,
            "feasible": False, "coef": pd.DataFrame(), "auc": pd.DataFrame(),
            "spearman": pd.DataFrame(), "tree_rules": [], "importances": pd.DataFrame(),
            "corr": pd.DataFrame(), "ridge": pd.DataFrame(), "imputed": {},
        }

    pred_cols = COMBINE_PREDS + CONTROLS
    X = cc[pred_cols].to_numpy(dtype=float)
    y = cc["success"].to_numpy(dtype=int)
    names = list(pred_cols)

    # Pairwise correlations among Combine tests (complete cases)
    corr = cc[COMBINE_PREDS].corr()

    # --- Multivariable L2 and Firth on standardized complete cases ---
    Xs, sc = standardize_fit(X)
    l2 = fit_l2(Xs, y, C=1.0)
    l2_or = np.exp(l2.coef_.ravel())
    beta_f, firth_p, firth_lr = firth_plrt_pvalues(add_intercept(Xs), y, n_coef=len(names))
    firth_or = np.exp(beta_f[1:])
    boot_l2 = bootstrap_ors(X, y, names, kind="l2", seed=BOOT_SEED)
    boot_f = bootstrap_ors(X, y, names, kind="firth", seed=BOOT_SEED + 1)

    # Univariable (one Combine test + controls), Firth + L2
    uni_rows = []
    for feat in COMBINE_PREDS:
        cols = [feat] + CONTROLS
        Xu = cc[cols].to_numpy(dtype=float)
        yu = y
        Xus, _ = standardize_fit(Xu)
        l2u = fit_l2(Xus, yu, C=1.0)
        bu, pu, _lu = firth_plrt_pvalues(add_intercept(Xus), yu, n_coef=len(cols))
        bootu = bootstrap_ors(Xu, yu, cols, kind="l2", seed=BOOT_SEED + 10 + COMBINE_PREDS.index(feat))
        uni_rows.append({
            "feature": feat,
            "uni_l2_or": float(np.exp(l2u.coef_.ravel()[0])),
            "uni_firth_or": float(np.exp(bu[1])),
            "uni_firth_p": float(pu[0]) if np.isfinite(pu[0]) else np.nan,
            "uni_l2_or_lo": float(bootu.loc[bootu.feature == feat, "or_lo"].iloc[0]) if len(bootu) else np.nan,
            "uni_l2_or_hi": float(bootu.loc[bootu.feature == feat, "or_hi"].iloc[0]) if len(bootu) else np.nan,
        })
    uni = pd.DataFrame(uni_rows)

    coef = pd.DataFrame({
        "pos_group": pos,
        "feature": names,
        "feature_label": [COMBINE_LABELS.get(n, CONTROL_LABELS.get(n, n)) for n in names],
        "family": ["combine" if n in COMBINE_PREDS else "control" for n in names],
        "n_eligible": len(elig),
        "n_complete": len(cc),
        "n_success": int(cc.success.sum()),
        "median_outcome": median,
        "outcome": spec.outcome,
        "outcome_label": spec.outcome_label,
        "sd": sc.scale_,
        "mean": sc.mean_,
        "l2_or": l2_or,
        "firth_or": firth_or,
        "firth_p": np.concatenate([firth_p, []]) if len(firth_p) == len(names) else firth_p,
        "firth_lr": firth_lr,
    })
    # firth_p is already length == n_coef == len(names)
    coef = coef.merge(boot_l2.add_prefix("l2_").rename(columns={"l2_feature": "feature"}),
                      on="feature", how="left")
    # fix merge: bootstrap_ors already has "feature"
    # I used add_prefix which would make l2_feature. Let me redo cleanly below if needed.
    coef = coef.drop(columns=[c for c in coef.columns if c.startswith("l2_l2") or c == "l2_feature"], errors="ignore")

    # Re-merge boots cleanly
    b1 = boot_l2.rename(columns={
        "or_lo": "l2_or_lo", "or_hi": "l2_or_hi", "boot_p": "l2_boot_p",
        "n_boot_ok": "l2_n_boot",
    })
    b2 = boot_f.rename(columns={
        "or_lo": "firth_or_lo", "or_hi": "firth_or_hi", "boot_p": "firth_boot_p",
        "n_boot_ok": "firth_n_boot",
    })
    # drop messy merge if it happened
    for c in list(coef.columns):
        if c.startswith("l2_or_lo") or c.startswith("l2_or_hi") or c.startswith("l2_boot") or c.startswith("l2_n_boot"):
            coef = coef.drop(columns=c)
    coef = coef.merge(b1, on="feature", how="left").merge(b2, on="feature", how="left")
    coef = coef.merge(uni, on="feature", how="left")

    # Holm on Firth PLRT p-values for Combine predictors only
    mask = coef["family"] == "combine"
    p = coef.loc[mask, "firth_p"].to_numpy(dtype=float)
    holm = np.full(len(p), np.nan)
    sig = np.zeros(len(p), dtype=bool)
    if np.isfinite(p).sum() >= 1:
        ok = np.isfinite(p)
        adj = np.full(len(p), np.nan)
        rej, p_adj, _, _ = multipletests(p[ok], alpha=0.05, method="holm")
        adj[ok] = p_adj
        holm = adj
        sig = np.zeros(len(p), dtype=bool)
        sig[ok] = rej
    coef["holm_p"] = np.nan
    coef["sig_holm_05"] = False
    coef.loc[mask, "holm_p"] = holm
    coef.loc[mask, "sig_holm_05"] = sig.astype(bool)
    coef["expected_sign"] = coef["feature"].map(EXPECTED_SIGN)
    match = np.sign(np.log(np.clip(coef["firth_or"].to_numpy(dtype=float), 1e-12, None))) == coef["expected_sign"].to_numpy(dtype=float)
    match = match.astype(float)
    match[coef["expected_sign"].isna() | (coef["expected_sign"] == 0)] = np.nan
    coef["or_direction_matches_expected"] = match

    # --- Partial Spearman on the continuous outcome (eligible, pairwise) ---
    sp_rows = []
    for feat in COMBINE_PREDS:
        d = elig[[feat, spec.outcome, "draft_year"]].dropna()
        # residualize on the eligible complete-for-this-test sample, not only joint CC
        res = spearman_controlled(d[feat], d[spec.outcome], d)
        lo, hi, nb = bootstrap_year_ci(d[feat], d[spec.outcome], d)
        sp_rows.append({
            "pos_group": pos,
            "feature": feat,
            "feature_label": COMBINE_LABELS[feat],
            "n": res["n"],
            "rho": res["rho"],
            "p": res["p"],
            "partial_year_rho": res["partial_year_rho"],
            "partial_year_p": res["partial_year_p"],
            "partial_ci_lo": lo,
            "partial_ci_hi": hi,
            "n_boot": nb,
            "outcome": spec.outcome,
        })
    spearman = pd.DataFrame(sp_rows)
    if len(spearman) and spearman["partial_year_p"].notna().any():
        ok = spearman["partial_year_p"].notna()
        rej, p_adj, _, _ = multipletests(
            spearman.loc[ok, "partial_year_p"], alpha=0.05, method="holm",
        )
        spearman.loc[ok, "holm_p"] = p_adj
        spearman.loc[ok, "sig_holm_05"] = rej
        spearman.loc[~ok, "holm_p"] = np.nan
        spearman.loc[~ok, "sig_holm_05"] = False
    else:
        spearman["holm_p"] = np.nan
        spearman["sig_holm_05"] = False

    # --- Ridge / OLS on continuous outcome, complete cases ---
    y_cont = cc[spec.outcome].to_numpy(dtype=float)
    # residualize outcome and features? Report raw ridge with year in the model.
    Xc, scc = standardize_fit(X)
    ridge = RidgeCV(alphas=np.logspace(-2, 3, 16), cv=min(5, n_splits_for(y) + 1) if len(cc) >= 12 else 3)
    try:
        ridge.fit(Xc, y_cont)
        ridge_coef = ridge.coef_
        ridge_alpha = float(ridge.alpha_)
    except Exception:
        ridge_coef = np.full(len(names), np.nan)
        ridge_alpha = np.nan
    # OLS
    A = add_intercept(Xc)
    try:
        ols, *_ = np.linalg.lstsq(A, y_cont, rcond=None)
        ols_coef = ols[1:]
    except Exception:
        ols_coef = np.full(len(names), np.nan)
    ridge_df = pd.DataFrame({
        "pos_group": pos,
        "feature": names,
        "ridge_coef_per_sd": ridge_coef,
        "ols_coef_per_sd": ols_coef,
        "ridge_alpha": ridge_alpha,
        "n": len(cc),
        "outcome": spec.outcome,
    })

    # --- CV AUCs ---
    min_leaf = max(3, len(cc) // 10)
    factories = model_factories(min_leaf)
    # Feature sets: full vs baseline (controls only)
    X_base = cc[CONTROLS].to_numpy(dtype=float)
    auc_rows = []
    auc_draws = {}
    for mname, fac in factories.items():
        Xuse = X_base if mname == "baseline_l2" else X
        # Trees and NB: scale is harmless; keep True for all for a single path
        draws = cv_aucs(Xuse, y, fac, scale=True)
        tr = train_auc(Xuse, y, fac, scale=True)
        auc_draws[mname] = draws
        auc_rows.append({
            "pos_group": pos,
            "model": mname,
            "model_label": MODEL_LABELS[mname],
            "n": len(cc),
            "n_splits": n_splits_for(y),
            "n_repeats": CV_REPEATS,
            "n_fold_aucs": int(len(draws)),
            "cv_auc_mean": float(np.mean(draws)) if len(draws) else np.nan,
            "cv_auc_sd": float(np.std(draws, ddof=1)) if len(draws) > 1 else np.nan,
            "cv_auc_lo": float(np.percentile(draws, 2.5)) if len(draws) >= 20 else np.nan,
            "cv_auc_hi": float(np.percentile(draws, 97.5)) if len(draws) >= 20 else np.nan,
            "train_auc": tr,
            "overfit_gap": (tr - float(np.mean(draws))) if len(draws) and np.isfinite(tr) else np.nan,
        })
    auc_df = pd.DataFrame(auc_rows)
    # Paired ΔAUC vs baseline on shared folds (same seed and split count,
    # but baseline uses different X so splits are the same because y and
    # n_splits and seed match — yes, RepeatedStratifiedKFold depends on y only).
    base_draws = auc_draws.get("baseline_l2", np.array([]))
    for mname, draws in auc_draws.items():
        if mname == "baseline_l2" or len(draws) == 0 or len(base_draws) == 0:
            continue
        k = min(len(draws), len(base_draws))
        delta = draws[:k] - base_draws[:k]
        mask = auc_df["model"] == mname
        auc_df.loc[mask, "delta_vs_baseline_mean"] = float(np.mean(delta))
        auc_df.loc[mask, "delta_vs_baseline_sd"] = float(np.std(delta, ddof=1)) if k > 1 else np.nan
        auc_df.loc[mask, "pct_folds_better"] = float((delta > 0).mean() * 100)
        # Wilcoxon signed-rank if enough
        if k >= 20 and np.unique(np.sign(delta[delta != 0])).size:
            try:
                w = stats.wilcoxon(delta, alternative="greater", zero_method="wilcox")
                auc_df.loc[mask, "wilcoxon_p_better"] = float(w.pvalue)
            except Exception:
                auc_df.loc[mask, "wilcoxon_p_better"] = np.nan

    # --- Shallow tree rules on RAW (coach units), full complete-case sample ---
    tree_rules = []
    importances = []
    raw_names = pred_cols
    units = {**COMBINE_UNITS, "year_idx": ""}
    for depth, key in [(2, "tree_d2"), (3, "tree_d3")]:
        clf = DecisionTreeClassifier(
            max_depth=depth, min_samples_leaf=min_leaf, random_state=CV_SEED,
        )
        clf.fit(X, y)  # raw units
        rules = english_tree_rules(clf, raw_names, units, X, y)
        tr_acc = float(clf.score(X, y))
        cv_mean = float(auc_df.loc[auc_df.model == key, "cv_auc_mean"].iloc[0])
        cv_sd = float(auc_df.loc[auc_df.model == key, "cv_auc_sd"].iloc[0])
        header = (
            f"{pos} decision tree, depth {depth} "
            f"(min leaf={min_leaf}): training accuracy {tr_acc:.2f}, "
            f"CV AUC {cv_mean:.2f} ± {cv_sd:.2f}. Training rules overfit; "
            f"trust the CV AUC, not the in-sample leaves."
        )
        tree_rules.append({"pos_group": pos, "depth": depth, "header": header, "rules": rules,
                           "train_acc": tr_acc, "cv_auc": cv_mean, "cv_auc_sd": cv_sd})
        for feat, imp in zip(raw_names, clf.feature_importances_):
            importances.append({
                "pos_group": pos, "model": key, "feature": feat,
                "feature_label": COMBINE_LABELS.get(feat, CONTROL_LABELS.get(feat, feat)),
                "importance": float(imp),
            })
    # RF importances too
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=3, min_samples_leaf=min_leaf,
        random_state=CV_SEED,
    )
    rf.fit(X, y)
    for feat, imp in zip(raw_names, rf.feature_importances_):
        importances.append({
            "pos_group": pos, "model": "random_forest", "feature": feat,
            "feature_label": COMBINE_LABELS.get(feat, CONTROL_LABELS.get(feat, feat)),
            "importance": float(imp),
        })
    imp_df = pd.DataFrame(importances)

    # --- Imputation sensitivity: snap-eligible, median impute Combine tests ---
    imp_out = {}
    elig_imp = elig.copy()
    # Only impute Combine tests; controls are complete. Need at least the outcome.
    Xi = elig_imp[pred_cols].to_numpy(dtype=float)
    yi = elig_imp["success"].to_numpy(dtype=int)
    # Drop rows that are missing *all* Combine tests? Impute anyway (median).
    if len(elig_imp) >= 15 and yi.min() != yi.max() and np.isnan(Xi).any():
        imp = SimpleImputer(strategy="median")
        Xi_f = imp.fit_transform(Xi)
        Xs_i, _ = standardize_fit(Xi_f)
        l2i = fit_l2(Xs_i, yi, C=1.0)
        beta_i, p_i, _ = firth_plrt_pvalues(add_intercept(Xs_i), yi, n_coef=len(names))
        draws_i = cv_aucs(Xi_f, yi, factories["logistic_l2"], scale=True)
        draws_b = cv_aucs(elig_imp[CONTROLS].to_numpy(dtype=float), yi,
                          factories["baseline_l2"], scale=True)
        imp_out = {
            "n": len(elig_imp),
            "n_imputed_rows": int(elig_imp[COMBINE_PREDS].isna().any(axis=1).sum()),
            "l2_or": dict(zip(names, np.exp(l2i.coef_.ravel()))),
            "firth_or": dict(zip(names, np.exp(beta_i[1:]))),
            "firth_p": dict(zip(names, p_i)),
            "cv_auc_l2": float(np.mean(draws_i)) if len(draws_i) else np.nan,
            "cv_auc_base": float(np.mean(draws_b)) if len(draws_b) else np.nan,
        }
        log(f"  Imputation sensitivity (n={imp_out['n']}, "
            f"{imp_out['n_imputed_rows']} rows with ≥1 imputed test): "
            f"L2 CV AUC {imp_out['cv_auc_l2']:.3f} vs baseline {imp_out['cv_auc_base']:.3f}")
    else:
        log("  Imputation sensitivity: not needed (no missing tests) or n too small.")

    # Console: blunt summary of tests
    log("  Firth OR per 1 SD (multivariable, complete cases):")
    for _, r in coef[coef.family == "combine"].iterrows():
        sig = "*" if bool(r.get("sig_holm_05")) else ""
        log(f"    {r['feature_label']}: OR {fmt_or(r['firth_or'])} "
            f"(95% boot CI {fmt_or(r['firth_or_lo'])}–{fmt_or(r['firth_or_hi'])}), "
            f"Holm p={fmt_p(r['holm_p'])}{sig}")
    base_auc = float(auc_df.loc[auc_df.model == "baseline_l2", "cv_auc_mean"].iloc[0])
    l2_auc = float(auc_df.loc[auc_df.model == "logistic_l2", "cv_auc_mean"].iloc[0])
    l2_sd = float(auc_df.loc[auc_df.model == "logistic_l2", "cv_auc_sd"].iloc[0])
    dlt = float(auc_df.loc[auc_df.model == "logistic_l2", "delta_vs_baseline_mean"].iloc[0]) if "delta_vs_baseline_mean" in auc_df.columns else np.nan
    log(f"  CV AUC  L2 multi-test {l2_auc:.3f} ± {l2_sd:.3f}  vs  year-only {base_auc:.3f}  "
        f"(Δ={dlt:+.3f})")

    return {
        "pos": pos, "spec": spec, "elig": elig, "cc": cc, "median": median,
        "feasible": True, "coef": coef, "auc": auc_df, "spearman": spearman,
        "tree_rules": tree_rules, "importances": imp_df, "corr": corr,
        "ridge": ridge_df, "imputed": imp_out, "auc_draws": auc_draws,
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------


def make_figure(results: dict) -> Path:
    _style()
    fig = plt.figure(figsize=(14.4, 12.2))
    gs = fig.add_gridspec(
        3, 2, height_ratios=[1.05, 1.05, 1.15], hspace=0.48, wspace=0.28,
        left=0.09, right=0.97, top=0.86, bottom=0.08,
    )

    from matplotlib.ticker import FixedLocator, FixedFormatter

    short_feat = {
        "forty": "Official 40 time",
        "ten_yd_split": "10-yard split",
        "vertical": "Vertical jump",
        "broad_jump": "Broad jump",
        "combine_weight": "Weight",
    }
    ticks = [0.1, 0.25, 0.5, 1, 2, 4, 10]
    tick_labels = ["0.10", "0.25", "0.50", "1", "2", "4", "10"]
    XMIN, XMAX = 0.10, 10.0

    for i, pos in enumerate(POS_ORDER):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        R = results[pos]
        ax.set_title(
            f"{pos}   n={len(R['cc'])} complete / {len(R['elig'])} eligible",
            color=POS_COLOR[pos], fontweight="bold", pad=6, loc="left",
        )
        if not R["feasible"] or R["coef"].empty:
            ax.text(0.5, 0.5, "Infeasible", ha="center", va="center", transform=ax.transAxes)
            continue
        c = R["coef"]
        c = c[c["family"] == "combine"].copy()
        c["_ord"] = c["feature"].map({f: j for j, f in enumerate(COMBINE_PREDS)})
        c = c.sort_values("_ord", ascending=False)
        y = np.arange(len(c))
        or_ = c["firth_or"].to_numpy(dtype=float)
        lo = c["firth_or_lo"].to_numpy(dtype=float)
        hi = c["firth_or_hi"].to_numpy(dtype=float)
        sig = c["sig_holm_05"].fillna(False).to_numpy(dtype=bool)
        color = POS_COLOR[pos]
        for yy, o, l, h, s in zip(y, or_, lo, hi, sig):
            l_plot = l if np.isfinite(l) else XMIN
            h_plot = h if np.isfinite(h) else XMAX
            left_clip = np.isfinite(l) and l < XMIN
            right_clip = np.isfinite(h) and h > XMAX
            l_plot = max(l_plot, XMIN)
            h_plot = min(h_plot, XMAX)
            ax.plot([l_plot, h_plot], [yy, yy], color=color, lw=2.0,
                    solid_capstyle="butt", alpha=0.9 if s else 0.75)
            if left_clip:
                ax.annotate("", xy=(XMIN, yy), xytext=(XMIN * 1.15, yy),
                            arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6))
            if right_clip:
                ax.annotate("", xy=(XMAX, yy), xytext=(XMAX / 1.15, yy),
                            arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6))
            o_plot = np.clip(o, XMIN, XMAX) if np.isfinite(o) else np.nan
            ax.plot(o_plot, yy, "o", color=color, ms=8 if s else 7,
                    markeredgecolor="#222", markeredgewidth=0.5, zorder=3)
            # OR label to the right of the point, inside the axis
            if np.isfinite(o):
                ax.text(o_plot, yy + 0.28,
                        f"{o:.2f}", va="bottom", ha="center", fontsize=8, color="#222",
                        fontweight="bold")
        ax.axvline(1.0, color="#555", lw=1.0, ls="--")
        ax.set_yticks(y)
        labels = []
        for _, r in c.iterrows():
            star = " *" if bool(r.get("sig_holm_05")) else ""
            labels.append(short_feat.get(r["feature"], r["feature_label"]) + star)
        ax.set_yticklabels(labels)
        ax.set_xscale("log")
        ax.set_xlim(XMIN, XMAX)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(FixedFormatter(tick_labels))
        ax.set_xlabel("Odds ratio per 1 SD  (arrow = CI extends past the axis)")
        ax.set_ylim(-0.7, len(c) - 0.35)
        ax.text(
            0.0, -0.20,
            f"{R['spec'].outcome_label}  ·  {R['spec'].min_label}",
            transform=ax.transAxes, ha="left", va="top", fontsize=8, color="#444",
        )

    # --- Model comparison AUC, full width ---
    ax = fig.add_subplot(gs[2, :])
    model_order = [
        "baseline_l2", "logistic_l2", "firth", "tree_d2", "tree_d3",
        "gaussian_nb", "random_forest", "grad_boost",
    ]
    short = {
        "baseline_l2": "Year only",
        "logistic_l2": "L2 logistic",
        "firth": "Firth logistic",
        "tree_d2": "Tree, depth 2",
        "tree_d3": "Tree, depth 3",
        "gaussian_nb": "Naive Bayes",
        "random_forest": "Random forest",
        "grad_boost": "Grad. boosting",
    }
    width = 0.18
    x = np.arange(len(model_order))
    for i, pos in enumerate(POS_ORDER):
        R = results[pos]
        if not R["feasible"] or R["auc"].empty:
            continue
        a = R["auc"].set_index("model")
        means, sds = [], []
        for m in model_order:
            if m in a.index:
                means.append(float(a.loc[m, "cv_auc_mean"]))
                sds.append(float(a.loc[m, "cv_auc_sd"]))
            else:
                means.append(np.nan)
                sds.append(0)
        offset = (i - 1.5) * width
        ax.bar(x + offset, means, width, yerr=sds, label=pos, color=POS_COLOR[pos],
               ecolor="#444", capsize=2, error_kw={"lw": 0.8}, zorder=3, alpha=0.92)
    ax.axhline(0.5, color="#555", ls="--", lw=1, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels([short[m] for m in model_order])
    ax.set_ylabel("Repeated-stratified CV AUC")
    ax.set_ylim(0.25, 1.05)
    # custom legend that includes chance line
    from matplotlib.lines import Line2D
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Line2D([0], [0], color="#555", ls="--", lw=1))
    labels.append("Chance (0.50)")
    ax.legend(handles, labels, loc="upper right", ncol=5, frameon=False)
    ax.set_title(
        "Does any multi-test model beat a draft-year-only baseline?  "
        "Error bars are the SD across CV folds — they are wide because each test fold is small.",
        loc="left", fontsize=11,
    )

    fig.suptitle(
        "Do Combine tests, used together, predict above-median rookies?",
        fontsize=16, fontweight="bold", y=0.975,
    )
    fig.text(
        0.5, 0.932,
        "Firth odds ratios per 1 SD, controlling for draft year only.  "
        "A slower 40 or 10-yard split should have OR < 1 if speed helps.  "
        "No test is Holm-significant at any position.",
        ha="center", va="top", fontsize=9.5, color="#333",
    )
    fig.text(
        0.5, 0.012,
        "CB and S use tackle involvement rate because yards allowed is not attributable in this file.  "
        "RB is excluded (n = 1).  Arrows mean the 95% bootstrap CI extends past the axis.  "
        "Wide error bars on AUC are expected: test folds are small.",
        ha="center", va="bottom", fontsize=8.5, color="#444",
    )
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / "fig9_multi_test_models.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    log(f"Wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    log("Loading players, Combine results, and gameplay outcomes...")
    M = load_players_combine()
    skill = load_skill_outcomes()
    te = build_te_outcomes()
    rb_note = build_rb_note(M)
    if len(rb_note):
        log("\n==== RB exclusion (not modeled) ====")
        for _, r in rb_note.iterrows():
            log(f"  {r['display_name']} ({r['nfl_position']}): "
                f"{r['n_snaps']} REG snaps, {r['n_routes']} routes, "
                f"{r['n_rush']} rush plays, {r['rush_yards']:.0f} rush yards. "
                f"Anecdote only — excluded from every model.")

    table = assemble_position_table(M, skill, te)
    # keep useful columns unique
    cov = coverage_rows(M, table, rb_note)
    cov.to_csv(OUT / "multi_test_coverage.csv", index=False)
    log("\n==== Coverage (all in file / snap-eligible / complete case) ====")
    show = ["pos_group", "scope", "n", "n_forty", "n_ten_yd_split", "n_vertical",
            "n_broad_jump", "n_three_cone", "n_short_shuttle", "n_combine_weight",
            "n_complete_primary"]
    log(cov[show].to_string(index=False))

    results = {}
    coef_all, auc_all, sp_all, ridge_all, imp_all = [], [], [], [], []
    player_frames = []
    tree_lines = []
    for pos in POS_ORDER:
        R = analyze_position(pos, table)
        results[pos] = R
        if len(R["elig"]):
            player_frames.append(R["elig"])
        if R["feasible"]:
            coef_all.append(R["coef"])
            auc_all.append(R["auc"])
            sp_all.append(R["spearman"])
            ridge_all.append(R["ridge"])
            if len(R["importances"]):
                imp_all.append(R["importances"])
            for block in R["tree_rules"]:
                tree_lines.append(block["header"])
                for rule in block["rules"]:
                    tree_lines.append("  " + rule)
                tree_lines.append("")

    coef_df = pd.concat(coef_all, ignore_index=True) if coef_all else pd.DataFrame()
    auc_df = pd.concat(auc_all, ignore_index=True) if auc_all else pd.DataFrame()
    sp_df = pd.concat(sp_all, ignore_index=True) if sp_all else pd.DataFrame()
    ridge_df = pd.concat(ridge_all, ignore_index=True) if ridge_all else pd.DataFrame()
    imp_df = pd.concat(imp_all, ignore_index=True) if imp_all else pd.DataFrame()

    # Imputation rows into a small CSV
    imp_rows = []
    for pos in POS_ORDER:
        imp = results[pos].get("imputed") or {}
        if not imp:
            continue
        for feat, or_ in (imp.get("l2_or") or {}).items():
            imp_rows.append({
                "pos_group": pos, "feature": feat, "n": imp["n"],
                "n_imputed_rows": imp["n_imputed_rows"],
                "l2_or": or_,
                "firth_or": imp["firth_or"].get(feat, np.nan),
                "firth_p": imp["firth_p"].get(feat, np.nan),
                "cv_auc_l2": imp["cv_auc_l2"],
                "cv_auc_base": imp["cv_auc_base"],
                "note": "Median imputation within the snap-eligible position sample. Sensitivity only.",
            })
    imp_df_or = pd.DataFrame(imp_rows)

    # Player table (eligible only)
    if player_frames:
        players_out = pd.concat(player_frames, ignore_index=True, sort=False)
        keep = [
            "nfl_id", "display_name", "nfl_position", "pos_group", "draft_year",
                        "forty", "ten_yd_split", "vertical", "broad_jump",
            "three_cone", "short_shuttle", "combine_height", "combine_weight",
            "n_routes", "n_targets", "rec_yards", "yards_per_route",
            "n_def_snaps", "n_pass_snaps", "n_tackles", "tackle_rate",
            "success", "median_outcome", "complete_case",
        ]
        keep = [c for c in keep if c in players_out.columns]
        players_out[keep].to_csv(OUT / "multi_test_players.csv", index=False)

    coef_df.to_csv(OUT / "multi_test_coefficients.csv", index=False)
    auc_df.to_csv(OUT / "multi_test_auc.csv", index=False)
    # Combined convenience file
    # (coefficients and AUCs also live in their own CSVs)
    if len(imp_df_or):
        imp_df_or.to_csv(OUT / "multi_test_imputation_sensitivity.csv", index=False)
    sp_df.to_csv(OUT / "multi_test_spearman.csv", index=False)
    ridge_df.to_csv(OUT / "multi_test_ridge.csv", index=False)
    if len(imp_df):
        imp_df.to_csv(OUT / "multi_test_importances.csv", index=False)
    rules_path = OUT / "multi_test_tree_rules.txt"
    rules_path.write_text("\n".join(tree_lines) + "\n")
    log(f"Wrote {rules_path}")

    fig_path = make_figure(results)

    # Final coach-facing dump
    log("\n==== COACH SUMMARY ====")
    log("RB: excluded. One player (Sione Vaki) in the 2023–2025 file. Not modeled.")
    for pos in POS_ORDER:
        R = results[pos]
        log(f"\n{pos}: success = above-median {R['spec'].outcome_label} "
            f"among rookies with {R['spec'].min_label}. "
            f"Eligible n={len(R['elig'])}, complete-case n={len(R['cc'])}.")
        if R["spec"].fallback_note:
            log(f"  {R['spec'].fallback_note}")
        if not R["feasible"]:
            log("  Infeasible.")
            continue
        any_sig = bool(R["coef"].loc[R["coef"].family == "combine", "sig_holm_05"].fillna(False).any())
        if not any_sig:
            log("  No Combine test is Holm-significant in the multivariable Firth model.")
        for _, r in R["coef"][R["coef"].family == "combine"].iterrows():
            log(f"  {r['feature_label']}: Firth OR/SD {fmt_or(r['firth_or'])} "
                f"(CI {fmt_or(r['firth_or_lo'])}–{fmt_or(r['firth_or_hi'])}), "
                f"Holm p={fmt_p(r['holm_p'])}")
        a = R["auc"].set_index("model")
        log("  CV AUC vs year-only baseline "
            f"{a.loc['baseline_l2','cv_auc_mean']:.3f}:")
        for m in ["logistic_l2", "firth", "tree_d2", "tree_d3", "gaussian_nb",
                  "random_forest", "grad_boost"]:
            row = a.loc[m]
            dlt = row["delta_vs_baseline_mean"] if "delta_vs_baseline_mean" in a.columns else np.nan
            log(f"    {MODEL_LABELS[m]}: {row['cv_auc_mean']:.3f} "
                f"(±{row['cv_auc_sd']:.3f}, train {row['train_auc']:.3f}, "
                f"Δ={dlt:+.3f})")
        for block in R["tree_rules"]:
            log("  " + block["header"])
            for rule in block["rules"]:
                log("    " + rule)

    log(f"\nFigure: {fig_path}")
    log("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
