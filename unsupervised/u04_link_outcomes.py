#!/usr/bin/env python3
"""Step 4: link archetypes, latent axes, interactions and anomalies to game outcomes (PLAN.md §5, pre-registered).

Family A  archetype -> outcome: Kruskal-Wallis (year-demeaned), epsilon^2 + bootstrap CI, Freedman-Lane permutation F
          for archetype beyond draft year + weight + height (+ role), BH across family, leave-one-class-out check, MDE.
Family B  retained PC scores (ALL set, <= 3) -> outcome: rank partial correlation with the same controls (robust.py engines),
          bootstrap CI, Freedman-Lane p, BH within family, leave-one-class-out with PCA refit on two classes.
Family C  pre-declared interactions (DL weight x explosiveness; WR 40 speed x explosiveness).
Family D  isolation-forest unusualness -> outcome.
Post hoc  DL size-adjusted k = 3 (the only stable k > 2), labelled post hoc.
Aggregate CSVs only: out/familyA.csv, out/familyB.csv, out/familyC.csv, out/familyD.csv, out/anomaly_profile.csv,
out/archetype_outcome_summary.csv
"""
from __future__ import annotations
import sys
import numpy as np, pandas as pd
from scipy import stats
from scipy.stats import ncf, f as fdist
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from common import CACHE, OUT, SEED, GROUPS, REPO, bh, assert_no_draft
from u01b_game_features import OUTCOMES
import pipe as P

sys.path.insert(0, str(REPO))
import robust as R  # noqa: E402  (repo's tested inference engines; asserts no draft slot)

LOWER_BETTER = {"pfr_yds_tgt", "pfr_mtkl_pct"}
OUT_LABEL = {"sunday_speed_mph": "Deep-route / coverage game speed (mph)", "sep_all_mean": "Separation, all routes (yd)",
             "break_y": "Separation, break routes (yd, shrunk)", "tackle_rate": "Tackle rate (shrunk)", "tfl_rate": "TFL rate (shrunk)",
             "close_rate_mph": "Closing speed to the tackle (mph)", "pfr_yds_tgt": "Yards allowed per target (PFR)",
             "pfr_mtkl_pct": "Missed-tackle % (PFR)", "pressure_rate": "Pressure rate (shrunk)", "sack_rate": "Sack rate (shrunk)",
             "run_stop_rate": "Run-stop rate (shrunk)", "speed_1s_mph": "Get-off: speed 1 s after snap (mph)"}
NPERM, NBOOT, NLOSO = 5000, 2000, 2000
rng = np.random.default_rng(SEED)


def controls(d: pd.DataFrame, group: str, drop_weight=False) -> np.ndarray:
    cols = [np.ones(len(d))]
    yd = pd.get_dummies(d.draft_year.astype(str), drop_first=True).to_numpy(float)
    cols += [yd[:, j] for j in range(yd.shape[1])]
    if not drop_weight:
        cols.append(stats.rankdata(d.combine_weight))
    cols.append(stats.rankdata(d.combine_height))
    if group in ("DB", "DL"):
        rd = pd.get_dummies(d.role.astype(str), drop_first=True).to_numpy(float)
        cols += [rd[:, j] for j in range(rd.shape[1])]
    return np.column_stack(cols)


def fl_F(y, Z, D, P_=NPERM):
    """Freedman-Lane permutation p for adding D to Z (y ranked)."""
    y = stats.rankdata(y); X = np.column_stack([Z, D])
    Hr = Z @ np.linalg.pinv(Z); Hf = X @ np.linalg.pinv(X)
    def F(v):
        rr = v - Hr @ v; rf = v - Hf @ v
        return ((rr @ rr - rf @ rf) / D.shape[1]) / (rf @ rf / (len(v) - np.linalg.matrix_rank(X))), (rr @ rr - rf @ rf) / (rr @ rr)
    F0, pe2 = F(y)
    fit, e = Hr @ y, y - Hr @ y
    idx = np.argsort(rng.random((P_, len(y))), axis=1)
    Ys = fit[None] + e[idx]
    RR = Ys - Ys @ Hr.T; RF = Ys - Ys @ Hf.T
    rss_r, rss_f = (RR ** 2).sum(1), (RF ** 2).sum(1)
    Fs = ((rss_r - rss_f) / D.shape[1]) / (rss_f / (len(y) - np.linalg.matrix_rank(X)))
    return float(F0), float(pe2), float((1 + (Fs >= F0 - 1e-12).sum()) / (P_ + 1))


def mde_eta2(n, k, p_ctrl, alpha=0.05, power=0.8):
    d1, d2 = k - 1, n - p_ctrl - (k - 1)
    if d2 < 2:
        return np.nan
    crit = fdist.ppf(1 - alpha, d1, d2)
    lo, hi = 0.0, 200.0
    for _ in range(60):
        lam = (lo + hi) / 2
        if 1 - ncf.cdf(crit, d1, d2, lam) < power:
            lo = lam
        else:
            hi = lam
    f2 = lam / n
    return f2 / (1 + f2)


def year_demean(y, yr):
    y = y.astype(float).copy()
    for v in np.unique(yr):
        m = yr == v; y[m] = y[m] - y[m].mean()
    return y


def eps2(y, lab):
    groups = [y[lab == a] for a in np.unique(lab)]
    if len(groups) < 2 or min(len(g) for g in groups) < 2:
        return np.nan, np.nan
    H, p = stats.kruskal(*groups)
    n, k = len(y), len(groups)
    return (H - k + 1) / (n - k), p


def loso_adjust(y, d, train, group):
    """Within-class demeaned outcome, residualised on weight/height(/role) fit on training rows."""
    yc = year_demean(y, d.draft_year.to_numpy())
    cols = [np.ones(len(d)), d.combine_weight.to_numpy(float), d.combine_height.to_numpy(float)]
    if group in ("DB", "DL"):
        cols.append((d.role.to_numpy() == d.role.mode()[0]).astype(float))
    Z = np.column_stack(cols)
    b, *_ = np.linalg.lstsq(Z[train], yc[train], rcond=None)
    return yc - Z @ b


def loso_score(pred, truth, cls):
    rho = stats.spearmanr(pred, truth)[0] if np.unique(pred).size > 1 else np.nan
    per = []
    for c in np.unique(cls):
        m = cls == c
        per.append(stats.spearmanr(pred[m], truth[m])[0] if np.unique(pred[m]).size > 1 and m.sum() > 3 else np.nan)
    null = []
    for _ in range(NLOSO):
        pp = pred.copy()
        for c in np.unique(cls):
            m = np.where(cls == c)[0]; pp[m] = pp[rng.permutation(m)]
        null.append(stats.spearmanr(pp, truth)[0] if np.unique(pp).size > 1 else 0)
    null = np.nan_to_num(np.array(null))
    p = (1 + (null >= rho).sum()) / (NLOSO + 1) if np.isfinite(rho) else np.nan
    npos = int(np.sum(np.array(per) > 0))
    return rho, p, npos, per


def oriented(y, outcome):
    return -y if outcome in LOWER_BETTER else y


# ------------------------------------------------------------------ Family A
def family_a(cf, arch, gf):
    rows, summ = [], []
    sols = [(g, fs, None) for g in GROUPS for fs in ("ALL", "SIZEADJ")] + [("DL", "SIZEADJ", 3)]   # last = post hoc
    for g, fs, kk in sols:
        df = cf[cf.group == g].reset_index(drop=True)
        a = arch[(arch.group == g) & (arch.fset == fs)]
        if kk is None:
            method, k, status = a.method.iloc[0], int(a.k.iloc[0]), a.status.iloc[0]
            labs = a.set_index("nfl_id").arch
            tag = "pre-registered"
        else:
            ids, X, _ = P.prepare(df, g, fs); method, k, status = "kmeans", kk, "stable (post hoc)"
            labs = pd.Series(P.fit_cluster(X, "kmeans", kk)[0], index=ids); tag = "post hoc"
        for o in OUTCOMES[g]:
            d = df.merge(gf[["nfl_id", o]], on="nfl_id").dropna(subset=[o, "combine_weight", "combine_height"])
            d = d[d.nfl_id.isin(labs.index)].reset_index(drop=True)
            if len(d) < 12:
                continue
            lab = labs.loc[d.nfl_id].to_numpy()
            y = oriented(d[o].to_numpy(float), o)
            yd = year_demean(y, d.draft_year.to_numpy())
            e, p_kw = eps2(yd, lab)
            bs = []
            for _ in range(NBOOT):
                ii = rng.integers(0, len(d), len(d))
                bs.append(eps2(yd[ii], lab[ii])[0])
            lo, hi = np.nanpercentile(bs, [2.5, 97.5])
            Z = controls(d, g); D = pd.get_dummies(lab.astype(str), drop_first=True).to_numpy(float)
            F0, pe2, p_size = fl_F(y, Z, D)
            # held-out class
            preds, truths, cls = [], [], []
            for c in sorted(df.draft_year.unique()):
                fit_on = df.draft_year != c
                ids, X, _ = P.prepare(df, g, fs, fit_on=fit_on)
                trm = ~pd.Series(ids).map(df.set_index("nfl_id").draft_year).eq(c).to_numpy()
                lt, _ = P.fit_cluster(X[trm], method if method != "hdbscan" else "kmeans", k)
                Cc = P.centroids(X[trm], lt)
                lab_all = pd.Series(np.r_[lt, P.assign(X[~trm], Cc)], index=np.r_[ids[trm], ids[~trm]])
                dd = d[d.nfl_id.isin(lab_all.index)].reset_index(drop=True)
                tr = (dd.draft_year != c).to_numpy()
                ya = loso_adjust(oriented(dd[o].to_numpy(float), o), dd, tr, g)
                la = lab_all.loc[dd.nfl_id].to_numpy()
                means = pd.Series(ya[tr]).groupby(la[tr]).mean()
                pr = pd.Series(la[~tr]).map(means).fillna(0).to_numpy()
                preds.append(pr); truths.append(ya[~tr]); cls.append(np.full((~tr).sum(), c))
            rho_h, p_h, npos, per = loso_score(np.concatenate(preds), np.concatenate(truths), np.concatenate(cls))
            # coach summary: as-reported medians by archetype
            for a_ in np.unique(lab):
                v = d[o].to_numpy(float)[lab == a_]
                summ.append(dict(group=g, fset=fs, k=k, tag=tag, outcome=o, arch=int(a_), n=len(v), median=np.median(v),
                                 q25=np.percentile(v, 25), q75=np.percentile(v, 75), mean=v.mean(),
                                 boot_lo=np.percentile([np.median(rng.choice(v, len(v))) for _ in range(1000)], 2.5),
                                 boot_hi=np.percentile([np.median(rng.choice(v, len(v))) for _ in range(1000)], 97.5)))
            rows.append(dict(group=g, fset=fs, method=method, k=k, cluster_status=status, tag=tag, outcome=o, label=OUT_LABEL[o], n=len(d),
                             eps2=e, eps2_lo=lo, eps2_hi=hi, p_kw=p_kw, partial_eta2_size=pe2, p_size=p_size,
                             loso_rho=rho_h, loso_p=p_h, loso_classes_pos=npos, loso_per_class=str(np.round(per, 2).tolist()),
                             mde_eta2=mde_eta2(len(d), k, Z.shape[1])))
            print("A", g, fs, k, o, len(d), round(e, 3), round(p_kw, 3), round(p_size, 3), round(rho_h, 2), flush=True)
    t = pd.DataFrame(rows)
    pre = t.tag == "pre-registered"
    t.loc[pre, "q_kw"] = bh(t.loc[pre, "p_kw"]); t.loc[pre, "q_size"] = bh(t.loc[pre, "p_size"])
    return t, pd.DataFrame(summ)


# ------------------------------------------------------------------ Family B
def family_b(cf, gf):
    rows = []
    var = pd.read_csv(OUT / "pca_variance.csv")
    for g in GROUPS:
        df = cf[cf.group == g].reset_index(drop=True)
        ids, X, f = P.prepare(df, g, "ALL")
        nkeep = min(3, int(var[(var.group == g) & (var.fset == "ALL") & var.kept].pc.max()))
        pca = PCA().fit(X); S = pd.DataFrame(pca.transform(X)[:, :nkeep], index=ids)
        for j in range(nkeep):
            for o in OUTCOMES[g]:
                d = df.merge(gf[["nfl_id", o]], on="nfl_id").dropna(subset=[o, "combine_weight", "combine_height"])
                d = d[d.nfl_id.isin(ids)].reset_index(drop=True)
                x = S.loc[d.nfl_id, j].to_numpy(); y = oriented(d[o].to_numpy(float), o)
                Z = controls(d, g)[:, 1:]
                yrd = pd.get_dummies(d.draft_year.astype(str), drop_first=True).to_numpy(float)
                C = np.column_stack([d.combine_weight, d.combine_height]); Dm = yrd
                if g in ("DB", "DL"):
                    Dm = np.column_stack([yrd, pd.get_dummies(d.role.astype(str), drop_first=True).to_numpy(float)])
                r = R.partial_rank_corr(x, y, C, Dm); lo, hi = R.boot_partial(x, y, C, Dm)
                p = R.perm_partial(x, y, C, Dm)
                r_raw = R.partial_rank_corr(x, y, None, yrd); p_raw = R.perm_partial(x, y, None, yrd, P=2000)
                preds, truths, cls = [], [], []
                for c in sorted(df.draft_year.unique()):
                    fit_on = df.draft_year != c
                    i2, X2, _ = P.prepare(df, g, "ALL", fit_on=fit_on)
                    trm = ~pd.Series(i2).map(df.set_index("nfl_id").draft_year).eq(c).to_numpy()
                    pc = PCA().fit(X2[trm]); comp = pc.components_[j]
                    if comp @ pca.components_[j] < 0:
                        comp = -comp
                    sc = pd.Series(X2 @ comp, index=i2)
                    dd = d[d.nfl_id.isin(i2)].reset_index(drop=True); tr = (dd.draft_year != c).to_numpy()
                    ya = loso_adjust(oriented(dd[o].to_numpy(float), o), dd, tr, g)
                    xs = sc.loc[dd.nfl_id].to_numpy()
                    xa = loso_adjust(xs, dd, tr, g)      # same size/role adjustment for the score
                    b = np.polyfit(xa[tr], ya[tr], 1)
                    preds.append(np.polyval(b, xa[~tr])); truths.append(ya[~tr]); cls.append(np.full((~tr).sum(), c))
                rho_h, p_h, npos, per = loso_score(np.concatenate(preds), np.concatenate(truths), np.concatenate(cls))
                rows.append(dict(group=g, pc=j + 1, outcome=o, label=OUT_LABEL[o], n=len(d), rho_yearonly=r_raw, p_yearonly=p_raw,
                                 rho_size=r, lo=lo, hi=hi, p_size=p, loso_rho=rho_h, loso_p=p_h, loso_classes_pos=npos,
                                 loso_per_class=str(np.round(per, 2).tolist())))
                print("B", g, j + 1, o, len(d), round(r_raw, 2), round(r, 2), round(p, 3), round(rho_h, 2), flush=True)
    t = pd.DataFrame(rows); t["q_size"] = bh(t.p_size); t["q_yearonly"] = bh(t.p_yearonly)
    return t


# ------------------------------------------------------------------ Family C
def family_c(cf, gf):
    rows = []
    spec = [("DL", "combine_weight", ["pressure_rate", "sack_rate"], "Weight x explosiveness"),
            ("WR", "forty", ["sep_all_mean", "break_y", "sunday_speed_mph"], "40 speed x explosiveness")]
    for g, x1n, outs, name in spec:
        df = cf[cf.group == g].reset_index(drop=True)
        for o in outs:
            d = df.merge(gf[["nfl_id", o]], on="nfl_id").dropna(subset=[o, x1n, "vertical", "broad_jump", "combine_weight", "combine_height"]).reset_index(drop=True)
            z = lambda v: (v - v.mean()) / v.std()
            expl = (z(d.vertical) + z(d.broad_jump)) / 2
            x1 = z(-d.forty) if x1n == "forty" else z(d.combine_weight)
            y = stats.rankdata(oriented(d[o].to_numpy(float), o))
            Z = controls(d, g, drop_weight=(x1n == "combine_weight"))
            base = np.column_stack([Z, x1, expl])
            inter = (x1 * expl).to_numpy()[:, None]
            F0, pe2, p = fl_F(y, base, inter)
            b, *_ = np.linalg.lstsq(np.column_stack([base, inter]), y, rcond=None)
            hi1, hie = x1 > x1.median(), expl > expl.median()
            cell = {f"{'hi' if a else 'lo'}_{'x1'}_{'hi' if b_ else 'lo'}_expl": float(np.median(d[o][(hi1 == a) & (hie == b_)]))
                    for a in (True, False) for b_ in (True, False)}
            ncell = {f"n_{'hi' if a else 'lo'}_x1_{'hi' if b_ else 'lo'}_expl": int(((hi1 == a) & (hie == b_)).sum()) for a in (True, False) for b_ in (True, False)}
            rows.append(dict(group=g, test=name, outcome=o, label=OUT_LABEL[o], n=len(d), interaction_coef_rank=b[-1], partial_eta2=pe2, p_perm=p, **cell, **ncell))
            print("C", g, name, o, len(d), round(b[-1], 2), round(p, 3), flush=True)
    t = pd.DataFrame(rows); t["q"] = bh(t.p_perm)
    return t


# ------------------------------------------------------------------ Family D
def family_d(cf, gf):
    rows, prof = [], []
    for g in GROUPS:
        df = cf[cf.group == g].reset_index(drop=True)
        ids, X, f = P.prepare(df, g, "ALL")
        iso = IsolationForest(n_estimators=300, random_state=SEED).fit(X)
        sc = pd.Series(-iso.score_samples(X), index=ids)
        top = sc >= sc.quantile(0.9)
        az = np.abs(X[top.to_numpy()]).mean(0)
        for fi, fn in enumerate(f):
            prof.append(dict(group=g, feature=fn, label=P.LABEL[fn], mean_abs_z_top10=az[fi], mean_abs_z_rest=np.abs(X[~top.to_numpy()]).mean(0)[fi],
                             mean_z_top10=X[top.to_numpy()].mean(0)[fi], n_top10=int(top.sum())))
        for o in OUTCOMES[g]:
            d = df.merge(gf[["nfl_id", o]], on="nfl_id").dropna(subset=[o, "combine_weight", "combine_height"])
            d = d[d.nfl_id.isin(ids)].reset_index(drop=True)
            x = sc.loc[d.nfl_id].to_numpy(); y = oriented(d[o].to_numpy(float), o)
            yrd = pd.get_dummies(d.draft_year.astype(str), drop_first=True).to_numpy(float)
            C = np.column_stack([d.combine_weight, d.combine_height]); Dm = yrd
            if g in ("DB", "DL"):
                Dm = np.column_stack([yrd, pd.get_dummies(d.role.astype(str), drop_first=True).to_numpy(float)])
            r = R.partial_rank_corr(x, y, C, Dm); lo, hi = R.boot_partial(x, y, C, Dm); p = R.perm_partial(x, y, C, Dm)
            t10 = sc.loc[d.nfl_id].to_numpy() >= sc.quantile(0.9)
            rows.append(dict(group=g, outcome=o, label=OUT_LABEL[o], n=len(d), n_unusual=int(t10.sum()), rho_size=r, lo=lo, hi=hi, p_size=p,
                             median_unusual=float(np.median(d[o][t10])) if t10.sum() else np.nan, median_rest=float(np.median(d[o][~t10]))))
            print("D", g, o, len(d), round(r, 2), round(p, 3), flush=True)
    t = pd.DataFrame(rows); t["q"] = bh(t.p_size)
    return t, pd.DataFrame(prof)


def main() -> None:
    cf = pd.read_parquet(CACHE / "combine_features.parquet"); arch = pd.read_parquet(CACHE / "archetypes.parquet")
    gf = pd.read_parquet(CACHE / "game_features.parquet")
    for d in (cf, arch, gf):
        assert_no_draft(d)
    a, s = family_a(cf, arch, gf); a.to_csv(OUT / "familyA.csv", index=False); s.to_csv(OUT / "archetype_outcome_summary.csv", index=False)
    family_b(cf, gf).to_csv(OUT / "familyB.csv", index=False)
    family_c(cf, gf).to_csv(OUT / "familyC.csv", index=False)
    d, prof = family_d(cf, gf); d.to_csv(OUT / "familyD.csv", index=False); prof.to_csv(OUT / "anomaly_profile.csv", index=False)


if __name__ == "__main__":
    main()
