#!/usr/bin/env python3
"""Builds notebook/bdb2027_writeup.ipynb and notebook/writeup_for_kaggle.md (11/2026, reframed: 'The Combine works, but read it right').

Structure (Kevin, 11/2026): hook + gate, then exactly five findings, each its own section with its own figure:
  1 WR speed carries to Sunday deep routes   2 DL drills predict pass rush, mostly through body size   3 Consistent leads that need more seasons
  4 DB: the Combine alone is a weak guide at this n (not detected, with MDE)   5 Weight is the variable scouts must adjust for
then a short scout-use section, compact methods, limitations.
Every number in the prose is read from the audited outputs at build time (scorecard_full.csv, scorecard.csv, scorecard_weight.csv,
wr_route_lead_cells.csv, wr_route_lead_contrasts.csv, power_simulation.csv) and key counts are asserted.
Official limits (Kaggle 'Submission Requirements'): <= 2,000 words, < 10 tables or figures, public notebook attached,
Combine tracking linked to regular-season performance, player tracking data used.
Visuals: 7 figures + 1 table = 8.
"""
import json, re, pathlib, shutil, hashlib
import numpy as np, pandas as pd
from scipy.stats import norm

HERE = pathlib.Path(__file__).resolve().parent
OUTD = HERE.parent / "out"
full = pd.read_csv(OUTD / "scorecard_full.csv")
card = pd.read_csv(OUTD / "scorecard.csv")
wt = pd.read_csv(OUTD / "scorecard_weight.csv")
rl = pd.read_csv(OUTD / "wr_route_lead_cells.csv")
rc = pd.read_csv(OUTD / "wr_route_lead_contrasts.csv")
sim = pd.read_csv(OUTD / "power_simulation.csv")
ND = "NOT DETECTED (low power)"
assert "DOESN'T TRANSLATE" not in set(full.verdict) and ND in set(full.verdict)

# ---------------------------------------------------------------- helpers
sg = lambda x, d=2: f"{x:+.{d}f}"
qf = lambda q: "<0.01" if q < 0.01 else f"{q:.2f}"
def F(group, test, outcome, sub="All"):
    r = full[(full.group == group) & (full.subgroup == sub) & (full.test == test) & (full.outcome == outcome)]
    assert len(r) == 1, (group, test, outcome, sub, len(r)); return r.iloc[0]
def W(group, outcome):
    r = wt[(wt.group == group) & (wt.outcome == outcome)]; assert len(r) == 1, (group, outcome); return r.iloc[0]
def CI(r, lo="ci_lo", hi="ci_hi"): return f"{sg(r[lo])} to {sg(r[hi])}"
def RC(hyp, test, contrast=None):
    r = rc[(rc.hyp == hyp) & (rc.test == test)]
    if contrast: r = r[r.contrast == contrast]
    assert len(r) == 1; return r.iloc[0]
def RL(split, test):
    r = rl[(rl.group == "S1") & (rl.test == test) & (rl.split == split)]; assert len(r) == 1; return r.iloc[0]
pc = lambda x: f"{100 * x:.0f}%"

# The power table: ONE code string, executed here (for the prose) and pasted in the notebook cell (so they cannot disagree).
POWER_CODE = '''
def power_table(full):
    g = full[full.n >= 25]
    spec = [("Receivers", g[g.group == "WR"]),
            ("Defensive line, all", g[(g.group == "DL") & (g.subgroup == "All")]),
            ("   edge only", g[(g.group == "DL") & (g.subgroup == "Edge")]),
            ("   interior only", g[(g.group == "DL") & (g.subgroup == "Interior")]),
            ("Defensive backs", g[g.group == "DB"]),
            ("Tight ends (n 15+)", full[(full.group == "TE") & (full.n >= 15)])]
    rows = [dict(Group=lab, **{"Typical n": int(d.n.median()), "Smallest |rho| seen 8 times in 10": float(f"{d.mde80.median():.2f}"),
                               "...after multiple-test correction": float(f"{d.mde80_bh.median():.2f}"),
                               "Chance to see a true rho of 0.30": float(d.power_rho03.median()),
                               "...after correction": float(d.power_rho03_bh.median())}) for lab, d in spec]
    return pd.DataFrame(rows)
'''
_ns = {"pd": pd, "np": np}; exec(POWER_CODE, _ns); PT = _ns["power_table"](full).set_index("Group")
P = lambda lab, col: PT.loc[lab, col]
n_db, mde_db, pw_db, pwbh_db = int(P("Defensive backs", "Typical n")), P("Defensive backs", "Smallest |rho| seen 8 times in 10"), P("Defensive backs", "Chance to see a true rho of 0.30"), P("Defensive backs", "...after correction")
mde_wr, mde_dl = P("Receivers", "Smallest |rho| seen 8 times in 10"), P("Defensive line, all", "Smallest |rho| seen 8 times in 10")
n_te, mde_te, pw_te = int(P("Tight ends (n 15+)", "Typical n")), P("Tight ends (n 15+)", "Smallest |rho| seen 8 times in 10"), P("Tight ends (n 15+)", "Chance to see a true rho of 0.30")
mde_ed, mde_in = P("   edge only", "Smallest |rho| seen 8 times in 10"), P("   interior only", "Smallest |rho| seen 8 times in 10")

# ---------------------------------------------------------------- numbers by finding
w40, wtop = F("WR", "forty", "sunday_speed_mph"), F("WR", "c_top_mph", "sunday_speed_mph")
assert w40.verdict == wtop.verdict == "TRANSLATES"
wr_other = full[(full.group == "WR") & (full.outcome == "sunday_speed_mph") & (full.n >= 25) & ~full.test.isin(["forty", "c_top_mph"])]
assert (wr_other.verdict == ND).all()
g = full[full.n >= 25]
N_CELLS, N_P05, N_Q05 = len(g), int((g.p_perm < 0.05).sum()), int((g.fdr_q < 0.05).sum()); N_EXP = int(round(N_CELLS * 0.05))
assert (N_CELLS, N_P05, N_Q05) == (164, 28, 2)
wrp = pd.read_csv(OUTD / "wr_te_robust_players.csv").query("pos_group == 'WR'")[["c_top_mph", "sunday_speed_mph"]].dropna()
SLOPE = float(np.polyfit(wrp.c_top_mph, wrp.sunday_speed_mph, 1)[0])

DL_OUT = ["speed_1s_mph", "pressure_rate", "sack_rate", "tfl_rate"]
dl = g[(g.group == "DL") & (g.subgroup == "All") & g.outcome.isin(DL_OUT)]
DL_N, DL_RAW, DL_SIZE = len(dl), dl.rho_raw.median(), dl.rho_size.median(); DL_SHARE = 1 - DL_SIZE / DL_RAW
DL_SNS = int((dl.verdict == "SIZE, NOT SPEED").sum())
dl40p, dl40s, dl10g = F("DL", "forty", "pressure_rate"), F("DL", "forty", "sack_rate"), F("DL", "ten_yd_split", "speed_1s_mph")
dl40p_e, dl40p_i = F("DL", "forty", "pressure_rate", "Edge"), F("DL", "forty", "pressure_rate", "Interior")
assert dl40p.verdict == "LEANS" and dl40p_e.verdict == "LEANS" and dl40p_i.verdict == "LEANS"
big = g[(g.group == "DL") & (g.subgroup == "All") & (g.rho_raw.abs() >= 0.30)]; BIG_N, BIG_HALF = len(big), int((big.rho_size.abs() <= 0.5 * big.rho_raw.abs()).sum())

LEADS = [("WR", "All", "vertical", "break_y", "WR: vertical jump -> separation, break routes"),
         ("WR", "All", "burst_0_100", "break_y", "WR: Burst Score -> separation, break routes"),
         ("DL", "All", "forty", "pressure_rate", "DL: 40 -> pressure rate"),
         ("DL", "All", "ten_yd_split", "speed_1s_mph", "DL: 10-yd split -> get-off speed"),
         ("DL", "All", "burst_0_100", "tfl_rate", "DL: Burst Score -> tackles for loss")]
lead = [F(a, c, d, b) for a, b, c, d, _ in LEADS]
assert all(r.verdict == "LEANS" and r.classes_helped == "3/3" for r in lead)
def need(rho, alpha, k=4): return int(np.ceil(1.06 * ((norm.ppf(1 - alpha / 2) + norm.ppf(0.8)) / np.arctanh(rho)) ** 2 + k + 3))
cls_needed = [(need(r.rho_size, r.alpha_bh) - r.n) / (r.n / 3) for r in lead]
CLS_LO, CLS_HI = int(round(min(cls_needed))), int(np.ceil(max(cls_needed)))
wvert, wburst, dlb = lead[0], lead[1], lead[4]
h1c, h1s, h3t = RC("H1", "three_cone"), RC("H1", "short_shuttle"), RC("H3", "ten_yd_split")
wr3c, wrsh = F("WR", "three_cone", "sunday_speed_mph"), F("WR", "short_shuttle", "sunday_speed_mph")
_ag = full[(full.group == "WR") & full.test.isin(["three_cone", "short_shuttle"])].n; AG_LO, AG_HI = int(_ag.min()), int(_ag.max())   # was hard-coded "22 to 30"; audited range is used

OTH = g[g.group.isin(['WR', 'DB']) & (g.subgroup == 'All') & (g.rho_raw.abs() >= 0.30)]
OTH_BIG = len(OTH); assert int((OTH.rho_size.abs() <= 0.5 * OTH.rho_raw.abs()).sum()) == 0
db = g[g.group == "DB"]; DB_N, DB_NO, DB_LEAN = len(db), int((db.verdict == ND).sum()), int((db.verdict == "LEANS").sum()); assert DB_NO + DB_LEAN == DB_N
DB_QMIN = db.fdr_q.min(); db40 = F("DB", "forty", "pfr_yds_tgt"); dbbj = F("DB", "broad_jump", "pfr_yds_tgt")
db_missed, db_tackle = F("DB", "forty", "pfr_mtkl_pct"), F("DB", "c_decel", "tackle_rate")
SIM_LO, SIM_HI = int(round(100 * sim.simulated_power_at_mde.min())), int(round(100 * sim.simulated_power_at_mde.max()))

gw, gb = W("DL", "player_get_off"), W("DL", "speed_1s_mph"); wpr = W("DL", "pressure_rate")
wsun, wss = W("WR", "sunday_speed_mph"), W("WR", "ssoe_mph")
s_scr, s_cro, s_brk, s_ver = RL("screen", "combine_weight"), RL("crosser", "combine_weight"), RL("break", "combine_weight"), RL("vertical", "combine_weight")
te_n = int(full[full.group == "TE"].n.max())
L_WR = F("WR", "forty", "sunday_speed_mph").coach_line; L_DL = F("DL", "forty", "pressure_rate").coach_line

# ---------------------------------------------------------------- unsupervised track (branch `unsupervised`, aggregates copied to out/unsupervised/, 11/2026)
UD = OUTD / "unsupervised"
ub = pd.read_csv(UD / "familyB.csv"); urel = pd.read_csv(UD / "drill_reliability.csv")
usel = pd.read_csv(UD / "cluster_selection.csv"); unull = pd.read_csv(UD / "cluster_null.csv")
uwr = ub[(ub.group == "WR") & (ub.pc == 3) & (ub.outcome == "sunday_speed_mph")].iloc[0]
assert uwr.q_size < 0.05 and uwr.loso_p < 0.05 and int(uwr.loso_classes_pos) == 3 and uwr.rho_size > 0 and uwr.loso_rho > 0
U_RHO, U_Q, U_HELD, U_CLS = sg(uwr.rho_size), f"{uwr.q_size:.3f}", sg(uwr.loso_rho), int(uwr.loso_classes_pos)
assert (U_RHO, U_Q, U_HELD) == ("+0.50", "0.004", "+0.44"), (U_RHO, U_Q, U_HELD)
# no stable distinct types at WR/TE/DB: no stable k >= 3 (k-means/GMM/Ward), and the stable k = 2 is no more distinct than one blob; DL k = 2 is
for gname in ("WR", "TE", "DB"):
    assert not usel[(usel.group == gname) & (usel.fset == "ALL") & (usel.k >= 3) & (usel.method != "hdbscan")].stable.any()
    assert unull[(unull.group == gname) & (unull.fset == "ALL") & (unull.k == 2)].p_one_blob.iloc[0] > 0.05
assert unull[(unull.group == "DL") & (unull.fset == "ALL") & (unull.k == 2)].p_one_blob.iloc[0] < 0.05
rr = urel[urel.feature.isin(["drill_dec", "drill_keep", "drill_turn"])]
rr_ex = rr[~((rr.group == "TE") & (rr.feature == "drill_turn"))]
U_REL = f"{rr_ex.alpha_k.max():.2f}"; assert U_REL == "0.42", U_REL
assert rr[(rr.group == "TE") & (rr.feature == "drill_turn")].alpha_k.iloc[0] >= 0.6   # the one exception, named in the sentence

PT_CELL = """
pt = power_table(full)
tbl = pt.copy()
for c in ["Chance to see a true rho of 0.30", "...after correction"]:
    tbl[c] = (100 * tbl[c]).map(lambda v: f"{v:.0f}%")
display(tbl.reset_index(drop=True))
"""
md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}
code = lambda s: {"cell_type": "code", "metadata": {"jupyter": {"source_hidden": True}, "_kg_hide-input": True, "tags": ["hide-input"]}, "execution_count": None, "outputs": [], "source": s.strip("\n").splitlines(True)}
C = []

# =====================================================================================  HOOK + GATE
C.append(md(f"""
# Read the Combine through body size: three positions, three different stories
*NFL Big Data Bowl 2027 · Open Track · Combine tracking linked to regular-season game tracking · WR, TE, DB, DL*

**Three positions, three stories.** Receivers: speed is real and shows up on Sunday. Linemen: the drills predict pass rush, mostly through body size, so read them size-adjusted. Defensive backs: the Combine alone is a weak guide at this sample size.

**The required link, stated plainly.** We connect each rookie's 10 Hz Combine tracking (2023 to 2025 classes) to his regular-season game tracking. A receiver's tracked Combine top speed predicts his regular-season speed on deep routes (ρ {sg(wtop.rho_raw)} year-controlled, **{sg(wtop.rho_size)} with body size held fixed**, n {int(wtop.n)}). The cell below recomputes that from the raw tracking files.

Data: the competition's Combine, game-tracking, play, player and game files, plus public Pro-Football-Reference stats (two DB outcomes). No draft-position information is used; draft *year* is a control only. Running backs are excluded. **Sunday Speed** is a player's 90th-percentile top speed per play where his job asks for speed (deep routes for receivers; man or deep coverage for defensive backs), regular season. **Burst Score** is a 0 to 100 within-position blend of the tracked 20-yard time and the jumps. ρ is a rank correlation; positive means the better athlete does better.
"""))

C.append(code('''
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt, matplotlib.lines as ml
from scipy import stats
from scipy.stats import norm
from IPython.display import Image, display

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
OKABE = {"blue": "#0072B2", "orange": "#E69F00", "red": "#D55E00", "green": "#009E73", "grey": "#8a8a8a"}
ND = "NOT DETECTED (low power)"

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
full = pd.read_csv(OUT / "scorecard_full.csv")
card = pd.read_csv(OUT / "scorecard.csv")
wt = pd.read_csv(OUT / "scorecard_weight.csv")
g25 = full[full.n >= 25]
qtxt = lambda q: "<0.01" if q < .01 else f"{q:.2f}"
print("audited outputs:", OUT, "| competition data:", COMP)
'''))
C.append(code(open(HERE / "fig_cells" / "setup_helpers.py").read()))

C.append(code(open(HERE / "fig_cells" / "gate.py").read()))
C.append(md("*Figure 1. Each dot is a receiver. A: as measured. B: after removing draft year, weight and height from both axes (ranks).*"))

# =====================================================================================  1 WR
C.append(md(f"""
## 1. Receivers: speed is real, and it carries to Sunday
Two Combine measures clear every check, and both are receiver straight-line speed. The 40-yard dash goes with faster game speed on deep routes (ρ {sg(w40.rho_size)} with size held fixed, 95% CI {CI(w40)}, n {int(w40.n)}, q {qf(w40.fdr_q)}). Tracked Combine top speed is stronger ({sg(wtop.rho_size)}, {CI(wtop)}, n {int(wtop.n)}, q {qf(wtop.fdr_q)}). Both improve predictions on held-out draft classes ({w40.classes_helped} each).

Each extra mph of Combine top speed goes with about {SLOPE:.2f} mph more on a deep route in a game (Figure 1). Size barely moves it, unlike the defensive line. The other receiver tests (10-yard split, jumps, shuttle, Burst Score) were not detected (about {mde_wr:.2f} or more was needed).

Figure 2 is the proof of method. Of {N_CELLS} tests with at least 25 players, {N_P05} reach p < 0.05 against about {N_EXP} expected by chance (cells share players, so that overstates independent findings). After false-discovery correction exactly {N_Q05} remain, both receiver rows. The method finds real signal where it exists. A blind unsupervised search that never saw game outcomes rediscovered this speed axis (ρ {U_RHO}, q {U_Q}; held-out {U_HELD}, {U_CLS} of 3 classes).
"""))
C.append(code(open(HERE / "fig_cells" / "fig2.py").read()))
C.append(md("*Figure 2. A: every receiver test against deep-route speed. B: all 164 tests; only two survive correction.*"))

# =====================================================================================  2 DL
C.append(md(f"""
## 2. Defensive line: the drills predict pass rush, mostly through body size
Faster linemen get off quicker, rush more and sack more, but much of that is body size. Across {DL_N} cells with at least 25 players (tests against get-off, pressure, sack and tackles for loss), the median year-controlled link is ρ {sg(DL_RAW)}. Hold weight, height and role (edge or interior) fixed and it is {sg(DL_SIZE)}: about {pc(DL_SHARE)} of the raw link is shared with body size and role (a statistical split, not proof of cause; Figure 3).

What remains is still positive:
- The 40 against **pressure rate** goes from {sg(dl40p.rho_raw)} to {sg(dl40p.rho_size)} (95% CI {CI(dl40p)}, q {dl40p.fdr_q:.2f}).
- The 10-yard split against **get-off speed** goes from {sg(dl10g.rho_raw)} to {sg(dl10g.rho_size)} (q {dl10g.fdr_q:.2f}).
- The 40 against **sack rate** goes from {sg(dl40s.rho_raw)} to {sg(dl40s.rho_size)}, and its interval ({CI(dl40s)}) now touches zero.

The pressure lean appears separately for edge ({sg(dl40p_e.rho_size)}, n {int(dl40p_e.n)}) and interior ({sg(dl40p_i.rho_size)}, n {int(dl40p_i.n)}) rushers. Of {BIG_N} defensive-line cells with a raw link of at least 0.30, {BIG_HALF} lose half or more to size; none of {OTH_BIG} receiver or DB cells do.
"""))
C.append(code(open(HERE / "fig_cells" / "fig3.py").read()))
C.append(md("*Figure 3. Defensive-line tests, raw to size-adjusted. The gap is what body size and role account for.*"))

# =====================================================================================  3 LEADS
C.append(md(f"""
## 3. Consistent leads that need more seasons
Five results hold in every held-out draft class ({lead[0].classes_helped} each) but do not clear the false-discovery bar. We call them leads:
- **Receivers:** a higher vertical jump ({sg(wvert.rho_size)}, n {int(wvert.n)}, q {wvert.fdr_q:.2f}) and Burst Score ({sg(wburst.rho_size)}, n {int(wburst.n)}, q {wburst.fdr_q:.2f}) go with more separation on break routes.
- **Defensive line:** the 40 goes with pressure rate ({sg(lead[2].rho_size)}, q {lead[2].fdr_q:.2f}), the 10-yard split with get-off speed ({sg(lead[3].rho_size)}, q {lead[3].fdr_q:.2f}), and Burst Score with tackles for loss ({sg(dlb.rho_size)}, q {dlb.fdr_q:.2f}).

Each estimate is at or below what these samples reliably detect even before correction (about {mde_wr:.2f} for receivers, {mde_dl:.2f} for linemen), and well below what the correction demands (about {P("Receivers","...after multiple-test correction"):.2f} and {P("Defensive line, all","...after multiple-test correction"):.2f}). If the true links equal today's estimates, confirming them needs roughly {CLS_LO} to {CLS_HI} more draft classes (Figure 4). That is optimistic: leads are the best-looking tests.

The textbook agility stories were not detected. We pre-declared that 3-cone and shuttle matter more on break than vertical routes (differences {sg(h1c['diff'])} and {sg(h1s['diff'])}, intervals include zero) and that quickness matters more against man than zone (10-yard difference {sg(h3t['diff'])}, CI {CI(h3t,'lo','hi')}). Only {AG_LO} to {AG_HI} receivers ran those drills, so only effects of about {wrsh.mde80:.2f} or more were visible; not detected is not ruled out.
"""))
C.append(code(open(HERE / "fig_cells" / "fig4.py").read()))
C.append(md("*Figure 4. The five leads. Gray band: what each sample could reliably see. Right label: players needed to confirm the estimate after correction, if it is true.*"))

# =====================================================================================  4 DB
C.append(md(f"""
## 4. Defensive backs: the Combine alone is a weak guide at this sample size
{DB_N} cornerback and safety cells have at least 25 players. {DB_NO} are **NOT DETECTED (low power)** and {DB_LEAN} lean; none clears the correction (lowest q {DB_QMIN:.2f}). That is a power problem: with about {n_db} players, only links of ρ {mde_db:.2f} or more would be seen 8 times in 10, and a true link of 0.30 only {pc(pw_db)} of the time ({pc(pwbh_db)} after correction; Table 1).

The intervals are wide. The 40 against missed tackles is {sg(db_missed.rho_size)} (CI {CI(db_missed)}); DB-drill braking against tackle rate is {sg(db_tackle.rho_size)} ({CI(db_tackle)}).

One result runs the wrong way. A faster 40 goes with *more* yards allowed per target ({sg(db40.rho_size)}, n {int(db40.n)}, 95% CI {CI(db40)}), and broad jump agrees ({sg(dbbj.rho_size)}). We read that as coverage role, not "speed hurts", and it does not clear correction. Use the Combine for defensive backs as one input beside tape and role.
"""))
C.append(code(POWER_CODE + "\n" + PT_CELL + "\n" + open(HERE / "fig_cells" / "fig5.py").read()))
C.append(md("*Table 1. What each sample can see: the smallest correlation seen 8 times in 10, and the chance of seeing a true 0.30 (medians over tests with 25+ players).*"))
C.append(md("*Figure 5. Defensive backs, best test per result: mostly inside the gray band, so not detected, not ruled out.*"))

# =====================================================================================  5 WEIGHT
C.append(md(f"""
## 5. Weight is the variable scouts must adjust for
A stopwatch cannot tell weight from talent. Holding height and draft year fixed (role too for linemen; Figure 6):

- **Defensive line.** Heavier linemen get off the ball slower (ρ {sg(gw.rho_height_ctrl)}, 95% CI {CI(gw)}, q {qf(gw.fdr_q)}) and reach a lower speed one second after the snap ({sg(gb.rho_height_ctrl)}, q {qf(gb.fdr_q)}).
- **Receivers.** Heavier receivers run slower on deep routes ({sg(wsun.rho_height_ctrl)}, q {qf(wsun.fdr_q)}) and slower than their own 40 predicts ({sg(wss.rho_height_ctrl)}, q {qf(wss.fdr_q)}).
- **Separation.** Heavier receivers also get less separation on break ({sg(s_brk.rho_size)}), vertical ({sg(s_ver.rho_size)}) and crosser ({sg(s_cro.rho_size)}) routes, not on screens ({sg(s_scr.rho_size)}): a lead (q {s_cro.fdr:.2f}).

Weight does not move everything: pressure rate is only weakly tied to it ({sg(wpr.rho_height_ctrl)}, q {wpr.fdr_q:.2f}). Scouts adjust a 40 for weight by feel; these numbers say how much.
"""))
C.append(code(open(HERE / "fig_cells" / "fig6.py").read()))
C.append(md("*Figure 6. Weight against on-field results. Left of zero: heavier players do worse.*"))

# =====================================================================================  SCOUT USE
C.append(md(f"""
## How a scout uses this
A scorecard, not a ranking (Figure 7), behind a lookup dashboard: enter a Combine line and each test returns a tag and a one-line read. One example:
- **{L_WR}**

Rules of thumb: trust a receiver's 40 and tracked top speed; compare linemen only with linemen of their weight and role; treat defensive-back numbers as one input among several. Every line carries its n and interval.
"""))
C.append(code(open(HERE / "fig_cells" / "fig7.py").read()))
C.append(md("*Figure 7. The scorecard, with the smallest detectable effect (MDE). Green TRANSLATES, orange LEANS, purple SIZE, NOT SPEED, gray NOT DETECTED (low power), light gray TOO FEW TO TELL.*"))

# =====================================================================================  METHODS + LIMITS
C.append(md(f"""
## Methods, in plain language
- **Size control.** Every link is repeated holding draft year, weight and height fixed (plus CB versus S, edge versus interior).
- **Shrinkage and held-out classes.** Rates from few snaps are pulled toward the group average. We train on two draft classes, predict the third, and ask whether adding the test beats a size-only model.
- **False-discovery control.** Each p comes from 10,000 permutations, each interval from a player-level bootstrap, and each result carries a Benjamini-Hochberg q across its whole family of tests. Verdict rules and receiver hypotheses were written first, and every p and interval was re-checked with a second method.
- Clustering found no stable athletic types at receiver, tight end or defensive back (only lean-edge versus heavy-interior linemen), and we skipped skill-drill braking, cut-speed and turn-rate tracking because they mostly do not repeat across drills (reliability {U_REL} or less).
- **Power.** The smallest detectable effect (MDE, 80% power) is a Fisher-z approximation, checked by simulation ({SIM_LO}% to {SIM_HI}% power at the MDE).

**Verdicts.** TRANSLATES: q below 0.05, interval excludes zero, held-out classes agree. LEANS: interval excludes zero or p below 0.05, but q does not clear. SIZE, NOT SPEED: a raw link of at least 0.30 that falls by half or more. TOO FEW TO TELL: under 25 players. **NOT DETECTED (low power):** none of the above; no link above the MDE was seen, not no link.
"""))
C.append(md(f"""
## Limitations
- Rookies only (2023 to 2025 classes) with tracked snaps; skipped drills are not random.
- Counts are small: receivers about {int(P("Receivers", "Typical n"))}, defensive backs about {n_db}, linemen about {int(P("Defensive line, all", "Typical n"))}, tight ends about {n_te}, too few to tell ({mde_te:.2f} detectable, {pc(pw_te)} power at 0.30).
- The same players produced the leads and test them; three held-out classes are the only out-of-sample check. Burst Score recipes were chosen using game results, and Figures 5 and 7 show the best-looking test per result, so those numbers are optimistic.
- Pooled defensive-line size may partly mean role; edge and interior splits have only {int(dl40p_e.n)} and {int(dl40p_i.n)} players (about {mde_ed:.2f} and {mde_in:.2f} detectable).
- No blocker or quarterback tracks are linked: pressure and sack results are association, not causation.
"""))
C.append(md("""
## Appendix
Code cells are collapsed. Attach the `bdb2027-outputs` dataset (audited result tables) and the competition data.
"""))

for i, c in enumerate(C):
    c["id"] = hashlib.md5(f"bdb2027-{i}".encode()).hexdigest()[:8]
NB = {"cells": C, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
(HERE / "bdb2027_writeup.ipynb").write_text(json.dumps(NB, indent=1, ensure_ascii=False) + "\n")
words, per = 0, []
for c in C:
    if c["cell_type"] == "markdown":
        n = len(re.findall(r"\S+", "".join(c["source"]))); words += n; per.append(n)
print("markdown words:", words, per)
assert words < 2000, words

# ---------------------------------------------------------------- paste-ready markdown for the Kaggle Writeup form
FIGD = HERE / "writeup_figs"; FIGD.mkdir(exist_ok=True)
IMG = {"Figure 1": "fig1_gate_wr.png", "Figure 2": "fig2_wr_control.png", "Figure 3": "fig3_dl_size.png", "Figure 4": "fig4_leads.png",
       "Figure 5": "fig5_db_power.png", "Figure 6": "fig6_weight.png", "Figure 7": "fig7_scorecard.png"}
tbl = ["| Group | Typical n | Smallest ρ seen 8 times in 10 | ...after multiple-test correction | Chance to see a true ρ of 0.30 | ...after correction |", "|---|---:|---:|---:|---:|---:|"]
for lab, r in PT.iterrows():
    tbl.append(f"| {lab.strip()} | {int(r['Typical n'])} | {r['Smallest |rho| seen 8 times in 10']:.2f} | {r['...after multiple-test correction']:.2f} | {pc(r['Chance to see a true rho of 0.30'])} | {pc(r['...after correction'])} |")
parts = []
for c in C:
    if c["cell_type"] != "markdown": continue
    t = "".join(c["source"]); m = re.match(r"\*(Figure \d|Table 1)\.", t)
    if m: parts.append("\n".join(tbl) if m.group(1) == "Table 1" else f"![{m.group(1)}](writeup_figs/{IMG[m.group(1)]})")
    parts.append(t)
# Writeup-only wording (audit 11/2026, F2-F6; approved by Kevin). Notebook cells above are left as published on Kaggle (v2).
_md_out = "\n\n".join(parts) + "\n"
WRITEUP_EDITS = [
    # F6: the Writeup form's title field carries the title, so the body drops the H1
    ("# Read the Combine through body size: three positions, three different stories\n", ""),
    # F2: no code cells in a Writeup
    ("The cell below recomputes that from the raw tracking files.",
     "The attached public notebook recomputes that from the raw tracking files."),
    # F5: explicit data credit
    ("plus public Pro-Football-Reference stats (two DB outcomes).",
     "plus public Pro-Football-Reference stats via nflverse (two DB outcomes). Source: NFL Big Data Bowl 2027 (CC BY-NC 4.0)."),
    # F4: judges cannot open a dashboard
    ("behind a lookup dashboard: enter a Combine line and each test returns a tag and a one-line read.",
     "built for lookup: for each Combine test it returns a tag and a one-line read."),
    # F3: notebook language out of the Appendix
    ("Code cells are collapsed. Attach the `bdb2027-outputs` dataset (audited result tables) and the competition data.",
     "Code: the attached public Kaggle notebook (competition data plus the public `bdb2027-outputs` result tables). All code is open source."),
]
for _old, _new in WRITEUP_EDITS:
    assert _md_out.count(_old) == 1, ("writeup edit target not found exactly once", _old[:60])
    _md_out = _md_out.replace(_old, _new)
assert _md_out.count("](writeup_figs/") == 7
(HERE / "writeup_for_kaggle.md").write_text(_md_out.lstrip("\n"))
print(f"exported writeup_for_kaggle.md; visuals: {len(IMG)} figures + 1 table = {len(IMG) + 1}")
_md = (HERE / "writeup_for_kaggle.md").read_text()
STRICT = len(re.findall(r"\S+", _md))   # strictest count: every token of the paste-ready markdown, table pipes and image lines included
_plain = re.sub(r"!\[.*?\]\(.*?\)", " ", _md); _plain = re.sub(r"[#*|>]+|(?<!\w)[-:]+(?!\w)", " ", _plain)
PLAIN = len([w for w in re.findall(r"\S+", _plain) if re.search(r"[A-Za-z0-9]", w)])
print(f"word counts: markdown cells {words}; paste-ready md, words only {PLAIN}; strict (every token) {STRICT}")
assert STRICT <= 1900, STRICT
_bad = re.findall(r"(?i)\b(pick\w*|round\w*|slot\w*)\b", _md + "".join("".join(c["source"]) for c in C))
assert not _bad, _bad
_comps = re.findall(r"(?i)\bcomps\b|athletic comp", _md + "".join("".join(c["source"]) for c in C if c["cell_type"] == "markdown"))
assert not _comps, _comps   # no athletic comps (dropped 11/19/2026)
print(f"slope {SLOPE:.3f}; DL share {DL_SHARE:.2f}; classes needed {cls_needed}; DB n {n_db} mde {mde_db} pw {pw_db:.2f}/{pwbh_db:.2f}; sim {SIM_LO}-{SIM_HI}")
print(PT.round(2).to_string())
