#!/usr/bin/env python3
"""Step 2: PCA (parallel analysis) and Combine archetypes with bootstrap stability. No outcomes are read.

Writes (aggregate): out/pca_variance.csv, out/pca_loadings.csv, out/cluster_selection.csv, out/archetype_centroids.csv,
out/archetype_sensitivity.csv ; (per player, cache only): cache/archetypes.parquet, cache/pca_scores.parquet
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score
from common import CACHE, OUT, SEED, GROUPS
import pipe as P

FSETS = ["ALL", "SIZEADJ"]
KS = range(2, 7)


def parallel_analysis(X, B=500, seed=SEED):
    rng = np.random.default_rng(seed); n, p = X.shape
    ev = np.array([np.linalg.eigvalsh(np.corrcoef(rng.standard_normal((n, p)), rowvar=False))[::-1] for _ in range(B)])
    return np.percentile(ev, 95, axis=0)


def main() -> None:
    cf = pd.read_parquet(CACHE / "combine_features.parquet")
    var_rows, load_rows, sel_rows, cen_rows, sens_rows, labs, scores = [], [], [], [], [], [], []
    for g in GROUPS:
        df = cf[cf.group == g].reset_index(drop=True)
        for fs in FSETS:
            ids, X, f = P.prepare(df, g, fs)
            n = len(X)
            # ---- PCA
            pca = PCA().fit(X); ev = pca.explained_variance_ * (n - 1) / n
            pa = parallel_analysis(X)
            n_keep = int(np.argmax(ev < pa)) if (ev < pa).any() else len(ev)
            for j in range(len(ev)):
                var_rows.append(dict(group=g, fset=fs, n=n, pc=j + 1, eigen=ev[j], pa95=pa[j], var_share=pca.explained_variance_ratio_[j], kept=j < n_keep))
            for j in range(min(4, len(ev))):
                for fi, fn in enumerate(f):
                    load_rows.append(dict(group=g, fset=fs, pc=j + 1, feature=fn, label=P.LABEL[fn], loading=pca.components_[j, fi]))
            sc = pca.transform(X)[:, :3]
            scores.append(pd.DataFrame({"nfl_id": ids, "group": g, "fset": fs, "pc1": sc[:, 0], "pc2": sc[:, 1], "pc3": sc[:, 2]}))
            # ---- clustering candidates
            cands = []
            for k in KS:
                lab, _ = P.fit_cluster(X, "kmeans", k)
                gap, gse = P.gap_stat(X, k)
                cands.append(dict(method="kmeans", k=k, sil=P.sil(X, lab), gap=gap, gap_se=gse, lab=lab))
            bics = {k: GaussianMixture(k, covariance_type="diag", n_init=10, random_state=SEED).fit(X).bic(X) for k in range(1, 7)}
            kg = min(bics, key=bics.get)
            ward = {k: P.sil(X, P.fit_cluster(X, "ward", k)[0]) for k in KS}
            kw = max(ward, key=ward.get)
            km_best = max([c for c in cands], key=lambda c: c["sil"])["k"]
            hl, _ = P.fit_cluster(X, "hdbscan", None)
            todo = [c for c in cands]  # stability for every k-means k (shows the k curve)
            if kg >= 2:
                todo.append(dict(method="gmm", k=kg, sil=None, lab=P.fit_cluster(X, "gmm", kg)[0], bic=bics[kg], bic_k1=bics[1]))
            todo.append(dict(method="ward", k=kw, sil=ward[kw], lab=P.fit_cluster(X, "ward", kw)[0]))
            hk = len(set(hl) - {-1})
            if hk >= 2:
                todo.append(dict(method="hdbscan", k=hk, sil=P.sil(X, hl), lab=hl, noise=float((hl < 0).mean())))
            for c in todo:
                lab = c["lab"]
                ari, jac = P.stability(X, c["method"], c["k"] if c["method"] != "hdbscan" else None, lab, B=200 if c["method"] != "hdbscan" else 100)
                c.update(ari=ari, jac_min=min(jac.values()), jac=jac, stable=(ari >= 0.6 and min(jac.values()) >= 0.6),
                         sil=c["sil"] if c["sil"] is not None else P.sil(X, lab),
                         sizes=list(np.bincount(lab[lab >= 0])))
                role = df.set_index("nfl_id").loc[ids, "role"].to_numpy()
                c["ari_role"] = adjusted_rand_score(role, lab) if g in ("DB", "DL") else np.nan
                sel_rows.append(dict(group=g, fset=fs, n=n, method=c["method"], k=c["k"], silhouette=c["sil"], gap=c.get("gap"), gap_se=c.get("gap_se"),
                                     bic=c.get("bic"), bic_k1=c.get("bic_k1"), hdb_noise=c.get("noise"), boot_ari_median=c["ari"],
                                     jaccard_min=c["jac_min"], jaccard=str({k: round(v, 2) for k, v in c["jac"].items()}), stable=c["stable"],
                                     sizes=str(c["sizes"]), ari_vs_role=c["ari_role"], kmeans_best_sil_k=km_best, gmm_bic_k=kg, ward_sil_k=kw, hdbscan_k=hk))
            # primary: most stable stable solution (tie -> kmeans); else flagged unstable best-silhouette kmeans
            stab = [c for c in todo if c["stable"] and c["method"] != "hdbscan"]
            if stab:
                best = max(stab, key=lambda c: (round(c["ari"], 2), c["method"] == "kmeans", -c["k"]))
                status = "stable"
            else:
                best = [c for c in cands if c["k"] == km_best][0]; status = "unstable"
            lab = best["lab"]
            labs.append(pd.DataFrame({"nfl_id": ids, "group": g, "fset": fs, "method": best["method"], "k": best["k"], "status": status, "arch": lab}))
            C = P.centroids(X, lab)
            for a in range(C.shape[0]):
                for fi, fn in enumerate(f):
                    cen_rows.append(dict(group=g, fset=fs, method=best["method"], k=best["k"], status=status, arch=a, n_arch=int((lab == a).sum()),
                                         feature=fn, label=P.LABEL[fn], z=C[a, fi]))
            # sensitivity: complete cases (same method, k)
            ids_c, Xc, _ = P.prepare(df, g, fs, complete_only=True)
            if len(Xc) >= 15 and best["method"] in ("kmeans", "gmm", "ward"):
                lc, _ = P.fit_cluster(Xc, best["method"], best["k"])
                ref = pd.Series(lab, index=ids).loc[ids_c].to_numpy()
                sens_rows.append(dict(group=g, fset=fs, n_imputed_set=n, n_complete=len(Xc), method=best["method"], k=best["k"],
                                      ari_complete_vs_imputed=adjusted_rand_score(ref, lc)))
            print(g, fs, n, "PCs kept", n_keep, "| primary", best["method"], best["k"], status, round(best["ari"], 2), flush=True)
    pd.DataFrame(var_rows).to_csv(OUT / "pca_variance.csv", index=False)
    pd.DataFrame(load_rows).to_csv(OUT / "pca_loadings.csv", index=False)
    pd.DataFrame(sel_rows).to_csv(OUT / "cluster_selection.csv", index=False)
    pd.DataFrame(cen_rows).to_csv(OUT / "archetype_centroids.csv", index=False)
    pd.DataFrame(sens_rows).to_csv(OUT / "archetype_sensitivity.csv", index=False)
    pd.concat(labs).to_parquet(CACHE / "archetypes.parquet", index=False)
    pd.concat(scores).to_parquet(CACHE / "pca_scores.parquet", index=False)


if __name__ == "__main__":
    main()
