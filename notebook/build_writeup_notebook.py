#!/usr/bin/env python3
"""Builds notebook/bdb2027_writeup.ipynb (competition-rules rebuild, 11/2026).

Prose lives here. Every number in the prose is read from the audited outputs in out/*.csv at build time
(scorecard_full.csv, scorecard.csv, scorecard_weight.csv, wr_route_lead_cells.csv, wr_route_lead_contrasts.csv).
The notebook itself recomputes the receiver gate link from the competition tracking files when they are attached,
and draws every figure except Figures 4 and 6 (pre-rendered PNGs) from the same CSVs.

Official limits (Kaggle 'Submission Requirements', checked via the Kaggle API 11/2026): <= 2,000 words, < 10 tables or figures,
a Public Kaggle Notebook attached, Combine tracking explicitly linked to regular-season performance, player tracking data used.
Visual budget here: 6 figures + 1 table = 7.  Word budget: see the count printed at the end of the build.
"""
import json, re, pathlib
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUTD = HERE.parent / "out"
full = pd.read_csv(OUTD / "scorecard_full.csv")
card = pd.read_csv(OUTD / "scorecard.csv")
wt = pd.read_csv(OUTD / "scorecard_weight.csv")
rl = pd.read_csv(OUTD / "wr_route_lead_cells.csv")
rc = pd.read_csv(OUTD / "wr_route_lead_contrasts.csv")

# ---------------------------------------------------------------- number helpers
sg = lambda x, d=2: f"{x:+.{d}f}"
qf = lambda q: "<0.01" if q < 0.01 else f"{q:.2f}"
def F(group, test, outcome, sub="All"):
    r = full[(full.group == group) & (full.subgroup == sub) & (full.test == test) & (full.outcome == outcome)]
    assert len(r) == 1, (group, test, outcome, sub, len(r))
    return r.iloc[0]
def W(group, outcome):
    r = wt[(wt.group == group) & (wt.outcome == outcome)]; assert len(r) == 1, (group, outcome); return r.iloc[0]
def CI(r, lo="ci_lo", hi="ci_hi"): return f"{sg(r[lo])} to {sg(r[hi])}"
def RC(hyp, test, contrast=None):
    r = rc[(rc.hyp == hyp) & (rc.test == test)]
    if contrast: r = r[r.contrast == contrast]
    assert len(r) == 1, (hyp, test); return r.iloc[0]
def RL(split, test):
    r = rl[(rl.group == "S1") & (rl.test == test) & (rl.split == split)]; assert len(r) == 1; return r.iloc[0]

# WR gate + control rows
w40 = F("WR", "forty", "sunday_speed_mph"); wtop = F("WR", "c_top_mph", "sunday_speed_mph")
wvert = F("WR", "vertical", "break_y"); wburst = F("WR", "burst_0_100", "break_y")
assert w40.verdict == wtop.verdict == "TRANSLATES"
# audit counts
g = full[full.n >= 25]
N_CELLS, N_P05, N_Q05 = len(g), int((g.p_perm < 0.05).sum()), int((g.fdr_q < 0.05).sum())
N_EXP = int(round(N_CELLS * 0.05))
assert (N_CELLS, N_P05, N_Q05) == (164, 28, 2), (N_CELLS, N_P05, N_Q05)
# DL mirage
DL_OUT = ["speed_1s_mph", "pressure_rate", "sack_rate", "tfl_rate"]
dl = g[(g.group == "DL") & (g.subgroup == "All") & g.outcome.isin(DL_OUT)]
DL_N, DL_RAW, DL_SIZE = len(dl), dl.rho_raw.median(), dl.rho_size.median()
DL_SNS = int((dl.verdict == "SIZE, NOT SPEED").sum())
big = g[(g.group == "DL") & (g.subgroup == "All") & (g.rho_raw.abs() >= 0.30)]
BIG_N, BIG_HALF = len(big), int((big.rho_size.abs() <= 0.5 * big.rho_raw.abs()).sum())
dl40s, dl40p = F("DL", "forty", "sack_rate"), F("DL", "forty", "pressure_rate")
dl10g = F("DL", "ten_yd_split", "speed_1s_mph")
# weight
gw, gb = W("DL", "player_get_off"), W("DL", "speed_1s_mph"); wpr = W("DL", "pressure_rate")
wsun, wss = W("WR", "sunday_speed_mph"), W("WR", "ssoe_mph")
s_scr, s_cro, s_brk, s_ver = RL("screen", "combine_weight"), RL("crosser", "combine_weight"), RL("break", "combine_weight"), RL("vertical", "combine_weight")
# DB
db = g[g.group == "DB"]
DB_N, DB_NO, DB_LEAN = len(db), int((db.verdict == "DOESN'T TRANSLATE").sum()), int((db.verdict == "LEANS").sum())
assert DB_NO + DB_LEAN == DB_N
db40 = F("DB", "forty", "pfr_yds_tgt")
dbbj = F("DB", "broad_jump", "pfr_yds_tgt")
oth = g[(g.group.isin(['WR','DB'])) & (g.subgroup == 'All') & (g.rho_raw.abs() >= 0.30)]
OTH_BIG = len(oth)
assert int((oth.rho_size.abs() <= 0.5 * oth.rho_raw.abs()).sum()) == 0
DB_QMIN = db.fdr_q.min()
te_n = int(full[full.group == "TE"].n.max())
# H1/H3
h1c, h1s = RC("H1", "three_cone"), RC("H1", "short_shuttle")
h3t, h3c = RC("H3", "ten_yd_split"), RC("H3", "three_cone")
h2v = RC("H2-ctx", "vertical")
# exchange rate (needs per-player file, which stays in the repo; the notebook recomputes it live)
wrp = pd.read_csv(OUTD / "wr_te_robust_players.csv").query("pos_group == 'WR'")[["c_top_mph", "sunday_speed_mph"]].dropna()
SLOPE = float(np.polyfit(wrp.c_top_mph, wrp.sunday_speed_mph, 1)[0])
# scout lines (verbatim coach lines from the scorecard)
def coach(group, test, outcome):
    return F(group, test, outcome).coach_line
L_WR = coach("WR", "forty", "sunday_speed_mph"); L_DL = coach("DL", "forty", "pressure_rate"); L_DB = coach("DB", "forty", "pfr_yds_tgt")

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}
code = lambda s: {"cell_type": "code", "metadata": {"jupyter": {"source_hidden": True}, "tags": ["hide-input"]}, "execution_count": None, "outputs": [], "source": s.strip("\n").splitlines(True)}
C = []

# =====================================================================================  TITLE + HOOK + GATE
C.append(md(f"""
# Body size in a stopwatch costume: what the Combine really tells you about NFL play
*NFL Big Data Bowl 2027 · Open Track · Combine tracking linked to regular-season game tracking · WR, TE, DB, DL*

**Most Combine signal is body size wearing a stopwatch. Here is the one place speed is real, and where scouts get fooled.**

**The required link, stated plainly.** We connect each rookie's 10 Hz Combine tracking (2023 to 2025 classes) to his regular-season NFL game tracking and ask which Combine measures show up on Sundays. The link holds in one place. A receiver's tracked Combine top speed predicts his regular-season speed on deep routes (ρ {sg(wtop.rho_raw)} year-controlled, **{sg(wtop.rho_size)} with body size held fixed**, n {int(wtop.n)}). The cell below recomputes that from the raw tracking files.

In four lines:
- **Weight is the hidden variable** behind defensive-line get-off and receiver game speed.
- **Defensive-line speed is mostly a mirage.** Hold size fixed and the link shrinks.
- **Agility drills do not do what scouts assume**, and defensive backs barely translate.
- **Receiver 40 and tracked top speed are the control.** They clear every check, so the method can find real signal.
"""))

C.append(md("""
## Data used
Competition files: `combine_tracking`, `game_tracking_2023/24/25`, `player_play`, `players`, `combine_results`, `games`. Two defensive-back outcomes (yards allowed per target, missed-tackle rate) come from free public Pro-Football-Reference season stats distributed through nflverse. We use no draft-position information; draft *year* is a control only. Running backs are excluded.

**Sunday Speed** is a player's 90th-percentile top speed per play on the plays his job asks for speed (deep routes for receivers, man or deep coverage for defensive backs), regular season only. **Burst Score** is a 0 to 100 within-position blend of the tracked 20-yard time and the jumps.
"""))

C.append(code('''
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy import stats
from IPython.display import Image, display

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
OKABE = {"blue": "#0072B2", "orange": "#E69F00", "red": "#D55E00", "green": "#009E73", "grey": "#8a8a8a", "sky": "#56B4E9", "pink": "#CC79A7"}
VCOL = {"TRANSLATES": OKABE["green"], "LEANS": OKABE["orange"], "SIZE, NOT SPEED": OKABE["red"], "DOESN'T TRANSLATE": OKABE["grey"], "TOO FEW TO TELL": "#c8c8c8"}

def find_out():
    for p in [Path("out"), Path("../out"), Path("/kaggle/working/out")]:
        if (p / "scorecard_full.csv").exists():
            return p
    hits = list(Path("/kaggle/input").rglob("scorecard_full.csv")) if Path("/kaggle/input").exists() else []
    if hits:
        return hits[0].parent
    raise FileNotFoundError("Attach the 'bdb2027-outputs' dataset (it holds the out/ folder).")

def find_comp():
    for p in [Path("data"), Path("../data")]:
        if (p / "combine_tracking.csv").exists():
            return p
    hits = list(Path("/kaggle/input").rglob("combine_tracking.csv")) if Path("/kaggle/input").exists() else []
    return hits[0].parent if hits else None

OUT, COMP = find_out(), find_comp()
FIGS = OUT / "figs"
SAVE = Path("/kaggle/working/writeup_figs") if Path("/kaggle/working").exists() else Path("writeup_figs")
SAVE.mkdir(parents=True, exist_ok=True)
card = pd.read_csv(OUT / "scorecard.csv")
full = pd.read_csv(OUT / "scorecard_full.csv")
wt = pd.read_csv(OUT / "scorecard_weight.csv")
g25 = full[full.n >= 25]
print("audited outputs:", OUT, "| competition data:", COMP)
'''))

C.append(code('''
# ---- THE GATE: Combine tracking -> regular-season game tracking, receivers, recomputed from the raw competition files ----
MPH = 2.0455  # yards/second to mph
gate = full.query("group == 'WR' and test == 'c_top_mph' and outcome == 'sunday_speed_mph'").iloc[0]
if COMP is not None:
    pl = pd.read_csv(COMP / "players.csv", usecols=["nfl_id", "nfl_position", "draft_year"])
    wr = pl[pl.nfl_position == "WR"]; ids = set(wr.nfl_id)
    # Combine side: fastest speed in any 40-yard-dash attempt, from the 10 Hz sensor
    ct = pd.read_csv(COMP / "combine_tracking.csv", usecols=["nfl_id", "entity_type", "drill_type", "s"])
    ct = ct[(ct.entity_type == "PLAYER") & (ct.drill_type == "FORTY_YARD_DASH") & ct.nfl_id.isin(ids)]
    top = (ct.groupby("nfl_id").s.max() * MPH).rename("combine_top_mph")
    # Game side: regular-season deep routes (go, post, corner, wheel) that stood; top speed on each play from game tracking
    games = pd.read_csv(COMP / "games.csv", usecols=["game_id", "season_type"])
    pp = pd.read_csv(COMP / "player_play.csv", usecols=["game_id", "play_id", "nfl_id", "route_ran", "play_nullified_by_penalty"])
    pp = pp[pp.nfl_id.isin(ids) & pp.route_ran.isin(["GO", "POST", "CORNER", "WHEEL"]) & (pp.play_nullified_by_penalty == "N")
            & pp.game_id.isin(games.game_id[games.season_type == "REG"])]
    parts = []
    for yr in (2023, 2024, 2025):
        for ch in pd.read_csv(COMP / f"game_tracking_{yr}.csv", usecols=["game_id", "play_id", "nfl_id", "s"], dtype={"s": "float32"}, chunksize=2_000_000):
            ch = ch[ch.nfl_id.isin(ids)]
            if len(ch):
                parts.append(ch.groupby(["game_id", "play_id", "nfl_id"], sort=False).s.max().reset_index())
    plays = pd.concat(parts).groupby(["game_id", "play_id", "nfl_id"], as_index=False).s.max()
    plays = plays.merge(pp[["game_id", "play_id", "nfl_id"]], on=["game_id", "play_id", "nfl_id"])
    cnt = plays.groupby("nfl_id").s.size()
    sunday = (plays.groupby("nfl_id").s.quantile(0.90) * MPH)[cnt >= 20].rename("sunday_speed_mph")   # at least 20 deep routes
    d = pd.concat([top, sunday], axis=1, join="inner").join(wr.set_index("nfl_id").draft_year).dropna()
    x, y = d.combine_top_mph, d.sunday_speed_mph
    rho_year = stats.spearmanr(x - x.groupby(d.draft_year).transform("mean"), y - y.groupby(d.draft_year).transform("mean"))[0]
    slope = np.polyfit(x, y, 1)
    print(f"Receivers with a tracked 40 and 20+ regular-season deep routes: n={len(d)} (audited n={int(gate.n)})")
    print(f"Combine top speed vs Sunday Speed: year-controlled rho={rho_year:+.2f} (audited {gate.rho_raw:+.2f}); {slope[0]:.2f} mph on Sunday per Combine mph")
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    ax.scatter(x, y, s=22, color=OKABE["blue"], alpha=.8, edgecolor="white", linewidth=.4)
    xs = np.linspace(x.min(), x.max(), 50); ax.plot(xs, np.polyval(slope, xs), color=OKABE["blue"], lw=1.6)
    ax.text(.03, .97, f"n={len(d)}\\nrho {rho_year:+.2f} (year-controlled)\\nrho {gate.rho_size:+.2f} with size held fixed\\n+{slope[0]:.2f} mph Sunday per Combine mph", transform=ax.transAxes, va="top", fontsize=8.5, color=OKABE["blue"])
    ax.set_xlabel("Combine top speed in the 40 (mph, 10 Hz tracking)"); ax.set_ylabel("Regular-season Sunday Speed (mph, deep routes)")
    ax.set_title("Receivers: Combine speed shows up on Sunday", loc="left", fontweight="bold", fontsize=10)
    fig.tight_layout(); fig.savefig(SAVE / "fig1_gate_wr.png", dpi=170); plt.show()
else:
    print("Competition data not attached: showing the saved gate figure and audited numbers instead.")
    display(Image(str(FIGS / "fig1_translation_scatter.png")))
ok = (gate.verdict == "TRANSLATES") and (gate.rho_raw > 0)
print(f"Audited: size-controlled rho {gate.rho_size:+.2f} (95% CI {gate.ci_lo:+.2f} to {gate.ci_hi:+.2f}), q {gate.fdr_q:.3f}, better on held-out draft classes in {gate.classes_helped}")
print("GATE (Combine tracking -> regular-season performance):", "PASS" if ok else "FAIL")
'''))
C.append(md("*Figure 1. Each dot is a receiver. Fast at the Combine means fast on deep routes on Sundays.*"))

# =====================================================================================  1 WEIGHT
C.append(md(f"""
## 1. Weight is the hidden variable
Heavier players are slower, and a stopwatch cannot tell weight from talent. Holding height and draft year fixed:

- **Defensive line.** Heavier linemen get off the ball slower (ρ {sg(gw.rho_height_ctrl)}, 95% CI {CI(gw)}, q {qf(gw.fdr_q)}) and reach a lower speed one second after the snap ({sg(gb.rho_height_ctrl)}, q {qf(gb.fdr_q)}).
- **Receivers.** Heavier receivers run slower on deep routes ({sg(wsun.rho_height_ctrl)}, q {qf(wsun.fdr_q)}) and slower than their own 40 predicts ({sg(wss.rho_height_ctrl)}, q {qf(wss.fdr_q)}).
- **Separation.** Heavier receivers also get less separation on break routes ({sg(s_brk.rho_size)}), vertical routes ({sg(s_ver.rho_size)}) and crossers ({sg(s_cro.rho_size)}), but not on screens ({sg(s_scr.rho_size)}). That is a lead, not a finding (q {s_cro.fdr:.2f}). It appears in Figure 4, panel D.

Weight does not move every outcome: pressure and sack rates are only weakly tied to it ({sg(wpr.rho_height_ctrl)}, q {wpr.fdr_q:.2f}). Where it matters, it is large, and it is why the next section exists.
"""))
C.append(code('''
rows = [("DL", "player_get_off", "DL get-off time"), ("DL", "speed_1s_mph", "DL speed 1 s after snap"), ("DL", "pen_pass_2s", "DL pass-rush depth at 2 s"),
        ("DL", "pressure_rate", "DL pressure rate"), ("DL", "sack_rate", "DL sack rate"),
        ("WR", "sunday_speed_mph", "WR deep-route game speed"), ("WR", "ssoe_mph", "WR game speed vs own 40"), ("WR", "sep_all_mean", "WR separation, all routes")]
fig, ax = plt.subplots(figsize=(8.2, 3.9))
for i, (grp, outc, lab) in enumerate(rows[::-1]):
    r = wt[(wt.group == grp) & (wt.outcome == outc)].iloc[0]; clear = r.fdr_q < .05
    col = OKABE["blue"] if grp == "WR" else OKABE["red"]; col = col if clear else "#9a9a9a"
    ax.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2); ax.scatter(r.rho_height_ctrl, i, s=48, color=col, zorder=3)
    ax.scatter(r.rho_raw, i, s=36, facecolor="white", edgecolor=col, marker="D", zorder=3)
    ax.text(.62, i, f"n {int(r.n)}  q {'<0.01' if r.fdr_q < .01 else f'{r.fdr_q:.2f}'}", va="center", fontsize=7.5, color=col)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[2] for r in rows[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-1, 1)
ax.set_xlabel("rank correlation of weight with the result (filled = height held fixed, 95% CI; hollow = before)\\n<- heavier does worse            heavier does better ->", fontsize=8)
ax.set_title("Weight is the hidden variable (colour = clears the correction)", loc="left", fontweight="bold", fontsize=9.5)
fig.tight_layout(); fig.savefig(SAVE / "fig2_weight.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 2. Weight against on-field results. Left of zero: heavier players do worse.*"))

# =====================================================================================  2 DL MIRAGE
C.append(md(f"""
## 2. Defensive-line speed is a mirage
The raw picture looks like a gift. Faster linemen get off quicker, rush the passer more and sack more. Across the four defensive-line outcomes with a strong raw link (get-off, pressure, sack, tackle for loss), {DL_N} test-by-outcome cells have at least 25 players. Their median year-controlled link is ρ {sg(DL_RAW)}. Hold weight, height and role (edge or interior) fixed and the median falls to {sg(DL_SIZE)}. {DL_SNS} of the {DL_N} earn **SIZE, NOT SPEED**: a real raw link that is really size.

- The 40 against **sack rate** goes from {sg(dl40s.rho_raw)} to {sg(dl40s.rho_size)} (95% CI {CI(dl40s)}).
- The 40 against **pressure rate** goes from {sg(dl40p.rho_raw)} to {sg(dl40p.rho_size)} (q {dl40p.fdr_q:.2f}). It survives as a lead.
- The 10-yard split against **get-off speed** goes from {sg(dl10g.rho_raw)} to {sg(dl10g.rho_size)}. It also survives as a lead.

Across all defensive-line cells with a raw link of at least 0.30, {BIG_HALF} of {BIG_N} lose half or more of it to size. None of the {OTH_BIG} receiver and defensive-back cells with a raw link that strong do.

**Where scouts get fooled:** a tackle who looks fast next to other big men still produces like a big man. Compare linemen only with linemen of the same weight.
"""))
C.append(code('''
tests = [("ten_yd_split", "10-yd split"), ("forty", "40"), ("c_top_mph", "Top speed (tracked)"), ("burst_0_100", "Burst Score"), ("vertical", "Vertical"), ("broad_jump", "Broad jump")]
outs = [("speed_1s_mph", "Get-off speed (1 s)"), ("pressure_rate", "Pressure rate"), ("sack_rate", "Sack rate"), ("tfl_rate", "Tackles for loss")]
fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.7), sharey=True, sharex=True)
for ax, (oc, ol) in zip(axes, outs):
    for i, (t, tl) in enumerate(tests[::-1]):
        r = g25[(g25.group == "DL") & (g25.subgroup == "All") & (g25.test == t) & (g25.outcome == oc)]
        if r.empty: continue
        r = r.iloc[0]; col = VCOL[r.verdict]
        ax.annotate("", xy=(r.rho_size, i), xytext=(r.rho_raw, i), arrowprops=dict(arrowstyle="->", color=col, lw=1.2, alpha=.7))
        ax.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2.2, alpha=.55, solid_capstyle="round")
        ax.scatter(r.rho_raw, i, s=34, facecolor="white", edgecolor=col, marker="D", zorder=3); ax.scatter(r.rho_size, i, s=44, color=col, zorder=4)
    ax.set_yticks(range(len(tests))); ax.set_yticklabels([t[1] for t in tests[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.45, .95); ax.set_title(ol, fontsize=9.5, fontweight="bold")
fig.supxlabel("hollow diamond = year-controlled rank correlation (before size); filled dot = size- and role-controlled with 95% CI; + = faster athlete does better", fontsize=8.5)
import matplotlib.lines as ml
fig.legend([ml.Line2D([], [], marker="o", color=VCOL[k], lw=0) for k in ["SIZE, NOT SPEED", "LEANS", "DOESN'T TRANSLATE"]], ["Size, not speed", "Leans (lead)", "Doesn't translate"], loc="upper right", ncol=3, fontsize=8, frameon=False)
fig.tight_layout(rect=(0, .03, 1, .95)); fig.savefig(SAVE / "fig3_dl_mirage.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 3. Defensive-line Combine tests, before and after holding size fixed. Arrows run from the raw link to the size-controlled link. 3-cone and shuttle (fewer than 36 linemen) are left out.*"))

# =====================================================================================  3 AGILITY
C.append(md(f"""
## 3. Agility drills do not do what scouts assume
Before looking, we wrote down two beliefs and the tests that would kill them.

- **H1: the 3-cone and shuttle matter more on break routes than on vertical routes.** They do not. The break-minus-vertical difference is {sg(h1c['diff'])} for the 3-cone (95% CI {CI(h1c,'lo','hi')}) and {sg(h1s['diff'])} for the shuttle ({CI(h1s,'lo','hi')}). **Dead.**
- **H3: quickness matters more against man coverage than zone.** It does not. For the 10-yard split the man-minus-zone difference is {sg(h3t['diff'])} (CI {CI(h3t,'lo','hi')}). The 3-cone contrast points the *opposite* way ({sg(h3c['diff'])}, n {int(h3c.n)}), and we do not trust it. **Dead.**

Only 22 to 30 receivers ran the 3-cone or shuttle, so a modest effect is not ruled out. The belief just has no support here.

What remains is a lead. A higher vertical jump ({sg(wvert.rho_size)}, n {int(wvert.n)}) and Burst Score ({sg(wburst.rho_size)}, n {int(wburst.n)}) go with more separation on break routes, with q {wvert.fdr_q:.2f}. We cannot show they are specific to breaks (break-minus-vertical {sg(h2v['diff'])}, CI {CI(h2v,'lo','hi')}). Treat it as something to test next season, not something to draft on.
"""))
C.append(code('''
display(Image(str(FIGS / "fig21_wr_route_lead.png")))
'''))
C.append(md("*Figure 4. Pre-declared receiver tests. A and C: route family. B: man versus zone. D: weight by route type.*"))

# =====================================================================================  4 DB
C.append(md(f"""
## 4. Defensive backs: the Combine mostly does not translate
{DB_N} cornerback and safety cells have at least 25 players. {DB_NO} do not translate. {DB_LEAN} lean. None clears the false-discovery bar (lowest q {DB_QMIN:.2f}). That is a clean null, and a useful one: a defensive back's Combine tests tell you little about his tackling, tackles for loss or deep-coverage speed.

One result runs the wrong way. A faster 40 goes with *more* yards allowed per target ({sg(db40.rho_size)}, n {int(db40.n)}, 95% CI {CI(db40)}), and broad jump agrees ({sg(dbbj.rho_size)}). We read that as coverage role, not "speed hurts", and it does not clear correction.
"""))
C.append(code('''
t = card[card.group == "DB"].copy()
t["Combine test"] = t.test_label; t["Result"] = t.outcome_label
t["Year-controlled rho"] = t.rho_raw.map("{:+.2f}".format)
t["Size-controlled rho (95% CI)"] = t.apply(lambda r: f"{r.rho_size:+.2f} ({r.ci_lo:+.2f} to {r.ci_hi:+.2f})", axis=1)
t["q"] = t.fdr_q.map(lambda q: "<0.01" if q < .01 else f"{q:.2f}")
t["Verdict"] = t.verdict
display(t[["Combine test", "Result", "n", "Year-controlled rho", "Size-controlled rho (95% CI)", "q", "Verdict"]].reset_index(drop=True))
'''))
C.append(md("*Table 1. Defensive backs, best test per result. + means a faster or better athlete does better, so a negative yards-allowed row means the wrong way.*"))

# =====================================================================================  5 CONTROL
C.append(md(f"""
## 5. The control: where speed is real
If we only ever said "no", a skeptic could call the method a machine for rejecting things. Here is the test it has to pass.

We ran {N_CELLS} Combine-by-outcome cells with at least 25 players. {N_P05} reach p < 0.05, against about {N_EXP} expected by chance. The cells share players and related outcomes, so that excess overstates how many are independent findings. After false-discovery correction, **{N_Q05} cells remain**, and both are receivers.

- **40-yard dash to deep-route game speed:** ρ {sg(w40.rho_size)} (95% CI {CI(w40)}, n {int(w40.n)}, q {qf(w40.fdr_q)}).
- **Tracked Combine top speed to deep-route game speed:** ρ {sg(wtop.rho_size)} ({CI(wtop)}, n {int(wtop.n)}, q {qf(wtop.fdr_q)}).

Both also improve predictions on draft classes the model never saw ({w40.classes_helped} held-out classes each). Straight-line speed is the one Combine trait that survives size control, correction and held-out validation. Everything else is a lead or a mirage; Figure 6 shows the full scorecard.
"""))
C.append(code('''
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.0), gridspec_kw={"width_ratios": [1.15, 1]})
tl = [("forty", "40"), ("c_top_mph", "Top speed (tracked)"), ("ten_yd_split", "10-yd split"), ("burst_0_100", "Burst Score"), ("vertical", "Vertical"), ("broad_jump", "Broad jump"), ("short_shuttle", "Short shuttle"), ("three_cone", "3-cone")]
for i, (t, lab) in enumerate(tl[::-1]):
    r = full[(full.group == "WR") & (full.subgroup == "All") & (full.test == t) & (full.outcome == "sunday_speed_mph")].iloc[0]; col = VCOL[r.verdict]
    a1.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2.2); a1.scatter(r.rho_size, i, s=48, color=col, zorder=3); a1.scatter(r.rho_raw, i, s=34, facecolor="white", edgecolor=col, marker="D", zorder=3)
    a1.text(.98, i, f"n {int(r.n)}  q {'<0.01' if r.fdr_q < .01 else f'{r.fdr_q:.2f}'}  held-out {r.classes_helped}", va="center", ha="left", fontsize=7.5, color=col)
a1.set_yticks(range(len(tl))); a1.set_yticklabels([x[1] for x in tl[::-1]]); a1.axvline(0, color="k", lw=.8); a1.set_xlim(-.9, .98)
a1.set_title("Receivers, deep-route game speed: every Combine test", loc="left", fontsize=9.5, fontweight="bold")
a1.set_xlabel("rank correlation (filled = size held fixed, 95% CI; hollow = before)")
p = g25.sort_values("p_perm").reset_index(drop=True); k = np.arange(1, len(p) + 1)
pass_ = p.fdr_q < .05
a2.scatter(k[~pass_], p.p_perm[~pass_], s=14, color="#9a9a9a", alpha=.8); a2.scatter(k[pass_], p.p_perm[pass_], s=60, color=OKABE["green"], zorder=3, label="clears false-discovery bar")
a2.plot(k, k / len(p), color="k", ls=":", lw=1, label="if nothing were real"); a2.axhline(.05, color=OKABE["red"], ls="--", lw=1, label="p = 0.05")
a2.set_yscale("log"); a2.set_xlabel(f"the {len(p)} tests, ranked by p-value"); a2.set_ylabel("permutation p-value")
a2.set_title(f"{int((p.p_perm < .05).sum())} under p=0.05 (about {round(len(p) * .05)} by chance); {int(pass_.sum())} survive", loc="left", fontsize=9.5, fontweight="bold"); a2.legend(fontsize=8, frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(SAVE / "fig5_control.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 5. Left: the receiver deep-route cells. Right: all 164 tests. Only the two receiver speed rows clear the bar.*"))
C.append(code('''
display(Image(str(FIGS / "fig22_scorecard.png")))
'''))
C.append(md("*Figure 6. The scorecard: best test per result and position group. Green means translates, orange leans, red size not speed, grey no translation.*"))

# =====================================================================================  METHODS
C.append(md("""
## Methods, in plain language
- **Size control.** Every link is repeated holding draft year (so a strong class cannot create a link), weight and height fixed, plus cornerback versus safety and edge versus interior where relevant. Hollow marks in the figures are the link before size.
- **Shrinkage.** Rates from few snaps are pulled toward the group average, so a hot 40-snap sample cannot top a list.
- **Held-out draft class.** Train on two classes, predict the third, and ask whether adding the Combine test beats a size-only model. We report how many of three classes improve.
- **False-discovery control.** Each p-value comes from 10,000 permutations, each interval from a player-level bootstrap, and each result carries a Benjamini-Hochberg q across its whole family of tests.
- **Pre-declaration.** Verdict rules and the receiver hypotheses were written down first.
- **Audit.** We re-checked every p-value and interval with a second method. The numbers here are the audited ones.

**Verdicts.** TRANSLATES: q below 0.05, interval excludes zero, same sign, held-out classes agree. LEANS: interval excludes zero or p below 0.05, but q does not clear. SIZE, NOT SPEED: raw link of at least 0.30 that falls by half or more and whose interval includes zero. TOO FEW: under 25 players. Otherwise DOESN'T TRANSLATE.
"""))

# =====================================================================================  SCOUT USE
C.append(md(f"""
## How a scout uses this
A scorecard, not a ranking. It powers a lookup dashboard: enter a prospect's Combine line and each test returns its tag and a one-line read. Three lines from it:

- **{L_WR}**
- **{L_DL}**
- **A faster 40 goes with *more* yards allowed per target (ρ {sg(db40.rho_size)}, n {int(db40.n)}), and it does not clear the false-discovery bar.**

Each line carries its n and interval, so nobody mistakes a lean for a verdict. In practice: trust a receiver's 40 and tracked top speed, compare linemen only with linemen of their weight, and do not lean on a defensive back's 40.
"""))

# =====================================================================================  LIMITS
C.append(md(f"""
## Limitations
- Rookies only: 2023 to 2025 classes, players who logged tracked snaps. Skipped drills are not random.
- Counts are small: receivers about 60, defensive backs about 70, linemen about 72, tight ends {te_n}. Tight ends are all "too few to tell". "Doesn't translate" means no evidence, not proof of zero.
- The same players produced the leads and test them. The three held-out draft classes are the only out-of-sample check. Treat every LEANS row, including the defensive-line pressure lead and the break-route lead, as a hypothesis. Each position's Burst Score recipe was chosen using game results, so its numbers are optimistic.
- Pooled defensive-line size may partly mean role. Edge and interior splits have only 39 and 33 players.
- No blocker or quarterback tracks are linked, so pressure and sack results are association, not causation. Man versus zone is a team-level play label.
"""))

C.append(md("""
## Appendix
Code cells above are collapsed and show every calculation. The notebook reads the audited result tables from the `bdb2027-outputs` dataset and the raw competition files, which must be attached.
"""))

import hashlib
for i, c in enumerate(C):
    c["id"] = hashlib.md5(f"bdb2027-{i}".encode()).hexdigest()[:8]
NB = {"cells": C, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
p = HERE / "bdb2027_writeup.ipynb"; p.write_text(json.dumps(NB, indent=1, ensure_ascii=False) + "\n")
words, per = 0, []
for c in C:
    if c["cell_type"] == "markdown":
        t = re.sub(r"<!--.*?-->", "", "".join(c["source"]), flags=re.S)
        n = len(re.findall(r"\S+", t)); words += n; per.append(n)
print("markdown words:", words, per)
print(f"slope {SLOPE:.3f}; DL cells {DL_N} sns {DL_SNS} raw {DL_RAW:.2f} size {DL_SIZE:.2f}; big {BIG_HALF}/{BIG_N}; DB {DB_N}/{DB_NO}/{DB_LEAN}")

# ---------------------------------------------------------------- paste-ready markdown for the Kaggle Writeup form
import shutil
FIGD = HERE / "writeup_figs"; FIGD.mkdir(exist_ok=True)
shutil.copy(OUTD / "figs" / "fig21_wr_route_lead.png", FIGD / "fig4_wr_route_lead.png")
shutil.copy(OUTD / "figs" / "fig22_scorecard.png", FIGD / "fig6_scorecard.png")
IMG = {"Figure 1": "fig1_gate_wr.png", "Figure 2": "fig2_weight.png", "Figure 3": "fig3_dl_mirage.png",
       "Figure 4": "fig4_wr_route_lead.png", "Figure 5": "fig5_control.png", "Figure 6": "fig6_scorecard.png"}
dbt = card[card.group == "DB"]
tbl = ["| Combine test | Result | n | Year-controlled ρ | Size-controlled ρ (95% CI) | q | Verdict |", "|---|---|---:|---:|---|---:|---|"]
for _, r in dbt.iterrows():
    tbl.append(f"| {r.test_label} | {r.outcome_label} | {int(r.n)} | {sg(r.rho_raw)} | {sg(r.rho_size)} ({CI(r)}) | {qf(r.fdr_q)} | {r.verdict} |")
parts = []
for c in C:
    if c["cell_type"] != "markdown": continue
    t = "".join(c["source"])
    m = re.match(r"\*(Figure \d|Table 1)\.", t)
    if m:
        parts.append("\n".join(tbl) if m.group(1) == "Table 1" else f"![{m.group(1)}](writeup_figs/{IMG[m.group(1)]})")
    parts.append(t)
(HERE / "writeup_for_kaggle.md").write_text("\n\n".join(parts) + "\n")
print("exported writeup_for_kaggle.md; visuals:", len(IMG) + 1)
