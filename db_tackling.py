"""RUN 1 - DB tackling: every Combine measure vs DB tackling outcomes.

DB = CB + SS + FS + DB (one headline group); CB vs S breakouts are secondary.
Primary statistic: Spearman controlled for draft year (within-year demeaning),
2,000-player bootstrap 95% CI, BH-FDR across the whole pooled-DB family.
Sensitivity: pooled DB controlled for year x role (CB vs S) cells.
Draft slot / round is never loaded into the analysis table.

Needs out/cache/tackle_window_frames.parquet from track_extract.py.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from bdb_stats import (OFFICIAL, TRACKING, MPH, spearman_ctrl, bh, split_half,
                       los_x, dir_sign, load_combine, fmt_p)

ROOT = Path(__file__).resolve().parent
DATA, OUT, FIGS, CACHE = ROOT / "data", ROOT / "out", ROOT / "out" / "figs", ROOT / "out" / "cache"
DB_POS = {"CB", "SS", "FS", "DB"}
MIN_SNAPS = 100      # rates per defensive snap
MIN_TRK_TACKLES = 10  # tracking tackle depth / closing speed
MIN_RUN_TACKLES = 8
KEY = ["game_id", "play_id", "nfl_id"]

TESTS = OFFICIAL + TRACKING + [
    ("c_decel", "Combine Brakes (peak decel, DB drill)", +1),
    ("c_accel", "Combine Re-Burst (peak accel, DB drill)", +1),
    ("burst_0_100", "Burst Score (0-100)", +1),
]
# (col, label, "good" direction: +1 higher is better for defense, -1 lower is better, 0 descriptive)
OUTCOMES = [
    ("tackle_rate", "Tackles per snap (solo+assist)", +1),
    ("solo_rate", "Solo tackles per snap", +1),
    ("assist_rate", "Assisted tackles per snap", +1),
    ("solo_share", "Solo share of tackles", +1),
    ("tfl_rate", "TFL per snap", +1),
    ("ff_rate", "Forced fumbles per snap", +1),
    ("tackle_depth", "Tackle depth past LOS (yd, tracking)", -1),
    ("run_tackle_depth", "Run-play tackle depth (yd, tracking)", -1),
    ("tackle_yds_gained", "Yards gained on his tackles (play-level)", -1),
    ("close_speed_mph", "Speed in last 1 s before tackle (mph)", +1),
    ("close_rate_mph", "Closing rate to tackle spot, last 1 s (mph)", +1),
    ("pfr_mtkl_pct", "PFR missed tackle %", -1),
    ("pfr_yds_tgt", "PFR yards per target allowed", -1),
]
OUT_LABEL = {c: l for c, l, _ in OUTCOMES}
TEST_LABEL = {c: l for c, l, _ in TESTS}


def players() -> pd.DataFrame:
    pl = pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "display_name", "draft_year", "nfl_position", "college_name"])
    pl = pl[pl.nfl_position.isin(DB_POS)].copy()
    pl["role"] = np.where(pl.nfl_position.isin({"SS", "FS"}), "S", "CB")
    return pl


def play_table(ids) -> pd.DataFrame:
    cols = KEY + ["team_abbr", "possession_team", "play_nullified_by_penalty", "pass_result", "down", "yards_to_go",
                  "yards_gained", "yardline_side", "yardline_number", "play_direction",
                  "tackle", "assist", "tackle_for_loss", "caused_forced_fumble", "lined_up_position"]
    pp = pd.read_csv(DATA / "player_play.csv", usecols=cols)
    pp = pp[pp.nfl_id.isin(ids)]
    g = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(g, on="game_id", how="left")
    pp = pp[(pp.season_type == "REG") & (pp.play_nullified_by_penalty == "N") & (pp.team_abbr != pp.possession_team)].copy()
    t = pd.to_numeric(pp.tackle, errors="coerce"); a = pd.to_numeric(pp.assist, errors="coerce")
    pp["solo"] = (t >= 1) & (a != 1)
    pp["ast"] = a == 1
    pp["inv"] = pp.solo | pp.ast
    pp["tfl"] = pp.tackle_for_loss.astype(str).str.lower().isin({"true", "1", "1.0"})
    pp["ff"] = pd.to_numeric(pp.caused_forced_fumble, errors="coerce").fillna(0) > 0
    pp["is_run"] = pp.pass_result.isna()
    return pp


def tackle_tracking(pp: pd.DataFrame) -> pd.DataFrame:
    """Per involved play: depth past LOS at the tackle event and closing in the last 1.0 s."""
    fr = pd.read_parquet(CACHE / "tackle_window_frames.parquet")
    inv = pp[pp.inv][KEY + ["yardline_side", "yardline_number", "possession_team", "play_direction", "is_run", "yards_gained"]]
    fr = fr.merge(inv[KEY], on=KEY)
    fr = fr.sort_values(KEY + ["t_tackle"])
    end = fr[fr.t_tackle.abs() < 0.051].groupby(KEY).last()[["x", "y", "s"]]
    start = fr[(fr.t_tackle + 1.0).abs() < 0.051].groupby(KEY).first()[["x", "y", "t_tackle"]]
    win = fr.groupby(KEY).agg(s_mean=("s", "mean"), s_max=("s", "max"), n_fr=("s", "size"))
    d = end.join(start, rsuffix="_0", how="inner").join(win)
    d = d.reset_index().merge(inv, on=KEY)
    d["tackle_depth"] = (d.x - los_x(d)) * dir_sign(d)
    dist = np.hypot(d.x - d.x_0, d.y - d.y_0)
    d["close_rate_mph"] = dist / (-d.t_tackle) * MPH
    d["close_speed_mph"] = d.s_mean * MPH
    d = d[d.n_fr >= 9]
    return d


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    pl = players()
    pp = play_table(set(pl.nfl_id))
    agg = pp.groupby("nfl_id").agg(n_snaps=("play_id", "size"), n_solo=("solo", "sum"), n_ast=("ast", "sum"),
                                     n_inv=("inv", "sum"), n_tfl=("tfl", "sum"), n_ff=("ff", "sum"))
    for c, n in [("tackle_rate", "n_inv"), ("solo_rate", "n_solo"), ("assist_rate", "n_ast"),
                 ("tfl_rate", "n_tfl"), ("ff_rate", "n_ff")]:
        agg[c] = agg[n] / agg.n_snaps
    agg["solo_share"] = np.where(agg.n_inv >= 10, agg.n_solo / agg.n_inv.replace(0, np.nan), np.nan)
    small = agg.n_snaps < MIN_SNAPS
    agg.loc[small, ["tackle_rate", "solo_rate", "assist_rate", "tfl_rate", "ff_rate", "solo_share"]] = np.nan
    ty = pp[pp.inv].groupby("nfl_id").yards_gained.median().rename("tackle_yds_gained")
    tt = tackle_tracking(pp)
    tagg = tt.groupby("nfl_id").agg(n_trk_tackles=("tackle_depth", "size"), tackle_depth=("tackle_depth", "median"),
                                    close_speed_mph=("close_speed_mph", "median"), close_rate_mph=("close_rate_mph", "median"))
    tagg.loc[tagg.n_trk_tackles < MIN_TRK_TACKLES, ["tackle_depth", "close_speed_mph", "close_rate_mph"]] = np.nan
    rt = tt[tt.is_run].groupby("nfl_id").agg(n_run_tackles=("tackle_depth", "size"), run_tackle_depth=("tackle_depth", "median"))
    rt.loc[rt.n_run_tackles < MIN_RUN_TACKLES, "run_tackle_depth"] = np.nan
    n_inv = agg.n_inv
    ty[n_inv.reindex(ty.index).fillna(0) < MIN_TRK_TACKLES] = np.nan
    pf = pd.read_csv(OUT / "pfr_def_career.csv", usecols=["nfl_id", "m_tkl_percent", "yds_tgt", "usable_tkl15", "usable_cov20", "tackle_attempts", "tgt"])
    pf["pfr_mtkl_pct"] = np.where(pf.usable_tkl15.astype(str) == "True", pf.m_tkl_percent * 100, np.nan)
    pf["pfr_yds_tgt"] = np.where(pf.usable_cov20.astype(str) == "True", pf.yds_tgt, np.nan)
    comb = load_combine(ROOT, set(pl.nfl_id))
    acc = pd.read_csv(OUT / "eda_accel_players.csv", usecols=["nfl_id", "c_decel", "c_accel"])
    d = (pl.merge(comb, on="nfl_id", how="left").merge(acc, on="nfl_id", how="left")
         .merge(agg.reset_index(), on="nfl_id", how="left").merge(ty.reset_index(), on="nfl_id", how="left")
         .merge(tagg.reset_index(), on="nfl_id", how="left").merge(rt.reset_index(), on="nfl_id", how="left")
         .merge(pf[["nfl_id", "pfr_mtkl_pct", "pfr_yds_tgt", "tackle_attempts", "tgt"]], on="nfl_id", how="left"))
    assert not any("draft_round" in c or "pick" in c for c in d.columns)
    # reliability
    ok = set(agg.index[agg.n_snaps >= MIN_SNAPS])
    pq = pp[pp.nfl_id.isin(ok)].copy()
    for c in ["inv", "solo", "ast", "tfl", "ff"]:
        pq[c] = pq[c].astype(float)
    rel = []
    for c, lab in [("inv", "tackle_rate"), ("solo", "solo_rate"), ("ast", "assist_rate"), ("tfl", "tfl_rate"), ("ff", "ff_rate")]:
        rel.append(dict(outcome=lab, **split_half(pq, "nfl_id", c, min_half=MIN_SNAPS // 2)))
    tq = tt[tt.nfl_id.isin(set(tagg.index[tagg.n_trk_tackles >= MIN_TRK_TACKLES]))]
    for c in ["tackle_depth", "close_speed_mph", "close_rate_mph"]:
        rel.append(dict(outcome=c, **split_half(tq, "nfl_id", c, agg="median", min_half=MIN_TRK_TACKLES // 2)))
    rq = tt[tt.is_run & tt.nfl_id.isin(set(rt.index[rt.n_run_tackles >= MIN_RUN_TACKLES]))]
    rel.append(dict(outcome="run_tackle_depth", **split_half(rq, "nfl_id", "tackle_depth", agg="median", min_half=MIN_RUN_TACKLES // 2)))
    tyq = pp[pp.inv & pp.nfl_id.isin(set(n_inv.index[n_inv >= MIN_TRK_TACKLES]))]
    rel.append(dict(outcome="tackle_yds_gained", **split_half(tyq, "nfl_id", "yards_gained", agg="median", min_half=MIN_TRK_TACKLES // 2)))
    rel = pd.DataFrame(rel)
    qc = dict(db_players=len(pl), cb=int((pl.role == "CB").sum()), s=int((pl.role == "S").sum()),
              reg_def_snaps=len(pp), involved_plays=int(pp.inv.sum()), tracked_tackle_plays=len(tt),
              tracked_share=round(len(tt) / max(1, int(pp.inv.sum())), 3),
              median_tackle_depth=round(float(tt.tackle_depth.median()), 2),
              median_close_mph=round(float(tt.close_speed_mph.median()), 2),
              eligible_snaps=int((agg.n_snaps >= MIN_SNAPS).sum()),
              eligible_trk=int((tagg.n_trk_tackles >= MIN_TRK_TACKLES).sum()))
    return d, rel, tt, qc


def run_tests(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frames = [("DB", d, "year"), ("DB", d, "year_role"), ("CB", d[d.role == "CB"], "year"), ("S", d[d.role == "S"], "year")]
    for grp, sub, ctrl in frames:
        cells = sub.draft_year.astype(str) + ("_" + sub.role if ctrl == "year_role" else "")
        for oc, ol, osgn in OUTCOMES:
            for tc, tl, tsgn in TESTS:
                r = spearman_ctrl(sub[tc], sub[oc], cells)
                rows.append(dict(group=grp, control=ctrl, test=tc, test_label=tl, outcome=oc, outcome_label=ol,
                                 test_good=tsgn, outcome_good=osgn, **r))
    t = pd.DataFrame(rows)
    t["fdr"] = np.nan
    for key, g in t.groupby(["group", "control"]):
        t.loc[g.index, "fdr"] = bh(g.p)
    # Does the better Combine result go with the better tackling result?
    t["good_direction"] = np.where((t.test_good != 0) & (t.outcome_good != 0),
                                   np.sign(t.rho) * t.test_good * t.outcome_good > 0, np.nan)
    return t


def fig18(t: pd.DataFrame, d: pd.DataFrame) -> Path:
    p = t[(t.group == "DB") & (t.control == "year")]
    M = p.pivot(index="test", columns="outcome", values="rho").reindex(index=[c for c, *_ in TESTS], columns=[c for c, *_ in OUTCOMES])
    Q = p.pivot(index="test", columns="outcome", values="fdr").reindex_like(M)
    P = p.pivot(index="test", columns="outcome", values="p").reindex_like(M)
    N = p.pivot(index="test", columns="outcome", values="n").reindex_like(M)
    fig = plt.figure(figsize=(19, 9.5))
    GS = fig.add_gridspec(2, 2, width_ratios=[2.3, 1], hspace=0.45, wspace=0.25, left=0.14, right=0.98, bottom=0.2, top=0.92)
    ax = fig.add_subplot(GS[:, 0])
    im = ax.imshow(M.to_numpy(float), cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.iat[i, j]
            if np.isfinite(v):
                mark = "**" if Q.iat[i, j] < 0.05 else ("*" if P.iat[i, j] < 0.05 else "")
                ax.text(j, i, f"{v:+.2f}{mark}", ha="center", va="center", fontsize=7.5)
    ax.set_xticks(range(M.shape[1])); ax.set_xticklabels([OUT_LABEL[c] for c in M.columns], rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(M.shape[0])); ax.set_yticklabels([TEST_LABEL[c] for c in M.index], fontsize=8.5)
    ax.set_title("DB (CB+S) — every Combine measure vs tackling outcomes\nSpearman ρ controlled for draft year. ** BH-FDR<0.05, * raw p<0.05. Blank = n<12.", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.025, label="ρ")
    # right: (a) strongest cell after year x role control, (b) best athletic test in the good direction
    pr = t[(t.group == "DB") & (t.control == "year_role")].dropna(subset=["p"]).sort_values("p")
    pg = p[(p.good_direction == 1) & ~p.outcome.isin(["ff_rate", "tfl_rate", "tackle_depth", "tackle_yds_gained", "close_speed_mph"])].dropna(subset=["p"]).sort_values("p")  # outcomes with split-half SB >= 0.40
    for k, (row, tag) in enumerate([(pr.iloc[0], "Strongest, year×role ctrl"), (pg.iloc[0], "Best athletic, good dir.")]):
        ax2 = fig.add_subplot(GS[k, 1])
        s_ = d[[row.test, row.outcome, "role"]].dropna()
        for role, col in [("CB", "#1f77b4"), ("S", "#d62728")]:
            q = s_[s_.role == role]
            ax2.scatter(q[row.test], q[row.outcome], s=24, alpha=.75, label=f"{role} (n={len(q)})", color=col)
        ax2.set_xlabel(TEST_LABEL[row.test], fontsize=8.5); ax2.set_ylabel(OUT_LABEL[row.outcome], fontsize=8.5)
        ax2.set_title(f"{tag}: ρ={row.rho:+.2f} (95% CI {row.lo:+.2f} to {row.hi:+.2f})\nn={row.n}, FDR={fmt_p(row.fdr)}", fontsize=8.5)
        ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
    fig.text(0.01, 0.01, "Sample: 2023–2025 rookie DBs, REG snaps that stood. Rates need ≥100 snaps; tracking tackle metrics ≥10 tracked tackles. "
             "PFR = nflverse/Pro Football Reference season aggregates. No draft slot used.", fontsize=8)
    path = FIGS / "fig18_db_tackling.png"
    fig.savefig(path, dpi=150); plt.close(fig)
    return path


def main() -> None:
    d, rel, tt, qc = build()
    t = run_tests(d)
    keep = ["nfl_id", "display_name", "draft_year", "nfl_position", "role", "college_name"] + [c for c, *_ in TESTS] + \
        ["n_snaps", "n_inv", "n_solo", "n_ast", "n_tfl", "n_ff", "n_trk_tackles", "n_run_tackles", "tackle_attempts", "tgt"] + [c for c, *_ in OUTCOMES]
    d[keep].to_csv(OUT / "db_tackle_players.csv", index=False)
    t.to_csv(OUT / "db_tackle_tests.csv", index=False)
    rel.to_csv(OUT / "db_tackle_reliability.csv", index=False)
    pd.Series(qc).to_csv(OUT / "db_tackle_qc.csv", header=["value"])
    # outcome sample sizes
    ns = pd.DataFrame({oc: [int(d[oc].notna().sum()), int(d.loc[d.role == "CB", oc].notna().sum()), int(d.loc[d.role == "S", oc].notna().sum())]
                       for oc, *_ in OUTCOMES}, index=["DB", "CB", "S"]).T
    ns.to_csv(OUT / "db_tackle_outcome_n.csv")
    fig18(t, d)
    print(qc); print(ns); print(rel.round(3).to_string())
    for (g, c), s in t.groupby(["group", "control"], sort=False):
        s = s.dropna(subset=["p"]).sort_values("p")
        print(f"\n=== {g} [{c}] cells={len(s)} FDR<0.05: {(s.fdr < 0.05).sum()}")
        print(s.head(12)[["test", "outcome", "n", "rho_raw", "rho", "lo", "hi", "p", "fdr", "good_direction"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
