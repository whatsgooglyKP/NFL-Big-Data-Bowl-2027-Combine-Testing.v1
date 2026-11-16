"""Shared stats for db_tackling.py and dl_recheck.py.

Spearman controlled for draft year (or year x role cells) by demeaning both
variables within cells, then rank-correlating the residuals. Draft slot is
never used. Vectorized player-level bootstrap for 95% CIs, BH-FDR, and
split-half reliability with Spearman-Brown.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

N_BOOT, SEED, MIN_N = 2000, 2027, 12
MPH = 2.0455


def _demean(v: np.ndarray, codes: np.ndarray, k: int) -> np.ndarray:
    """Row-wise demean v (B x n) within integer cells codes (B x n)."""
    B, n = v.shape
    flat = codes + (np.arange(B)[:, None] * k)
    sums = np.bincount(flat.ravel(), weights=v.ravel(), minlength=B * k)
    cnt = np.bincount(flat.ravel(), minlength=B * k)
    means = np.divide(sums, cnt, out=np.zeros_like(sums), where=cnt > 0)
    return v - means[flat]


def _rowcorr_rank(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ra = stats.rankdata(a, axis=1); rb = stats.rankdata(b, axis=1)
    ra -= ra.mean(1, keepdims=True); rb -= rb.mean(1, keepdims=True)
    den = np.sqrt((ra ** 2).sum(1) * (rb ** 2).sum(1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return (ra * rb).sum(1) / den


def spearman_ctrl(x, y, cells, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    d = pd.DataFrame({"x": np.asarray(x, float), "y": np.asarray(y, float),
                      "c": np.asarray(cells)}).dropna()
    out = dict(n=len(d), rho_raw=np.nan, p_raw=np.nan, rho=np.nan, p=np.nan, lo=np.nan, hi=np.nan)
    if len(d) < MIN_N or d.x.nunique() < 3 or d.y.nunique() < 3:
        return out
    r, p = stats.spearmanr(d.x, d.y)
    out.update(rho_raw=float(r), p_raw=float(p))
    codes = pd.factorize(d.c)[0]; k = codes.max() + 1
    xv, yv = d.x.to_numpy()[None], d.y.to_numpy()[None]
    rx, ry = _demean(xv, codes[None], k)[0], _demean(yv, codes[None], k)[0]
    r, p = stats.spearmanr(rx, ry)
    out.update(rho=float(r), p=float(p))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    cb = codes[idx]
    bx = _demean(d.x.to_numpy()[idx], cb, k); by = _demean(d.y.to_numpy()[idx], cb, k)
    rb = _rowcorr_rank(bx, by); rb = rb[np.isfinite(rb)]
    if len(rb) >= 100:
        out["lo"], out["hi"] = (float(v) for v in np.percentile(rb, [2.5, 97.5]))
    return out


def bh(p: pd.Series) -> pd.Series:
    q = pd.Series(np.nan, index=p.index)
    m = p.notna()
    if m.sum():
        q[m] = multipletests(p[m], method="fdr_bh")[1]
    return q


def split_half(plays: pd.DataFrame, pid: str, val: str, agg: str = "mean",
               min_half: int = 1, seed: int = SEED) -> dict:
    """Odd/even play order split per player (plays sorted by game, play)."""
    p = plays.sort_values(["game_id", "play_id"]).copy()
    p["half"] = p.groupby(pid).cumcount() % 2
    g = p.groupby([pid, "half"])[val]
    a = (g.mean() if agg == "mean" else g.median()).unstack()
    n = g.size().unstack()
    keep = (n.min(axis=1) >= min_half)
    a = a[keep].dropna()
    if len(a) < MIN_N:
        return dict(n_players=len(a), r_half=np.nan, spearman_brown=np.nan)
    r = stats.spearmanr(a[0], a[1])[0]
    return dict(n_players=len(a), r_half=float(r), spearman_brown=float(2 * r / (1 + r)) if r > -1 else np.nan)


def los_x(df: pd.DataFrame) -> np.ndarray:
    right = df.play_direction.eq("right").to_numpy()
    own = df.yardline_side.eq(df.possession_team).to_numpy()
    yl = df.yardline_number.to_numpy(float)
    return np.where(own, np.where(right, 10 + yl, 110 - yl), np.where(right, 110 - yl, 10 + yl))


def dir_sign(df: pd.DataFrame) -> np.ndarray:
    return np.where(df.play_direction.eq("right").to_numpy(), 1.0, -1.0)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "—"
    return f"{p:.2g}" if p < 0.001 else f"{p:.3f}"


OFFICIAL = [
    ("ten_yd_split", "Official 10-yard", -1), ("forty", "Official 40", -1),
    ("vertical", "Vertical", +1), ("broad_jump", "Broad jump", +1),
    ("three_cone", "3-cone", -1), ("short_shuttle", "Short shuttle", -1),
    ("bench_reps", "Bench reps", +1), ("arm_length", "Arm length", +1),
    ("hand_size", "Hand size", +1), ("wing_span", "Wingspan", +1),
    ("combine_weight", "Weight", 0), ("combine_height", "Height", 0),
]
TRACKING = [
    ("c_t20_derived", "20-yard split (tracking)", -1),
    ("c_t10_derived", "10-yard split (tracking)", -1),
    ("c_top_mph", "Combine top speed", +1),
    ("c_40_accel", "40-yard peak accel", +1),
]


def load_combine(root, ids) -> pd.DataFrame:
    """Official Combine results + tracking-derived 40 metrics + Burst Score. No draft slot."""
    cr = pd.read_csv(root / "data" / "combine_results.csv")
    cr = cr[cr.nfl_id.isin(ids)].drop_duplicates("nfl_id")
    keep = ["nfl_id"] + [c for c, *_ in OFFICIAL]
    c = cr[keep].copy()
    ctg = pd.read_csv(root / "out" / "combine_to_game_players.csv",
                      usecols=["nfl_id"] + [k for k, *_ in TRACKING])
    c = c.merge(ctg.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    b = pd.read_csv(root / "out" / "combine_to_game_burst_players.csv", usecols=["nfl_id", "burst_0_100"])
    c = c.merge(b.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    return c
