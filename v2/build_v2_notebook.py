#!/usr/bin/env python3
"""Builds v2/bdb2027_v2.ipynb (branch v2-review, 11/2026). Every statistic is recomputed LIVE from the competition CSVs;
no precomputed result table is read. The gate raises (FAIL) if the data are not attached. Aggregate output only.
Run it, then v2/render_writeup.py turns results_v2.json into writeup_for_kaggle_v2.md."""
import json, hashlib, pathlib
HERE = pathlib.Path(__file__).resolve().parent
LIB = (HERE / "v2_analysis.py").read_text()
md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")}
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n")}
C = []
C.append(md("""
# The Combine works, but read it right (v2, live recompute)
NFL Big Data Bowl 2027 · Open Track. Every number in the v2 writeup is recomputed here from the competition files (seed 2027).
If the competition data are not attached, the gate cell stops with an error: it never falls back to a saved figure.
Source: NFL Big Data Bowl 2027 competition data (CC BY-NC 4.0). Draft slot, pick and round are never used as variables.
"""))
C.append(md("## Shared code: rank partial correlation, Freedman–Lane permutation, bootstrap, BH, MDE, best-of-N"))
C.append(code(LIB))
C.append(code(r'''
import json, time, warnings
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore", category=RuntimeWarning)
plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": .25, "figure.dpi": 110, "savefig.dpi": 150})
CLS = {2023: "#009E73", 2024: "#E69F00", 2025: "#7570B3"}   # green/orange/purple = 2023/2024/2025 classes, always
BLUE, GREY, RED = "#0072B2", "#8a8a8a", "#D55E00"
ND = "NOT DETECTED (low power)"
SAVE = Path("/kaggle/working/figs") if Path("/kaggle/working").exists() else Path("figs"); SAVE.mkdir(parents=True, exist_ok=True)
R = {}                                  # every reported number lands here, then results_v2.json
SZ = ("draft_year", "combine_weight", "combine_height")
def cell(df, x, y, ctrl=SZ, P=10000, B=2000):
    r, n, *_ = rank_partial(df, x, y, ctrl); lo, hi = boot_ci(df, x, y, ctrl, B=B); p = perm_p(df, x, y, ctrl, P=P)
    return dict(rho=r, n=n, lo=lo, hi=hi, p=p, mde=mde(n, len(ctrl)))
import textwrap
def footer(fig, text):
    fig.text(.01, .01, "\n".join(textwrap.wrap(text, int(fig.get_size_inches()[0] * 17))), fontsize=7.5, color="#444", va="bottom")
'''))
C.append(md("## The gate: Combine tracking → regular-season game tracking (receivers)"))
C.append(code(r'''
t0 = time.time()
COMP = find_comp()                       # raises RuntimeError -> GATE FAIL if the competition data are not attached
pl, cr, pp, ct = load(COMP)
feat = combine_tracking_features(ct)
plays = wr_play_speeds(COMP, set(pl.nfl_id[pl.nfl_position == "WR"]))
WRALL = wr_table(pl, cr, pp, feat, plays)
FUN, WR = funnel(WRALL); R["funnel"] = FUN
print("Funnel: {listed} receivers listed -> {tracked_40} with a tracked 40 -> {deep20} with 20+ deep routes -> {both} with both".format(**FUN))
print(f"Undrafted (descriptive only): {FUN['undrafted_in_sample']} of {FUN['both']} in the sample vs {FUN['undrafted_listed']} of {FUN['listed']} listed")
g = cell(WR, "c_top_mph", "sunday_speed_mph"); R["gate"] = g
WRF = family(WRALL, ["c_top_mph", "vertical", "broad_jump", "short_shuttle"], ["sunday_speed_mph", "sep_all_mean", "break_y"], SZ)
gq = float(WRF.query("test == 'c_top_mph' and outcome == 'sunday_speed_mph'").q.iloc[0]); R["gate"]["q"] = gq
print(f"Combine top speed vs Sunday Speed, size-adjusted: rho {g['rho']:+.2f} (95% CI {g['lo']:+.2f} to {g['hi']:+.2f}), n {g['n']}, permutation p {g['p']:.4f}, BH q {gq:.3f}")
ok = g["rho"] > 0 and g["lo"] > 0 and gq < 0.05
if not ok:
    raise RuntimeError("GATE: FAIL (live recompute does not support the Combine-to-game link)")
print("GATE (Combine tracking -> regular-season performance): PASS", f"[{time.time() - t0:.0f}s]")
'''))
C.append(md("## Table 1: who is in the sample, and does the receiver link survive other samples?"))
C.append(code(r'''
T1 = {"Size-adjusted (class, weight, height)": g,
      "Class only (no size adjustment)": cell(WR, "c_top_mph", "sunday_speed_mph", ("draft_year",)),
      "Laser-timed 40 instead of tracked top speed": cell(WR, "forty", "sunday_speed_mph"),
      "Rookie-season routes only (20+)": cell(WRALL, "c_top_mph", "sunday_rookie"),
      "First 20 deep routes only": cell(WR, "c_top_mph", "sunday_first20"),
      "First 30 deep routes only": cell(WRALL, "c_top_mph", "sunday_first30")}
R["table1"] = T1
for k, v in T1.items():
    print(f"{k:45s} n {v['n']:3d}  rho {v['rho']:+.2f} ({v['lo']:+.2f}, {v['hi']:+.2f})")
x, y = WR.c_top_mph, WR.sunday_speed_mph
rng = np.random.default_rng(SEED); bs = [np.polyfit(x.values[i], y.values[i], 1)[0] for i in (rng.integers(0, len(WR), len(WR)) for _ in range(2000))]
R["slope"] = dict(b=float(np.polyfit(x, y, 1)[0]), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), theil_sen=float(stats.theilslopes(y, x)[0]))
R["by_class"] = {}
for c in (2023, 2024, 2025):
    d = WR[WR.draft_year == c]; f = lambda dd: stats.spearmanr(dd.c_top_mph, dd.sunday_speed_mph)[0]
    lo, hi = boot_ci(d, "c_top_mph", "sunday_speed_mph", (), stat=f); R["by_class"][c] = dict(rho=float(f(d)), n=len(d), lo=lo, hi=hi)
print("slope", {k: round(v, 2) for k, v in R["slope"].items()}); print("by class", {k: (round(v["rho"], 2), v["n"]) for k, v in R["by_class"].items()})
'''))
C.append(code(r'''
# Figure 1: receiver speed carries to Sunday (title has no "drafted": 7 of the 62 are undrafted)
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
xs = np.linspace(x.min(), x.max(), 50); bb = []
rng = np.random.default_rng(SEED)
for _ in range(1000):
    i = rng.integers(0, len(WR), len(WR)); bb.append(np.polyval(np.polyfit(x.values[i], y.values[i], 1), xs))
a.fill_between(xs, *np.percentile(bb, [2.5, 97.5], axis=0), color="#ddd", lw=0)
a.plot(xs, np.polyval(np.polyfit(x, y, 1), xs), color="k", lw=1.8)
for c, col in CLS.items():
    m = WR.draft_year == c; a.scatter(x[m], y[m], s=24, color=col, edgecolor="white", lw=.4, label=f"{c} class (n={m.sum()})")
a.set_xlabel("Combine top speed in the 40-yard dash (mph, tracked at 10 Hz)"); a.set_ylabel("Sunday Speed (mph)\n90th-percentile top speed on deep routes")
a.set_title("A receiver's 40 speed shows up on Sunday", loc="left", fontweight="bold")
a.text(.02, .97, f"size-adjusted ρ {g['rho']:+.2f} [{g['lo']:+.2f}, {g['hi']:+.2f}], n {g['n']}\n{R['slope']['b']:+.2f} mph per mph [{R['slope']['lo']:.2f}, {R['slope']['hi']:.2f}]",
       transform=a.transAxes, va="top", fontsize=8.5)
a.legend(loc="lower right", fontsize=8, frameon=False)
rows = [(f"{c} class", v["rho"], v["lo"], v["hi"], v["n"], CLS[c]) for c, v in R["by_class"].items()]
rows.append(("All, class held fixed", T1["Class only (no size adjustment)"]["rho"], T1["Class only (no size adjustment)"]["lo"], T1["Class only (no size adjustment)"]["hi"], g["n"], "k"))
for i, (lab, r, lo, hi, n, col) in enumerate(rows[::-1]):
    b.plot([lo, hi], [i, i], color=col, lw=2); b.scatter([r], [i], color=col, s=40, zorder=3, marker="D" if col == "k" else "o")
    b.text(1.02, i, f"n={n}", va="center", fontsize=8)
b.set_yticks(range(len(rows))); b.set_yticklabels([r[0] for r in rows[::-1]]); b.axvline(0, color="k", ls=":", lw=.8); b.set_xlim(-.1, 1.1)
b.set_xlabel("ρ, 40 top speed vs Sunday Speed (95% CI)"); b.set_title("Same sign in every draft class", loc="left", fontweight="bold")
footer(fig, f"Sample: {g['n']} receivers (2023–25 classes; {FUN['undrafted_in_sample']} undrafted) with a tracked 40 and 20+ regular-season deep routes (go, post, corner, wheel). "
       "Line and band: straight-line fit, 1,000 player bootstraps. Right: within-class ρ, no size adjustment; bottom row holds class fixed.")
fig.tight_layout(rect=(0, .07, 1, 1)); fig.savefig(SAVE / "fig1_wr_speed_carries_over.png"); plt.show()
'''))
C.append(md("## Receivers: the NGS athleticism score, weight, and production"))
C.append(code(r'''
N = {"NGS score, class only": cell(WR, "ngs_athleticism_score", "sunday_speed_mph", ("draft_year",)),
     "NGS score, size-adjusted": cell(WR, "ngs_athleticism_score", "sunday_speed_mph"),
     "Laser 40, size-adjusted": T1["Laser-timed 40 instead of tracked top speed"],
     "Tracked top speed, size-adjusted": g,
     "NGS score, top speed held fixed": cell(WR, "ngs_athleticism_score", "sunday_speed_mph", SZ + ("c_top_mph",)),
     "Top speed, NGS score held fixed": cell(WR, "c_top_mph", "sunday_speed_mph", SZ + ("ngs_athleticism_score",))}
R["ngs"] = N; R["ngs_weight"] = rank_partial(WR, "ngs_athleticism_score", "combine_weight", ("draft_year",))[0]
def dif(a, b2): return lambda dd: rank_partial(dd, a, "sunday_speed_mph", SZ)[0] - rank_partial(dd, b2, "sunday_speed_mph", SZ)[0]
W2 = WR.dropna(subset=["ngs_athleticism_score", "forty"])
R["diff_top_ngs"] = dict(d=dif("c_top_mph", "ngs_athleticism_score")(W2), ci=boot_ci(W2, "c_top_mph", "sunday_speed_mph", SZ, stat=dif("c_top_mph", "ngs_athleticism_score")))
R["diff_top_laser"] = dict(d=dif("c_top_mph", "forty")(W2), ci=boot_ci(W2, "c_top_mph", "sunday_speed_mph", SZ, stat=dif("c_top_mph", "forty")))
for k, v in N.items(): print(f"{k:35s} {v['rho']:+.2f} ({v['lo']:+.2f}, {v['hi']:+.2f}) p {v['p']:.3f}")
print("NGS vs weight (class fixed)", round(R["ngs_weight"], 2), "| top - NGS", R["diff_top_ngs"], "| top - laser", R["diff_top_laser"])
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9), gridspec_kw={"width_ratios": [1.4, 1]})
for i, (k, v) in enumerate(list(N.items())[::-1]):
    col = BLUE if (v["lo"] > 0 and "NGS score" not in k.split(",")[0]) else GREY
    a.plot([v["lo"], v["hi"]], [i, i], color=col, lw=2); a.scatter([v["rho"]], [i], color=col, s=36, zorder=3); a.text(1.0, i, f"{v['rho']:+.2f}", va="center", fontsize=8)
a.set_yticks(range(len(N))); a.set_yticklabels(list(N)[::-1]); a.axvline(0, color="k", ls=":", lw=.8); a.set_xlim(-.45, 1.05)
a.set_xlabel(f"ρ with Sunday Speed (95% CI), n {g['n']}"); a.set_title("The NGS score adds nothing once top speed is known", loc="left", fontweight="bold")
for i, (lab, v) in enumerate([("Top speed − NGS score", R["diff_top_ngs"]), ("Top speed − laser 40", R["diff_top_laser"])][::-1]):
    col = BLUE if v["ci"][0] > 0 else GREY
    b.plot(v["ci"], [i, i], color=col, lw=2); b.scatter([v["d"]], [i], color=col, s=36, zorder=3); b.text(.62, i, f"{v['d']:+.2f}", va="center", fontsize=8)
b.set_yticks([0, 1]); b.set_yticklabels(["Top speed − laser 40", "Top speed − NGS score"]); b.axvline(0, color="k", ls=":", lw=.8); b.set_xlim(-.2, .7); b.set_ylim(-.6, 1.6)
b.set_xlabel("Difference in size-adjusted ρ\n(paired bootstrap)"); b.set_title("Top speed beats the score", loc="left", fontweight="bold")
footer(fig, "Blue: interval above zero. Grey: interval includes zero, or the NGS score. Same receivers throughout; 'held fixed' adds that measure as a control. NGS athleticism score: column in combine_results.csv.")
fig.tight_layout(rect=(0, .07, 1, 1)); fig.savefig(SAVE / "fig2_ngs_vs_tracked_speed.png"); plt.show()
'''))
C.append(code(r'''
# Weight: heavier receivers run slower than their own 40 says (Figure 3, regenerated from its spec)
R["wt_vs_top"] = cell(WR, "combine_weight", "c_top_mph", ("draft_year", "combine_height"))
R["wt_partial"] = cell(WR, "combine_weight", "sunday_speed_mph", ("draft_year", "combine_height", "c_top_mph"))
def wslope(dd):
    X = np.column_stack([np.ones(len(dd)), dd.c_top_mph, dd.combine_weight, dd.combine_height, pd.get_dummies(dd.draft_year.astype(str), drop_first=True).to_numpy(float)])
    return float(np.linalg.lstsq(X, dd.sunday_speed_mph.to_numpy(float), rcond=None)[0][2] * 10)
R["wt_slope10"] = dict(b=wslope(WR), ci=boot_ci(WR, "combine_weight", "sunday_speed_mph", (), stat=wslope))
R["wt_slope_by_class"] = {}
for c in (2023, 2024, 2025):
    d = WR[WR.draft_year == c]; X = np.column_stack([np.ones(len(d)), d.c_top_mph, d.combine_weight])
    R["wt_slope_by_class"][c] = float(np.linalg.lstsq(X, d.sunday_speed_mph.to_numpy(float), rcond=None)[0][2] * 10)
print("weight vs top speed", {k: round(v, 2) for k, v in R["wt_vs_top"].items()}); print("weight | top speed", {k: round(v, 3) for k, v in R["wt_partial"].items()})
print("mph per 10 lb", R["wt_slope10"], "by class", R["wt_slope_by_class"])
# leftover = Sunday Speed minus what top speed, height and class predict (mph)
X = np.column_stack([np.ones(len(WR)), WR.c_top_mph, WR.combine_height, pd.get_dummies(WR.draft_year.astype(str), drop_first=True).to_numpy(float)])
left = WR.sunday_speed_mph - X @ np.linalg.lstsq(X, WR.sunday_speed_mph.to_numpy(float), rcond=None)[0]
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
for c, col in CLS.items():
    m = WR.draft_year == c; a.scatter(WR.combine_weight[m], left[m], s=24, color=col, edgecolor="white", lw=.4, label=f"{c} class")
xx = np.linspace(WR.combine_weight.min(), WR.combine_weight.max(), 2); bw = np.polyfit(WR.combine_weight, left, 1)
a.plot(xx, np.polyval(bw, xx), color=BLUE, lw=2); a.axhline(0, color="k", lw=.6)
a.set_xlabel("Combine weight (lb)"); a.set_ylabel("Sunday Speed vs what his 40 top speed predicts (mph)")
a.set_title("Heavier receivers run slower on Sunday than their 40 says", loc="left", fontweight="bold")
s = R["wt_slope10"]; a.text(.02, .04, f"{s['b']:+.2f} mph per 10 lb [{s['ci'][0]:+.2f}, {s['ci'][1]:+.2f}]\npartial ρ {R['wt_partial']['rho']:+.2f}, n {R['wt_partial']['n']}", transform=a.transAxes, fontsize=8.5)
a.legend(fontsize=8, frameon=False, loc="upper right")
cls = list(R["wt_slope_by_class"].items())
b.barh([f"{c} class" for c, _ in cls][::-1], [v for _, v in cls][::-1], color=[CLS[c] for c, _ in cls][::-1])
b.axvline(0, color="k", lw=.8); b.set_xlabel("mph per 10 lb, at the same 40 top speed"); b.set_title("Same sign in every class", loc="left", fontweight="bold")
footer(fig, "Holding 40 top speed, height and class fixed. An association: the data cannot say whether weight, role, or how a receiver is used on deep routes explains it.")
fig.tight_layout(rect=(0, .06, 1, 1)); fig.savefig(SAVE / "fig3_heavy_receivers_slower.png"); plt.show()
'''))
C.append(code(r'''
# Production: does Sunday Speed buy production? (class held fixed; top speed size-adjusted)
R["prod"] = {o: cell(WRALL, "sunday_speed_mph", o, ("draft_year",)) for o in ["yards_per_route", "deep_yds_per_deep_route", "deep_target_share"]}
R["prod_top"] = {o: cell(WRALL, "c_top_mph", o) for o in ["yards_per_route", "deep_yds_per_deep_route", "deep_target_share"]}
for k in R["prod"]: print(k, {kk: round(vv, 2) for kk, vv in R["prod"][k].items()}, "| top speed", round(R["prod_top"][k]["rho"], 2))
'''))
C.append(md("## Defensive line: how much of the drill link is role and size? (as-reported rates)"))
C.append(code(r'''
DL = dl_table(pl, cr, pp, feat)
DLT = ["short_shuttle", "three_cone", "forty", "ten_yd_split", "c_top_mph", "broad_jump", "vertical"]; DLO = ["pressure_rate", "sack_rate", "tfl_rate"]
M = [("draft_year",), ("draft_year", "role"), ("draft_year", "role", "combine_weight", "combine_height")]
def ladder(D):
    rows = []
    for t in DLT:
        for o in DLO:
            d = D[[t, o, *M[2]]].dropna()
            if len(d) >= 25: rows.append([rank_partial(d, t, o, m)[0] for m in M] + [len(d)])
    return np.array(rows)
L = ladder(DL); med = np.median(L[:, :3], axis=0)
rng = np.random.default_rng(SEED); sh = []
for _ in range(1000):
    Lb = ladder(DL.iloc[rng.integers(0, len(DL), len(DL))]); m = np.median(Lb[:, :3], axis=0); sh.append(1 - m[2] / m[0])
R["dl"] = dict(n_players=len(DL), cells=len(L), n_lo=int(L[:, 3].min()), n_hi=int(L[:, 3].max()), med=med.tolist(), share=float(1 - med[2] / med[0]),
               share_role=float(1 - med[1] / med[0]), share_ci=np.percentile(sh, [2.5, 97.5]).tolist(), undrafted=int(DL.undrafted.sum()))
SZR = ("draft_year", "role", "combine_weight", "combine_height")
R["dl40p"] = cell(DL, "forty", "pressure_rate", SZR)
R["dl_role"] = {r: cell(DL[DL.role == r], "forty", "pressure_rate") for r in ("Edge", "Interior")}
R["dl_wt_pressure"] = cell(DL, "combine_weight", "pressure_rate", ("draft_year", "role", "combine_height"))
print({k: v for k, v in R["dl"].items()}); print("40 -> pressure", R["dl40p"]); print("within role", R["dl_role"]); print("weight -> pressure", R["dl_wt_pressure"])
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.2, 1]})
lab = {"short_shuttle": "Short shuttle", "three_cone": "3-cone", "forty": "40-yd dash", "ten_yd_split": "10-yd split", "c_top_mph": "40 top speed", "broad_jump": "Broad jump", "vertical": "Vertical"}
for i, t in enumerate(DLT[::-1]):
    d = DL[[t, "pressure_rate", *M[2]]].dropna(); v = [rank_partial(d, t, "pressure_rate", m)[0] for m in M]
    a.plot([min(v), max(v)], [i, i], color="#ccc", lw=2, zorder=1)
    for vv, col in zip(v, [GREY, "#E69F00", BLUE]): a.scatter([vv], [i], color=col, s=40, zorder=3)
    lab[t] = lab[t] + f" (n={len(d)})"
a.set_yticks(range(len(DLT))); a.set_yticklabels([lab[t] for t in DLT[::-1]]); a.axvline(0, color="k", ls=":", lw=.8); a.set_xlim(-.45, .85)
a.set_xlabel("Rank partial ρ with pressure rate (as reported)\n+ = better athlete, more pressures")
a.set_title(f"Most of the line link is edge vs interior\nmedian of {len(L)} cells: {med[0]:+.2f} → {med[1]:+.2f} (+role) → {med[2]:+.2f} (+size)", loc="left", fontweight="bold", fontsize=9.5)
a.scatter([], [], color=GREY, label="class only"); a.scatter([], [], color="#E69F00", label="+ role"); a.scatter([], [], color=BLUE, label="+ weight, height"); a.legend(fontsize=8, frameon=False, loc="lower left")
pairs = [("forty", "pressure_rate", "40-yd → pressure"), ("ten_yd_split", "pressure_rate", "10-yd → pressure"), ("forty", "sack_rate", "40-yd → sack")]
yl = []
for j, (t, o, lb) in enumerate(pairs[::-1]):
    for k, (r, col) in enumerate([("Edge", "#8c564b"), ("Interior", "#e377c2")]):
        v = cell(DL[DL.role == r], t, o, P=5000, B=1000); yy = j * 2.6 + k
        b.plot([v["lo"], v["hi"]], [yy, yy], color=col, lw=2); b.scatter([v["rho"]], [yy], color=col, s=34, zorder=3)
        b.text(1.02, yy, f"{r} n={v['n']} p" + ("<0.01" if v['p'] < .01 else f"={v['p']:.2f}"), va="center", fontsize=7.5); yl.append((yy + .5 if k == 0 else None, lb))
b.set_yticks([j * 2.6 + .5 for j in range(len(pairs))]); b.set_yticklabels([p[2] for p in pairs[::-1]]); b.axvline(0, color="k", ls=":", lw=.8); b.set_xlim(-.6, 1.0)
b.set_xlabel("Within-role rank partial ρ (95% CI)\nclass, weight, height held fixed"); b.set_title("Inside each role the link is weaker or noisy", loc="left", fontweight="bold", fontsize=9.5)
footer(fig, f"{len(DL)} defensive linemen (2023–25 classes; {R['dl']['undrafted']} undrafted) with 20+ pass-rush snaps. Pressure rate = pressures per pass-rush snap, as reported (not shrunk). Right: brown edge, pink interior; p = permutation p within role, unadjusted.")
fig.tight_layout(rect=(0, .07, .93, 1)); fig.savefig(SAVE / "fig4_dl_ladder.png"); plt.show()
'''))
C.append(md("## Offensive line: slide-drill acceleration and pressures allowed"))
C.append(code(r'''
OL = ol_table(pl, cr, pp, feat); X0, Y0 = "ol_slide_acc", "pressure_allowed_rate"   # Y0 is -(rate): + = fewer pressures
o = cell(OL, X0, Y0, SZR); R["ol"] = dict(o, rho_rate=-o["rho"], lo_rate=-o["hi"], hi_rate=-o["lo"], undrafted=int(OL.undrafted.sum()),
                                          snaps_med={int(c): float(v) for c, v in OL.groupby("draft_year").pb_snaps.median().items()})
R["ol_class"] = {}
for c in (2023, 2024, 2025):
    d = OL[OL.draft_year == c][[X0, Y0]].dropna(); f = lambda dd: stats.spearmanr(dd[X0], -dd[Y0])[0]
    lo, hi = boot_ci(d, X0, Y0, (), stat=f); R["ol_class"][c] = dict(rho=float(f(d)), n=len(d), lo=lo, hi=hi)
R["ol_2324"] = cell(OL[OL.draft_year < 2025], X0, Y0, SZR)
dd = OL[[X0, Y0, "draft_year"]].dropna()
def cdiff(df):
    a = df[df.draft_year == 2025]; return stats.spearmanr(a[X0], a[Y0])[0] - np.mean([stats.spearmanr(df[df.draft_year == k][X0], df[df.draft_year == k][Y0])[0] for k in (2023, 2024)])
rng = np.random.default_rng(SEED); obs = cdiff(dd); sims = []
for _ in range(10000):
    e = dd.copy(); e["draft_year"] = rng.permutation(e.draft_year.values); sims.append(cdiff(e))
R["ol_class_p"] = float((1 + np.sum(np.abs(sims) >= abs(obs))) / 10001)
print("OL", {k: v for k, v in R["ol"].items()}); print("by class", R["ol_class"]); print("2023+24", R["ol_2324"]["rho"], "class-difference p", R["ol_class_p"])
fig, axs = plt.subplots(1, 4, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1, 1, 1, 1.35]})
for a, c in zip(axs[:3], (2023, 2024, 2025)):
    d = OL[OL.draft_year == c]; a.scatter(d[X0], -100 * d[Y0], s=22, color=CLS[c], edgecolor="white", lw=.4)
    bfit = np.polyfit(d[X0], -100 * d[Y0], 1); xx = np.linspace(d[X0].min(), d[X0].max(), 2); a.plot(xx, np.polyval(bfit, xx), color=RED if c == 2025 else "k", lw=1.6)
    v = R["ol_class"][c]; a.set_title(f"{c} (n={v['n']}): ρ {v['rho']:+.2f}\n[{v['lo']:+.2f}, {v['hi']:+.2f}]", loc="left", fontsize=9)
    a.set_xlabel("Slide-drill peak acceleration (yd/s²)")
axs[0].set_ylabel("Pressures allowed\nper pass-block snap (%)")
a = axs[3]; rows = [("All 3 classes + size, role", R["ol"]["rho_rate"], R["ol"]["lo_rate"], R["ol"]["hi_rate"], R["ol"]["n"], BLUE),
                    ("2023+2024 + size, role", -R["ol_2324"]["rho"], -R["ol_2324"]["hi"], -R["ol_2324"]["lo"], R["ol_2324"]["n"], "k"),
                    ("2025 only, raw", R["ol_class"][2025]["rho"], R["ol_class"][2025]["lo"], R["ol_class"][2025]["hi"], R["ol_class"][2025]["n"], RED)]
for i, (lb, r, lo, hi, n, col) in enumerate(rows[::-1]):
    a.plot([lo, hi], [i, i], color=col, lw=2); a.scatter([r], [i], color=col, s=36, zorder=3); a.text(.62, i, f"{r:+.2f} (n={n})", va="center", fontsize=8)
a.set_yticks(range(3)); a.set_yticklabels([r[0] for r in rows[::-1]], fontsize=8); a.axvline(0, color="k", ls=":", lw=.8); a.set_xlim(-1, .6)
a.set_xlabel("ρ with pressure rate allowed\n(− = more acceleration, fewer pressures)"); a.set_title("Strong in two classes, absent in 2025", loc="left", fontweight="bold", fontsize=9)
fig.suptitle("Offensive line: slide-drill acceleration went with fewer pressures allowed in 2023–24, not in 2025", x=.01, ha="left", fontweight="bold")
footer(fig, f"{R['ol']['n']} offensive linemen (2023–25 classes; {R['ol']['undrafted']} undrafted) with 100+ regular-season pass-block snaps. Peak acceleration = largest 0.1-s speed gain, averaged over attempts. "
       f"2025 vs other classes: permutation p {R['ol_class_p']:.3f}. The 2023+2024 restriction was chosen after seeing the data. Median snaps: " + ", ".join(f"{k} {v:.0f}" for k, v in R['ol']['snaps_med'].items()) + ".")
fig.tight_layout(rect=(0, .08, 1, .93)); fig.savefig(SAVE / "fig5_ol_slide_reversal.png"); plt.show()
'''))
C.append(md("## How many tests, and what survives best-of-N luck (Westfall–Young max-|z|, 2,000 within-class shuffles)"))
C.append(code(r'''
DB = db_table(pl, cr, pp, feat)
OLT = ["c_top_mph", "forty", "ten_yd_split", "vertical", "broad_jump", "three_cone", "short_shuttle", "bench_reps"] + [c for c in OL.columns if c.startswith("ol_")]
FAMS = {"Receivers": (WRALL, ["c_top_mph", "vertical", "broad_jump", "short_shuttle"], ["sunday_speed_mph", "sep_all_mean", "break_y"], SZ),
        "Defensive line": (DL, ["c_top_mph", "ten_yd_split", "vertical", "broad_jump", "three_cone", "short_shuttle"], DLO, SZR),
        "Offensive line": (OL, OLT, [Y0], SZR),
        "Defensive backs": (DB, ["c_top_mph", "ten_yd_split", "vertical", "broad_jump", "three_cone", "short_shuttle"], ["tackle_rate", "tfl_rate"], SZ + ("role",))}
FR, KTH = {}, {}
for k, (T, te, ou, c) in FAMS.items():
    F = family(T, te, ou, c); F, kth = best_of_n(T, F, c, S=2000); FR[k], KTH[k] = F, kth
R["families"] = {k: dict(cells=len(F), p05=int((F.p < .05).sum()), expected=round(.05 * len(F), 1), q05=int((F.q < .05).sum()),
                         survive=int((F.p_best_of_n < .05).sum()), best=F.sort_values("p").iloc[0][["test", "outcome", "n", "rho", "p", "q", "p_best_of_n"]].to_dict()) for k, F in FR.items()}
R["families_total"] = dict(cells=sum(v["cells"] for v in R["families"].values()), p05=sum(v["p05"] for v in R["families"].values()),
                           expected=round(.05 * sum(v["cells"] for v in R["families"].values()), 1), survive=sum(v["survive"] for v in R["families"].values()))
R["db"] = dict(n_players=len(DB), mde=mde(int(np.median(FR["Defensive backs"].n)), 4), n_med=int(np.median(FR["Defensive backs"].n)))
for k, v in R["families"].items(): print(k, v)
print("TOTAL", R["families_total"])
fig, axs = plt.subplots(1, 4, figsize=(12.5, 4), sharey=True)
for a, (k, F) in zip(axs, FR.items()):
    z = np.sort(F.z.values)[::-1]; kth = KTH[k]; r = np.arange(1, len(z) + 1)
    a.fill_between(r, np.percentile(kth, 5, axis=0), np.percentile(kth, 95, axis=0), color="#ddd", lw=0); a.plot(r, np.median(kth, axis=0), color=GREY, lw=1)
    surv = np.sort(F.z[F.p_best_of_n < .05].values)[::-1]
    a.scatter(r, z, color=["#0072B2" if zz in surv else "k" for zz in z], s=[60 if zz in surv else 18 for zz in z], zorder=3)
    v = R["families"][k]; a.set_title(f"{k}: {v['cells']} cells\n{v['p05']} with p<.05 ({v['expected']} by chance)", loc="left", fontsize=9, fontweight="bold")
    a.set_xlabel("Rank of cell (strongest = 1)")
axs[0].set_ylabel("Evidence |z| (rank partial ρ → z)")
fig.suptitle("Only two links beat best-of-N luck: receiver speed and offensive-line slide-drill acceleration", x=.01, ha="left", fontweight="bold")
footer(fig, "Each dot is one Combine test × outcome cell (25+ players), size-adjusted. Grey band: luck, 5th–95th percentile of the k-th best cell when the whole outcome block is shuffled within draft class (2,000 shuffles). Blue: survives best-of-N (p<.05).")
fig.tight_layout(rect=(0, .07, 1, .93)); fig.savefig(SAVE / "fig6_best_of_n_null.png"); plt.show()
'''))
C.append(md("## Table 2: held-out effect sizes (best test chosen inside two classes, scored on the third; 300-shuffle luck range)"))
C.append(code(r'''
WRT = ["c_top_mph", "forty", "vertical", "broad_jump", "short_shuttle", "ten_yd_split"]
T2 = {"Receiver Sunday Speed": loco_null(WRALL, WRT, "sunday_speed_mph"),
      "Receiver separation, break routes": loco_null(WRALL, WRT, "break_y"),
      "Receiver separation, all routes": loco_null(WRALL, WRT, "sep_all_mean"),
      "Defensive-line pressure rate": loco_null(DL, ["forty", "ten_yd_split", "c_top_mph", "vertical", "broad_jump"], "pressure_rate", extra=("role",)),
      "Offensive-line pressures allowed": loco_null(OL, OLT, Y0, extra=("role",))}
R["table2"] = {k: dict(gain=v[0], n=v[1], luck95=v[2], p=v[3]) for k, v in T2.items()}
for k, v in R["table2"].items(): print(f"{k:36s} n {v['n']:3d} gain {v['gain']:+.3f} luck95 {v['luck95']:+.3f} p {v['p']:.3f}")
'''))
C.append(md("## Tight ends, and the results file"))
C.append(code(r'''
te = pl[pl.nfl_position == "TE"].set_index("nfl_id").join(cr.set_index("nfl_id")).join(feat)
te_routes = pp[pp.nfl_id.isin(te.index) & pp.route_ran.notna()].groupby("nfl_id").size()
R["te"] = dict(listed=len(te), tracked40_and_20routes=int(((te.c_top_mph.notna()) & (te_routes.reindex(te.index).fillna(0) >= 20)).sum()))
R["te"]["mde"] = mde(R["te"]["tracked40_and_20routes"], 3)
print("TE", R["te"])
def _j(o):
    if isinstance(o, dict): return {str(k): _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_j(v) for v in o]
    if isinstance(o, (np.floating, float)): return float(o)
    if isinstance(o, (np.integer, int)): return int(o)
    return o
OUTJ = (SAVE.parent / "results_v2.json"); OUTJ.write_text(json.dumps(_j(R), indent=1))
print("figures:", sorted(p.name for p in SAVE.glob("fig*.png")), "| results:", OUTJ, f"| total {time.time() - t0:.0f}s")
assert len(list(SAVE.glob("fig*.png"))) == 6
'''))
for i, c in enumerate(C):
    c["id"] = hashlib.md5(f"bdb2027-v2-{i}".encode()).hexdigest()[:8]
NB = {"cells": C, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
(HERE / "bdb2027_v2.ipynb").write_text(json.dumps(NB, indent=1, ensure_ascii=False) + "\n")
print("wrote", HERE / "bdb2027_v2.ipynb", len(C), "cells")
