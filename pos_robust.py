"""Robust pass (robust.py defaults) for WR, TE and DB primary outcomes.

WR / TE : tracking route separation (mean over routes, snap-weighted sensitivity), WR also Sunday
          Speed and SSOE (official sample).
DB      : CB + S combined, role (CB vs S) control; tackle rate and TFL rate shrunk with
          beta-binomial, plus closing rate, tackle depth, PFR yards/target, PFR missed-tackle %.
Controls: draft year, role (DB), weight, height. No draft slot / pick / round is read (usecols only).
"""
from __future__ import annotations
import numpy as np, pandas as pd
import robust as R
from bdb_stats import OFFICIAL, TRACKING, load_combine
from dl_recheck import ROOT, OUT

TESTS = OFFICIAL + TRACKING + [("burst_0_100", "Burst Score (0-100)", +1)]
DB_TESTS = TESTS + [("c_decel", "Combine Brakes (DB drill peak decel)", +1), ("c_accel", "Combine Re-Burst (DB drill peak accel)", +1)]


PRIOR: list = []


def wr_te() -> pd.DataFrame:
    r = pd.read_csv(OUT / "route_cod_game_player.csv",
                    usecols=["nfl_id", "display_name", "draft_year", "pos_group", "sep_all_n", "sep_all_mean", "sep_brk_n", "sep_brk_mean", "n_route_plays"])
    r = r[r.pos_group.isin(["WR", "TE"])].copy()
    r.loc[r.sep_all_n < 30, "sep_all_mean"] = np.nan
    r.loc[r.sep_brk_n < 30, "sep_brk_mean"] = np.nan
    g = pd.read_csv(OUT / "gameplay_success_players.csv", usecols=["nfl_id", "ssoe_mph", "sunday_speed_mph"])
    c = load_combine(ROOT, set(r.nfl_id))
    d = r.merge(c, on="nfl_id", how="left").merge(g.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    R.assert_no_draft_slot(d)
    return d


def db() -> pd.DataFrame:
    d = pd.read_csv(OUT / "db_tackle_players.csv")
    R.assert_no_draft_slot(d)
    g = pd.read_csv(OUT / "gameplay_success_players.csv", usecols=["nfl_id", "ssoe_mph", "sunday_speed_mph"])
    d = d.merge(g.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    d["tackle_rate_raw"], d["tfl_rate_raw"] = d.tackle_rate, d.tfl_rate
    n = d.n_snaps.where(d.tackle_rate_raw.notna())
    d["tackle_rate"], info1 = R.eb_shrink(d, d.n_inv.where(n.notna()), n, by="role")
    n2 = d.n_snaps.where(d.tfl_rate_raw.notna())
    d["tfl_rate"], info2 = R.eb_shrink(d, d.n_tfl.where(n2.notna()), n2, by="role")
    PRIOR.append(pd.DataFrame([dict(outcome="tackle_rate", role=k, **v) for k, v in info1.items()] +
                                    [dict(outcome="tfl_rate", role=k, **v) for k, v in info2.items()]))
    return d


def main() -> None:
    w = wr_te()
    wr_out = [dict(col="sep_all_mean", label="Separation, all routes (yd, tracking)", sign=1, weight="sep_all_n"),
              dict(col="sep_brk_mean", label="Separation, break routes (yd, tracking)", sign=1, weight="sep_brk_n"),
              dict(col="sunday_speed_mph", label="Sunday Speed (mph, deep routes)", sign=1),
              dict(col="ssoe_mph", label="SSOE (mph over expected from the 40)", sign=1)]
    te_out = wr_out[:2]
    dd = db()
    db_out = [dict(col="tackle_rate", label="Tackle rate (shrunk)", sign=1, alt="tackle_rate_raw", weight="n_snaps"),
              dict(col="tfl_rate", label="TFL rate (shrunk)", sign=1, alt="tfl_rate_raw", weight="n_snaps"),
              dict(col="close_rate_mph", label="Closing rate to tackle spot (mph)", sign=1, weight="n_trk_tackles"),
              dict(col="tackle_depth", label="Tackle depth downfield (yd)", sign=0, weight="n_trk_tackles"),
              dict(col="pfr_yds_tgt", label="PFR yards / target allowed", sign=-1, weight="tgt"),
              dict(col="pfr_mtkl_pct", label="PFR missed-tackle %", sign=-1, weight="tackle_attempts"),
              dict(col="sunday_speed_mph", label="Sunday Speed (mph)", sign=1),
              dict(col="ssoe_mph", label="SSOE (mph)", sign=1)]
    tw = R.run_family([("WR", w[w.pos_group == "WR"], None)], TESTS, wr_out)
    tt = R.run_family([("TE", w[w.pos_group == "TE"], None)], TESTS, te_out)
    td = R.run_family([("DB", dd, "role")], DB_TESTS, db_out)
    t = pd.concat([tw, tt, td], ignore_index=True)
    t.to_csv(OUT / "pos_robust_tests.csv", index=False)
    PRIOR[0].to_csv(OUT / "db_robust_shrinkage.csv", index=False)
    keepw = [c for c in w.columns]
    w[keepw].to_csv(OUT / "wr_te_robust_players.csv", index=False)
    dd.to_csv(OUT / "db_robust_players.csv", index=False)
    print(PRIOR[0].round(3)); print(t.groupby("group").agg(cells=("p_perm", "size"), fdr05=("fdr", lambda s: int((s < .05).sum()))))
    print(t.groupby("group").verdict.value_counts())


if __name__ == "__main__":
    main()
