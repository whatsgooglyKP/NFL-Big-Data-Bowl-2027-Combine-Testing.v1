#!/usr/bin/env python3
"""Step 3: in-game movement / deployment styles, and do Combine archetypes line up with them?

Game-style features (u01b, PLAN §4) standardised within group, >= 70% observed, iterative imputation.
k-means k = 2..5 by silhouette, 200-resample bootstrap stability, one-blob null (as u02b).
Crosstab vs the primary Combine archetype (ALL set): ARI and NMI with 5,000-shuffle permutation p, BH across groups.
Post hoc (labelled in FINDINGS): RV coefficient between the whole Combine matrix and the whole game-style matrix,
permutation p (2,000 shuffles).
Writes out/game_style_selection.csv, out/game_style_centroids.csv, out/crosstab_tests.csv, out/crosstab_counts.csv,
cache/game_styles.parquet (per player).
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score, normalized_mutual_info_score
from common import CACHE, OUT, SEED, GROUPS, bh
from u01b_game_features import STYLE
import pipe as P

STYLE_LABEL = {"game_wr_peak_decel_mag": "Brakes into the cut", "game_wr_peak_accel": "Re-accel out of the cut",
               "game_wr_speed_lost": "Speed lost in the cut", "game_wr_time_through": "Time through the cut",
               "g_deep_speed": "Deep-route game speed", "cushion_mean": "Defender cushion", "slot_share": "Slot share",
               "deep_route_share": "Deep-route share", "short_route_share": "Short-route share",
               "game_db_peak_decel_mag": "Brakes in coverage", "game_db_peak_accel": "Re-accel in coverage",
               "game_db_speed_lost": "Speed lost in coverage cut", "game_db_time_through": "Time through coverage cut",
               "close_speed_at_arrival": "Speed arriving at tackle", "close_max_s_0p5": "Peak closing speed",
               "g_cov_speed": "Coverage game speed", "man_share": "Man-coverage share", "high_safety_share": "High-safety share",
               "g_speed_1s": "Speed 1 s after snap", "g_get_off": "NGS get-off time", "pen_pass_2s": "Penetration at 2 s (pass)",
               "pen_run_2s": "Penetration at 2 s (run)", "edge_share": "Edge alignment share"}


def rv(X, Y):
    X = X - X.mean(0); Y = Y - Y.mean(0)
    Sxy = X.T @ Y; Sxx = X.T @ X; Syy = Y.T @ Y
    return float(np.trace(Sxy @ Sxy.T) / np.sqrt(np.trace(Sxx @ Sxx) * np.trace(Syy @ Syy)))


def main() -> None:
    gf = pd.read_parquet(CACHE / "game_features.parquet")
    arch = pd.read_parquet(CACHE / "archetypes.parquet")
    cf = pd.read_parquet(CACHE / "combine_features.parquet")
    rng = np.random.default_rng(SEED)
    sel, cen, tests, counts, labs = [], [], [], [], []
    for g in GROUPS:
        f = STYLE[g]
        d = gf[gf.group == g].reset_index(drop=True)
        d = d[d[f].notna().mean(axis=1) >= 0.7].reset_index(drop=True)
        A = d[f].to_numpy(float); Z = (A - np.nanmean(A, 0)) / np.nanstd(A, 0)
        if np.isnan(Z).any():
            Z = IterativeImputer(estimator=BayesianRidge(), max_iter=10, random_state=SEED).fit_transform(Z)
        n = len(Z); best = None
        for k in range(2, 6):
            lab = KMeans(k, n_init=50, random_state=SEED).fit_predict(Z)
            s = silhouette_score(Z, lab)
            ari, jac = P.stability(Z, "kmeans", k, lab, B=200)
            C = np.cov(Z, rowvar=False)
            null = [silhouette_score(Y, KMeans(k, n_init=5, random_state=b).fit_predict(Y))
                    for b, Y in enumerate(rng.multivariate_normal(np.zeros(len(f)), C, (200, n)))]
            p_blob = (1 + (np.array(null) >= s).sum()) / 201
            stable = ari >= 0.6 and min(jac.values()) >= 0.6
            sel.append(dict(group=g, n=n, k=k, silhouette=s, boot_ari_median=ari, jaccard_min=min(jac.values()), stable=stable,
                            p_one_blob=p_blob, sizes=str(np.bincount(lab).tolist())))
            if best is None or s > best[1]:
                best = (k, s, lab, stable)
        k, s, lab, stable = best
        labs.append(pd.DataFrame({"nfl_id": d.nfl_id, "group": g, "style": lab, "k": k, "stable": stable}))
        Cz = np.vstack([Z[lab == a].mean(0) for a in range(k)])
        for a in range(k):
            for j, fn in enumerate(f):
                cen.append(dict(group=g, k=k, style=a, n_style=int((lab == a).sum()), feature=fn, label=STYLE_LABEL[fn], z=Cz[a, j],
                                raw_mean=float(np.nanmean(A[lab == a, j]))))
        # crosstab vs Combine archetype (ALL)
        ar = arch[(arch.group == g) & (arch.fset == "ALL")][["nfl_id", "arch"]]
        m = pd.DataFrame({"nfl_id": d.nfl_id, "style": lab}).merge(ar, on="nfl_id")
        a_, b_ = m.arch.to_numpy(), m["style"].to_numpy()
        ari0, nmi0 = adjusted_rand_score(a_, b_), normalized_mutual_info_score(a_, b_)
        perm = np.array([[adjusted_rand_score(a_, rng.permutation(b_)), normalized_mutual_info_score(a_, rng.permutation(b_))] for _ in range(5000)])
        tests.append(dict(group=g, n=len(m), combine_k=int(m.arch.nunique()), style_k=k, style_stable=stable, ari=ari0, nmi=nmi0,
                          p_ari=(1 + (perm[:, 0] >= ari0).sum()) / 5001, p_nmi=(1 + (perm[:, 1] >= nmi0).sum()) / 5001))
        ct = pd.crosstab(m.arch, m["style"])
        for (i, j), v in ct.stack().items():
            counts.append(dict(group=g, combine_arch=i, game_style=j, count=int(v)))
        # post hoc RV: whole Combine (ALL, standardised + imputed) vs whole game-style matrix
        ids, Xc, _ = P.prepare(cf[cf.group == g].reset_index(drop=True), g, "ALL")
        xc = pd.DataFrame(Xc, index=ids)
        common_ids = [i for i in d.nfl_id if i in xc.index]
        Xm = xc.loc[common_ids].to_numpy(); Ym = Z[d.nfl_id.isin(common_ids).to_numpy()]
        Ym = pd.DataFrame(Z, index=d.nfl_id).loc[common_ids].to_numpy()
        r0 = rv(Xm, Ym)
        rp = np.array([rv(Xm, Ym[rng.permutation(len(Ym))]) for _ in range(2000)])
        tests[-1].update(rv_combine_vs_style=r0, rv_null_median=float(np.median(rp)), p_rv=(1 + (rp >= r0).sum()) / 2001, n_rv=len(common_ids))
        print(g, "style k", k, "sil", round(s, 3), "stable", stable, tests[-1], flush=True)
    t = pd.DataFrame(tests); t["q_ari"] = bh(t.p_ari); t["q_nmi"] = bh(t.p_nmi); t["q_rv"] = bh(t.p_rv)
    t.to_csv(OUT / "crosstab_tests.csv", index=False)
    pd.DataFrame(sel).to_csv(OUT / "game_style_selection.csv", index=False)
    pd.DataFrame(cen).to_csv(OUT / "game_style_centroids.csv", index=False)
    pd.DataFrame(counts).to_csv(OUT / "crosstab_counts.csv", index=False)
    pd.concat(labs).to_parquet(CACHE / "game_styles.parquet", index=False)


if __name__ == "__main__":
    main()
