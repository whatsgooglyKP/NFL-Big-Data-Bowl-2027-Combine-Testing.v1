#!/usr/bin/env python3
"""Step 1a: Combine-side feature sets per position group. NO game outcome is read here.

(a) standard  : official Combine results (40, 10-yd, vertical, broad, 3-cone, shuttle, bench, height, weight, arm, hand)
(b) tracking  : 10 Hz Combine movement features
                 - 40-yard dash: top speed, peak accel, speed 1.0 s after start, time to 90% of top speed,
                   tracked 10/20-yd split, finish hold (speed at 40 yd / top speed)
                 - position skill drills (WR / TE / DB / DL drills): per drill, peak speed, peak accel,
                   peak braking, speed kept through cuts, peak turn rate, duration; z-scored within drill
                   and averaged across that group's drills (tolerant of missing drills)
(c) size-adj. : (a)+(b) residualised on height and weight within group (built in u02)
Writes cache/combine_features.parquet (per player, gitignored) and out/feature_missingness.csv,
out/drill_reliability.csv (aggregates only).
"""
from __future__ import annotations
import numpy as np, pandas as pd
from common import DATA, CACHE, OUT, players, assert_no_draft

SKILL = {"WR": "SKILL_DRILLS_WR", "TE": "SKILL_DRILLS_TE", "DB": "SKILL_DRILLS_DB", "DL": "SKILL_DRILLS_DL"}
NAME_FIX = {"LINE": "LINE_DRILL", "SPEED_OUT_LEFT": "SPEED_OUT_ROUTE_LEFT", "OVER_THE_SHOULDER_ADJUST": "OVER_SHOULDER_ADJUST",
            "SHORT_ZONE_BREAK_FLAT_WHEEL": "SHORT_ZONE_BREAKS", "SHORT_ZONE_BREAK_FORWARD": "SHORT_ZONE_BREAKS",
            "SHORT_ZONE_BREAK_INSIDE": "SHORT_ZONE_BREAKS"}
STD = ["forty", "ten_yd_split", "vertical", "broad_jump", "three_cone", "short_shuttle", "bench_reps",
       "combine_height", "combine_weight", "arm_length", "hand_size"]
DRILL_FEATS = ["top", "acc", "dec", "keep", "turn", "dur"]


def attempt_features(g: pd.DataFrame) -> dict:
    g = g.sort_values("time")
    t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
    s = g.s.to_numpy(float); x = g.x.to_numpy(float); y = g.y.to_numpy(float); d = g.dir.to_numpy(float)
    if len(s) < 8:
        return {}
    mv = np.where(s > 0.5)[0]
    if len(mv) < 5:
        return {}
    i0, i1 = mv[0], mv[-1]
    dt = np.diff(t); dt[dt <= 0] = np.nan
    a = np.diff(s) / dt
    a = pd.Series(a).rolling(3, center=True, min_periods=1).mean().to_numpy().copy()
    a[np.abs(a) > 12] = np.nan
    a = a[i0:i1]
    top = np.nanmax(s[i0:i1 + 1]); itop = i0 + int(np.nanargmax(s[i0:i1 + 1]))
    t90 = t[i0 + np.argmax(s[i0:] >= 0.9 * top)] - t[i0]
    j1 = np.searchsorted(t, t[i0] + 1.0)
    s1 = s[j1] if j1 < len(s) else np.nan
    hi = np.where(s >= 0.8 * top)[0]
    keep = np.nanmin(s[hi[0]:hi[-1] + 1]) / top if len(hi) else np.nan
    dd = (np.diff(d) + 180) % 360 - 180
    tr = np.abs(dd) / dt
    tr = pd.Series(tr).rolling(3, center=True, min_periods=1).median().to_numpy().copy()
    ok = (s[1:] > 1.5); ok[:i0] = False; ok[i1:] = False
    turn = np.nanpercentile(tr[ok], 95) if ok.sum() >= 3 else np.nan
    step = np.r_[0, np.hypot(np.diff(x), np.diff(y))]; step[:i0] = 0
    cum = np.cumsum(step)
    def t_at(dist):
        k = np.argmax(cum >= dist)
        return t[k] - t[i0] if cum[-1] >= dist else np.nan
    s40 = s[np.argmax(cum >= 40)] if cum[-1] >= 40 else np.nan
    return dict(top=top, acc=np.nanmax(a) if np.isfinite(a).any() else np.nan,
                dec=-np.nanmin(a) if np.isfinite(a).any() else np.nan, keep=keep, turn=turn,
                dur=t[i1] - t[i0], t90=t90, s1=s1, t10=t_at(10), t20=t_at(20), t40=t_at(40),
                hold=s40 / top if np.isfinite(s40) else np.nan)


def main() -> None:
    pl = players()
    ct = pd.read_csv(DATA / "combine_tracking.csv",
                     usecols=["event_id", "nfl_id", "entity_type", "time", "drill_type", "drill_name", "attempt", "x", "y", "s", "dir"],
                     dtype={"x": "float32", "y": "float32", "s": "float32", "dir": "float32"})
    ct = ct[(ct.entity_type == "PLAYER") & ct.nfl_id.isin(pl.nfl_id)]
    ct["time"] = pd.to_datetime(ct.time, format="ISO8601")
    ct["drill_name"] = ct.drill_name.replace(NAME_FIX)
    rows = []
    for (eid, pid, dt_, dn), g in ct.groupby(["event_id", "nfl_id", "drill_type", "drill_name"], sort=False):
        f = attempt_features(g)
        if f:
            rows.append(dict(event_id=eid, nfl_id=pid, drill_type=dt_, drill_name=dn, **f))
    at = pd.DataFrame(rows).merge(pl[["nfl_id", "group"]], on="nfl_id")
    print("attempts", len(at))

    # 40-yard dash: fastest tracked 40 attempt (glitch guard: top speed 6-12.5 yd/s, t40 3.8-6.5 s)
    f40 = at[(at.drill_type == "FORTY_YARD_DASH") & at.top.between(6, 12.5) & at.t40.between(3.8, 6.5)]
    f40 = f40.sort_values("t40").drop_duplicates("nfl_id")
    f40 = f40[["nfl_id", "top", "acc", "s1", "t90", "t10", "t20", "hold"]].rename(columns=lambda c: c if c == "nfl_id" else f"f40_{c}")
    f40["f40_top"] *= 2.0455; f40["f40_s1"] *= 2.0455   # mph

    # skill drills: mean over attempts per player x drill, z within (group, drill), mean over drills
    comp, rel = [], []
    for grp, dtype in SKILL.items():
        sk = at[(at.group == grp) & (at.drill_type == dtype)]
        pd_ = sk.groupby(["nfl_id", "drill_name"])[DRILL_FEATS].mean().reset_index()
        n_grp = pl.group.eq(grp).sum()
        cover = pd_.groupby("drill_name").nfl_id.nunique()
        drills = cover[cover >= 0.4 * n_grp].index
        pd_ = pd_[pd_.drill_name.isin(drills)]
        z = pd_.copy()
        for f in DRILL_FEATS:
            z[f] = pd_.groupby("drill_name")[f].transform(lambda v: (v - v.mean()) / v.std())
        # reliability: mean pairwise correlation of the same feature across drills (player level)
        for f in DRILL_FEATS:
            w = z.pivot_table(index="nfl_id", columns="drill_name", values=f)
            c = w.corr(min_periods=20).to_numpy(); iu = np.triu_indices_from(c, 1)
            r = np.nanmean(c[iu]); k = w.shape[1]
            rel.append(dict(group=grp, feature=f"drill_{f}", n_drills=k, mean_inter_drill_r=r,
                            alpha_k=(k * r / (1 + (k - 1) * r)) if np.isfinite(r) else np.nan))
        m = z.groupby("nfl_id")[DRILL_FEATS].mean().add_prefix("drill_")
        m["drill_n"] = z.groupby("nfl_id").drill_name.nunique()
        comp.append(m.reset_index())
        print(grp, "drills used:", list(drills))
    comp = pd.concat(comp, ignore_index=True)

    cr = pd.read_csv(DATA / "combine_results.csv", usecols=["nfl_id"] + STD)
    df = pl.merge(cr.drop_duplicates("nfl_id"), on="nfl_id", how="left").merge(f40, on="nfl_id", how="left").merge(comp, on="nfl_id", how="left")
    assert_no_draft(df)
    df.to_parquet(CACHE / "combine_features.parquet", index=False)
    feats = STD + [c for c in df.columns if c.startswith(("f40_", "drill_")) and c != "drill_n"]
    miss = df.groupby("group")[feats].apply(lambda g: g.isna().mean()).T.round(3)
    miss.loc["n_players"] = df.groupby("group").size()
    miss.to_csv(OUT / "feature_missingness.csv")
    pd.DataFrame(rel).to_csv(OUT / "drill_reliability.csv", index=False)
    print(miss.to_string()); print(pd.DataFrame(rel).round(2).to_string())


if __name__ == "__main__":
    main()
