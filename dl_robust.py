"""RUN 3 - DL re-run with the robust defaults (robust.py): size control, empirical-Bayes
shrinkage of rate outcomes, leave-one-draft-class-out validation, bootstrap CI,
permutation p, BH-FDR.  Reads the saved player table out/dl_recheck_players.csv (built by
dl_recheck.py from Kaggle tracking), so it needs no raw Kaggle data.
No draft slot / round / pick is used (asserted).
"""
from __future__ import annotations
import sys
import numpy as np, pandas as pd
import robust as R
from dl_recheck import OUT, TESTS, OUTCOMES, FIGS

RATES = {  # outcome -> (count column builder, exposure column)
    "pressure_rate": ("n_rush_plays", "pressure_rate"),
    "sack_rate": ("n_rush_plays", "sack_rate"),
    "tfl_rate": ("n_snaps", "tfl_rate"),
    "run_stop_rate": ("n_run", "run_stop_rate"),
    "run_stop_near_rate": ("n_run", "run_stop_near_rate"),
}
# Fix of the old label: this is speed 1.0 s after the snap from tracking, not the NFL/NGS get-off.
OUTCOME_ROBUST = [(c, ("1-sec burst speed (tracking, mph)" if c == "speed_1s_mph" else l), s) for c, l, s in OUTCOMES]
OUTCOME_ROBUST.insert(3, ("player_get_off", "NFL/NGS get-off time (s, lower = faster)", -1))


def prepare() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pd.read_csv(OUT / "dl_recheck_players.csv")
    R.assert_no_draft_slot(d)
    prior = []
    for oc, (nc, _) in RATES.items():
        n = d[nc].where(d[oc].notna())
        k = (d[oc] * n).round()
        d[oc + "_raw"] = d[oc]
        d[oc], info = R.eb_shrink(d, k, n, by="subtype")
        for g, v in info.items():
            prior.append(dict(outcome=oc, subtype=g, **v))
    return d, pd.DataFrame(prior)


def build_outcomes():
    out = []
    for c, l, s in OUTCOME_ROBUST:
        o = dict(col=c, label=l, sign=s)
        if c in RATES:
            o.update(alt=c + "_raw", weight=RATES[c][0])
        out.append(o)
    return out


PROD = ["pressure_rate", "sack_rate", "tfl_rate", "run_stop_rate", "run_stop_near_rate"]


def post(t: pd.DataFrame) -> pd.DataFrame:
    """FDR families + verdict, then whether the pooled DL sign also holds inside Edge and Interior."""
    t = R.finalize(t, PROD)
    k = ["test", "outcome"]
    e = t[t.group == "Edge"].set_index(k).rho_size; i = t[t.group == "Interior"].set_index(k).rho_size
    dl = t.group == "DL"
    idx = pd.MultiIndex.from_frame(t.loc[dl, k])
    t["sign_edge"] = np.nan; t["sign_interior"] = np.nan
    t.loc[dl, "sign_edge"] = np.sign(e.reindex(idx).to_numpy())
    t.loc[dl, "sign_interior"] = np.sign(i.reindex(idx).to_numpy())
    return t


def main() -> None:
    if "--reuse" in sys.argv:
        t = post(pd.read_csv(OUT / "dl_robust_tests.csv"))
        t.to_csv(OUT / "dl_robust_tests.csv", index=False)
        print(t.groupby("group").verdict.value_counts()); return
    d, prior = prepare()
    prior.to_csv(OUT / "dl_robust_shrinkage.csv", index=False)
    print(prior.round(3).to_string(index=False))
    groups = [("DL", d, "subtype"), ("Edge", d[d.subtype == "Edge"], None), ("Interior", d[d.subtype == "Interior"], None)]
    t = post(R.run_family(groups, TESTS, build_outcomes(), prod_outcomes=PROD))
    t.to_csv(OUT / "dl_robust_tests.csv", index=False)
    keep = [c for c in d.columns if c in ("nfl_id", "display_name", "draft_year", "nfl_position", "subtype", "college_name")
            or c in [x for x, *_ in TESTS] or c in [x for x, *_ in OUTCOME_ROBUST] or c.endswith("_raw") or c.startswith("n_")]
    d[keep].to_csv(OUT / "dl_robust_players.csv", index=False)
    chain(d).to_csv(OUT / "dl_robust_chain.csv", index=False)
    print(t.groupby("group").agg(cells=("p_perm", "size"), fdr05=("fdr", lambda s: int((s < 0.05).sum()))))


def chain(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for x, y in [("ten_yd_split", "speed_1s_mph"), ("ten_yd_split", "pressure_rate"), ("speed_1s_mph", "pressure_rate"),
                 ("ten_yd_split", "player_get_off"), ("player_get_off", "pressure_rate"), ("player_get_off", "speed_1s_mph")]:
        r = R.test_pair(d, x, y, role_col="subtype", do_loso=False)
        rows.append(dict(x=x, y=y, **r))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()


ROW_LABELS = {"combine_weight": "Weight  ‡ (beyond height)", "combine_height": "Height  ‡ (beyond weight)"}


def fig19_robust(path=None):
    """Figure 19 with the robust defaults: size/role/year-controlled rank partial correlation on shrunk rates."""
    from dl_recheck import fig19
    t = pd.read_csv(OUT / "dl_robust_tests.csv")
    d = pd.read_csv(OUT / "dl_robust_players.csv")
    p = t[t.group == "DL"].copy()
    p["control"] = "year"
    p["rho_orig"] = p.rho_size
    p["rho"] = p.rho_size
    p["p"] = p.p_perm
    p["mark"] = np.where(p.verdict.isin(["LEAN", "SURVIVES"]), "◆", np.where(p.p_perm < 0.05, "*", ""))
    p.loc[p.fdr < 0.05, "mark"] = "**"
    subtitle = ("Rank partial correlation controlling draft year, Edge vs Interior, weight and height (‡ = the other size measure only); rate outcomes shrunk "
                "toward the role mean (beta-binomial).\nTimed drills (†) and lower-is-better outcomes are sign-flipped so red = better athlete goes with better result.   "
                "◆ = permutation p < 0.05, CI excludes 0, same sign unshrunk, and improves leave-one-class-out prediction.\n"
                "* = permutation p < 0.05 only.   ** = BH-FDR < 0.05 over all 273 cells (none of the athletic tests clear it).")
    footer = ("Sample: 2023–2025 rookie DL, REG snaps that stood, lined up EDGE/INTERIOR_LINE.  Rates ≥100 snaps (run rates ≥50 run snaps); penetration ≥50 tracked snaps; time to pressure ≥5 pressures.\n"
              "No draft slot, pick or round used.  † Timed drill (lower raw time = faster) — sign-flipped in the heat map only.  "
              "\nScatter panels plot the shrunk rate; the 3-cone axis is raw seconds (← faster).  “1-sec burst speed” = tracked speed 1.0 s after the snap (not the NGS get-off).")
    return fig19(t=p, d=d, path=path or FIGS / "fig19_dl_recheck.png", subtitle=subtitle,
                 rho_desc="size-controlled ρ", row_labels=ROW_LABELS,
                 scatter_titles=("3-cone vs pressure rate (34 players)", "Burst Score vs TFL rate"),
                 ylabels=("Pressure rate (shrunk)", "TFL per snap (shrunk)"), footer=footer, fdr_text="FDR (all cells)")
