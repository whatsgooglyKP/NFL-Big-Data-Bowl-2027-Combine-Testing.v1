"""Shared preprocessing, clustering and stability code (no outcomes here)."""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LinearRegression
from sklearn.cluster import KMeans, AgglomerativeClustering, HDBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, adjusted_rand_score
from common import SEED

STD = ["forty", "ten_yd_split", "vertical", "broad_jump", "combine_height", "combine_weight", "arm_length", "hand_size"]
TRK40 = ["f40_top", "f40_acc", "f40_s1", "f40_t90", "f40_hold"]
DRILL_OK = {"WR": ["drill_acc"], "TE": ["drill_turn"], "DB": ["drill_top"], "DL": ["drill_top", "drill_acc"]}  # alpha >= 0.6 (PLAN §1)
FLIP = {"forty", "ten_yd_split", "f40_t90"}           # times: flip so higher = more athletic
LABEL = {"forty": "40 speed", "ten_yd_split": "10-yd burst", "vertical": "Vertical", "broad_jump": "Broad jump",
         "combine_height": "Height", "combine_weight": "Weight", "arm_length": "Arm length", "hand_size": "Hand size",
         "f40_top": "Top speed (trk)", "f40_acc": "Peak accel (trk)", "f40_s1": "Speed at 1 s (trk)",
         "f40_t90": "Quick to top speed (trk)", "f40_hold": "Holds speed to finish (trk)",
         "drill_acc": "Drill accel (trk)", "drill_turn": "Drill turn rate (trk)", "drill_top": "Drill speed (trk)"}


def feats(group: str, fset: str) -> list[str]:
    allf = STD + TRK40 + DRILL_OK[group]
    if fset == "ALL":
        return allf
    if fset == "SIZEADJ":
        return [f for f in allf if f not in ("combine_height", "combine_weight")]
    if fset == "STD":
        return STD
    if fset == "TRK":
        return TRK40 + DRILL_OK[group]
    raise ValueError(fset)


def prepare(df: pd.DataFrame, group: str, fset: str, min_obs: float = 0.6, fit_on: pd.Series | None = None,
            complete_only: bool = False):
    """Return (ids, X standardised+imputed, feature names, fitted transform dict). Fit on rows where fit_on is True."""
    f = feats(group, fset)
    d = df[["nfl_id", "combine_height", "combine_weight"] + [c for c in f if c not in ("combine_height", "combine_weight")]].copy()
    for c in FLIP & set(f):
        d[c] = -d[c]
    keep = d[f].notna().mean(axis=1) >= (1.0 if complete_only else min_obs)
    d = d[keep].reset_index(drop=True)
    fit = np.ones(len(d), bool) if fit_on is None else fit_on[keep].to_numpy()
    if fset == "SIZEADJ":   # residualise each feature on height + weight (fit rows, observed values only)
        for c in f:
            m = d[c].notna() & fit
            lr = LinearRegression().fit(d.loc[m, ["combine_height", "combine_weight"]], d.loc[m, c])
            ok = d[c].notna()
            d.loc[ok, c] = d.loc[ok, c] - lr.predict(d.loc[ok, ["combine_height", "combine_weight"]])
    A = d[f].to_numpy(float)
    mu, sd = np.nanmean(A[fit], 0), np.nanstd(A[fit], 0); sd[sd == 0] = 1
    Z = (A - mu) / sd
    if np.isnan(Z).any():
        imp = IterativeImputer(estimator=BayesianRidge(), max_iter=10, random_state=SEED).fit(Z[fit])
        Z = imp.transform(Z)
    return d.nfl_id.to_numpy(), Z, f


def fit_cluster(X, method: str, k: int | None, seed: int = SEED, n_init: int = 50):
    if method == "kmeans":
        m = KMeans(k, n_init=n_init, random_state=seed).fit(X); return m.labels_, m
    if method == "gmm":
        m = GaussianMixture(k, covariance_type="diag", n_init=min(n_init, 10), random_state=seed).fit(X); return m.predict(X), m
    if method == "ward":
        lab = AgglomerativeClustering(k, linkage="ward").fit_predict(X); return lab, None
    if method == "hdbscan":
        mcs = max(5, len(X) // 10)
        lab = HDBSCAN(min_cluster_size=mcs).fit_predict(X); return lab, None
    raise ValueError(method)


def centroids(X, lab):
    ks = sorted(k for k in np.unique(lab) if k >= 0)
    return np.vstack([X[lab == k].mean(0) for k in ks])


def assign(X_new, C):
    return np.argmin(((X_new[:, None, :] - C[None]) ** 2).sum(2), 1)


def gap_stat(X, k, B=20, seed=SEED):
    rng = np.random.default_rng(seed)
    def W(Y, kk):
        return KMeans(kk, n_init=10, random_state=seed).fit(Y).inertia_
    lo, hi = X.min(0), X.max(0)
    ref = [np.log(W(rng.uniform(lo, hi, X.shape), k)) for _ in range(B)]
    return float(np.mean(ref) - np.log(W(X, k))), float(np.std(ref) * np.sqrt(1 + 1 / B))


def stability(X, method, k, ref_lab, B=200, seed=SEED):
    """Bootstrap ARI (vs reference on resampled unique players) and Hennig per-cluster Jaccard."""
    rng = np.random.default_rng(seed); n = len(X)
    aris, jac = [], {c: [] for c in np.unique(ref_lab) if c >= 0}
    for b in range(B):
        idx = np.unique(rng.integers(0, n, n))
        lab_b, _ = fit_cluster(X[idx], method, k, seed=seed + b + 1, n_init=10)
        ref = ref_lab[idx]
        aris.append(adjusted_rand_score(ref, lab_b))
        for c in jac:
            A = set(np.where(ref == c)[0])
            if not A:
                continue
            best = 0.0
            for c2 in np.unique(lab_b):
                if c2 < 0:
                    continue
                Bs = set(np.where(lab_b == c2)[0])
                best = max(best, len(A & Bs) / len(A | Bs))
            jac[c].append(best)
    return float(np.median(aris)), {int(c): float(np.mean(v)) for c, v in jac.items()}


def sil(X, lab):
    m = lab >= 0
    return float(silhouette_score(X[m], lab[m])) if len(np.unique(lab[m])) > 1 else np.nan
