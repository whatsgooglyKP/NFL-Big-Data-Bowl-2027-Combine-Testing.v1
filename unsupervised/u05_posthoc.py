#!/usr/bin/env python3
"""Step 5: POST HOC checks (not pre-registered; labelled post hoc in FINDINGS.md). BH within this family.

 1. Does WR PC3 add anything beyond Combine top speed (game speed) / vertical (break-route separation)?
 2. DL PC1 vs single tests for pressure rate (same sample, same controls).
 3. Is the tracked 'launch' (speed at 1 s, peak accel) a different trait from the official 10-yd split?
 4. WR deployment: does Combine size / speed predict slot share, deep-route share, short-route share?
 5. DB deployment: Combine PC1 vs man share / high-safety share / slot share, controlling CB vs S role.
Writes out/posthoc.csv (aggregate).
"""
from __future__ import annotations
import sys
import numpy as np, pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from common import CACHE, OUT, REPO, GROUPS, bh
import pipe as P
sys.path.insert(0, str(REPO))
import robust as R  # noqa: E402


def pcs(cf, g):
    df = cf[cf.group == g].reset_index(drop=True)
    ids, X, f = P.prepare(df, g, "ALL")
    pca = PCA().fit(X)
    return pd.DataFrame(pca.transform(X)[:, :3], index=ids, columns=["pc1", "pc2", "pc3"])


def prc(d, x, y, cont, role=False, B=True):
    d = d.dropna(subset=[x, y] + cont).reset_index(drop=True)
    yrd = pd.get_dummies(d.draft_year.astype(str), drop_first=True).to_numpy(float)
    D = yrd
    if role:
        D = np.column_stack([yrd, pd.get_dummies(d.role.astype(str), drop_first=True).to_numpy(float)])
    C = d[cont].to_numpy(float) if cont else None
    xv, yv = d[x].to_numpy(float), d[y].to_numpy(float)
    r = R.partial_rank_corr(xv, yv, C, D)
    lo, hi = R.boot_partial(xv, yv, C, D) if B else (np.nan, np.nan)
    return dict(n=len(d), rho=r, lo=lo, hi=hi, p=R.perm_partial(xv, yv, C, D))


def main():
    cf = pd.read_parquet(CACHE / "combine_features.parquet"); gf = pd.read_parquet(CACHE / "game_features.parquet")
    rows = []
    SZ = ["combine_weight", "combine_height"]
    # 1
    w = cf[cf.group == "WR"].join(pcs(cf, "WR"), on="nfl_id").merge(gf.drop(columns=["group", "role", "draft_year"]), on="nfl_id")
    rows.append(dict(check="1 WR PC3 -> game speed, also holding Combine top speed fixed", **prc(w, "pc3", "sunday_speed_mph", SZ + ["f40_top"])))
    rows.append(dict(check="1 WR PC3 -> game speed, also holding the official 40 fixed", **prc(w, "pc3", "sunday_speed_mph", SZ + ["forty"])))
    rows.append(dict(check="1 WR PC3 -> break-route separation, also holding vertical fixed", **prc(w, "pc3", "break_y", SZ + ["vertical"])))
    rows.append(dict(check="1 WR Combine top speed -> game speed (same controls, reference)", **prc(w, "f40_top", "sunday_speed_mph", SZ)))
    rows.append(dict(check="1 WR vertical -> break-route separation (reference)", **prc(w, "vertical", "break_y", SZ)))
    # 2
    dl = cf[cf.group == "DL"].join(pcs(cf, "DL"), on="nfl_id").merge(gf.drop(columns=["group", "role", "draft_year"]), on="nfl_id")
    dl = dl.dropna(subset=["pc1", "forty", "ten_yd_split", "vertical", "broad_jump", "pressure_rate"])
    for x, lab in [("pc1", "DL PC1 (all-round athleticism)"), ("forty", "DL 40 (lower = faster; sign flipped below)"),
                   ("ten_yd_split", "DL 10-yd split (sign flipped)"), ("vertical", "DL vertical"), ("broad_jump", "DL broad jump")]:
        dd = dl.copy()
        if x in ("forty", "ten_yd_split"):
            dd[x] = -dd[x]
        rows.append(dict(check=f"2 {lab} -> pressure rate, size+role controlled, same sample", **prc(dd, x, "pressure_rate", SZ, role=True)))
    # 3
    for g in GROUPS:
        d = cf[cf.group == g].copy(); d["ten_fast"] = -d.ten_yd_split; d["forty_fast"] = -d.forty
        for x in ("f40_s1", "f40_acc"):
            for y in ("ten_fast", "forty_fast", "f40_top"):
                s = d[[x, y]].dropna()
                r, p = stats.spearmanr(s[x], s[y])
                rows.append(dict(check=f"3 {g} {x} vs {y} (plain Spearman)", n=len(s), rho=r, lo=np.nan, hi=np.nan, p=p))
    # 4
    for x, xl in [("combine_weight", "weight"), ("combine_height", "height"), ("forty_fast", "40 speed")]:
        w["forty_fast"] = -w.forty
        for y in ("slot_share", "deep_route_share", "short_route_share"):
            cont = [c for c in SZ if c != x] if x != "forty_fast" else SZ
            rows.append(dict(check=f"4 WR {xl} -> {y} (year + other size controlled)", **prc(w, x, y, cont)))
    # 5
    db = cf[cf.group == "DB"].join(pcs(cf, "DB"), on="nfl_id").merge(gf.drop(columns=["group", "role", "draft_year"]), on="nfl_id")
    for y in ("man_share", "high_safety_share", "slot_share"):
        rows.append(dict(check=f"5 DB PC1 -> {y} (year + CB/S role controlled)", **prc(db, "pc1", y, [], role=True)))
        rows.append(dict(check=f"5 DB PC1 -> {y} (year + role + size controlled)", **prc(db, "pc1", y, SZ, role=True)))
    t = pd.DataFrame(rows); t["q_posthoc"] = bh(t.p)
    t.to_csv(OUT / "posthoc.csv", index=False)
    pd.set_option("display.width", 250); print(t.round(3).to_string())


if __name__ == "__main__":
    main()
