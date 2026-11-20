#!/usr/bin/env python3
"""Step 2b: are there real 'types', or is it one continuous cloud? (no outcomes)

For each group and feature set, compare k-means silhouette (k = 2..4) on the real data with 200 datasets drawn
from a single multivariate normal with the same n and the same correlation matrix (one blob, no types).
p = share of one-blob datasets with silhouette >= observed. Writes out/cluster_null.csv.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from common import CACHE, OUT, SEED, GROUPS
import pipe as P


def main(B: int = 200) -> None:
    cf = pd.read_parquet(CACHE / "combine_features.parquet"); rows = []
    rng = np.random.default_rng(SEED)
    for g in GROUPS:
        df = cf[cf.group == g].reset_index(drop=True)
        for fs in ["ALL", "SIZEADJ"]:
            _, X, _ = P.prepare(df, g, fs)
            C = np.cov(X, rowvar=False); n = len(X)
            for k in (2, 3, 4):
                obs = silhouette_score(X, KMeans(k, n_init=20, random_state=SEED).fit_predict(X))
                null = []
                for b in range(B):
                    Y = rng.multivariate_normal(np.zeros(X.shape[1]), C, n)
                    null.append(silhouette_score(Y, KMeans(k, n_init=5, random_state=b).fit_predict(Y)))
                null = np.array(null)
                rows.append(dict(group=g, fset=fs, n=n, k=k, sil_obs=obs, sil_null_median=np.median(null),
                                 sil_null_95=np.percentile(null, 95), p_one_blob=(1 + (null >= obs).sum()) / (B + 1)))
                print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT / "cluster_null.csv", index=False)


if __name__ == "__main__":
    main()
