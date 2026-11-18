"""Reusable robust-testing module (Combine test vs outcome), small-sample defaults.

Defaults (documented in METRICS.md, "Robust testing defaults"):
  1. Size control      rank partial correlation controlling for draft year, role (DL: edge vs
                       interior), weight and height (minus the test itself). Reported next to the
                       unadjusted Spearman.
  2. Noisy rates       empirical-Bayes beta-binomial shrinkage toward the (role) mean, using the
                       player's snap counts. Shrunk rate is the primary outcome; the unshrunk and
                       snap-weighted versions are reported as sensitivity.
  3. Out of sample     leave-one-draft-class-out: fit size-only and size+test ridge models on two
                       classes, predict the third; report incremental out-of-sample R^2 and
                       Spearman of predictions vs truth, plus a within-class permutation p-value.
  4. Inference         player-level bootstrap 95% CI, Freedman-Lane permutation p-value, BH-FDR
                       across every test x outcome cell in the group.
Draft slot / pick / round is never an input (asserted).
"""
from __future__ import annotations
import numpy as np, pandas as pd
from scipy import stats, optimize, special

SEED = 2027
N_BOOT, N_PERM, N_PERM_LOSO = 2000, 10000, 1000
MIN_N = 12
RIDGE_ALPHA = 5.0
SIZE = ["combine_weight", "combine_height"]


# ------------------------------------------------------------------ helpers
def assert_no_draft_slot(df: pd.DataFrame) -> None:
    bad = [c for c in df.columns if any(k in c.lower() for k in ("draft_round", "pick", "overall", "draft_slot"))]
    assert not bad, f"draft slot columns present: {bad}"


def _rank(v: np.ndarray) -> np.ndarray:
    return stats.rankdata(v, axis=-1)


def _design(n: int, ranks_ctrl: list[np.ndarray], dummies: np.ndarray | None) -> np.ndarray:
    cols = [np.ones(n)]
    if dummies is not None and dummies.shape[1]:
        cols += [dummies[:, j].astype(float) for j in range(dummies.shape[1])]
    cols += list(ranks_ctrl)
    return np.column_stack(cols)


def _resid(v: np.ndarray, Z: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    if w is None:
        beta, *_ = np.linalg.lstsq(Z, v, rcond=None)
        return v - Z @ beta
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(Z * sw[:, None], v * sw, rcond=None)
    return v - Z @ beta


def _pearson(a, b, w=None):
    if w is None:
        a = a - a.mean(); b = b - b.mean()
        den = np.sqrt((a * a).sum() * (b * b).sum())
        return float((a * b).sum() / den) if den > 0 else np.nan
    w = w / w.sum(); a = a - (w * a).sum(); b = b - (w * b).sum()
    den = np.sqrt((w * a * a).sum() * (w * b * b).sum())
    return float((w * a * b).sum() / den) if den > 0 else np.nan


def dummies_from(df: pd.DataFrame, cols: list[str]) -> np.ndarray | None:
    cols = [c for c in cols if c in df.columns and df[c].nunique() > 1]
    if not cols:
        return None
    return pd.get_dummies(df[cols].astype(str), drop_first=True).to_numpy(float)


def partial_rank_corr(x, y, ctrl_cont: np.ndarray | None, dummies: np.ndarray | None, w=None) -> float:
    """Rank partial correlation: rank x, y and each continuous control, residualise on controls, Pearson."""
    n = len(x)
    rc = [] if ctrl_cont is None else [_rank(ctrl_cont[:, j]) for j in range(ctrl_cont.shape[1])]
    Z = _design(n, rc, dummies)
    rx, ry = _resid(_rank(x), Z, w), _resid(_rank(y), Z, w)
    return _pearson(rx, ry, w)


# ------------------------------------------------------------------ shrinkage
def fit_beta_binomial(k: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Marginal-likelihood fit of Beta(a, b) prior for k ~ BetaBinomial(n, a, b)."""
    k, n = np.asarray(k, float), np.asarray(n, float)

    def nll(th):
        a, b = np.exp(th)
        return -np.sum(special.betaln(k + a, n - k + b) - special.betaln(a, b))
    mu = (k.sum() / n.sum()).clip(1e-4, 1 - 1e-4)
    best = None
    for s in (3, 30, 300, 3000):
        r = optimize.minimize(nll, np.log([mu * s, (1 - mu) * s]), method="Nelder-Mead",
                              options=dict(xatol=1e-4, fatol=1e-6, maxiter=2000))
        if best is None or r.fun < best.fun:
            best = r
    a, b = np.exp(best.x)
    return float(a), float(b)


def eb_shrink(df: pd.DataFrame, k: pd.Series, n: pd.Series, by: str | None = None) -> tuple[pd.Series, dict]:
    """Posterior-mean rate per player; prior fit separately within `by` (e.g. Edge / Interior)."""
    out = pd.Series(np.nan, index=df.index); info = {}
    groups = [(None, df.index)] if by is None else list(df.groupby(by).groups.items())
    for g, idx in groups:
        ok = [i for i in idx if np.isfinite(k[i]) and np.isfinite(n[i]) and n[i] > 0]
        if len(ok) < 8:
            continue
        a, b = fit_beta_binomial(k[ok].to_numpy(), n[ok].to_numpy())
        out[ok] = (a + k[ok]) / (a + b + n[ok])
        info[g] = dict(alpha=a, beta=b, prior_n=a + b, prior_mean=a / (a + b), n_players=len(ok),
                       median_exposure=float(np.median(n[ok])))
    return out, info


# ------------------------------------------------------------------ inference engines
def _boot_idx(n, B, seed):
    return np.random.default_rng(seed).integers(0, n, size=(B, n))


def boot_spearman(x, y, B=N_BOOT, seed=SEED):
    n = len(x); idx = _boot_idx(n, B, seed)
    rx, ry = _rank(x[idx]), _rank(y[idx])
    rx = rx - rx.mean(1, keepdims=True); ry = ry - ry.mean(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (rx * ry).sum(1) / np.sqrt((rx ** 2).sum(1) * (ry ** 2).sum(1))
    r = r[np.isfinite(r)]
    return tuple(np.percentile(r, [2.5, 97.5])) if len(r) > 100 else (np.nan, np.nan)


def boot_partial(x, y, C: np.ndarray | None, D: np.ndarray | None, B=N_BOOT, seed=SEED):
    """Bootstrap players; re-rank everything inside each resample; residualise on controls (batched)."""
    n = len(x); idx = _boot_idx(n, B, seed)
    cols = [np.ones((B, n))]
    if D is not None:
        cols += [D[:, j][idx].astype(float) for j in range(D.shape[1])]
    if C is not None:
        cols += [_rank(C[:, j][idx]) for j in range(C.shape[1])]
    Z = np.stack(cols, axis=2)                                   # B x n x k
    H = Z @ np.linalg.pinv(Z)                                    # B x n x n projection
    rx, ry = _rank(x[idx]), _rank(y[idx])
    ex = rx - np.einsum("bij,bj->bi", H, rx); ey = ry - np.einsum("bij,bj->bi", H, ry)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (ex * ey).sum(1) / np.sqrt((ex ** 2).sum(1) * (ey ** 2).sum(1))
    r = r[np.isfinite(r)]
    return tuple(np.percentile(r, [2.5, 97.5])) if len(r) > 100 else (np.nan, np.nan)


def perm_partial(x, y, C: np.ndarray | None, D: np.ndarray | None, P=N_PERM, seed=SEED):
    """Freedman-Lane permutation p for the rank partial correlation (two-sided)."""
    n = len(x)
    rc = [] if C is None else [_rank(C[:, j]) for j in range(C.shape[1])]
    Z = _design(n, rc, D)
    rx, ry = _rank(x), _rank(y)
    ex, ey = _resid(rx, Z), _resid(ry, Z)
    r_obs = _pearson(ex, ey)
    rng = np.random.default_rng(seed)
    idx = np.argsort(rng.random((P, n)), axis=1)
    e = ey[idx]                                                   # P x n permuted reduced-model residuals
    H = Z @ np.linalg.pinv(Z)
    me = e - e @ H
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (me @ ex) / (np.sqrt((ex ** 2).sum()) * np.sqrt((me ** 2).sum(1)))
    return float((1 + np.sum(np.abs(r) >= abs(r_obs) - 1e-12)) / (P + 1))


def param_p(r, n, k):
    df = n - 2 - k
    if df < 1 or not np.isfinite(r) or abs(r) >= 1:
        return np.nan
    t = r * np.sqrt(df / (1 - r * r))
    return float(2 * stats.t.sf(abs(t), df))


# ------------------------------------------------------------------ leave-one-class-out
def _normal_scores_by_class(v: np.ndarray, cls: np.ndarray) -> np.ndarray:
    out = np.zeros(len(v))
    for c in np.unique(cls):
        m = cls == c
        r = stats.rankdata(v[m])
        out[m] = stats.norm.ppf((r - 0.5) / m.sum())
    return out


def _ridge_fit_predict(Xtr, ytr, Xte, alpha=RIDGE_ALPHA):
    mu, sd = Xtr.mean(0), Xtr.std(0); sd[sd == 0] = 1
    A = (Xtr - mu) / sd; ym = ytr.mean()
    beta = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ (ytr - ym))
    return ym + ((Xte - mu) / sd) @ beta


def _loso_pred(Xs, Xf, y, cls, folds):
    ps, pf, ys, cs = [], [], [], []
    for f in folds:
        te = cls == f; tr = ~te
        ps.append(_ridge_fit_predict(Xs[tr], y[tr], Xs[te])); pf.append(_ridge_fit_predict(Xf[tr], y[tr], Xf[te]))
        ys.append(y[te]); cs.append(np.full(te.sum(), f))
    return np.concatenate(ps), np.concatenate(pf), np.concatenate(ys), np.concatenate(cs)


def _r2(y, p):
    return 1 - np.sum((y - p) ** 2) / np.sum(y ** 2)


def loso(x, y, size_cols: np.ndarray | None, dummies: np.ndarray | None, cls: np.ndarray,
         P=N_PERM_LOSO, seed=SEED, min_train=12, min_test=5) -> dict:
    """Size-only vs size+test, trained on two draft classes, tested on the third (pooled over folds).

    x, y and size columns are converted to within-class normal scores first, so draft-class
    experience differences cannot masquerade as signal. Baseline = predict the class mean (0).
    """
    n = len(x); res = dict(loso_folds=0, loso_r2_size=np.nan, loso_r2_full=np.nan, loso_dr2=np.nan,
                           loso_sp_size=np.nan, loso_sp_full=np.nan, loso_pos_folds=0, loso_p=np.nan)
    zs = []
    if size_cols is not None:
        zs = [_normal_scores_by_class(size_cols[:, j], cls) for j in range(size_cols.shape[1])]
    base = np.column_stack(zs + ([dummies] if dummies is not None else [])) if (zs or dummies is not None) else np.zeros((n, 1))
    zx, zy = _normal_scores_by_class(x, cls), _normal_scores_by_class(y, cls)
    folds = [c for c in np.unique(cls) if (cls == c).sum() >= min_test and (cls != c).sum() >= min_train]
    if len(folds) < 2:
        return res
    Xs, Xf = base, np.column_stack([base, zx])
    ps, pf, yt, ct = _loso_pred(Xs, Xf, zy, cls, folds)
    res.update(loso_folds=len(folds), loso_r2_size=_r2(yt, ps), loso_r2_full=_r2(yt, pf))
    res["loso_dr2"] = res["loso_r2_full"] - res["loso_r2_size"]
    res["loso_sp_size"] = float(stats.spearmanr(ps, yt)[0]); res["loso_sp_full"] = float(stats.spearmanr(pf, yt)[0])
    pos = 0
    for f in folds:
        m = ct == f
        pos += int(_r2(yt[m], pf[m]) - _r2(yt[m], ps[m]) > 0)
    res["loso_pos_folds"] = pos
    # within-class permutation of the test variable -> null distribution of the incremental R^2
    rng = np.random.default_rng(seed); null = np.empty(P)
    cls_idx = {c: np.where(cls == c)[0] for c in np.unique(cls)}
    for b in range(P):
        zp = zx.copy()
        for c, ii in cls_idx.items():
            zp[ii] = zx[rng.permutation(ii)]
        ps_, pf_, yt_, _ = _loso_pred(Xs, np.column_stack([base, zp]), zy, cls, folds)
        null[b] = _r2(yt_, pf_) - _r2(yt_, ps_)
    res["loso_p"] = float((1 + np.sum(null >= res["loso_dr2"])) / (P + 1))
    return res


# ------------------------------------------------------------------ one cell
def test_pair(df: pd.DataFrame, test: str, outcome: str, *, year_col="draft_year", role_col: str | None = None,
              size_cols=SIZE, weight_col: str | None = None, do_boot=True, do_perm=True, do_loso=True,
              alt_outcome: str | None = None) -> dict:
    """All checks for one test x outcome pair.

    outcome            primary outcome column (already shrunk if it is a rate)
    alt_outcome        unshrunk version of the same rate (sensitivity), optional
    weight_col         exposure column (snaps) for the snap-weighted sensitivity, optional
    """
    need = [test, outcome, year_col] + list(size_cols) + ([role_col] if role_col else []) + \
           ([alt_outcome] if alt_outcome else []) + ([weight_col] if weight_col else [])
    s = df[list(dict.fromkeys(need))].dropna().reset_index(drop=True)
    out = dict(n=len(s))
    keys = ["rho_raw", "raw_lo", "raw_hi", "rho_yr", "rho_size", "lo", "hi", "p_param", "p_perm",
            "rho_size_unshrunk", "rho_size_wtd", "n_controls", "controls"]
    out.update({k: np.nan for k in keys})
    if len(s) < MIN_N or s[test].nunique() < 3 or s[outcome].nunique() < 3:
        return out
    x, y = s[test].to_numpy(float), s[outcome].to_numpy(float)
    ctrl_size = [c for c in size_cols if c != test]
    C = s[ctrl_size].to_numpy(float) if ctrl_size else None
    D = dummies_from(s, [year_col] + ([role_col] if role_col else []))
    out["rho_raw"] = float(stats.spearmanr(x, y)[0])
    out["rho_yr"] = partial_rank_corr(x, y, None, D)
    out["rho_size"] = partial_rank_corr(x, y, C, D)
    k = (0 if D is None else D.shape[1]) + len(ctrl_size)
    out["n_controls"] = k
    out["controls"] = "+".join(([year_col] + ([role_col] if role_col else []) + ctrl_size))
    out["p_param"] = param_p(out["rho_size"], len(s), k)
    if alt_outcome:
        out["rho_size_unshrunk"] = partial_rank_corr(x, s[alt_outcome].to_numpy(float), C, D)
    if weight_col:
        out["rho_size_wtd"] = partial_rank_corr(x, y, C, D, w=s[weight_col].to_numpy(float))
    if do_boot:
        out["raw_lo"], out["raw_hi"] = boot_spearman(x, y)
        out["lo"], out["hi"] = boot_partial(x, y, C, D)
    if do_perm:
        out["p_perm"] = perm_partial(x, y, C, D)
    if do_loso:
        cls = s[year_col].to_numpy()
        out.update(loso(x, y, C, D if role_col else None, cls))
    return out


def bh(p: pd.Series) -> pd.Series:
    q = pd.Series(np.nan, index=p.index); m = p.notna()
    if m.sum():
        pv = p[m].to_numpy(); o = np.argsort(pv); r = np.empty(len(pv), int); r[o] = np.arange(1, len(pv) + 1)
        adj = np.minimum.accumulate((pv[o] * len(pv) / np.arange(1, len(pv) + 1))[::-1])[::-1]
        q[m] = np.minimum(adj[r - 1], 1.0)
    return q


def verdict(r: pd.Series, fdr_col: str = "fdr") -> str:
    """Survives-all-checks rule used in the Results Log (see METRICS.md).

    SURVIVES = every check passes: FDR < 0.05, bootstrap CI excludes 0, raw and size-controlled
               signs agree, unshrunk sign agrees, leave-one-class-out incremental R^2 > 0
               (permutation p < 0.10, positive in >= 2 of 3 classes), enough players per control.
    LEAN     = nominal evidence only: permutation p < 0.05, CI excludes 0, unshrunk sign agrees
               and the out-of-sample check passes, but FDR >= 0.05.
    """
    if r.test in SIZE:
        return "size variable"
    if not np.isfinite(r.rho_size):
        return ""
    if r.n < 25 or r.n / (r.n_controls + 1) < 5:
        return "small n"
    ci = (r.lo > 0) or (r.hi < 0)
    same = np.sign(r.rho_raw) == np.sign(r.rho_size)
    shrink = (not np.isfinite(r.rho_size_unshrunk)) or (np.sign(r.rho_size_unshrunk) == np.sign(r.rho_size))
    oos = (r.loso_dr2 > 0) and (r.loso_p < 0.10) and (r.loso_pos_folds >= 2)
    if r[fdr_col] < 0.05 and ci and same and shrink and oos:
        return "SURVIVES"
    if r.p_perm < 0.05 and ci and shrink and oos:
        return "LEAN"
    return ""


def finalize(t: pd.DataFrame, prod_outcomes: list[str] | None = None) -> pd.DataFrame:
    """FDR (full family and production-outcome family) and verdict, per group."""
    t = t.copy()
    t["fdr"] = np.nan; t["fdr_param"] = np.nan; t["fdr_prod"] = np.nan
    for _, g in t.groupby("group"):
        t.loc[g.index, "fdr"] = bh(g.p_perm)
        t.loc[g.index, "fdr_param"] = bh(g.p_param)
        if prod_outcomes:
            gp = g[g.outcome.isin(prod_outcomes)]
            t.loc[gp.index, "fdr_prod"] = bh(gp.p_perm)
    t["verdict"] = t.apply(verdict, axis=1)
    return t


# ------------------------------------------------------------------ family runner
def run_family(groups, tests, outcomes, *, year_col="draft_year", size_cols=SIZE, progress=True, prod_outcomes=None) -> pd.DataFrame:
    """groups: list of (name, DataFrame, role_col|None).  tests: list of (col, label, sign).
    outcomes: list of dicts(col, label, sign, alt=None, weight=None).  BH-FDR is applied per group
    over every test x outcome cell, on the permutation p-value."""
    import time
    rows = []
    for gname, sub, role in groups:
        assert_no_draft_slot(sub)
        t0 = time.time()
        for o in outcomes:
            for tc, tl, tsg in tests:
                if tc not in sub.columns or o["col"] not in sub.columns:
                    continue
                r = test_pair(sub, tc, o["col"], year_col=year_col, role_col=role, size_cols=size_cols,
                              weight_col=o.get("weight"), alt_outcome=o.get("alt"))
                rows.append(dict(group=gname, test=tc, test_label=tl, test_good=tsg, outcome=o["col"],
                                 outcome_label=o["label"], outcome_good=o.get("sign", 0), **r))
        if progress:
            print(f"  {gname}: {time.time() - t0:.0f}s", flush=True)
    return finalize(pd.DataFrame(rows), prod_outcomes)
