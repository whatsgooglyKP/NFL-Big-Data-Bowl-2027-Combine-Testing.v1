"""Part B (11/2026): re-test the WR break-route lead, pre-declared in METRICS.md section 8.

Reads data/player_play.csv + data/games.csv (route_ran, separation_at_pass_forward,
team_coverage_man_zone) and out/wr_te_robust_players.csv (WR Combine tests, size, draft year).
No draft slot / pick / round is read. Uses robust.py defaults for every cell.
Writes out/wr_route_lead_{cells,contrasts,players,plays_summary}.csv.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from scipy import stats
import robust as R
from dl_recheck import ROOT, OUT

SEED = R.SEED
BREAK = ["OUT", "IN", "HITCH", "SLANT"]
VERT = ["GO", "POST", "CORNER"]
MIN_ROUTES, MIN_SCREEN = 20, 10
B, P = R.N_BOOT, R.N_PERM
TESTS = {  # col -> (label, sign so that positive = better test)
    "three_cone": ("3-cone", -1), "short_shuttle": ("Short shuttle", -1), "ten_yd_split": ("Official 10-yard", -1),
    "vertical": ("Vertical jump", +1), "burst_0_100": ("Burst Score", +1), "combine_weight": ("Weight", +1),
}


# ------------------------------------------------------------------ data
def load_plays() -> pd.DataFrame:
    pp = pd.read_csv(ROOT / "data" / "player_play.csv",
                     usecols=["game_id", "play_id", "nfl_id", "route_ran", "separation_at_pass_forward",
                              "team_coverage_man_zone", "play_nullified_by_penalty"])
    gm = pd.read_csv(ROOT / "data" / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(gm, on="game_id", how="left")
    pp = pp[(pp.season_type == "REG") & pp.route_ran.notna() & pp.separation_at_pass_forward.notna()
            & pp.team_coverage_man_zone.isin(["MAN_COVERAGE", "ZONE_COVERAGE"])
            & (pp.play_nullified_by_penalty.astype(str).str.upper().isin(["N", "FALSE", "0"]))].copy()
    pp["cov"] = pp.team_coverage_man_zone.map({"MAN_COVERAGE": "man", "ZONE_COVERAGE": "zone"})
    return pp


def build_players() -> tuple[pd.DataFrame, pd.DataFrame]:
    w = pd.read_csv(OUT / "wr_te_robust_players.csv")
    w = w[w.pos_group == "WR"].copy()
    R.assert_no_draft_slot(w)
    pp = load_plays()
    pp = pp[pp.nfl_id.isin(w.nfl_id)].copy()
    # route-type x coverage mean over all WR plays: remove what the route / coverage itself gives.
    pp["res"] = pp.separation_at_pass_forward - pp.groupby(["route_ran", "cov"]).separation_at_pass_forward.transform("mean")
    pp["fam"] = np.where(pp.route_ran.isin(BREAK), "break", np.where(pp.route_ran.isin(VERT), "vertical",
                 np.where(pp.route_ran == "CROSS", "crosser", np.where(pp.route_ran == "SCREEN", "screen", "other"))))
    splits = {"break": pp.fam == "break", "vertical": pp.fam == "vertical", "crosser": pp.fam == "crosser",
              "screen": pp.fam == "screen", "man_all": pp["cov"] == "man", "zone_all": pp["cov"] == "zone",
              "man_break": (pp["cov"] == "man") & (pp.fam == "break"), "zone_break": (pp["cov"] == "zone") & (pp.fam == "break")}
    out = w[["nfl_id", "display_name", "draft_year", "combine_weight", "combine_height", "three_cone", "short_shuttle",
             "ten_yd_split", "vertical", "burst_0_100"]].copy().set_index("nfl_id")
    info = []
    for s, m in splits.items():
        sub = pp[m]
        g = sub.groupby("nfl_id").res
        n, mean = g.size(), g.mean()
        var_i = g.var(ddof=1)
        mn = MIN_SCREEN if s == "screen" else MIN_ROUTES
        ok = n >= mn
        # pooled within-player variance; method-of-moments tau^2 (floored at 0)
        sig2 = float(((n[ok] - 1) * var_i[ok]).sum() / (n[ok] - 1).sum())
        mu = float(mean[ok].mean())
        tau2 = max(float(mean[ok].var(ddof=1)) - float((sig2 / n[ok]).mean()), 0.0)
        wgt = tau2 / (tau2 + sig2 / n)
        shr = mu + wgt * (mean - mu)
        out[f"{s}_n"] = n.reindex(out.index)
        out[f"{s}_raw"] = mean.where(ok).reindex(out.index)
        out[f"{s}_y"] = shr.where(ok).reindex(out.index)
        info.append(dict(split=s, n_players=int(ok.sum()), median_routes=float(n[ok].median()), min_routes=mn,
                         sigma2_within=sig2, tau2_between=tau2, mean_shrink_weight=float(wgt[ok].mean()),
                         reliability_median=float(wgt[ok].median())))
    out = out.reset_index()
    return out, pd.DataFrame(info)


# ------------------------------------------------------------------ paired contrast
def _design_parts(s: pd.DataFrame, test: str, size_cols):
    ctrl = [c for c in size_cols if c != test]
    C = s[ctrl].to_numpy(float) if ctrl else None
    D = R.dummies_from(s, ["draft_year"])
    return C, D


def _pcorr_pair(x, a, b, C, D):
    return R.partial_rank_corr(x, a, C, D), R.partial_rank_corr(x, b, C, D)


def contrast(df: pd.DataFrame, test: str, sign: int, ya: str, yb: str, label: str, size_cols=R.SIZE,
             seed=SEED) -> dict:
    """rho(test, ya) - rho(test, yb) on players with both outcomes; paired bootstrap CI + within-player swap permutation."""
    s = df[[test, ya, yb, "draft_year"] + [c for c in size_cols]].dropna().reset_index(drop=True)
    n = len(s)
    out = dict(contrast=label, test=test, n=n, rho_a=np.nan, rho_b=np.nan, diff=np.nan, lo=np.nan, hi=np.nan, p_swap=np.nan)
    if n < R.MIN_N:
        return out
    x = s[test].to_numpy(float) * sign
    C, D = _design_parts(s, test, size_cols)
    a, b = s[ya].to_numpy(float), s[yb].to_numpy(float)
    ra, rb = _pcorr_pair(x, a, b, C, D)
    out.update(rho_a=ra, rho_b=rb, diff=ra - rb)
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        Ci = None if C is None else C[i]; Di = None if D is None else D[i]
        ra_, rb_ = _pcorr_pair(x[i], a[i], b[i], Ci, Di)
        if np.isfinite(ra_) and np.isfinite(rb_):
            d.append(ra_ - rb_)
    out["lo"], out["hi"] = np.percentile(d, [2.5, 97.5])
    # swap permutation: standardise control-residualised rank outcomes, swap within player at random
    rc = [] if C is None else [R._rank(C[:, j]) for j in range(C.shape[1])]
    Z = R._design(n, rc, D)
    ex = R._resid(R._rank(x), Z)
    za = R._resid(R._rank(a), Z); zb = R._resid(R._rank(b), Z)
    za = (za - za.mean()) / za.std(); zb = (zb - zb.mean()) / zb.std()
    obs = R._pearson(ex, za) - R._pearson(ex, zb)
    sw = rng.random((P, n)) < 0.5
    A = np.where(sw, zb, za); Bm = np.where(sw, za, zb)
    def corr(M):
        Mc = M - M.mean(1, keepdims=True); xc = ex - ex.mean()
        return (Mc @ xc) / np.sqrt((Mc ** 2).sum(1) * (xc ** 2).sum())
    perm = corr(A) - corr(Bm)
    out["p_swap"] = float((1 + np.sum(np.abs(perm) >= abs(obs) - 1e-12)) / (P + 1))
    return out


def cells(df: pd.DataFrame, spec: list[tuple[str, str, str]], group: str, size_cols=R.SIZE) -> pd.DataFrame:
    rows = []
    for test, split, hyp in spec:
        d = df.copy(); sign = TESTS[test][1]
        d[test] = d[test] * sign
        r = R.test_pair(d, test, f"{split}_y", year_col="draft_year", size_cols=size_cols,
                        weight_col=f"{split}_n", alt_outcome=f"{split}_raw")
        rows.append(dict(group=group, hyp=hyp, test=test, test_label=TESTS[test][0], split=split, outcome=f"{split}_y",
                         outcome_label=f"{split} separation over route/coverage mean (EB)", **r))
        print(f"  {hyp} {test:14s} {split:10s} n={r['n']:3d} rho={r['rho_size']:+.2f} p={r['p_perm']:.3f}", flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    d, info = build_players()
    info.to_csv(OUT / "wr_route_lead_plays_summary.csv", index=False)
    d.to_csv(OUT / "wr_route_lead_players.csv", index=False)
    print(info.round(3).to_string())
    primary = []
    for t in ["three_cone", "short_shuttle"]:
        for s in ["break", "vertical"]:
            primary.append((t, s, "H1"))
    for t in ["vertical", "burst_0_100"]:
        for s in ["break", "vertical"]:
            primary.append((t, s, "H2" if s == "break" else "H2-ref"))
    for t in ["three_cone", "short_shuttle", "ten_yd_split"]:
        for s in ["man_all", "zone_all"]:
            primary.append((t, s, "H3"))
    c1 = cells(d, primary, "primary")
    # BH across the 14 primary cells, then the section-7 verdict
    c1["fdr"] = R.bh(c1.p_perm); c1["fdr_param"] = R.bh(c1.p_param)
    c1["verdict"] = c1.apply(R.verdict, axis=1)
    # S1: weight (test) -> control draft year + height only
    sec = [("combine_weight", s, "S1") for s in ["screen", "crosser", "break", "vertical"]]
    c2 = cells(d, sec, "S1", size_cols=["combine_height"])
    c2["fdr"] = R.bh(c2.p_perm); c2["fdr_param"] = R.bh(c2.p_param)
    # sensitivity for H3: man vs zone on break routes only
    sens = [(t, s, "H3-brk") for t in ["three_cone", "short_shuttle", "ten_yd_split"] for s in ["man_break", "zone_break"]]
    c3 = cells(d, sens, "sens"); c3["fdr"] = R.bh(c3.p_perm)
    cells_all = pd.concat([c1, c2, c3], ignore_index=True)
    cells_all.to_csv(OUT / "wr_route_lead_cells.csv", index=False)

    # formal contrasts
    rows = []
    for t in ["three_cone", "short_shuttle"]:
        rows.append(dict(hyp="H1", **contrast(d, t, TESTS[t][1], "break_y", "vertical_y", "break - vertical")))
    for t in ["three_cone", "short_shuttle", "ten_yd_split"]:
        rows.append(dict(hyp="H3", **contrast(d, t, TESTS[t][1], "man_all_y", "zone_all_y", "man - zone")))
    for t in ["three_cone", "short_shuttle", "ten_yd_split"]:
        rows.append(dict(hyp="H3-brk", **contrast(d, t, TESTS[t][1], "man_break_y", "zone_break_y", "man - zone (break routes)")))
    for t in ["vertical", "burst_0_100"]:  # context for H2, not in the BH family
        rows.append(dict(hyp="H2-ctx", **contrast(d, t, TESTS[t][1], "break_y", "vertical_y", "break - vertical")))
    for s in ["screen", "crosser"]:
        rows.append(dict(hyp="S1", **contrast(d, "combine_weight", 1, f"{s}_y", "vertical_y", f"{s} - vertical",
                                               size_cols=["combine_height"])))
    ct = pd.DataFrame(rows)
    m = ct.hyp.isin(["H1", "H3"])
    ct["q_bh5"] = np.nan; ct.loc[m, "q_bh5"] = R.bh(ct.loc[m, "p_swap"]).to_numpy()

    def cv(r):
        if r.hyp not in ("H1", "H3"):
            return ""
        if not np.isfinite(r["diff"]):
            return ""
        if r["diff"] <= 0 and (r.hi < 0 and r.p_swap < 0.05):
            return "REVERSED"
        ok = r["diff"] > 0 and r.lo > 0 and r.p_swap < 0.05
        if ok and r.q_bh5 < 0.05:
            return "SURVIVES"
        if ok:
            return "LEAN"
        return "NOT SUPPORTED"
    ct["verdict"] = ct.apply(cv, axis=1)
    ct.to_csv(OUT / "wr_route_lead_contrasts.csv", index=False)
    pd.set_option("display.width", 220)
    print(cells_all[["hyp", "test", "split", "n", "rho_raw", "rho_size", "lo", "hi", "p_perm", "fdr", "loso_dr2", "loso_p", "verdict"]].round(3).to_string())
    print(ct.round(3).to_string())


if __name__ == "__main__":
    main()
