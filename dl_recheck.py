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


# Display-only grouping / orientation for Figure 19 (stats are not recomputed).
# Timed drills and lower-is-better outcomes are sign-flipped so red always
# means "better athlete goes with better on-field result."
SPEED_AGILITY = [
    "ten_yd_split", "forty", "three_cone", "short_shuttle",
    "c_t10_derived", "c_t20_derived",
    "c_top_mph", "c_40_accel",
    "tc_peak_decel_mag", "tc_peak_accel",
    "ss_peak_decel_mag", "ss_peak_accel",
]
POWER_SIZE = [
    "burst_0_100", "vertical", "broad_jump", "bench_reps",
    "combine_weight", "combine_height", "arm_length", "hand_size", "wing_span",
]
PASS_RUSH = [
    "speed_1s_mph", "pressure_rate", "sack_rate", "ttp_median",
    "pen_max_2s", "pen_2s", "pen_pass_2s",
]
RUN_DEF = [
    "tfl_rate", "run_stop_rate", "run_stop_near_rate", "run_tackle_depth", "pen_run_2s",
]
FLIP_TESTS = {
    "ten_yd_split", "forty", "three_cone", "short_shuttle",
    "c_t10_derived", "c_t20_derived",
}
FLIP_OUTCOMES = {"ttp_median", "run_tackle_depth"}

FIG19_ROW_LABELS = {
    "ten_yd_split": "Official 10-yard  †",
    "forty": "Official 40  †",
    "three_cone": "3-cone  †",
    "short_shuttle": "Short shuttle  †",
    "c_t10_derived": "10-yard split (tracking)  †",
    "c_t20_derived": "20-yard split (tracking)  †",
    "c_top_mph": "Combine top speed",
    "c_40_accel": "40-yard peak accel",
    "tc_peak_decel_mag": "3-cone Brakes (peak decel)",
    "tc_peak_accel": "3-cone Re-Burst (peak accel)",
    "ss_peak_decel_mag": "Shuttle Brakes (peak decel)",
    "ss_peak_accel": "Shuttle Re-Burst (peak accel)",
    "burst_0_100": "Burst Score (0–100)",
    "vertical": "Vertical",
    "broad_jump": "Broad jump",
    "bench_reps": "Bench reps",
    "combine_weight": "Weight",
    "combine_height": "Height",
    "arm_length": "Arm length",
    "hand_size": "Hand size",
    "wing_span": "Wingspan",
}
FIG19_COL_LABELS = {
    "speed_1s_mph": "Sunday get-off (1.0 s)",
    "pressure_rate": "Pressure rate",
    "sack_rate": "Sack rate",
    "ttp_median": "Time to pressure (faster = higher)",
    "pen_max_2s": "Penetration, max in first 2 s",
    "pen_2s": "Penetration at 2.0 s",
    "pen_pass_2s": "Penetration at 2.0 s, pass",
    "tfl_rate": "TFL per snap",
    "run_stop_rate": "Run stops per run snap",
    "run_stop_near_rate": "Run tackles at ≤2 yd / run snap",
    "run_tackle_depth": "Run-tackle depth (shallower = higher)",
    "pen_run_2s": "Penetration at 2.0 s, run",
}
_FIG19_GAP = 0.55


def _fig19_edges(n1: int, n2: int, gap: float = _FIG19_GAP) -> np.ndarray:
    e = list(np.arange(n1 + 1, dtype=float))
    start = n1 + gap
    e += list(start + np.arange(n2 + 1, dtype=float))
    return np.asarray(e)


def _fig19_fill_gap(src: np.ndarray, n1r: int, n1c: int) -> np.ndarray:
    """Insert a NaN gap row and column into a (n1r+n2r) x (n1c+n2c) array."""
    n2r, n2c = src.shape[0] - n1r, src.shape[1] - n1c
    out = np.full((n1r + 1 + n2r, n1c + 1 + n2c), np.nan)
    out[:n1r, :n1c] = src[:n1r, :n1c]
    out[:n1r, n1c + 1:] = src[:n1r, n1c:]
    out[n1r + 1:, :n1c] = src[n1r:, :n1c]
    out[n1r + 1:, n1c + 1:] = src[n1r:, n1c:]
    return out


def _fig19_centers(edges: np.ndarray, n1: int, n2: int) -> np.ndarray:
    c1 = 0.5 * (edges[:n1] + edges[1:n1 + 1])
    c2 = 0.5 * (edges[n1 + 1:n1 + 1 + n2] + edges[n1 + 2:n1 + 2 + n2])
    return np.concatenate([c1, c2])


def fig19(t: pd.DataFrame, d: pd.DataFrame, path: Path | None = None) -> Path:
    """Coach-oriented heat map plus the 3-cone and Burst Score scatter panels.

    Reuses saved Spearman / FDR values; only the display signs and layout change.
    """
    p = t[(t.group == "DL") & (t.control == "year")].copy()
    rows = SPEED_AGILITY + POWER_SIZE
    cols = PASS_RUSH + RUN_DEF
    M = p.pivot(index="test", columns="outcome", values="rho").reindex(index=rows, columns=cols)
    Q = p.pivot(index="test", columns="outcome", values="fdr").reindex_like(M)
    Pval = p.pivot(index="test", columns="outcome", values="p").reindex_like(M)

    flip_r = np.array([-1.0 if r in FLIP_TESTS else 1.0 for r in rows])
    flip_c = np.array([-1.0 if c in FLIP_OUTCOMES else 1.0 for c in cols])
    oriented = M.to_numpy(float) * flip_r[:, None] * flip_c[None, :]

    n1r, n2r = len(SPEED_AGILITY), len(POWER_SIZE)
    n1c, n2c = len(PASS_RUSH), len(RUN_DEF)
    ye, xe = _fig19_edges(n1r, n2r), _fig19_edges(n1c, n2c)
    C = _fig19_fill_gap(oriented, n1r, n1c)
    Qm = _fig19_fill_gap(Q.to_numpy(float), n1r, n1c)
    Pm = _fig19_fill_gap(Pval.to_numpy(float), n1r, n1c)

    fig = plt.figure(figsize=(21.6, 12.0))
    GS = fig.add_gridspec(
        2, 2, width_ratios=[2.55, 1], hspace=0.38, wspace=0.30,
        left=0.200, right=0.985, bottom=0.195, top=0.80,
    )
    ax = fig.add_subplot(GS[:, 0])
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad((1, 1, 1, 0))
    im = ax.pcolormesh(
        xe, ye, C, cmap=cmap, vmin=-0.7, vmax=0.7,
        shading="flat", edgecolors="white", linewidth=0.6, antialiased=True,
    )
    ax.invert_yaxis()

    for i in range(C.shape[0]):
        for j in range(C.shape[1]):
            v = C[i, j]
            if not np.isfinite(v):
                continue
            mark = "**" if Qm[i, j] < 0.05 else ("*" if Pm[i, j] < 0.05 else "")
            xc = 0.5 * (xe[j] + xe[j + 1])
            yc = 0.5 * (ye[i] + ye[i + 1])
            color = "white" if abs(v) >= 0.48 else "black"
            ax.text(xc, yc, f"{v:+.2f}{mark}", ha="center", va="center",
                    fontsize=7.3, color=color)

    ax.set_yticks(_fig19_centers(ye, n1r, n2r))
    ax.set_yticklabels([FIG19_ROW_LABELS[r] for r in rows], fontsize=8.5)
    ax.set_xticks(_fig19_centers(xe, n1c, n2c))
    ax.set_xticklabels([FIG19_COL_LABELS[c] for c in cols], rotation=38, ha="right", fontsize=8.0)
    ax.tick_params(axis="x", pad=3, length=0)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(xe[0], xe[-1])
    ax.set_ylim(ye[-1], ye[0])

    ygap = 0.5 * (ye[n1r] + ye[n1r + 1])
    xgap = 0.5 * (xe[n1c] + xe[n1c + 1])
    ax.axhline(ygap, color="#222222", lw=1.7, zorder=5)
    ax.axvline(xgap, color="#222222", lw=1.7, zorder=5)

    trans = ax.get_yaxis_transform()
    y_speed = 0.5 * (ye[0] + ye[n1r])
    y_power = 0.5 * (ye[n1r + 1] + ye[-1])
    ax.text(
        -0.275, y_speed, "Speed & agility\n(timed drills † flipped\nso faster = higher)",
        transform=trans, rotation=90, ha="center", va="center",
        fontsize=8.7, fontweight="bold", color="#1a1a1a", linespacing=1.2,
        clip_on=False,
    )
    ax.text(
        -0.275, y_power, "Power, size & length\n(higher = more)",
        transform=trans, rotation=90, ha="center", va="center",
        fontsize=8.7, fontweight="bold", color="#1a1a1a", linespacing=1.2,
        clip_on=False,
    )

    transx = ax.get_xaxis_transform()
    x_pass = 0.5 * (xe[0] + xe[n1c])
    x_run = 0.5 * (xe[n1c + 1] + xe[-1])
    for x, lab in ((x_pass, "Pass rush"), (x_run, "TFL & run defense")):
        ax.text(
            x, 1.03, lab, transform=transx, ha="center", va="bottom",
            fontsize=11, fontweight="bold", clip_on=False,
        )
    ax.plot([xe[0] + 0.15, xe[n1c] - 0.15], [1.015, 1.015],
            transform=transx, color="#222222", lw=1.2, clip_on=False, solid_capstyle="butt")
    ax.plot([xe[n1c + 1] + 0.15, xe[-1] - 0.15], [1.015, 1.015],
            transform=transx, color="#222222", lw=1.2, clip_on=False, solid_capstyle="butt")

    cbar = fig.colorbar(im, ax=ax, fraction=0.026, pad=0.018, shrink=0.88)
    cbar.set_ticks([-0.6, -0.3, 0.0, 0.3, 0.6])
    cbar.set_label("Oriented Spearman ρ\nred = better athlete\nwith better result", fontsize=8.0)
    cbar.ax.tick_params(labelsize=7.5)

    fig.suptitle(
        "DL (DE + DT + NT + OLB)  —  Combine measures vs in-game outcomes",
        fontsize=13.5, fontweight="bold", x=0.50, y=0.975, ha="center",
    )
    fig.text(
        0.50, 0.928,
        "Spearman ρ controlled for draft year.  Timed drills (†) and lower-is-better outcomes are sign-flipped "
        "so red always means “better athlete goes with better result.”\n"
        "** BH-FDR < 0.05,   * raw p < 0.05.   Weight and height have no assumed “better” direction "
        "(red = heavier / taller with a better result).",
        ha="center", va="top", fontsize=8.2, linespacing=1.35,
    )

    def scatter_panel(ax2, test, outcome, xlabel, ylabel, title_lead):
        row = t[(t.group == "DL") & (t.control == "year") & (t.test == test) & (t.outcome == outcome)].iloc[0]
        s_ = d[[test, outcome, "subtype"]].dropna()
        for st, col in [("Edge", "#ff7f0e"), ("Interior", "#2ca02c")]:
            q = s_[s_.subtype == st]
            ax2.scatter(q[test], q[outcome], s=28, alpha=.8, color=col, edgecolors="none",
                        label=f"{st} (n={len(q)})")
        ax2.set_xlabel(xlabel, fontsize=8.6)
        ax2.set_ylabel(ylabel, fontsize=8.6)
        ax2.set_title(
            f"{title_lead}\nyear-only ρ = {row.rho:+.2f} (95% CI {row.lo:+.2f} to {row.hi:+.2f}), "
            f"n = {int(row.n)}, FDR = {fmt_p(row.fdr)}",
            fontsize=8.5,
        )
        ax2.legend(fontsize=7.6, frameon=True, fancybox=False, edgecolor="#cccccc")
        ax2.grid(alpha=.3)

    ax_a = fig.add_subplot(GS[0, 1])
    # Raw 3-cone time (faster to the left) so the published ρ = −0.65 matches the downward slope.
    scatter_panel(
        ax_a, "three_cone", "pressure_rate",
        xlabel="3-cone (s)   ← faster",
        ylabel="Pressure rate",
        title_lead="3-cone vs pressure  (holds within subtype)",
    )
    ax_b = fig.add_subplot(GS[1, 1])
    scatter_panel(
        ax_b, "burst_0_100", "tfl_rate",
        xlabel="Burst Score (0–100)",
        ylabel="TFL per snap",
        title_lead="Burst Score vs TFL  (best new production link)",
    )

    fig.text(
        0.012, 0.012,
        "Sample: 2023–2025 rookie DL, REG snaps that stood, lined up EDGE/INTERIOR_LINE.  "
        "Rates ≥100 snaps; run rates ≥50 run snaps; penetration ≥50 tracked snaps; time to pressure ≥5 pressures.  "
        "No draft slot used.  † Timed drill (lower raw time is faster) — sign-flipped in the heat map only.  "
        "The two scatter panels use raw (unflipped) values.",
        fontsize=7.5,
    )
    if path is None:
        path = FIGS / "fig19_dl_recheck.png"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def fig19_from_cache(path: Path | None = None) -> Path:
    """Redraw Figure 19 from saved CSVs without rerunning the tests."""
    t = pd.read_csv(OUT / "dl_recheck_tests.csv")
    d = pd.read_csv(OUT / "dl_recheck_players.csv")
    return fig19(t, d, path)


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
    import sys
    if "--figure-only" in sys.argv:
        fig19_from_cache()
    else:
        main()
