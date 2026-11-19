#!/usr/bin/env python3
"""Independent statistical audit of out/scorecard_full.csv (11/2026). Re-derives every row from the saved player tables
with code that does NOT call robust.py: partial rank correlation via the precision matrix, analytic t p-value,
a different permutation scheme (permute the x-residuals, Freedman-Lane on x), a 5000-rep player bootstrap that refits
the residualisation in every resample, and BH-FDR via statsmodels. Writes out/audit_stats.csv.
No draft slot, pick or round is read. Usage: python3 audit_stats.py [--quick]
"""
from __future__ import annotations
import sys, numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import scorecard as SC

OUT = SC.OUT
B = 1000 if "--quick" in sys.argv else 5000
PERM = 4000 if "--quick" in sys.argv else 20000
TIMED = {"forty", "ten_yd_split", "three_cone", "short_shuttle"}
LOWER_BETTER = {"pfr_yds_tgt", "pfr_mtkl_pct"}


def partial_precision(x, y, Z):
    """Partial Pearson r of (x, y) given columns Z (already ranked / dummy-coded), from the inverse covariance."""
    M = np.column_stack([x, y, Z]) if Z.shape[1] else np.column_stack([x, y])
    C = np.cov(M, rowvar=False)
    P = np.linalg.pinv(C)
    return float(-P[0, 1] / np.sqrt(P[0, 0] * P[1, 1]))


def build(s, test, outcome, role):
    n = len(s)
    yr = pd.get_dummies(s.draft_year.astype(str), drop_first=True).to_numpy(float)
    parts = [yr]
    if role:
        parts.append(pd.get_dummies(s[role].astype(str), drop_first=True).to_numpy(float))
    D = np.column_stack(parts) if parts else np.zeros((n, 0))
    return D


def pr(x, y, W, H, D):
    Z = np.column_stack([D, stats.rankdata(W), stats.rankdata(H)])
    return partial_precision(stats.rankdata(x), stats.rankdata(y), Z)


def resid(v, Z):
    A = np.column_stack([np.ones(len(v)), Z]); b, *_ = np.linalg.lstsq(A, v, rcond=None); return v - A @ b


def frame_for(r, F, rl):
    if r.outcome == "break_y":
        fr = rl.copy(); role = None
        s = fr[["break_y", "break_raw", "draft_year", "combine_weight", "combine_height", r.test]].dropna().copy()
        s[r.test] = s[r.test] * SC.RL_SIGN[r.test]
        return s, "break_y", None
    fr = F[(r.group, r.subgroup)]
    role = "subtype" if (r.group == "DL" and r.subgroup == "All") else ("role" if r.group == "DB" else None)
    cols = [r.test, r.outcome, "draft_year", "combine_weight", "combine_height"] + ([role] if role else [])
    return fr[cols].dropna().copy(), r.outcome, role


def audit_row(r, F, rl, rng):
    s, oc, role = frame_for(r, F, rl)
    n = len(s)
    D = build(s, r.test, oc, role)
    x, y = s[r.test].to_numpy(float), s[oc].to_numpy(float)
    W, H = s.combine_weight.to_numpy(float), s.combine_height.to_numpy(float)
    sg = 1.0
    if oc != "break_y":
        tg = -1 if r.test in TIMED else 1
        og = -1 if r.outcome in LOWER_BETTER else 1
        sg = tg * og
    k = D.shape[1] + 2
    rho = pr(x, y, W, H, D) * sg
    # analytic t p-value, df = n - 2 - k
    df = n - 2 - k
    t = rho * np.sqrt(df / (1 - rho ** 2)) if abs(rho) < 1 and df > 0 else np.nan
    p_t = float(2 * stats.t.sf(abs(t), df)) if df > 0 else np.nan
    # Fisher-z / Bonett-Wright analytic 95% CI for a Spearman partial correlation
    se = np.sqrt(1.06 / max(n - 3 - k, 1))
    z = np.arctanh(np.clip(rho, -0.999, 0.999)); ci_z = (float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se)))
    # permutation (x-side Freedman-Lane): permute reduced-model residuals of rank(x) given controls, re-residualise
    Zc = np.column_stack([D, stats.rankdata(W), stats.rankdata(H)])
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    ex, ey = resid(rx, Zc), resid(ry, Zc)
    A = np.column_stack([np.ones(n), Zc]); Hm = A @ np.linalg.pinv(A)
    obs = abs(np.corrcoef(ex, ey)[0, 1]); cnt = 0; done = 0
    for _ in range(PERM // 1000):
        idx = np.argsort(rng.random((1000, n)), axis=1)
        e = ex[idx]; me = e - e @ Hm
        c = (me @ ey) / (np.sqrt((me ** 2).sum(1)) * np.sqrt((ey ** 2).sum()))
        cnt += int(np.sum(np.abs(c) >= obs - 1e-12)); done += 1000
    p_perm = (1 + cnt) / (done + 1)
    # bootstrap players, refit everything in each resample
    bs = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        Di = D[i]
        if np.linalg.matrix_rank(np.column_stack([np.ones(n), Di])) < 1 + Di.shape[1]:
            Di = Di[:, np.abs(Di - Di.mean(0)).sum(0) > 0]
        v = pr(x[i], y[i], W[i], H[i], Di)
        if np.isfinite(v):
            bs.append(v * sg)
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    # BCa
    z0 = stats.norm.ppf(np.clip((bs < rho).mean(), 1e-3, 1 - 1e-3))
    jk = []
    for j in range(n):
        m = np.arange(n) != j
        Dj = D[m]; Dj = Dj[:, np.abs(Dj - Dj.mean(0)).sum(0) > 0]
        jk.append(pr(x[m], y[m], W[m], H[m], Dj) * sg)
    jk = np.array(jk); d = jk.mean() - jk
    acc = (d ** 3).sum() / (6 * ((d ** 2).sum() ** 1.5)) if (d ** 2).sum() > 0 else 0
    a1, a2 = stats.norm.cdf(z0 + (z0 + stats.norm.ppf(0.025)) / (1 - acc * (z0 + stats.norm.ppf(0.025)))), \
        stats.norm.cdf(z0 + (z0 + stats.norm.ppf(0.975)) / (1 - acc * (z0 + stats.norm.ppf(0.975))))
    bca = tuple(np.percentile(bs, [100 * a1, 100 * a2]))
    return dict(n_aud=n, rho_aud=rho, p_t_aud=p_t, p_perm_aud=p_perm, lo_aud=lo, hi_aud=hi, bca_lo=bca[0], bca_hi=bca[1],
                z_lo=ci_z[0], z_hi=ci_z[1], k_ctrl=k, boot_mean=float(bs.mean()))


def main():
    full = pd.read_csv(OUT / "scorecard_full.csv")
    F = SC._frames(); rl = pd.read_csv(OUT / "wr_route_lead_players.csv")
    rng = np.random.default_rng(20271)
    rows = []
    for i, r in enumerate(full.itertuples()):
        a = audit_row(r, F, rl, rng); rows.append(a)
        if i % 20 == 0: print(i, flush=True)
    A = pd.concat([full, pd.DataFrame(rows)], axis=1)
    A.to_csv(OUT / "audit_stats.csv", index=False)
    print("wrote", OUT / "audit_stats.csv")


if __name__ == "__main__":
    main()
