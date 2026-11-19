#!/usr/bin/env python3
"""What translates and what doesn't: the scorecard (METRICS.md section 9).

Reads only saved robust outputs (no recomputation, no draft slot):
  out/dl_robust_tests.csv, out/pos_robust_tests.csv, out/wr_route_lead_cells.csv
Writes out/scorecard_full.csv, out/scorecard.csv, out/scorecard_weight.csv, out/scorecard.md
"""
from __future__ import annotations
import numpy as np, pandas as pd
from scipy import stats
import robust as R
from dl_recheck import OUT

TESTS = ["forty", "ten_yd_split", "vertical", "broad_jump", "three_cone", "short_shuttle", "c_top_mph", "burst_0_100", "c_decel", "c_accel"]
TRACKING_TESTS = {"c_top_mph", "burst_0_100", "c_decel", "c_accel", "c_t10_derived", "c_t20_derived", "c_40_accel"}
TEST_LABEL = {"forty": "40-yard dash", "ten_yd_split": "10-yard split", "vertical": "Vertical jump", "broad_jump": "Broad jump",
              "three_cone": "3-cone", "short_shuttle": "Short shuttle", "c_top_mph": "Combine top speed (tracking)",
              "burst_0_100": "Burst Score (tracking)", "c_decel": "DB-drill braking (tracking)", "c_accel": "DB-drill re-burst (tracking)"}
TEST_PHRASE = {"forty": "A faster 40", "ten_yd_split": "A faster 10-yard split", "vertical": "A higher vertical",
               "broad_jump": "A longer broad jump", "three_cone": "A faster 3-cone", "short_shuttle": "A faster shuttle",
               "c_top_mph": "A higher Combine top speed", "burst_0_100": "A higher Burst Score",
               "c_decel": "Harder braking in the DB-drill", "c_accel": "A quicker re-burst in the DB-drill"}
# outcome -> (label, phrase for the BETTER result)
OUT_INFO = {
    "sunday_speed_mph": ("Game speed on deep routes (Sunday Speed)", "faster game speed on deep routes"),
    "sep_all_mean": ("Separation, all routes", "more separation on routes"),
    "break_y": ("Separation, break routes", "more separation on break routes"),
    "pressure_rate": ("Pressure rate", "a higher pressure rate"),
    "sack_rate": ("Sack rate", "a higher sack rate"),
    "tfl_rate": ("Tackles for loss", "more tackles for loss"),
    "run_stop_rate": ("Run stops", "more run stops"),
    "speed_1s_mph": ("Get-off (speed 1 s after snap)", "a faster first second off the snap"),
    "tackle_rate": ("Tackle rate", "more tackles per snap"),
    "close_rate_mph": ("Closing speed to the tackle", "faster closing speed to the tackle"),
    "pfr_yds_tgt": ("Yards allowed per target (PFR)", "fewer yards allowed per target"),
    "pfr_mtkl_pct": ("Missed-tackle % (PFR)", "fewer missed tackles"),
}
GROUP_OUTCOMES = {
    "WR": ["sunday_speed_mph", "sep_all_mean", "break_y"], "TE": ["sep_all_mean", "break_y"],
    "DB": ["tackle_rate", "tfl_rate", "close_rate_mph", "pfr_yds_tgt", "pfr_mtkl_pct", "sunday_speed_mph"],
    "DL": ["pressure_rate", "sack_rate", "tfl_rate", "run_stop_rate", "speed_1s_mph"],
}
MIN_CARD, MAX_CARD, MIN_N = 4, 8, 25


# ---------------------------------------------------------------- "raw" = year-controlled only (corrected 11/2026)
SIZE_COLS = ["combine_weight", "combine_height"]
YEAR_B, YEAR_SEED = 2000, R.SEED


def _year_resid(v: np.ndarray, yr: np.ndarray) -> np.ndarray:
    out = v.astype(float).copy()
    for k in np.unique(yr):
        m = yr == k
        out[m] = v[m] - v[m].mean()
    return out


def year_partial(x, y, yr) -> float:
    """Earlier-reports convention: demean both sides within draft-year cells, then Spearman of the residuals."""
    rx, ry = _year_resid(np.asarray(x, float), np.asarray(yr)), _year_resid(np.asarray(y, float), np.asarray(yr))
    if np.unique(rx).size < 2 or np.unique(ry).size < 2:
        return np.nan
    return float(stats.spearmanr(rx, ry)[0])


def year_partial_ci(x, y, yr, B=YEAR_B, seed=YEAR_SEED):
    x, y, yr = np.asarray(x, float), np.asarray(y, float), np.asarray(yr)
    n = len(x); idx = np.random.default_rng(seed).integers(0, n, size=(B, n))
    xi, yi, yri = x[idx], y[idx], yr[idx]
    rx, ry = np.empty((B, n)), np.empty((B, n))
    for k in np.unique(yr):
        m = (yri == k); cnt = m.sum(1, keepdims=True).clip(min=1)
        mx = (xi * m).sum(1, keepdims=True) / cnt; my = (yi * m).sum(1, keepdims=True) / cnt
        rx = np.where(m, xi - mx, rx); ry = np.where(m, yi - my, ry)
    ax, ay = stats.rankdata(rx, axis=1), stats.rankdata(ry, axis=1)
    ax = ax - ax.mean(1, keepdims=True); ay = ay - ay.mean(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (ax * ay).sum(1) / np.sqrt((ax ** 2).sum(1) * (ay ** 2).sum(1))
    r = r[np.isfinite(r)]
    return tuple(np.percentile(r, [2.5, 97.5])) if len(r) > 200 else (np.nan, np.nan)


def _frames() -> dict:
    dl = pd.read_csv(OUT / "dl_robust_players.csv")
    wt = pd.read_csv(OUT / "wr_te_robust_players.csv")
    db = pd.read_csv(OUT / "db_robust_players.csv")
    rl = pd.read_csv(OUT / "wr_route_lead_players.csv")
    return {("DL", "DL"): dl, ("DL", "All"): dl, ("DL", "Edge"): dl[dl.subtype == "Edge"], ("DL", "Interior"): dl[dl.subtype == "Interior"],
            ("WR", "All"): wt[wt.pos_group == "WR"], ("TE", "All"): wt[wt.pos_group == "TE"], ("DB", "All"): db, ("WR", "RL"): rl}


RL_SIGN = {"three_cone": -1, "short_shuttle": -1, "ten_yd_split": -1, "vertical": 1, "burst_0_100": 1}


def year_raw(fr: pd.DataFrame, test: str, outcome: str):
    """(rho, lo, hi, n): year-controlled Spearman of `test` vs the same outcome the size-controlled fit uses, same sample as the robust fit."""
    rc = outcome  # audit fix 11/2026: same outcome as the size-controlled fit
    s = fr[list(dict.fromkeys([test, outcome, rc, "draft_year"] + SIZE_COLS))].dropna()
    if len(s) < 12 or s[test].nunique() < 3 or s[rc].nunique() < 3:
        return (np.nan,) * 3 + (len(s),)
    x, y, yr = s[test].to_numpy(float), s[rc].to_numpy(float), s["draft_year"].to_numpy()
    lo, hi = year_partial_ci(x, y, yr)
    return year_partial(x, y, yr), lo, hi, len(s)


def add_year_only(t: pd.DataFrame) -> pd.DataFrame:
    """Replace plain pooled Spearman by the year-controlled Spearman on the same outcome as the size-controlled fit (+ as-reported check column)."""
    F = _frames(); t = t.copy()
    t["rho_unadjusted"] = t.rho_raw
    # audit fix 11/2026: the year-only "raw" link is computed on the SAME outcome the size-controlled fit uses (shrunk rate where one exists),
    # so the SIZE test compares like with like; the as-reported (unshrunk) year-controlled value is kept in rho_asreported.
    t["raw_def"] = "year-controlled Spearman (demean within draft year), same outcome as the size-controlled fit"
    new = {"rho_raw": [], "raw_lo": [], "raw_hi": [], "n_raw": [], "rho_asreported": []}
    for _, r in t.iterrows():
        rl = r.outcome == "break_y"
        fr = F[("WR", "RL")] if rl else F[(r.card_group, r.subgroup)]
        out_col = "break_y" if rl else r.outcome
        raw_col = "break_raw" if rl else (r.outcome + "_raw" if (r.outcome + "_raw") in fr.columns else r.outcome)
        cols = [r.test, out_col, raw_col, "draft_year"] + SIZE_COLS
        s = fr[list(dict.fromkeys(cols))].dropna()
        x = s[r.test].to_numpy(float) * (RL_SIGN[r.test] if rl else 1)
        y = s[out_col].to_numpy(float); yr = s["draft_year"].to_numpy(); ya = s[raw_col].to_numpy(float)
        if len(s) < 12 or np.unique(x).size < 3 or np.unique(y).size < 3:
            for k in new: new[k].append(np.nan)
            continue
        lo, hi = year_partial_ci(x, y, yr)
        new["rho_raw"].append(year_partial(x, y, yr)); new["raw_lo"].append(lo); new["raw_hi"].append(hi); new["n_raw"].append(len(s))
        new["rho_asreported"].append(year_partial(x, ya, yr))
    for k, v in new.items():
        t[k] = v
    bad = t[(t.n_raw != t.n) & t.n_raw.notna()]
    if len(bad):
        print(f"note: {len(bad)} rows where the year-only sample differs from the robust sample (kept; n_raw column)")
    return t


def load() -> pd.DataFrame:
    d = pd.read_csv(OUT / "dl_robust_tests.csv"); p = pd.read_csv(OUT / "pos_robust_tests.csv")
    d["card_group"] = "DL"; d["subgroup"] = d.group.map({"DL": "All", "Edge": "Edge", "Interior": "Interior"})
    p["card_group"] = p.group; p["subgroup"] = "All"
    p = p[~((p.group.isin(["WR", "TE"])) & (p.outcome == "sep_brk_mean"))]  # superseded by the pre-declared section-8 break family
    t = pd.concat([d, p], ignore_index=True)
    t["orient"] = t.test_good * t.outcome_good
    t["fdr_basis"] = t.group.map(lambda g: "BH over all cells in group (DL/Edge/Interior: 273 each)" if g in ("DL", "Edge", "Interior")
                                 else {"WR": "BH over 68 WR cells", "TE": "BH over 34 TE cells", "DB": "BH over 152 DB cells"}[g])
    # section-8 WR break-route cells (already oriented: + = better test, more separation)
    c = pd.read_csv(OUT / "wr_route_lead_cells.csv")
    c = c[(c.group == "primary") & (c.split == "break")].copy()
    c["card_group"] = "WR"; c["subgroup"] = "All"; c["group"] = "WR"; c["outcome"] = "break_y"
    c["outcome_good"] = 1; c["test_good"] = 1; c["orient"] = 1
    c["fdr_basis"] = "BH over 14 pre-declared WR route cells (section 8)"
    keep = [k for k in t.columns if k in c.columns] 
    t = pd.concat([t, c[keep]], ignore_index=True)
    t = t[t.test.isin(TESTS) & t.outcome.isin(OUT_INFO)].copy().reset_index(drop=True)
    return add_year_only(t)


def verdict(r) -> str:
    if r.n < MIN_N or (r.n_controls == r.n_controls and r.n / (r.n_controls + 1) < 5):
        return "TOO FEW TO TELL"
    ci0 = (r.lo > 0) or (r.hi < 0)
    same = np.sign(r.rho_raw) == np.sign(r.rho_size)
    if r.fdr < 0.05 and ci0 and same and (r.loso_dr2 > 0) and (r.loso_p < 0.10) and (r.loso_pos_folds >= 2) \
            and (not np.isfinite(r.rho_size_unshrunk) or np.sign(r.rho_size_unshrunk) == np.sign(r.rho_size)):
        return "TRANSLATES"
    if abs(r.rho_raw) >= 0.30 and abs(r.rho_size) <= 0.5 * abs(r.rho_raw) and not ci0:
        return "SIZE, NOT SPEED"
    if (ci0 or r.p_perm < 0.05) and same:
        return "LEANS"
    return "DOESN'T TRANSLATE"


def coach(r) -> str:
    tp, (_, op) = TEST_PHRASE[r.test], OUT_INFO[r.outcome]
    tl = tp[0].lower() + tp[1:]
    rs = f"ρ {r.rho_o:+.2f}"
    share = 1 - abs(r.rho_o) / abs(r.rho_raw_o) if abs(r.rho_raw_o) > 0 and np.sign(r.rho_o) == np.sign(r.rho_raw_o) else 0
    if r.verdict == "TRANSLATES":
        return f"{tp} shows up as {op}. It holds after size control and on a held-out draft class ({rs}, n {int(r.n)})."
    if r.verdict == "LEANS":
        side = "tends to go with" if r.rho_o > 0 else "tends to go the WRONG way for"
        body = f" About {share:.0%} of the year-controlled link goes away once weight, height{' and role' if r.subgroup == 'All' and r.card_group in ('DL', 'DB') else ''} are held fixed." if share >= 0.5 else ""
        return f"{tp} {side} {op} ({rs}, n {int(r.n)}), but it does not clear the false-discovery bar.{body}"
    if r.verdict == "SIZE, NOT SPEED":
        return f"{tp} looks tied to {op} (year-controlled {r.rho_raw_o:+.2f}), but that is body size: it drops to {r.rho_o:+.2f} once weight, height{' and role' if r.subgroup == 'All' and r.card_group in ('DL', 'DB') else ''} are held fixed."
    if r.verdict == "TOO FEW TO TELL":
        return f"Only {int(r.n)} players. Too few to say whether {tl} goes with {op}."
    return f"No sign that {tl} shows up as {op} ({rs}, CI {r.lo_o:+.2f} to {r.hi_o:+.2f}, n {int(r.n)})."


def prep(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    s = np.sign(t.orient).replace(0, 1)
    t["rho_o"], t["rho_raw_o"], t["rho_unadj_o"] = t.rho_size * s, t.rho_raw * s, t.rho_unadjusted * s
    t["rho_asrep_o"] = t.rho_asreported * s
    t["lo_o"] = np.where(s > 0, t.lo, -t.hi); t["hi_o"] = np.where(s > 0, t.hi, -t.lo)
    t["raw_lo_o"] = np.where(s > 0, t.raw_lo, -t.raw_hi); t["raw_hi_o"] = np.where(s > 0, t.raw_hi, -t.raw_lo)
    t["verdict"] = t.apply(verdict, axis=1)
    t["classes_helped"] = t.apply(lambda r: f"{int(r.loso_pos_folds)}/{int(r.loso_folds)}" if np.isfinite(r.loso_folds) and r.loso_folds > 0 else "", axis=1)
    t["combine_source"] = np.where(t.test.isin(TRACKING_TESTS), "tracking", "official")
    t["test_label"] = t.test.map(TEST_LABEL); t["outcome_label"] = t.outcome.map(lambda o: OUT_INFO[o][0])
    t["coach_line"] = t.apply(coach, axis=1)
    return t


def pick_rows(full: pd.DataFrame) -> pd.DataFrame:
    chosen = []
    for g, outs in GROUP_OUTCOMES.items():
        sub = full[(full.card_group == g) & (full.subgroup == "All") & full.outcome.isin(outs)]
        rows = []
        for o in outs:
            so = sub[sub.outcome == o]
            if so.empty:
                continue
            ok = so[so.n >= MIN_N]
            pool = ok if len(ok) else so
            rows.append(pool.sort_values(["p_perm", "n"], ascending=[True, False]).index[0])
        rest = sub.drop(index=rows).sort_values("p_perm")
        rest = rest[rest.n >= MIN_N] if (rest.n >= MIN_N).any() else rest
        for i in rest.index:
            if len(rows) >= MIN_CARD:
                break
            rows.append(i)
        chosen += rows[:MAX_CARD]
    card = full.loc[chosen].copy(); card["breakout"] = False
    out = [card]
    dl = card[card.card_group == "DL"]
    for sg in ("Edge", "Interior"):
        b = full[(full.card_group == "DL") & (full.subgroup == sg)]
        b = b.merge(dl[["test", "outcome"]], on=["test", "outcome"]); b["breakout"] = True
        out.append(b)
    return pd.concat(out, ignore_index=True)


def main() -> None:
    full = prep(load()).reset_index(drop=True)
    cols = ["card_group", "subgroup", "test", "test_label", "combine_source", "outcome", "outcome_label", "n", "rho_raw_o", "raw_lo_o", "raw_hi_o", "rho_unadj_o",
            "rho_o", "lo_o", "hi_o", "p_perm", "fdr", "fdr_basis", "rho_asrep_o", "loso_dr2", "classes_helped", "verdict", "coach_line"]
    ren = {"rho_asrep_o": "rho_asreported_yearctrl", "card_group": "group", "rho_unadj_o": "rho_unadjusted_pooled_shrunk", "rho_raw_o": "rho_raw", "raw_lo_o": "raw_lo", "raw_hi_o": "raw_hi", "rho_o": "rho_size",
           "lo_o": "ci_lo", "hi_o": "ci_hi", "fdr": "fdr_q", "loso_dr2": "oos_delta_r2"}
    full[cols].rename(columns=ren).to_csv(OUT / "scorecard_full.csv", index=False)
    card = pick_rows(full)
    gorder = {"WR": 0, "TE": 1, "DB": 2, "DL": 3}; sorder = {"All": 0, "Edge": 1, "Interior": 2}
    card["_g"] = card.card_group.map(gorder); card["_s"] = card.subgroup.map(sorder)
    card = card.sort_values(["_g", "breakout", "outcome", "_s", "p_perm"]).drop(columns=["_g", "_s"])
    card[cols + ["breakout"]].rename(columns=ren).to_csv(OUT / "scorecard.csv", index=False)

    # weight: the hidden variable (test = weight, controls = draft year + height [+ role])
    d = pd.read_csv(OUT / "dl_robust_tests.csv"); p = pd.read_csv(OUT / "pos_robust_tests.csv")
    w = pd.concat([d, p]); w = w[(w.test == "combine_weight") & (w.outcome_good != 0)].copy()
    w["rho_o"] = w.rho_size * np.where(w.outcome_good > 0, 1, -1)  # + = heavier goes with better result
    w["lo_o"] = np.where(w.outcome_good > 0, w.lo, -w.hi); w["hi_o"] = np.where(w.outcome_good > 0, w.hi, -w.lo)
    F = _frames()
    def wraw(r):
        fr = F[("DL", r.group)] if r.group in ("DL", "Edge", "Interior") else F[(r.group, "All")]
        rc = r.outcome + "_raw" if (r.outcome + "_raw") in fr.columns else r.outcome
        s_ = fr[list(dict.fromkeys(["combine_weight", r.outcome, rc, "draft_year", "combine_height"]))].dropna()
        return year_partial(s_.combine_weight, s_[r.outcome], s_.draft_year) if len(s_) >= 12 else np.nan
    w["rho_raw"] = w.apply(wraw, axis=1)
    w["rho_raw_o"] = w.rho_raw * np.where(w.outcome_good > 0, 1, -1)
    w = w[["group", "outcome", "outcome_label", "n", "rho_raw_o", "rho_o", "lo_o", "hi_o", "p_perm", "fdr", "loso_dr2", "loso_pos_folds"]]
    w.columns = ["group", "outcome", "outcome_label", "n", "rho_raw", "rho_height_ctrl", "ci_lo", "ci_hi", "p_perm", "fdr_q", "oos_delta_r2", "classes_helped"]
    w = w[w.n >= MIN_N].sort_values("p_perm")
    w.to_csv(OUT / "scorecard_weight.csv", index=False)
    write_md(card, w, full)
    print(card[card.card_group.notna()].groupby(["card_group", "verdict"]).size())


def fp(p: float) -> str:
    """Permutation p with 10,000 shuffles cannot go below 1/10,001: print it as a bound, never as 0.000."""
    return "" if not np.isfinite(p) else ("<0.001" if p < 0.001 else f"{p:.3f}")


def fq(q: float) -> str:
    return "" if not np.isfinite(q) else ("<0.01" if q < 0.01 else f"{q:.2f}")


def fmt_row(r) -> str:
    q = "" if not np.isfinite(r.fdr) else fq(r.fdr)
    return (f"| {r.test_label} | {r.outcome_label} | {int(r.n)} | {r.rho_raw_o:+.2f} | {r.rho_o:+.2f} ({r.lo_o:+.2f} to {r.hi_o:+.2f}) | {fp(r.p_perm)} | {q} | "
            f"{r.loso_dr2:+.2f} ({r.classes_helped}) | **{r.verdict}** | {r.coach_line} |")


def write_md(card, w, full) -> None:
    L = ["# What translates and what doesn't: Combine → regular-season scorecard", "",
         "Generated by `scorecard.py` from the saved robust outputs (METRICS.md §9). ρ is oriented so **+ = a better athlete goes with a better result**. "
         "Year-controlled ρ is the raw link: both sides demeaned within draft year, on the same outcome as the size-controlled fit (shrunk rate where one exists), nothing else held fixed (METRICS.md §9, audit fix 11/2026; the as-reported-rate version is in `scorecard_full.csv` as `rho_asreported_yearctrl`). Size-controlled ρ also holds weight and height fixed (DB also CB vs S; DL also Edge vs Interior). q = BH false-discovery rate over the full family; "
         "ΔR² = held-out-draft-class gain over a size-only model (classes that improved). Draft slot is never used.", ""]
    H = "| Test | Result | n | year-controlled ρ | size-controlled ρ (95% CI) | perm p | q | out-of-sample ΔR² | Verdict | Coach line |\n|---|---|---:|---:|---|---:|---:|---|---|---|"
    for g, title in [("WR", "Wide receivers"), ("TE", "Tight ends"), ("DB", "Defensive backs (CB + S)"), ("DL", "Defensive line (all DL)")]:
        L += [f"## {title}", "", H]
        main_rows = card[(card.card_group == g) & (~card.breakout)]
        for _, r in main_rows.iterrows():
            L.append(fmt_row(r))
        L.append("")
        if g == "DL":
            L += ["**Edge vs Interior breakout (same test × result as above):**", "", "| Test | Result | Edge n | Edge ρ (CI) | Edge verdict | Interior n | Interior ρ (CI) | Interior verdict |", "|---|---|---:|---|---|---:|---|---|"]
            for _, r in main_rows.iterrows():
                e = card[(card.breakout) & (card.subgroup == "Edge") & (card.test == r.test) & (card.outcome == r.outcome)]
                i = card[(card.breakout) & (card.subgroup == "Interior") & (card.test == r.test) & (card.outcome == r.outcome)]
                def cell(x):
                    return ("—", "—", "—") if x.empty else (str(int(x.n.iloc[0])), f"{x.rho_o.iloc[0]:+.2f} ({x.lo_o.iloc[0]:+.2f} to {x.hi_o.iloc[0]:+.2f})", x.verdict.iloc[0])
                (en, ec, ev), (inn, ic, iv) = cell(e), cell(i)
                L.append(f"| {r.test_label} | {r.outcome_label} | {en} | {ec} | {ev} | {inn} | {ic} | {iv} |")
            L.append("")
    L += ["## The hidden variable: weight", "",
          "Weight as the test, controlling draft year and height (+ = heavier goes with the better result). Rows with n ≥ 25, sorted by permutation p.", "",
          "| Group | Result | n | year-controlled ρ | ρ (height held) (95% CI) | perm p | q |", "|---|---|---:|---:|---|---:|---:|"]
    for _, r in w.head(12).iterrows():
        L.append(f"| {r.group} | {r.outcome_label} | {int(r.n)} | {r.rho_raw:+.2f} | {r.rho_height_ctrl:+.2f} ({r.ci_lo:+.2f} to {r.ci_hi:+.2f}) | {fp(r.p_perm)} | {fq(r.fdr_q)} |")
    L += ["", "## Selection and caveats", "",
          "- One row per group × result: the test with the smallest permutation p among tests with n ≥ 25 (rule fixed in METRICS.md §9). The full grid is `out/scorecard_full.csv`.",
          f"- SIZE, NOT SPEED rows in the full grid: {int((full.verdict == 'SIZE, NOT SPEED').sum())} (all DL; {int(((full.verdict == 'SIZE, NOT SPEED') & full.index.isin(card.index)).sum())} on the card). Get-off speed rows are the clearest case: year-controlled ρ of about +0.65 to +0.78 falls to roughly +0.06 to +0.20 once weight, height and role are held fixed.",
          f"- Multiple testing: the grid has {int((full.n >= MIN_N).sum())} cells with n ≥ {MIN_N}; about {0.05 * int((full.n >= MIN_N).sum()):.0f} would reach perm p < 0.05 by chance alone, and {int(((full.n >= MIN_N) & (full.p_perm < 0.05)).sum())} do. Only {int(((full.n >= MIN_N) & (full.fdr < 0.05)).sum())} clear q < 0.05 (the TRANSLATES rows). LEANS rows are nominal-p findings and should be read as leads. The card shows the best-p test per result, so card ρ values are optimistic by construction.",
          "- Confidence intervals are 2,000-resample percentile bootstraps over players (the whole fit is redone in each resample). Below n = 15 the bootstrap is unreliable and the dashboard hides the interval.",
          "- WR break-route separation comes from the pre-declared re-test (METRICS.md §8); the broader break family in the first robust pass is not used.",
          "- Same 2023–25 players generated the leads and test them; held-out draft classes are the only out-of-sample check, and there are three.",
          "- A TOO FEW or DOESN'T TRANSLATE verdict is absence of evidence at this sample size, not proof of no effect."]
    (OUT / "scorecard.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
