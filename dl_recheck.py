"""RUN 2 - DL re-check: every Combine measure vs wider DL outcomes.

DL = DE + DT + NT + OLB (one headline group); Edge (DE, OLB) vs Interior (DT, NT)
breakouts are secondary. Same stats as db_tackling.py: Spearman controlled for
draft year, 2,000-player bootstrap 95% CI, BH-FDR across the pooled family,
plus a year x subtype sensitivity. The known chain (official 10-yard ->
Sunday get-off -> pressure) is reproduced as the reference.
Draft slot / round is never loaded into the analysis table.

Needs out/cache/dl_snap_frames.parquet and tackle_window_frames.parquet (track_extract.py).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from bdb_stats import (OFFICIAL, TRACKING, spearman_ctrl, bh, split_half,
                       los_x, dir_sign, load_combine, fmt_p, _demean)

ROOT = Path(__file__).resolve().parent
DATA, OUT, FIGS, CACHE = ROOT / "data", ROOT / "out", ROOT / "out" / "figs", ROOT / "out" / "cache"
DL_POS = {"DE", "DT", "NT", "OLB"}
EDGE_POS = {"DE", "OLB"}
ON_LINE = {"EDGE", "INTERIOR_LINE"}
MIN_SNAPS, MIN_RUN, MIN_TRK, MIN_PRESS, MIN_RUN_TK = 100, 50, 50, 5, 8
KEY = ["game_id", "play_id", "nfl_id"]

TESTS = OFFICIAL + TRACKING + [
    ("tc_peak_decel_mag", "3-cone Brakes (tracked peak decel)", +1),
    ("tc_peak_accel", "3-cone Re-Burst (tracked peak accel)", +1),
    ("ss_peak_decel_mag", "Shuttle Brakes (tracked peak decel)", +1),
    ("ss_peak_accel", "Shuttle Re-Burst (tracked peak accel)", +1),
    ("burst_0_100", "Burst Score (0-100)", +1),
]
OUTCOMES = [
    ("pressure_rate", "Pressure rate (reference)", +1),
    ("sack_rate", "Sack rate (reference)", +1),
    ("speed_1s_mph", "Sunday get-off: speed at 1.0 s (reference)", +1),
    ("ttp_median", "Time to pressure, median (s)", -1),
    ("tfl_rate", "TFL per snap", +1),
    ("run_stop_rate", "Run stops per run snap", +1),
    ("run_stop_near_rate", "Run tackles at ≤2 yd per run snap", +1),
    ("run_tackle_depth", "Run-tackle depth past LOS (yd, tracking)", -1),
    ("pen_max_2s", "Penetration, max in first 2 s (yd)", +1),
    ("pen_2s", "Penetration at 2.0 s (yd)", +1),
    ("pen_run_2s", "Penetration at 2.0 s, run plays (yd)", +1),
    ("pen_pass_2s", "Penetration at 2.0 s, pass plays (yd)", +1),
]
OUT_LABEL = {c: l for c, l, _ in OUTCOMES}
TEST_LABEL = {c: l for c, l, _ in TESTS}


def players() -> pd.DataFrame:
    pl = pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "display_name", "draft_year", "nfl_position", "college_name"])
    pl = pl[pl.nfl_position.isin(DL_POS)].copy()
    pl["subtype"] = np.where(pl.nfl_position.isin(EDGE_POS), "Edge", "Interior")
    return pl


def play_table(ids) -> pd.DataFrame:
    cols = KEY + ["team_abbr", "possession_team", "play_nullified_by_penalty", "pass_result", "down", "yards_to_go",
                  "yards_gained", "yardline_side", "yardline_number", "play_direction", "lined_up_position",
                  "tackle", "assist", "tackle_for_loss", "time_to_pressure"]
    pp = pd.read_csv(DATA / "player_play.csv", usecols=cols)
    pp = pp[pp.nfl_id.isin(ids)]
    g = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(g, on="game_id", how="left")
    pp = pp[(pp.season_type == "REG") & (pp.play_nullified_by_penalty == "N") & (pp.team_abbr != pp.possession_team)
            & pp.lined_up_position.isin(ON_LINE)].copy()
    t = pd.to_numeric(pp.tackle, errors="coerce"); a = pd.to_numeric(pp.assist, errors="coerce")
    pp["inv"] = (t >= 1) | (a == 1)
    pp["tfl"] = pp.tackle_for_loss.astype(str).str.lower().isin({"true", "1", "1.0"})
    pp["is_run"] = pp.pass_result.isna()
    yg, ytg, dn = pp.yards_gained, pp.yards_to_go, pp.down
    fail = np.where(dn == 1, yg < 0.4 * ytg, np.where(dn == 2, yg < 0.6 * ytg, yg < ytg))
    pp["stop"] = pp.is_run & pp.inv & fail
    pp["stop_near"] = pp.is_run & pp.inv & (yg <= 2)
    return pp


def penetration(pp: pd.DataFrame) -> pd.DataFrame:
    fr = pd.read_parquet(CACHE / "dl_snap_frames.parquet")
    meta = pp[KEY + ["yardline_side", "yardline_number", "possession_team", "play_direction", "is_run"]]
    fr = fr.merge(meta, on=KEY)
    fr["pen"] = (los_x(fr) - fr.x) * dir_sign(fr)
    fr = fr[fr.t_snap >= -0.001]
    g = fr.groupby(KEY)
    d = g.agg(pen_max_2s=("pen", "max"), n_fr=("pen", "size"), is_run=("is_run", "first"))
    at2 = fr[(fr.t_snap - 2.0).abs() < 0.051].groupby(KEY).pen.first().rename("pen_2s")
    at0 = fr[fr.t_snap < 0.051].groupby(KEY).pen.first().rename("pen_0")
    d = d.join(at2).join(at0).reset_index()
    return d[(d.n_fr >= 18) & d.pen_2s.notna()]


def run_tackle_depth(pp: pd.DataFrame) -> pd.DataFrame:
    fr = pd.read_parquet(CACHE / "tackle_window_frames.parquet")
    inv = pp[pp.inv & pp.is_run][KEY + ["yardline_side", "yardline_number", "possession_team", "play_direction"]]
    e = fr[fr.t_tackle.abs() < 0.051].merge(inv, on=KEY).drop_duplicates(KEY)
    e["depth"] = (e.x - los_x(e)) * dir_sign(e)
    return e


def build():
    pl = players()
    pp = play_table(set(pl.nfl_id))
    a = pp.groupby("nfl_id").agg(n_snaps=("play_id", "size"), n_tfl=("tfl", "sum"))
    a["tfl_rate"] = np.where(a.n_snaps >= MIN_SNAPS, a.n_tfl / a.n_snaps, np.nan)
    r = pp[pp.is_run].groupby("nfl_id").agg(n_run=("play_id", "size"), n_stop=("stop", "sum"), n_near=("stop_near", "sum"))
    r["run_stop_rate"] = np.where(r.n_run >= MIN_RUN, r.n_stop / r.n_run, np.nan)
    r["run_stop_near_rate"] = np.where(r.n_run >= MIN_RUN, r.n_near / r.n_run, np.nan)
    pr = pp[pp.pass_result.notna() & pp.time_to_pressure.notna()]
    tp = pr.groupby("nfl_id").agg(n_press=("time_to_pressure", "size"), ttp_median=("time_to_pressure", "median"))
    tp.loc[tp.n_press < MIN_PRESS, "ttp_median"] = np.nan
    pen = penetration(pp)
    pa = pen.groupby("nfl_id").agg(n_pen=("pen_2s", "size"), pen_max_2s=("pen_max_2s", "median"), pen_2s=("pen_2s", "median"))
    pa.loc[pa.n_pen < MIN_TRK, ["pen_max_2s", "pen_2s"]] = np.nan
    for lab, m in [("run", pen.is_run), ("pass", ~pen.is_run.astype(bool))]:
        s = pen[m].groupby("nfl_id").agg(**{f"n_pen_{lab}": ("pen_2s", "size"), f"pen_{lab}_2s": ("pen_2s", "median")})
        s.loc[s[f"n_pen_{lab}"] < 25, f"pen_{lab}_2s"] = np.nan
        pa = pa.join(s, how="left")
    rt = run_tackle_depth(pp)
    ra = rt.groupby("nfl_id").agg(n_run_tk=("depth", "size"), run_tackle_depth=("depth", "median"))
    ra.loc[ra.n_run_tk < MIN_RUN_TK, "run_tackle_depth"] = np.nan
    ref = pd.read_csv(OUT / "dl_burst_players.csv", usecols=["nfl_id", "n_rush_plays", "pressure_rate", "sack_rate", "speed_1s_mph", "player_get_off"])
    comb = load_combine(ROOT, set(pl.nfl_id))
    cod = pd.read_csv(OUT / "route_cod_combine_player.csv", usecols=["nfl_id", "tc_peak_decel_mag", "tc_peak_accel", "ss_peak_decel_mag", "ss_peak_accel"])
    d = pl.merge(comb, on="nfl_id", how="left").merge(cod, on="nfl_id", how="left")
    for x in [ref, a.reset_index(), r.reset_index(), tp.reset_index(), pa.reset_index(), ra.reset_index()]:
        d = d.merge(x, on="nfl_id", how="left")
    assert not any("draft_round" in c or "pick" in c for c in d.columns)
    # reliability (odd/even plays)
    rel = []
    q = pp[pp.nfl_id.isin(set(a.index[a.n_snaps >= MIN_SNAPS]))].copy(); q["tfl"] = q.tfl.astype(float)
    rel.append(dict(outcome="tfl_rate", **split_half(q, "nfl_id", "tfl", min_half=MIN_SNAPS // 2)))
    q = pp[pp.is_run & pp.nfl_id.isin(set(r.index[r.n_run >= MIN_RUN]))].copy()
    for c in ["stop", "stop_near"]:
        q[c] = q[c].astype(float)
        rel.append(dict(outcome=f"run_{c}_rate".replace("stop_stop", "stop"), **split_half(q, "nfl_id", c, min_half=MIN_RUN // 2)))
    q = pr[pr.nfl_id.isin(set(tp.index[tp.n_press >= MIN_PRESS]))]
    rel.append(dict(outcome="ttp_median", **split_half(q, "nfl_id", "time_to_pressure", agg="median", min_half=2)))
    q = pen[pen.nfl_id.isin(set(pa.index[pa.n_pen >= MIN_TRK]))]
    for c in ["pen_max_2s", "pen_2s"]:
        rel.append(dict(outcome=c, **split_half(q, "nfl_id", c, agg="median", min_half=MIN_TRK // 2)))
    q2 = q[q.is_run.astype(bool)]; rel.append(dict(outcome="pen_run_2s", **split_half(q2, "nfl_id", "pen_2s", agg="median", min_half=12)))
    q2 = q[~q.is_run.astype(bool)]; rel.append(dict(outcome="pen_pass_2s", **split_half(q2, "nfl_id", "pen_2s", agg="median", min_half=12)))
    q = rt[rt.nfl_id.isin(set(ra.index[ra.n_run_tk >= MIN_RUN_TK]))]
    rel.append(dict(outcome="run_tackle_depth", **split_half(q, "nfl_id", "depth", agg="median", min_half=4)))
    gp = pd.read_parquet(OUT / "dl_play_getoff.parquet")
    q = gp[gp.nfl_id.isin(set(ref.nfl_id[ref.n_rush_plays >= 20]))].dropna(subset=["speed_1s"])
    rel.append(dict(outcome="speed_1s_mph", **split_half(q, "nfl_id", "speed_1s", min_half=10)))
    rel = pd.DataFrame(rel)
    qc = dict(dl_players=len(pl), edge=int((pl.subtype == "Edge").sum()), interior=int((pl.subtype == "Interior").sum()),
              on_line_snaps=len(pp), run_snaps=int(pp.is_run.sum()), tracked_pen_plays=len(pen),
              median_pen_at_snap=round(float(pen.pen_0.median()), 2), median_pen_2s=round(float(pen.pen_2s.median()), 2),
              run_tackles_tracked=len(rt), eligible_snaps=int((a.n_snaps >= MIN_SNAPS).sum()))
    return d, rel, qc


def run_tests(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frames = [("DL", d, "year"), ("DL", d, "year_subtype"), ("Edge", d[d.subtype == "Edge"], "year"),
              ("Interior", d[d.subtype == "Interior"], "year")]
    for grp, sub, ctrl in frames:
        cells = sub.draft_year.astype(str) + ("_" + sub.subtype if ctrl == "year_subtype" else "")
        for oc, ol, osg in OUTCOMES:
            for tc, tl, tsg in TESTS:
                rows.append(dict(group=grp, control=ctrl, test=tc, test_label=tl, outcome=oc, outcome_label=ol,
                                 test_good=tsg, outcome_good=osg, **spearman_ctrl(sub[tc], sub[oc], cells)))
    t = pd.DataFrame(rows)
    t["fdr"] = np.nan
    for _, g in t.groupby(["group", "control"]):
        t.loc[g.index, "fdr"] = bh(g.p)
    t["good_direction"] = np.where((t.test_good != 0) & (t.outcome_good != 0),
                                   np.sign(t.rho) * t.test_good * t.outcome_good > 0, np.nan)
    return t


def chain(d: pd.DataFrame) -> pd.DataFrame:
    """Reference chain plus: does Sunday get-off carry the new outcomes? Mediation by get-off."""
    rows = []
    cells = d.draft_year.astype(str)
    for x, y in [("ten_yd_split", "speed_1s_mph"), ("ten_yd_split", "pressure_rate"), ("speed_1s_mph", "pressure_rate")] + \
                [("speed_1s_mph", oc) for oc, *_ in OUTCOMES if oc not in ("speed_1s_mph", "pressure_rate")]:
        rows.append(dict(kind="chain", x=x, y=y, **spearman_ctrl(d[x], d[y], cells)))
    # Partial Spearman: Combine test vs outcome, controlling year and one extra variable
    # (Sunday get-off for mediation; weight and the 10-yard for the 3-cone beyond-the-10 check).
    def partial(x, y, z):
        s = d[[x, y, z, "draft_year"]].dropna()
        if len(s) < 12:
            return None
        codes = pd.factorize(s.draft_year)[0][None]; k = codes.max() + 1
        g = _demean(s[z].to_numpy(float)[None], codes, k)[0]
        res = []
        for c in (x, y):
            v = _demean(s[c].to_numpy(float)[None], codes, k)[0]
            b = np.polyfit(g, v, 1); res.append(v - np.polyval(b, g))
        r, p = stats.spearmanr(*res)
        return dict(kind=f"partial_{z}", x=x, y=y, n=len(s), rho=float(r), p=float(p))
    for x in ["ten_yd_split", "c_t10_derived", "burst_0_100", "forty", "three_cone"]:
        for y in ["pressure_rate", "sack_rate", "pen_max_2s", "pen_pass_2s", "tfl_rate", "run_stop_rate", "ttp_median"]:
            r = partial(x, y, "speed_1s_mph")
            if r: rows.append(r)
    for z in ["combine_weight", "ten_yd_split", "forty"]:
        for y in ["pressure_rate", "sack_rate", "tfl_rate"]:
            r = partial("three_cone", y, z)
            if r: rows.append(r)
    for z in ["combine_weight", "speed_1s_mph"]:
        r = partial("burst_0_100", "tfl_rate", z)
        if r: rows.append(r)
    return pd.DataFrame(rows)


def fig19(t: pd.DataFrame, d: pd.DataFrame) -> Path:
    p = t[(t.group == "DL") & (t.control == "year")]
    M = p.pivot(index="test", columns="outcome", values="rho").reindex(index=[c for c, *_ in TESTS], columns=[c for c, *_ in OUTCOMES])
    Q = p.pivot(index="test", columns="outcome", values="fdr").reindex_like(M)
    P = p.pivot(index="test", columns="outcome", values="p").reindex_like(M)
    fig = plt.figure(figsize=(20, 10))
    GS = fig.add_gridspec(2, 2, width_ratios=[2.3, 1], hspace=0.45, wspace=0.25, left=0.14, right=0.98, bottom=0.2, top=0.92)
    ax = fig.add_subplot(GS[:, 0])
    im = ax.imshow(M.to_numpy(float), cmap="RdBu_r", vmin=-0.7, vmax=0.7, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.iat[i, j]
            if np.isfinite(v):
                mark = "**" if Q.iat[i, j] < 0.05 else ("*" if P.iat[i, j] < 0.05 else "")
                ax.text(j, i, f"{v:+.2f}{mark}", ha="center", va="center", fontsize=7.5)
    ax.set_xticks(range(M.shape[1])); ax.set_xticklabels([OUT_LABEL[c] for c in M.columns], rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(M.shape[0])); ax.set_yticklabels([TEST_LABEL[c] for c in M.index], fontsize=8.5)
    ax.set_title("DL (DE+DT+NT+OLB) — every Combine measure vs wider DL outcomes\nSpearman ρ controlled for draft year. ** BH-FDR<0.05, * raw p<0.05. Lower times = faster.", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.025, label="ρ")
    # right: production links beyond the 10-yard (pressure / sack / TFL / run / time to pressure),
    # (a) strongest after year x subtype control, (b) strongest year-only with n>=50
    prod = ["pressure_rate", "sack_rate", "ttp_median", "tfl_rate", "run_stop_rate", "run_stop_near_rate", "run_tackle_depth"]
    base = t[t.outcome.isin(prod) & (t.test != "ten_yd_split") & (t.good_direction == 1) & (t.group == "DL")].dropna(subset=["p"])
    ra = base[base.control == "year_subtype"].sort_values("p").iloc[0]
    rb = base[(base.control == "year") & (base.n >= 50) & ~base.outcome.isin(["pressure_rate", "sack_rate"])].sort_values("p").iloc[0]
    rb = t[(t.group == "DL") & (t.control == "year") & (t.test == rb.test) & (t.outcome == rb.outcome)].iloc[0]
    ra_y = t[(t.group == "DL") & (t.control == "year") & (t.test == ra.test) & (t.outcome == ra.outcome)].iloc[0]
    for k, (row, tag) in enumerate([(ra_y, f"Beyond the 10-yard (year×subtype ρ={ra.rho:+.2f}, FDR={fmt_p(ra.fdr)})"),
                                    (rb, "Beyond pressure/sack: new outcome, n≥50")]):
        ax2 = fig.add_subplot(GS[k, 1])
        s_ = d[[row.test, row.outcome, "subtype"]].dropna()
        for st, col in [("Edge", "#ff7f0e"), ("Interior", "#2ca02c")]:
            q = s_[s_.subtype == st]
            ax2.scatter(q[row.test], q[row.outcome], s=24, alpha=.75, color=col, label=f"{st} (n={len(q)})")
        ax2.set_xlabel(TEST_LABEL[row.test], fontsize=8.5); ax2.set_ylabel(OUT_LABEL[row.outcome], fontsize=8.5)
        ax2.set_title(f"{tag}\nyear-only ρ={row.rho:+.2f} (95% CI {row.lo:+.2f} to {row.hi:+.2f}), n={row.n}, FDR={fmt_p(row.fdr)}", fontsize=8.5)
        ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
    fig.text(0.01, 0.01, "Sample: 2023–2025 rookie DL, REG snaps that stood, lined up EDGE/INTERIOR_LINE. Rates ≥100 snaps; run rates ≥50 run snaps; "
             "penetration ≥50 tracked snaps; time to pressure ≥5 pressures. No draft slot used.", fontsize=8)
    path = FIGS / "fig19_dl_recheck.png"
    fig.savefig(path, dpi=150); plt.close(fig)
    return path


def main() -> None:
    d, rel, qc = build()
    t = run_tests(d)
    ch = chain(d)
    keep = ["nfl_id", "display_name", "draft_year", "nfl_position", "subtype", "college_name"] + [c for c, *_ in TESTS] + \
        ["n_rush_plays", "n_snaps", "n_run", "n_press", "n_pen", "n_pen_run", "n_pen_pass", "n_run_tk", "player_get_off"] + [c for c, *_ in OUTCOMES]
    d[keep].to_csv(OUT / "dl_recheck_players.csv", index=False)
    t.to_csv(OUT / "dl_recheck_tests.csv", index=False)
    ch.to_csv(OUT / "dl_recheck_chain.csv", index=False)
    rel.to_csv(OUT / "dl_recheck_reliability.csv", index=False)
    pd.Series(qc).to_csv(OUT / "dl_recheck_qc.csv", header=["value"])
    ns = pd.DataFrame({oc: [int(d[oc].notna().sum()), int(d.loc[d.subtype == "Edge", oc].notna().sum()),
                            int(d.loc[d.subtype == "Interior", oc].notna().sum())] for oc, *_ in OUTCOMES}, index=["DL", "Edge", "Interior"]).T
    ns.to_csv(OUT / "dl_recheck_outcome_n.csv")
    fig19(t, d)
    print(qc); print(ns); print(rel.round(3).to_string()); print(ch.round(3).to_string())
    for (g, c), s in t.groupby(["group", "control"], sort=False):
        s = s.dropna(subset=["p"]).sort_values("p")
        print(f"\n=== {g} [{c}] cells={len(s)} FDR<0.05: {(s.fdr < 0.05).sum()}")
        print(s.head(25)[["test", "outcome", "n", "rho_raw", "rho", "lo", "hi", "p", "fdr", "good_direction"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
