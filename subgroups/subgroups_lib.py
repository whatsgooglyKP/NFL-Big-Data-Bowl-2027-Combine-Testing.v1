"""BDB 2027 subgroup prelim: S vs CB and EDGE vs IDL.

Self-contained (raw competition files only). Same methods as the main entry (robust.py):
size-controlled rank partial correlation (draft year dummies + ranked weight + height),
beta-binomial shrinkage of rates (prior fit inside each subgroup), player bootstrap CI,
Freedman-Lane permutation p, BH-FDR inside each subgroup, leave-one-draft-class-out check,
and the minimum detectable effect (MDE, 80% power). New here: a Freedman-Lane interaction
test of whether the size-controlled link differs between the two subgroups of a pair.
Draft slot / pick / round is never read. Per-player tables stay in memory; only aggregates are written.
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats, optimize, special
from scipy.stats import norm

SEED = 2027
N_BOOT, N_PERM, N_PERM_LOSO, N_PERM_INT = 2000, 10000, 1000, 10000
MIN_N, MIN_VERDICT_N = 12, 25
MPH, ACCEL_CLIP = 2.0455, 12.0
SIZE = ["combine_weight", "combine_height"]
RANK_VAR = 1.06
ND = "NOT DETECTED (low power)"
KEY = ["game_id", "play_id", "nfl_id"]
DB_POS, DL_POS = {"CB", "SS", "FS", "DB"}, {"DE", "OLB", "DT", "NT"}
DEEP_OR_MAN = ("MAN", "DEEP_", "QUARTERS_", "PREVENT")

TESTS = [  # (col, coach label, good direction: -1 = lower/faster is better)
    ("forty", "40-yard dash", -1), ("ten_yd_split", "10-yard split", -1),
    ("c_t20_derived", "20-yard split (tracking)", -1), ("c_t10_derived", "10-yard split (tracking)", -1),
    ("c_top_mph", "Top speed (tracking)", +1), ("c_40_accel", "Peak acceleration (tracking)", +1),
    ("burst_0_100", "Burst Score 0-100 (tracking)", +1),
    ("vertical", "Vertical jump", +1), ("broad_jump", "Broad jump", +1),
    ("three_cone", "3-cone", -1), ("short_shuttle", "Short shuttle", -1),
]
TRACKING_TESTS = {"c_t20_derived", "c_t10_derived", "c_top_mph", "c_40_accel", "burst_0_100"}
DB_OUT = [  # (col, label, good direction, exposure col for the weighted check)
    ("tackle_rate", "Tackles per snap (shrunk)", +1, "n_snaps"),
    ("tfl_rate", "Tackles for loss per snap (shrunk)", +1, "n_snaps"),
    ("cov_speed_mph", "Game speed in man/deep coverage (p90, mph)", +1, "n_cov"),
    ("close_speed_mph", "Closing speed into the tackle (last 1 s, mph)", +1, "n_close"),
]
DL_OUT = [
    ("pressure_rate", "Pressure rate (shrunk)", +1, "n_rush"),
    ("sack_rate", "Sack rate (shrunk)", +1, "n_rush"),
    ("getoff_mph", "Get-off: speed 1 s after snap (mph)", +1, "n_getoff"),
    ("tfl_rate", "Tackles for loss per snap (shrunk)", +1, "n_snaps"),
    ("run_stop_rate", "Run stops (tackle at <=2 yd) per run snap (shrunk)", +1, "n_run"),
]
PAIRS = {"DB": ("S", "CB", DB_OUT), "DL": ("EDGE", "IDL", DL_OUT)}


def log(m):
    print(m, flush=True)


def _bool(s):
    return s.astype(str).str.strip().str.lower().isin({"true", "1", "1.0", "y", "yes"})


# ====================================================================== data
def find_comp() -> Path:
    for p in [Path("data"), Path("../data"), Path("../../data")]:
        if (p / "combine_tracking.csv").exists():
            return p
    hits = list(Path("/kaggle/input").rglob("combine_tracking.csv")) if Path("/kaggle/input").exists() else []
    if not hits:
        raise FileNotFoundError("Attach the NFL Big Data Bowl 2027 competition data.")
    return hits[0].parent


def roster(C: Path, pp: pd.DataFrame) -> pd.DataFrame:
    pl = pd.read_csv(C / "players.csv", usecols=["nfl_id", "draft_year", "nfl_position"])  # no draft-slot columns read
    pl = pl[pl.nfl_position.isin(DB_POS | DL_POS)].copy()
    pl["group"] = np.where(pl.nfl_position.isin(DB_POS), "DB", "DL")
    sub = {"CB": "CB", "SS": "S", "FS": "S", "DE": "EDGE", "OLB": "EDGE", "DT": "IDL", "NT": "IDL"}
    pl["sub"] = pl.nfl_position.map(sub)
    # players listed only as "DB": use where they lined up most in regular-season snaps (in this cohort they have none, so they drop out)
    lu = pp[pp.nfl_id.isin(pl.nfl_id[pl.nfl_position == "DB"])]
    if len(lu):
        m = lu.groupby("nfl_id").lined_up_position.agg(lambda v: v.value_counts().index[0])
        pl.loc[pl.nfl_position == "DB", "sub"] = pl.nfl_id.map(m).map(
            {"CB": "CB", "SLOT_CB": "CB", "HIGH_SAFETY": "S", "BOX_SAFETY": "S"})
    pl = pl.dropna(subset=["sub"])
    cr = pd.read_csv(C / "combine_results.csv", usecols=["nfl_id"] + SIZE + [
        "ten_yd_split", "forty", "vertical", "broad_jump", "three_cone", "short_shuttle"]).drop_duplicates("nfl_id")
    return pl.merge(cr, on="nfl_id", how="left")


def _attempt(g: pd.DataFrame) -> dict:
    s, x = g.s.to_numpy(float), g.x.to_numpy(float)
    t = g.t.to_numpy(float)
    out = dict(max_s=np.nan, accel=np.nan, t10=np.nan, t20=np.nan)
    if len(g) < 8 or not np.isfinite(s).any():
        return out
    out["max_s"] = float(np.nanmax(s))
    ds = np.diff(s) * 10.0
    ds = ds[np.abs(ds) <= ACCEL_CLIP]
    if ds.size:
        out["accel"] = float(ds.max())
    start = float(np.nanmax(x) - 40.0); nf = min(8, len(g))

    def cross(target):
        if x[0] >= target:
            c = np.polyfit(t[:nf], x[:nf], 1)
            return np.nan if abs(c[0]) < 1e-6 else float((target - c[1]) / c[0])
        hit = np.where(x >= target)[0]
        if not len(hit):
            return np.nan
        i = int(hit[0])
        if i == 0 or x[i] == x[i - 1]:
            return float(t[i])
        return float(t[i - 1] + (target - x[i - 1]) / (x[i] - x[i - 1]) * (t[i] - t[i - 1]))
    t0 = cross(start)
    if np.isfinite(t0):
        for yd, k in ((10, "t10"), (20, "t20")):
            tc = cross(start + yd)
            out[k] = tc - t0 if np.isfinite(tc) else np.nan
    return out


def combine_tracking(C: Path, ids) -> pd.DataFrame:
    """40-yard dash from the 10 Hz Combine sensor: best attempt (highest top speed)."""
    ct = pd.read_csv(C / "combine_tracking.csv", usecols=["event_id", "nfl_id", "entity_type", "time", "drill_type", "x", "s"])
    ct = ct[(ct.entity_type == "PLAYER") & (ct.drill_type == "FORTY_YARD_DASH") & ct.nfl_id.isin(ids)].copy()
    ct["time"] = pd.to_datetime(ct.time)
    ct = ct.sort_values(["event_id", "time"])
    ct["t"] = (ct.time - ct.groupby("event_id").time.transform("min")).dt.total_seconds()
    rows = [dict(nfl_id=n, **_attempt(g)) for (e, n), g in ct.groupby(["event_id", "nfl_id"], sort=False)]
    a = pd.DataFrame(rows).dropna(subset=["max_s"])
    best = a.loc[a.groupby("nfl_id").max_s.idxmax()].copy()
    best["c_top_mph"] = best.max_s * MPH
    return best.rename(columns={"t10": "c_t10_derived", "t20": "c_t20_derived", "accel": "c_40_accel"})[
        ["nfl_id", "c_top_mph", "c_t10_derived", "c_t20_derived", "c_40_accel"]]


def plays(C: Path, ids) -> pd.DataFrame:
    cols = KEY + ["team_abbr", "possession_team", "lined_up_position", "pass_result", "play_nullified_by_penalty",
                  "yards_gained", "coverage_assignment", "sack", "tackle", "assist", "tackle_for_loss", "time_to_pressure"]
    parts = [ch[ch.nfl_id.isin(ids)] for ch in pd.read_csv(C / "player_play.csv", usecols=cols, chunksize=100_000)]
    pp = pd.concat(parts, ignore_index=True)
    g = pd.read_csv(C / "games.csv", usecols=["game_id", "season_type"])
    pp = pp[pp.game_id.isin(g.game_id[g.season_type == "REG"])]
    pp = pp[(pp.play_nullified_by_penalty == "N") & (pp.team_abbr != pp.possession_team)].copy()
    t = pd.to_numeric(pp.tackle, errors="coerce"); a = pd.to_numeric(pp.assist, errors="coerce")
    pp["inv"] = (t >= 1) | (a == 1)
    pp["tfl"] = _bool(pp.tackle_for_loss)
    pp["is_pass"] = pp.pass_result.notna()
    pp["sack_n"] = pd.to_numeric(pp.sack, errors="coerce").fillna(0).clip(0, 1)
    pp["press"] = pp.time_to_pressure.notna()
    pp["stop"] = pp.inv & (pd.to_numeric(pp.yards_gained, errors="coerce") <= 2)
    pp["rush"] = pp.is_pass & pp.lined_up_position.isin(["EDGE", "INTERIOR_LINE"])
    ca = pp.coverage_assignment.fillna("")
    pp["cov"] = pp.is_pass & ca.str.startswith(DEEP_OR_MAN)
    return pp


def game_tracking(C: Path, pp: pd.DataFrame, chunksize=2_000_000) -> dict:
    """One streaming pass over the three game-tracking files.
    DB coverage plays -> per-play top speed. DL rush plays + DB tackle plays -> keep (time, s, event) frames."""
    cov = pp.loc[pp["cov"] & (pp.grp == "DB"), KEY]
    rush = pp.loc[pp.rush & (pp.grp == "DL"), KEY]
    tak = pp.loc[pp.inv & (pp.grp == "DB"), KEY]
    ids = set(pp.nfl_id)
    k_cov = pd.MultiIndex.from_frame(cov); k_rush = pd.MultiIndex.from_frame(rush); k_tak = pd.MultiIndex.from_frame(tak)
    cov_parts, fr_parts = [], []
    files = sorted(C.glob("game_tracking_*.csv"))
    for f in files:
        t0 = time.time()
        for ch in pd.read_csv(f, usecols=KEY + ["time", "s", "event"], dtype={"s": "float32"}, chunksize=chunksize):
            ch = ch[ch.nfl_id.isin(ids)]
            if not len(ch):
                continue
            mi = pd.MultiIndex.from_frame(ch[KEY])
            c = ch[mi.isin(k_cov)]
            if len(c):
                cov_parts.append(c.groupby(KEY, sort=False).s.max().reset_index())
            keep = mi.isin(k_rush) | mi.isin(k_tak)
            if keep.any():
                fr_parts.append(ch[keep])
        log(f"  {f.name}: {time.time() - t0:.0f}s")
    cv = pd.concat(cov_parts).groupby(KEY, as_index=False).s.max()
    fr = pd.concat(fr_parts, ignore_index=True)
    fr["time"] = pd.to_datetime(fr.time)
    fr = fr.sort_values(KEY + ["time"])
    # DL get-off: speed nearest to 1.0 s after the snap (within 0.15 s)
    rf = fr.merge(rush, on=KEY)
    snap = rf[rf.event.isin(["ball_snap", "autoevent_ballsnap"])].groupby(KEY).time.min().rename("t_snap")
    rf = rf.join(snap, on=KEY, how="inner")
    rf["d"] = ((rf.time - rf.t_snap).dt.total_seconds() - 1.0).abs()
    rf = rf[rf.d <= 0.15]
    getoff = rf.loc[rf.groupby(KEY).d.idxmin(), KEY + ["s"]].rename(columns={"s": "s1"})
    # DB closing: mean speed over the 1.0 s before the 'tackle' event, on plays he made or assisted the tackle
    tf = fr.merge(tak, on=KEY)
    tk = tf[tf.event == "tackle"].groupby(KEY).time.min().rename("t_tk")
    tf = tf.join(tk, on=KEY, how="inner")
    dt = (tf.t_tk - tf.time).dt.total_seconds()
    close = tf[(dt >= 0) & (dt <= 1.0)].groupby(KEY, as_index=False).s.mean().rename(columns={"s": "s_close"})
    return dict(cov=cv, getoff=getoff, close=close)


def fit_beta_binomial(k, n):
    k, n = np.asarray(k, float), np.asarray(n, float)

    def nll(th):
        a, b = np.exp(th)
        return -np.sum(special.betaln(k + a, n - k + b) - special.betaln(a, b))
    mu = (k.sum() / n.sum()).clip(1e-4, 1 - 1e-4); best = None
    for s in (3, 30, 300, 3000):
        r = optimize.minimize(nll, np.log([mu * s, (1 - mu) * s]), method="Nelder-Mead",
                              options=dict(xatol=1e-4, fatol=1e-6, maxiter=2000))
        best = r if best is None or r.fun < best.fun else best
    return tuple(np.exp(best.x))


def shrink(d: pd.DataFrame, k: str, n: str, min_n: int) -> pd.Series:
    """Empirical-Bayes posterior-mean rate, prior fit inside each subgroup."""
    out = pd.Series(np.nan, index=d.index)
    for _, g in d.groupby("sub"):
        g = g[(g[n] >= min_n)]
        if len(g) < 8:
            continue
        a, b = fit_beta_binomial(g[k], g[n])
        out[g.index] = (a + g[k]) / (a + b + g[n])
    return out


def burst_score(d: pd.DataFrame) -> pd.Series:
    """0-100 within-subgroup blend of tracked 20-yard time (faster = better) and the two jumps."""
    z = pd.DataFrame(index=d.index)
    for c, sg in (("c_t20_derived", -1), ("vertical", 1), ("broad_jump", 1)):
        z[c] = sg * (d[c] - d.groupby("sub")[c].transform("mean")) / d.groupby("sub")[c].transform("std")
    m = z.mean(axis=1).where(z.notna().sum(axis=1) >= 2)
    return (m.groupby(d["sub"]).rank(pct=True) * 100).round(1)


def build(C: Path | None = None) -> pd.DataFrame:
    C = C or find_comp(); t0 = time.time()
    pl0 = pd.read_csv(C / "players.csv", usecols=["nfl_id", "nfl_position"])
    ids0 = set(pl0.nfl_id[pl0.nfl_position.isin(DB_POS | DL_POS)])
    pp = plays(C, ids0)
    P = roster(C, pp)
    pp = pp.merge(P[["nfl_id", "group", "sub"]].rename(columns={"group": "grp"}), on="nfl_id")
    log(f"plays loaded ({len(pp):,} defensive REG snaps) {time.time() - t0:.0f}s")
    P = P.merge(combine_tracking(C, set(P.nfl_id)), on="nfl_id", how="left")
    log(f"combine tracking done {time.time() - t0:.0f}s")
    G = game_tracking(C, pp)
    log(f"game tracking done {time.time() - t0:.0f}s")
    a = pp.groupby("nfl_id").agg(n_snaps=("inv", "size"), n_inv=("inv", "sum"), n_tfl=("tfl", "sum"))
    r = pp[pp.rush].groupby("nfl_id").agg(n_rush=("rush", "size"), n_press=("press", "sum"), n_sack=("sack_n", "sum"))
    ru = pp[~pp.is_pass].groupby("nfl_id").agg(n_run=("stop", "size"), n_stop=("stop", "sum"))
    cv = G["cov"].groupby("nfl_id").s.agg(n_cov="size", cov_p90=lambda v: v.quantile(0.90))
    go = G["getoff"].groupby("nfl_id").s1.agg(n_getoff="size", s1="median")
    cl = G["close"].groupby("nfl_id").s_close.agg(n_close="size", sc="median")
    P = P.set_index("nfl_id").join([a, r, ru, cv, go, cl]).reset_index()
    for c in ["n_snaps", "n_inv", "n_tfl", "n_rush", "n_press", "n_sack", "n_run", "n_stop", "n_cov", "n_getoff", "n_close"]:
        P[c] = P[c].fillna(0)
    P["tackle_rate"] = shrink(P, "n_inv", "n_snaps", 100)
    P["tfl_rate"] = shrink(P, "n_tfl", "n_snaps", 100)
    P["pressure_rate"] = shrink(P, "n_press", "n_rush", 20)
    P["sack_rate"] = shrink(P, "n_sack", "n_rush", 20)
    P["run_stop_rate"] = shrink(P, "n_stop", "n_run", 50)
    P["cov_speed_mph"] = np.where(P.n_cov >= 20, P.cov_p90 * MPH, np.nan)
    P["getoff_mph"] = np.where(P.n_getoff >= 20, P.s1 * MPH, np.nan)
    P["close_speed_mph"] = np.where(P.n_close >= 10, P.sc * MPH, np.nan)
    P["burst_0_100"] = burst_score(P)
    bad = [c for c in P.columns if any(k in c.lower() for k in ("round", "pick", "overall", "slot"))]
    assert not bad, f"draft-slot columns present: {bad}"
    log(f"player table built: {len(P)} DB/DL players, {time.time() - t0:.0f}s")
    return P


# ====================================================================== stats (same engines as robust.py)
def _rank(v):
    return stats.rankdata(v, axis=-1)


def _design(df, ctrl):
    cols = [np.ones(len(df))]
    if df["draft_year"].nunique() > 1:
        cols += list(pd.get_dummies(df["draft_year"].astype(str), drop_first=True).to_numpy(float).T)
    cols += [_rank(df[c].to_numpy(float)) for c in ctrl]
    return np.column_stack(cols)


def _resid(v, Z):
    return v - Z @ np.linalg.lstsq(Z, v, rcond=None)[0]


def _corr(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else np.nan


def _year_only(s, x, y):
    Z = _design(s, [])
    return _corr(_resid(_rank(x), Z), _resid(_rank(y), Z))


def boot_partial(s, x, y, ctrl, B=N_BOOT, seed=SEED):
    n = len(x); idx = np.random.default_rng(seed).integers(0, n, size=(B, n))
    yr = pd.get_dummies(s["draft_year"].astype(str), drop_first=True).to_numpy(float)
    cols = [np.ones((B, n))] + [yr[:, j][idx] for j in range(yr.shape[1])] + [_rank(s[c].to_numpy(float)[idx]) for c in ctrl]
    Z = np.stack(cols, axis=2); H = Z @ np.linalg.pinv(Z)
    rx, ry = _rank(x[idx]), _rank(y[idx])
    ex = rx - np.einsum("bij,bj->bi", H, rx); ey = ry - np.einsum("bij,bj->bi", H, ry)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (ex * ey).sum(1) / np.sqrt((ex ** 2).sum(1) * (ey ** 2).sum(1))
    r = r[np.isfinite(r)]
    return tuple(np.percentile(r, [2.5, 97.5])) if len(r) > 100 else (np.nan, np.nan)


def perm_fl(ex, ey, Z, P=N_PERM, seed=SEED):
    """Freedman-Lane: permute reduced-model residuals of y, re-residualise, correlate with x residual."""
    n = len(ex); r_obs = _corr(ex, ey)
    idx = np.argsort(np.random.default_rng(seed).random((P, n)), axis=1)
    e = ey[idx]; H = Z @ np.linalg.pinv(Z); me = e - e @ H
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (me @ ex) / (np.sqrt((ex ** 2).sum()) * np.sqrt((me ** 2).sum(1)))
    return float((1 + np.sum(np.abs(r) >= abs(r_obs) - 1e-12)) / (P + 1))


def _nscore(v, cls):
    out = np.zeros(len(v))
    for c in np.unique(cls):
        m = cls == c; r = stats.rankdata(v[m]); out[m] = norm.ppf((r - 0.5) / m.sum())
    return out


def _ridge(Xtr, ytr, Xte, alpha=5.0):
    mu, sd = Xtr.mean(0), Xtr.std(0); sd[sd == 0] = 1
    A = (Xtr - mu) / sd; ym = ytr.mean()
    b = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ (ytr - ym))
    return ym + ((Xte - mu) / sd) @ b


def _r2(y, p):
    return 1 - np.sum((y - p) ** 2) / np.sum(y ** 2)


def loso(s, x, y, ctrl, P=N_PERM_LOSO, seed=SEED):
    """Held-out draft classes: train size-only vs size+test on two classes, predict the third."""
    cls = s["draft_year"].to_numpy(); res = dict(ho_dr2=np.nan, ho_pos=0, ho_folds=0, ho_p=np.nan)
    folds = [c for c in np.unique(cls) if (cls == c).sum() >= 5 and (cls != c).sum() >= 12]
    if len(folds) < 2:
        return res
    base = np.column_stack([_nscore(s[c].to_numpy(float), cls) for c in ctrl])
    zx, zy = _nscore(x, cls), _nscore(y, cls)

    def run(zxx):
        Xf = np.column_stack([base, zxx]); out = []
        for f in folds:
            te = cls == f; tr = ~te
            out.append((zy[te], _ridge(base[tr], zy[tr], base[te]), _ridge(Xf[tr], zy[tr], Xf[te])))
        yt = np.concatenate([o[0] for o in out]); ps = np.concatenate([o[1] for o in out]); pf = np.concatenate([o[2] for o in out])
        return _r2(yt, pf) - _r2(yt, ps), sum(_r2(o[0], o[2]) - _r2(o[0], o[1]) > 0 for o in out)
    d, pos = run(zx)
    rng = np.random.default_rng(seed); null = np.empty(P)
    groups = [np.where(cls == c)[0] for c in np.unique(cls)]
    for b in range(P):
        zp = zx.copy()
        for ii in groups:
            zp[ii] = zx[rng.permutation(ii)]
        null[b] = run(zp)[0]
    res.update(ho_dr2=d, ho_pos=int(pos), ho_folds=len(folds), ho_p=float((1 + (null >= d).sum()) / (P + 1)))
    return res


def _se(n, k):
    df = np.asarray(n, float) - np.asarray(k, float) - 3
    return np.where(df > 1, np.sqrt(RANK_VAR / np.where(df > 1, df, np.nan)), np.nan)


def mde(n, k, alpha=0.05, power=0.80):
    return np.tanh((norm.ppf(1 - alpha / 2) + norm.ppf(power)) * _se(n, k))


def mde_diff(n1, n2, k, alpha=0.05, power=0.80):
    """Smallest difference in size-controlled rho between two independent subgroups (around rho = 0)."""
    se = np.sqrt(_se(n1, k) ** 2 + _se(n2, k) ** 2)
    return np.tanh((norm.ppf(1 - alpha / 2) + norm.ppf(power)) * se)


def bh(p: pd.Series) -> pd.Series:
    q = pd.Series(np.nan, index=p.index); m = p.notna()
    if m.sum():
        pv = p[m].to_numpy(); o = np.argsort(pv); n = len(pv)
        adj = np.minimum.accumulate((pv[o] * n / np.arange(1, n + 1))[::-1])[::-1]
        r = np.empty(n); r[o] = np.minimum(adj, 1); q[m] = r
    return q


def cell(sub: pd.DataFrame, test, outcome, sign, ctrl_role=None) -> dict:
    need = [test, outcome, "draft_year"] + SIZE + ([ctrl_role] if ctrl_role else [])
    s = sub[need].dropna().reset_index(drop=True)
    out = dict(n=len(s))
    if len(s) < MIN_N or s[test].nunique() < 3 or s[outcome].nunique() < 3:
        return out
    x, y = s[test].to_numpy(float) * sign, s[outcome].to_numpy(float)  # sign: + = better athlete does better
    Z = _design(s, SIZE)
    if ctrl_role:
        Z = np.column_stack([Z, (s[ctrl_role] == s[ctrl_role].iloc[0]).to_numpy(float)])
    ex, ey = _resid(_rank(x), Z), _resid(_rank(y), Z)
    out.update(rho_year=_year_only(s, x, y), rho=_corr(ex, ey), k=Z.shape[1] - 1)
    if ctrl_role:  # pooled reference: point estimate + permutation p only
        out["p"] = perm_fl(ex, ey, Z, P=2000)
        return out
    out["lo"], out["hi"] = boot_partial(s, x, y, SIZE)
    out["p"] = perm_fl(ex, ey, Z)
    out.update(loso(s, x, y, SIZE))
    return out


def run_cells(P: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grp, (a, b, outs) in PAIRS.items():
        for sub in (a, b):
            d = P[P["sub"] == sub]; t0 = time.time()
            for oc, ol, og, _ in outs:
                for tc, tl, tg in TESTS:
                    rows.append(dict(group=grp, sub=sub, test=tc, test_label=tl, outcome=oc, outcome_label=ol,
                                     tracking=tc in TRACKING_TESTS, **cell(d, tc, oc, tg * og)))
            log(f"  {sub}: {time.time() - t0:.0f}s")
        d = P[P.group == grp]
        for oc, ol, og, _ in outs:
            for tc, tl, tg in TESTS:
                rows.append(dict(group=grp, sub=f"{grp} pooled", test=tc, test_label=tl, outcome=oc, outcome_label=ol,
                                 tracking=tc in TRACKING_TESTS, **cell(d, tc, oc, tg * og, ctrl_role="sub")))
    t = pd.DataFrame(rows)
    t["q"] = np.nan
    for sub, g in t.groupby("sub"):
        t.loc[g.index, "q"] = bh(g.p)
    t["mde80"] = mde(t.n, t.k.fillna(4))
    t["held_out_ok"] = (t.ho_dr2 > 0) & (t.ho_p < 0.10) & (t.ho_pos >= 2)
    t["verdict"] = t.apply(verdict, axis=1)
    return t


def verdict(r) -> str:
    if "pooled" in r["sub"]:
        return "reference"
    if not np.isfinite(r.get("rho", np.nan)):
        return "TOO FEW TO TELL"
    if r.n < MIN_VERDICT_N:
        return "TOO FEW TO TELL"
    ci = (r.lo > 0) or (r.hi < 0)
    if r.q < 0.05 and ci and r.held_out_ok:
        return "TRANSLATES"
    if ci or r.p < 0.05:
        return "LEAD (preliminary)"
    if abs(r.rho_year) >= 0.30 and abs(r.rho) <= abs(r.rho_year) / 2:
        return "SIZE, NOT SPEED"
    return ND


# ====================================================================== interaction (does the slope differ?)
def _zmats(s):
    yr = s["draft_year"].to_numpy()
    D = np.column_stack([(yr == v).astype(float) for v in np.unique(yr)[1:]]) if len(np.unique(yr)) > 1 else np.zeros((len(s), 0))
    return D, s[SIZE].to_numpy(float)


def _within(D, S, x, y):
    Z = np.column_stack([np.ones(len(x)), D] + [_rank(S[:, j]) for j in range(S.shape[1])])
    ex, ey = _resid(_rank(x), Z), _resid(_rank(y), Z)
    return ex / ex.std(), ey / ey.std()


def interaction(P, grp, a, b, test, outcome, sign, B=N_BOOT, NP=N_PERM_INT, seed=SEED):
    """Size-controlled residuals are built inside each subgroup (so level and size differences between
    the subgroups cannot leak in). Then on the stacked residuals: e_y ~ e_x + e_x*[subgroup b] + [subgroup b];
    Freedman-Lane permutation of the reduced-model (no interaction) residuals gives the p-value.
    Effect size = rho_a - rho_b, with a stratified player bootstrap CI."""
    need = [test, outcome, "draft_year"] + SIZE
    sa = P[P["sub"] == a][need].dropna().reset_index(drop=True)
    sb = P[P["sub"] == b][need].dropna().reset_index(drop=True)
    out = dict(group=grp, test=test, outcome=outcome, n_a=len(sa), n_b=len(sb))
    if min(len(sa), len(sb)) < MIN_N:
        return out
    xa, ya = sa[test].to_numpy(float) * sign, sa[outcome].to_numpy(float)
    xb, yb = sb[test].to_numpy(float) * sign, sb[outcome].to_numpy(float)
    Da, Sa = _zmats(sa); Db, Sb = _zmats(sb)
    exa, eya = _within(Da, Sa, xa, ya); exb, eyb = _within(Db, Sb, xb, yb)
    ra, rb = _corr(exa, eya), _corr(exb, eyb)
    ex = np.r_[exa, exb]; ey = np.r_[eya, eyb]; g = np.r_[np.zeros(len(exa)), np.ones(len(exb))]
    Zr = np.column_stack([np.ones(len(ex)), g, ex])
    inter = ex * g
    e_int = _resid(inter, Zr); e_y = _resid(ey, Zr)
    beta_obs = (e_int @ e_y) / (e_int @ e_int)
    rng = np.random.default_rng(seed); fit = ey - e_y
    idx = np.argsort(rng.random((NP, len(ey))), axis=1)
    ystar = fit[None, :] + e_y[idx]
    H = Zr @ np.linalg.pinv(Zr); res = ystar - ystar @ H.T
    bnull = (res @ e_int) / (e_int @ e_int)
    p = float((1 + np.sum(np.abs(bnull) >= abs(beta_obs) - 1e-12)) / (NP + 1))
    # stratified bootstrap CI of rho_a - rho_b (re-residualise inside each resample)
    r1 = np.random.default_rng(seed + 1); diffs = []
    for _ in range(B):
        ia = r1.integers(0, len(sa), len(sa)); ib = r1.integers(0, len(sb), len(sb))
        try:
            da = _corr(*_within(Da[ia], Sa[ia], xa[ia], ya[ia])); db = _corr(*_within(Db[ib], Sb[ib], xb[ib], yb[ib]))
        except Exception:
            continue
        if np.isfinite(da) and np.isfinite(db):
            diffs.append(da - db)
    lo, hi = np.percentile(diffs, [2.5, 97.5]) if len(diffs) > 100 else (np.nan, np.nan)
    k = 2 + len(SIZE)
    out.update(rho_a=ra, rho_b=rb, diff=ra - rb, diff_lo=lo, diff_hi=hi, p_int=p,
               mde_diff=float(mde_diff(len(sa), len(sb), k)))
    return out


def run_interactions(P: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grp, (a, b, outs) in PAIRS.items():
        t0 = time.time()
        for oc, ol, og, _ in outs:
            for tc, tl, tg in TESTS:
                rows.append(dict(sub_a=a, sub_b=b, test_label=tl, outcome_label=ol, tracking=tc in TRACKING_TESTS,
                                 **interaction(P, grp, a, b, tc, oc, tg * og)))
        log(f"  {a} vs {b}: {time.time() - t0:.0f}s")
    t = pd.DataFrame(rows)
    t["q_int"] = np.nan
    for grp, g in t.groupby("group"):
        t.loc[g.index, "q_int"] = bh(g.p_int)
    small = t[["n_a", "n_b"]].min(axis=1) < MIN_VERDICT_N

    def v(r):
        if not np.isfinite(r.get("diff", np.nan)) or min(r.n_a, r.n_b) < MIN_N:
            return "TOO FEW TO TELL"
        if r.q_int < 0.05:
            return "REAL DIFFERENCE"
        if r.p_int < 0.05:
            return "LEAD (preliminary)"
        return ND
    t["verdict"] = t.apply(v, axis=1)
    t.loc[small & t["diff"].notna(), "verdict"] = "TOO FEW TO TELL"
    return t


def sample_sizes(P: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grp, (a, b, outs) in PAIRS.items():
        for sub in (a, b):
            d = P[P["sub"] == sub]
            r = dict(group=grp, subgroup=sub, players=len(d), with_size=int(d[SIZE].notna().all(axis=1).sum()),
                     with_40_tracking=int(d.c_top_mph.notna().sum()), with_official_40=int(d.forty.notna().sum()))
            for oc, *_ in outs:
                r[f"n_{oc}"] = int(d[[oc] + SIZE].notna().all(axis=1).sum())
            nn = int(d[["c_top_mph", outs[0][0]] + SIZE].notna().all(axis=1).sum())
            r["n_core"] = nn; r["mde80_core"] = float(mde(nn, 4))
            rows.append(r)
    return pd.DataFrame(rows)
