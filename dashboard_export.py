#!/usr/bin/env python3
"""Export everything the coach dashboard (Page/canvas) embeds: out/dashboard_data.json (+ out/dashboard_data.ts.txt).

Sources (derived tables only; no raw Kaggle tracking data is read or written):
  out/scorecard.csv, scorecard_full.csv, scorecard_weight.csv   verdicts, size-controlled rho, CI, n, coach lines
  out/*_robust_players.csv, wr_route_lead_players.csv            simple fitted models for TRANSLATES / LEANS rows
  data/players.csv + combine_results.csv                         2023-25 percentile tables (quantiles only, no names)
Draft slot / pick / round is never read or exported (asserted below).

Prediction model per TRANSLATES/LEANS row with a typed Combine test:
  y = b0 + b_test*test + b_wt*weight + b_ht*height [+ role dummy] + draft-year dummies (OLS, same sample and outcome
  column as the size-controlled rho). Year dummies are set to their sample mean for prediction.
Usage: python3 dashboard_export.py
"""
from __future__ import annotations
import json, warnings
import numpy as np, pandas as pd
import scorecard as SC

warnings.filterwarnings("ignore")
OUT, DATA = SC.OUT, SC.OUT.parent / "data"
TYPED = ["forty", "ten_yd_split", "vertical", "broad_jump", "three_cone", "short_shuttle"]
PCT_FEATS = TYPED + ["combine_weight", "combine_height"]
LOWER_BETTER = {"forty", "ten_yd_split", "three_cone", "short_shuttle"}
QS = list(range(0, 101, 10))


def assert_clean(*dfs):
    for d in dfs:
        bad = [c for c in d.columns if any(k in c.lower() for k in ("draft_pick", "draft_round", "slot", "udfa", "overall_pick"))]
        assert not bad, f"draft slot column present: {bad}"


def _f(v) -> str:
    v = round(float(v), 2)
    return f"{v:+.2f}"


def js_line(x) -> str:
    """Python mirror of the dashboard's template for DOESN'T TRANSLATE / SIZE, NOT SPEED / TOO FEW rows (checked against scorecard.csv)."""
    tp, op = SC.TEST_PHRASE[x.test], SC.OUT_INFO[x.outcome][1]
    tl = tp[0].lower() + tp[1:]
    if x.verdict == "SIZE, NOT SPEED":
        return f"{tp} looks tied to {op} (year-controlled {_f(x.rho_raw)}), but that is body size: it drops to {_f(x.rho_size)} once weight, height{' and role' if x.subgroup == 'All' and x.group in ('DL', 'DB') else ''} are held fixed."
    if x.verdict == "TOO FEW TO TELL":
        return f"Only {int(x.n)} players. Too few to say whether {tl} goes with {op}."
    return f"No sign that {tl} shows up as {op} (ρ {_f(x.rho_size)}, CI {_f(x.ci_lo)} to {_f(x.ci_hi)}, n {int(x.n)})."


def scorecard_blocks():
    card = pd.read_csv(OUT / "scorecard.csv"); full = pd.read_csv(OUT / "scorecard_full.csv"); w = pd.read_csv(OUT / "scorecard_weight.csv")
    assert_clean(card, full, w)
    r = lambda v, d=2: None if pd.isna(v) else round(float(v), d)
    cardkeys = set(zip(card.group, card.subgroup, card.test, card.outcome))
    rows = []
    for x in full.itertuples():
        is_card = (x.group, x.subgroup, x.test, x.outcome) in cardkeys
        coach = x.coach_line
        if not is_card and x.verdict in ("DOESN'T TRANSLATE", "SIZE, NOT SPEED", "TOO FEW TO TELL") and js_line(x) == x.coach_line:
            coach = ""  # the page rebuilds this line from the row's own numbers with the same template (verified equal here)
        elif x.verdict == "TOO FEW TO TELL" and not is_card:
            coach = ""
        okci = x.n >= 15  # bootstrap CIs are degenerate (endpoints at +-1) below n = 15: hide them
        rows.append([x.group, x.subgroup, x.test, x.outcome, int(x.n), r(x.rho_size), r(x.ci_lo) if okci else None, r(x.ci_hi) if okci else None, r(x.rho_raw), r(x.p_perm, 4), r(x.fdr_q, 3),
                     x.verdict, x.classes_helped if isinstance(x.classes_helped, str) else "", coach, 1 if is_card else 0])
    cardrows = []
    w4 = w.sort_values(["group", "fdr_q", "p_perm"]).groupby("group").head(4)  # top 4 weight rows per group (smallest q)
    wrows = [[x.group, x.outcome_label, int(x.n), r(x.rho_raw), r(x.rho_height_ctrl), r(x.ci_lo), r(x.ci_hi), r(x.fdr_q)] for x in w4.itertuples()]
    labels = full.drop_duplicates("test").set_index("test").test_label.to_dict()
    olabels = full.drop_duplicates("outcome").set_index("outcome").outcome_label.to_dict()
    return rows, cardrows, wrows, labels, olabels, full


def pct_tables():
    players = pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "draft_year", "nfl_position"])  # only these columns are read
    comb = pd.read_csv(DATA / "combine_results.csv", usecols=lambda c: c in {"nfl_id", "draft_year"} | set(PCT_FEATS))
    M = players.merge(comb, on=["nfl_id", "draft_year"], how="left")
    assert_clean(M)
    grp = {"WR": "WR", "TE": "TE", "CB": "CB", "FS": "S", "SS": "S", "DE": "Edge", "OLB": "Edge", "DT": "Interior", "NT": "Interior"}
    M["role"] = M.nfl_position.map(grp); M = M[M.role.notna()].copy()
    M["group"] = M.role.map({"WR": "WR", "TE": "TE", "CB": "DB", "S": "DB", "Edge": "DL", "Interior": "DL"})
    for c in PCT_FEATS:
        M[c] = pd.to_numeric(M[c], errors="coerce")
    out = {}
    for key, sub in [("WR", M[M.group == "WR"]), ("TE", M[M.group == "TE"]), ("DB", M[M.group == "DB"]), ("DL", M[M.group == "DL"]),
                     ("CB", M[M.role == "CB"]), ("S", M[M.role == "S"]), ("Edge", M[M.role == "Edge"]), ("Interior", M[M.role == "Interior"])]:
        out[key] = {c: [int(sub[c].notna().sum())] + [round(float(v), 2) for v in sub[c].dropna().quantile([q / 100 for q in QS])] for c in PCT_FEATS if sub[c].notna().sum() >= 8}
    return out


def models(full):
    """One OLS per TRANSLATES/LEANS cell, fit on the AS-REPORTED outcome (audit fix 11/2026: it used the shrunk rate, whose residual SD is ~half the
    as-reported one, so the old 80% range covered only ~50% of real pressure rates). Range = t quantile x residual SD x sqrt(1 + 1/n + z' C z),
    a prediction interval for a NEW player (residual variance + estimation variance); z = (test, weight, height[, role]) minus the sample mean and
    C the matching block of (X'X)^-1. Year effects are set to the sample mean."""
    from scipy import stats as st
    F = SC._frames()
    rl = pd.read_csv(OUT / "wr_route_lead_players.csv")
    keep = full[full.verdict.isin(["TRANSLATES", "LEANS"]) & full.test.isin(TYPED) & (full.subgroup == "All")]  # pooled fits; DL/DB role enters as a dummy
    res = []; cov_rows = []
    for r in keep.itertuples():
        fr = rl if r.outcome == "break_y" else F[("DL", r.subgroup) if r.group == "DL" else (r.group, "All")]
        rolecol = "subtype" if r.group == "DL" and r.subgroup == "All" else ("role" if r.group == "DB" else None)
        rawc = "break_raw" if r.outcome == "break_y" else (r.outcome + "_raw" if (r.outcome + "_raw") in fr.columns else r.outcome)
        cols = list(dict.fromkeys([r.test, r.outcome, rawc, "draft_year", "combine_weight", "combine_height"] + ([rolecol] if rolecol else [])))
        s = fr[cols].dropna().copy()
        assert len(s) == int(r.n), (r.test, r.outcome, len(s), r.n)  # displayed n == n used
        yrs = sorted(s.draft_year.unique())[1:]
        X = [np.ones(len(s)), s[r.test].to_numpy(float), s.combine_weight.to_numpy(float), s.combine_height.to_numpy(float)]
        names = ["b0", "test", "wt", "ht"]
        role_levels = None
        if rolecol:
            role_levels = sorted(s[rolecol].unique()); base = role_levels[0]
            X.append((s[rolecol] != base).astype(float).to_numpy()); names.append("role")
        ydum = [(s.draft_year == y).astype(float).to_numpy() for y in yrs]
        Xm = np.column_stack(X + ydum); y = s[rawc].to_numpy(float)
        beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
        resid = y - Xm @ beta; k = Xm.shape[1]; dof = len(s) - k; sd = float(np.sqrt((resid ** 2).sum() / max(dof, 1)))
        XtXi = np.linalg.inv(Xm.T @ Xm); h = np.einsum("ij,jk,ik->i", Xm, XtXi, Xm)
        tq = float(st.t.ppf(0.90, dof))
        loo = resid / (1 - h)  # leave-one-out prediction errors -> honest coverage check of the 80% range
        cov = float((np.abs(loo) <= tq * sd * np.sqrt(1 + h / (1 - h))).mean())
        cov_rows.append(dict(group=r.group, test=r.test, outcome=r.outcome, n=len(s), outcome_scale="as-reported" if rawc != r.outcome else "unshrunk", resid_sd=sd,
                             loo_coverage_80=cov))
        zi = slice(1, len(X)); C = XtXi[zi, zi]; zm = Xm[:, zi].mean(0)
        ymean = [float(d.mean()) for d in ydum]; yconst = float(np.dot(beta[len(X):], ymean))
        b = dict(zip(names, beta[:len(X)]))
        entry = dict(g=r.group, sg=r.subgroup, t=r.test, o=r.outcome, n=int(len(s)), v=r.verdict,
                     c=round(float(b["b0"] + yconst), 4), bt=round(float(b["test"]), 5), bw=round(float(b["wt"]), 5), bh=round(float(b["ht"]), 5),
                     sd=round(sd, 4), ym=round(float(np.median(y)), 4), yq=[round(float(v), 4) for v in np.quantile(y, [i / 10 for i in range(11)])],
                     tr=[round(float(s[r.test].min()), 2), round(float(s[r.test].max()), 2)],
                     tq=round(tq, 4), zm=[float(f"{v:.6g}") for v in zm], cz=[[float(f"{v:.6g}") for v in row] for row in C])
        if rolecol:
            entry["role"] = dict(base=str(base), other=str(role_levels[1]), br=round(float(b["role"]), 4), share=round(float((s[rolecol] != base).mean()), 3))
        res.append(entry)
    pd.DataFrame(cov_rows).to_csv(OUT / "audit_prediction_coverage.csv", index=False)
    return res


def main():
    rows, cardrows, wrows, labels, olabels, full = scorecard_blocks()
    pct = pct_tables(); mods = models(full)
    data = dict(rows=rows, card=cardrows, weight=wrows, tlabels=labels, olabels=olabels, pct=pct, models=mods,
                note="Generated by dashboard_export.py from out/scorecard*.csv and the robust player tables. No draft slot.")
    (OUT / "dashboard_data.json").write_text(json.dumps(data, separators=(",", ":")))
    (OUT / "dashboard_data.ts.txt").write_text(ts_literals(data))
    sizes = {k: len(json.dumps(v, separators=(",", ":"))) for k, v in data.items()}
    print("sizes (bytes):", sizes, "| models:", len(mods))


def ts_literals(d):
    """TypeScript const literals pasted into the canvas source (one row per line)."""
    J = lambda v: json.dumps(v, separators=(",", ":"), ensure_ascii=False)
    L = ["const RAW: (string | number | null)[][] = ["] + ["  " + J(r) + "," for r in d["rows"]] + ["];"]
    L += ["const WRAW: (string | number)[][] = ["] + ["  " + J(r) + "," for r in d["weight"]] + ["];"]
    L += ["const PCT: Record<string, Record<string, number[]>> = {"]
    for g in ["WR", "TE", "DB", "DL", "CB", "S", "Edge", "Interior"]:
        L.append(f"  {g}: {{")
        L += [f"    {k}: {J(v)}," for k, v in d["pct"][g].items()]
        L.append("  },")
    L.append("};")
    L += ["const MODELS: Model[] = ["] + ["  " + J(m) + "," for m in d["models"]] + ["];"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
