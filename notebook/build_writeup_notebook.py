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
    rows = [dict(Group=lab, **{"Typical n": int(d.n.median()), "Smallest |rho| seen 8 times in 10": round(float(d.mde80.median()), 2),
                               "...after multiple-test correction": round(float(d.mde80_bh.median()), 2),
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

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}
code = lambda s: {"cell_type": "code", "metadata": {"jupyter": {"source_hidden": True}, "tags": ["hide-input"]}, "execution_count": None, "outputs": [], "source": s.strip("\n").splitlines(True)}
C = []

# =====================================================================================  HOOK + GATE
C.append(md(f"""
# Read the Combine through body size: three positions, three different stories
*NFL Big Data Bowl 2027 · Open Track · Combine tracking linked to regular-season game tracking · WR, TE, DB, DL*

**Read Combine numbers through body size, and three positions tell three different stories.** Receivers: speed is real and shows up on Sunday. Linemen: the drills predict pass rush, mostly through body size, so read them size-adjusted. Defensive backs: the Combine alone is a weak guide at this sample size.

**The required link, stated plainly.** We connect each rookie's 10 Hz Combine tracking (2023 to 2025 classes) to his regular-season game tracking. A receiver's tracked Combine top speed predicts his regular-season speed on deep routes (ρ {sg(wtop.rho_raw)} year-controlled, **{sg(wtop.rho_size)} with body size held fixed**, n {int(wtop.n)}). The cell below recomputes that from the raw tracking files.

Data: the competition's Combine tracking, game tracking, play, player and game files, plus free public Pro-Football-Reference season stats for two defensive-back outcomes. No draft-position information is used; draft *year* is a control only. Running backs are excluded. **Sunday Speed** is a player's 90th-percentile top speed per play where his job asks for speed (deep routes for receivers; man or deep coverage for defensive backs), regular season. **Burst Score** is a 0 to 100 within-position blend of the tracked 20-yard time and the jumps. ρ is a rank correlation; positive means the better athlete does better.
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
VCOL = {"TRANSLATES": OKABE["green"], "LEANS": OKABE["orange"], "SIZE, NOT SPEED": OKABE["red"], ND: OKABE["grey"], "TOO FEW TO TELL": "#c8c8c8"}

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

# =====================================================================================  1 WR
C.append(md(f"""
## 1. Receivers: speed is real, and it carries to Sunday
Two Combine measures clear every check, and both are receiver straight-line speed. The 40-yard dash goes with faster game speed on deep routes (ρ {sg(w40.rho_size)} with size held fixed, 95% CI {CI(w40)}, n {int(w40.n)}, q {qf(w40.fdr_q)}). The tracked Combine top speed does so even more strongly ({sg(wtop.rho_size)}, {CI(wtop)}, n {int(wtop.n)}, q {qf(wtop.fdr_q)}). Both improve predictions on held-out draft classes ({w40.classes_helped} each).

Each extra mph of Combine top speed goes with about {SLOPE:.2f} mph more on a deep route in a game (Figure 1). Size barely moves this result ({sg(wtop.rho_raw)} before size control, {sg(wtop.rho_size)} after), unlike the defensive line. The other receiver tests (10-yard split, jumps, shuttle, Burst Score) were not detected against deep-route speed (about {mde_wr:.2f} or more was needed to see them).

Figure 2 is the proof of method. Of {N_CELLS} tests with at least 25 players, {N_P05} reach p < 0.05 against about {N_EXP} expected by chance (cells share players, so that overstates independent findings). After false-discovery correction exactly {N_Q05} remain, both receiver rows. The method finds real signal where it exists.
"""))
C.append(md("*Figure 1. Each dot is a receiver: faster at the Combine, faster on Sunday deep routes.*"))
C.append(code('''
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.0), gridspec_kw={"width_ratios": [1.15, 1]})
tl = [("forty", "40"), ("c_top_mph", "Top speed (tracked)"), ("ten_yd_split", "10-yd split"), ("burst_0_100", "Burst Score"), ("vertical", "Vertical"), ("broad_jump", "Broad jump"), ("short_shuttle", "Short shuttle"), ("three_cone", "3-cone")]
for i, (t, lab) in enumerate(tl[::-1]):
    r = full[(full.group == "WR") & (full.subgroup == "All") & (full.test == t) & (full.outcome == "sunday_speed_mph")].iloc[0]; col = VCOL[r.verdict]
    a1.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2.2); a1.scatter(r.rho_size, i, s=48, color=col, zorder=3); a1.scatter(r.rho_raw, i, s=34, facecolor="white", edgecolor=col, marker="D", zorder=3)
    a1.text(.98, i, f"n {int(r.n)}  q {qtxt(r.fdr_q)}  held-out {r.classes_helped}", va="center", ha="left", fontsize=7.5, color=col)
a1.set_yticks(range(len(tl))); a1.set_yticklabels([x[1] for x in tl[::-1]]); a1.axvline(0, color="k", lw=.8); a1.set_xlim(-.9, .98)
a1.set_title("Receivers, deep-route game speed: every Combine test", loc="left", fontsize=9.5, fontweight="bold")
a1.set_xlabel("rank correlation (filled = size held fixed, 95% CI; hollow = before)")
p = g25.sort_values("p_perm").reset_index(drop=True); k = np.arange(1, len(p) + 1)
pass_ = p.fdr_q < .05
a2.scatter(k[~pass_], p.p_perm[~pass_], s=14, color="#9a9a9a", alpha=.8); a2.scatter(k[pass_], p.p_perm[pass_], s=60, color=OKABE["green"], zorder=3, label="clears false-discovery bar")
a2.plot(k, k / len(p), color="k", ls=":", lw=1, label="if nothing were real"); a2.axhline(.05, color=OKABE["red"], ls="--", lw=1, label="p = 0.05")
a2.set_yscale("log"); a2.set_xlabel(f"the {len(p)} tests, ranked by p-value"); a2.set_ylabel("permutation p-value")
a2.set_title(f"{int((p.p_perm < .05).sum())} under p=0.05 (about {round(len(p) * .05)} by chance); {int(pass_.sum())} survive", loc="left", fontsize=9.5, fontweight="bold"); a2.legend(fontsize=8, frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(SAVE / "fig2_wr_control.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 2. Left: every receiver test against deep-route speed. Right: all 164 tests; only two survive correction.*"))

# =====================================================================================  2 DL
C.append(md(f"""
## 2. Defensive line: the drills predict pass rush, mostly through body size
Linemen's Combine numbers do carry information: faster linemen get off quicker, rush more and sack more. The catch is how much is body size. Across the four outcomes with a strong raw link (get-off, pressure, sack, tackle for loss), {DL_N} test-by-outcome cells have at least 25 players. Their median year-controlled link is ρ {sg(DL_RAW)}. Hold weight, height and role (edge or interior) fixed and the median is {sg(DL_SIZE)}, so about {pc(DL_SHARE)} of the raw link runs through body size (Figure 3).

What remains is still positive and still useful:
- The 40 against **pressure rate** goes from {sg(dl40p.rho_raw)} to {sg(dl40p.rho_size)} (95% CI {CI(dl40p)}, q {dl40p.fdr_q:.2f}).
- The 10-yard split against **get-off speed** goes from {sg(dl10g.rho_raw)} to {sg(dl10g.rho_size)} (q {dl10g.fdr_q:.2f}).
- The 40 against **sack rate** goes from {sg(dl40s.rho_raw)} to {sg(dl40s.rho_size)}, and its interval ({CI(dl40s)}) now touches zero.

**How scouts should read it:** a lineman's 40 is a size-adjusted signal. Compare him with linemen of the same weight and role, not the whole group. The pressure lean appears separately for edge ({sg(dl40p_e.rho_size)}, n {int(dl40p_e.n)}) and interior ({sg(dl40p_i.rho_size)}, n {int(dl40p_i.n)}) rushers. Of {BIG_N} defensive-line cells with a raw link of at least 0.30, {BIG_HALF} lose half or more to size; none of {OTH_BIG} receiver or DB cells do.
"""))
C.append(code('''
tests = [("ten_yd_split", "10-yd split"), ("forty", "40"), ("c_top_mph", "Top speed (tracked)"), ("burst_0_100", "Burst Score"), ("vertical", "Vertical"), ("broad_jump", "Broad jump")]
outs = [("speed_1s_mph", "Get-off speed (1 s)"), ("pressure_rate", "Pressure rate"), ("sack_rate", "Sack rate"), ("tfl_rate", "Tackles for loss")]
fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.7), sharey=True, sharex=True)
for ax, (oc, ol) in zip(axes, outs):
    for i, (t, tl_) in enumerate(tests[::-1]):
        r = g25[(g25.group == "DL") & (g25.subgroup == "All") & (g25.test == t) & (g25.outcome == oc)]
        if r.empty: continue
        r = r.iloc[0]; col = VCOL[r.verdict]
        ax.annotate("", xy=(r.rho_size, i), xytext=(r.rho_raw, i), arrowprops=dict(arrowstyle="->", color=col, lw=1.2, alpha=.7))
        ax.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2.2, alpha=.55, solid_capstyle="round")
        ax.scatter(r.rho_raw, i, s=34, facecolor="white", edgecolor=col, marker="D", zorder=3); ax.scatter(r.rho_size, i, s=44, color=col, zorder=4)
    ax.set_yticks(range(len(tests))); ax.set_yticklabels([t[1] for t in tests[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.45, .95); ax.set_title(ol, fontsize=9.5, fontweight="bold")
fig.supxlabel("hollow diamond = raw link (year-controlled); filled dot = size- and role-adjusted with 95% CI; + = faster athlete does better", fontsize=8.5)
fig.legend([ml.Line2D([], [], marker="o", color=VCOL[k], lw=0) for k in ["SIZE, NOT SPEED", "LEANS"]], ["Mostly size (interval includes 0)", "Survives size adjustment (a lead)"], loc="upper right", ncol=2, fontsize=8, frameon=False)
fig.tight_layout(rect=(0, .03, 1, .95)); fig.savefig(SAVE / "fig3_dl_size.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 3. Defensive-line tests, raw to size-adjusted. The gap is body size. 3-cone and shuttle (under 36 linemen) are left out.*"))

# =====================================================================================  3 LEADS
C.append(md(f"""
## 3. Consistent leads that need more seasons
Five results hold in every held-out draft class ({lead[0].classes_helped} each) but do not clear the false-discovery bar. We call them leads and show the honest q:
- **Receivers:** a higher vertical jump ({sg(wvert.rho_size)}, n {int(wvert.n)}, q {wvert.fdr_q:.2f}) and Burst Score ({sg(wburst.rho_size)}, n {int(wburst.n)}, q {wburst.fdr_q:.2f}) go with more separation on break routes.
- **Defensive line:** the 40 goes with pressure rate ({sg(lead[2].rho_size)}, q {lead[2].fdr_q:.2f}), the 10-yard split with get-off speed ({sg(lead[3].rho_size)}, q {lead[3].fdr_q:.2f}), and Burst Score with tackles for loss ({sg(dlb.rho_size)}, q {dlb.fdr_q:.2f}).

Each estimate is at or below what these samples reliably detect even before correction (about {mde_wr:.2f} for receivers, {mde_dl:.2f} for linemen), and well below what the correction demands (about {P("Receivers","...after multiple-test correction"):.2f} and {P("Defensive line, all","...after multiple-test correction"):.2f}). If the true links equal today's estimates, confirming them needs roughly {CLS_LO} to {CLS_HI} more draft classes (Figure 4). That is optimistic: leads are the best-looking tests.

The textbook agility stories were not detected. We pre-declared that 3-cone and shuttle matter more on break than vertical routes (differences {sg(h1c['diff'])} and {sg(h1s['diff'])}, intervals include zero) and that quickness matters more against man than zone (10-yard difference {sg(h3t['diff'])}, CI {CI(h3t,'lo','hi')}). Only 22 to 30 receivers ran those drills, so only effects of about {wrsh.mde80:.2f} or more were visible. Not detected is not ruled out.
"""))
C.append(code('''
def players_needed(rho, alpha, k=4):
    return int(np.ceil(1.06 * ((norm.ppf(1 - alpha / 2) + norm.ppf(.8)) / np.arctanh(rho)) ** 2 + k + 3))
LEADS = [("WR", "All", "vertical", "break_y", "Receivers: vertical jump -> break separation"),
         ("WR", "All", "burst_0_100", "break_y", "Receivers: Burst Score -> break separation"),
         ("DL", "All", "forty", "pressure_rate", "Linemen: 40 -> pressure rate"),
         ("DL", "All", "ten_yd_split", "speed_1s_mph", "Linemen: 10-yd split -> get-off speed"),
         ("DL", "All", "burst_0_100", "tfl_rate", "Linemen: Burst Score -> tackles for loss")]
fig, ax = plt.subplots(figsize=(9.6, 3.9))
for i, (grp, sub, t, oc, lab) in enumerate(LEADS[::-1]):
    r = full[(full.group == grp) & (full.subgroup == sub) & (full.test == t) & (full.outcome == oc)].iloc[0]
    col = OKABE["blue"] if grp == "WR" else OKABE["red"]
    ax.fill_betweenx([i - .32, i + .32], -r.mde80, r.mde80, color="#cfcfcf", alpha=.45, zorder=0)
    ax.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2.4); ax.scatter(r.rho_size, i, s=56, color=col, zorder=3)
    need = players_needed(r.rho_size, r.alpha_bh)
    ax.text(.97, i, f"q {qtxt(r.fdr_q)} | held-out {r.classes_helped} | n {int(r.n)}, ~{need} needed", va="center", fontsize=7.8, color="#333")
ax.set_yticks(range(len(LEADS))); ax.set_yticklabels([x[4] for x in LEADS[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.55, .97)
ax.set_xlabel("size-controlled rank correlation (dot, 95% CI).  Gray band: the smallest effect this n would reliably detect (80% power)")
ax.set_title("Leads: consistent in every held-out class, not yet past the correction", loc="left", fontweight="bold", fontsize=10)
fig.tight_layout(); fig.savefig(SAVE / "fig4_leads.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 4. The five leads. Gray band: what each sample could reliably see. Right label: players needed to confirm the estimate after correction, if it is true.*"))

# =====================================================================================  4 DB
C.append(md(f"""
## 4. Defensive backs: the Combine alone is a weak guide at this sample size
{DB_N} cornerback and safety cells have at least 25 players. {DB_NO} are **not detected** and {DB_LEAN} lean; none clears the correction (lowest q {DB_QMIN:.2f}). The Combine is not useless for defensive backs; with about {n_db} players, only links of ρ {mde_db:.2f} or more would be seen 8 times in 10, and a true link of 0.30 only {pc(pw_db)} of the time ({pc(pwbh_db)} after correction; Table 1).

The intervals are wide. The 40 against missed tackles is {sg(db_missed.rho_size)} (CI {CI(db_missed)}); DB-drill braking against tackle rate is {sg(db_tackle.rho_size)} ({CI(db_tackle)}). Absence of evidence is not evidence of absence.

One result runs the wrong way. A faster 40 goes with *more* yards allowed per target ({sg(db40.rho_size)}, n {int(db40.n)}, 95% CI {CI(db40)}), and broad jump agrees ({sg(dbbj.rho_size)}). We read that as coverage role, not "speed hurts", and it does not clear correction. Use the Combine for defensive backs as one input beside tape and role. Table 1 shows what every group's sample can see; tight ends (about {n_te} players, {mde_te:.2f} detectable) are too few to say anything.
"""))
C.append(code(POWER_CODE + '''
pt = power_table(full)
tbl = pt.copy()
for c in ["Chance to see a true rho of 0.30", "...after correction"]:
    tbl[c] = (100 * tbl[c]).round(0).astype(int).astype(str) + "%"
display(tbl.reset_index(drop=True))

db = card[card.group == "DB"]
fig, ax = plt.subplots(figsize=(9.6, 3.9))
for i, (_, r) in enumerate(db.iloc[::-1].iterrows()):
    col = VCOL[r.verdict]
    ax.fill_betweenx([i - .32, i + .32], -r.mde80, r.mde80, color="#cfcfcf", alpha=.45, zorder=0)
    ax.plot([r.ci_lo, r.ci_hi], [i, i], color=col, lw=2.4); ax.scatter(r.rho_size, i, s=52, color=col, zorder=3)
    ax.text(.97, i, f"n {int(r.n)}  q {qtxt(r.fdr_q)}", va="center", fontsize=7.8, color="#333")
ax.set_yticks(range(len(db))); ax.set_yticklabels([f"{a} -> {b}" for a, b in zip(db.test_label.iloc[::-1], db.outcome_label.iloc[::-1])], fontsize=8)
ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.7, .97)
ax.set_xlabel("size-controlled rank correlation (dot, 95% CI; orange = lead, gray = not detected)\\nGray band: smallest effect this n could reliably see", fontsize=8.5)
ax.set_title("Defensive backs: wide intervals, mostly inside what this n can see", loc="left", fontweight="bold", fontsize=10)
fig.tight_layout(); fig.savefig(SAVE / "fig5_db_power.png", dpi=170); plt.show()
'''))
C.append(md("*Table 1. What each sample can see: the smallest correlation seen 8 times in 10, and the chance of seeing a true 0.30 (medians over tests with 25+ players).*"))
C.append(md("*Figure 5. Defensive backs, best test per result: mostly inside the gray band, so not detected, not ruled out.*"))

# =====================================================================================  5 WEIGHT
C.append(md(f"""
## 5. Weight is the variable scouts must adjust for
A stopwatch cannot tell weight from talent. Holding height and draft year fixed (Figure 6):

- **Defensive line.** Heavier linemen get off the ball slower (ρ {sg(gw.rho_height_ctrl)}, 95% CI {CI(gw)}, q {qf(gw.fdr_q)}) and reach a lower speed one second after the snap ({sg(gb.rho_height_ctrl)}, q {qf(gb.fdr_q)}). This is why Section 2 reads linemen size-adjusted.
- **Receivers.** Heavier receivers run slower on deep routes ({sg(wsun.rho_height_ctrl)}, q {qf(wsun.fdr_q)}) and slower than their own 40 predicts ({sg(wss.rho_height_ctrl)}, q {qf(wss.fdr_q)}).
- **Separation.** Heavier receivers also get less separation on break ({sg(s_brk.rho_size)}), vertical ({sg(s_ver.rho_size)}) and crosser ({sg(s_cro.rho_size)}) routes, not on screens ({sg(s_scr.rho_size)}): a lead (q {s_cro.fdr:.2f}).

Weight does not move everything: pressure rate is only weakly tied to it ({sg(wpr.rho_height_ctrl)}, q {wpr.fdr_q:.2f}). Scouts adjust a 40 for weight by feel; these numbers say how much.
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
    ax.text(.62, i, f"n {int(r.n)}  q {qtxt(r.fdr_q)}", va="center", fontsize=7.5, color=col)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[2] for r in rows[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-1, 1)
ax.set_xlabel("rank correlation of weight with the result (filled = height held fixed, 95% CI; hollow = before)\\n<- heavier does worse            heavier does better ->", fontsize=8)
ax.set_title("Weight: where it matters (colour = clears the correction)", loc="left", fontweight="bold", fontsize=9.5)
fig.tight_layout(); fig.savefig(SAVE / "fig6_weight.png", dpi=170); plt.show()
'''))
C.append(md("*Figure 6. Weight against on-field results. Left of zero: heavier players do worse.*"))

# =====================================================================================  SCOUT USE
C.append(md(f"""
## How a scout uses this
A scorecard, not a ranking (Figure 7), behind a lookup dashboard: enter a Combine line and each test returns a tag and a one-line read. Two examples:
- **{L_WR}**
- **{L_DL}**

Rules of thumb: trust a receiver's 40 and tracked top speed; compare linemen only with linemen of their weight and role; treat defensive-back numbers as one input among several. Every line carries its n and interval, so a lead is never mistaken for a verdict.
"""))
C.append(code('''
display(Image(str(FIGS / "fig22_scorecard.png")))
'''))
C.append(md("*Figure 7. The scorecard, with the smallest detectable effect (MDE). Green translates, orange leans, red mostly size, gray not detected.*"))

# =====================================================================================  METHODS + LIMITS
C.append(md(f"""
## Methods, in plain language
- **Size control.** Every link is repeated holding draft year, weight and height fixed (plus CB versus S, edge versus interior). Hollow marks are the link before size.
- **Shrinkage and held-out classes.** Rates from few snaps are pulled toward the group average. We train on two draft classes, predict the third, and ask whether adding the test beats a size-only model.
- **False-discovery control.** Each p comes from 10,000 permutations, each interval from a player-level bootstrap, and each result carries a Benjamini-Hochberg q across its whole family of tests. Verdict rules and receiver hypotheses were written first, and every p and interval was re-checked with a second method.
- **Power.** The smallest detectable effect (MDE, 80% power) is a Fisher-z approximation, checked by simulation ({SIM_LO}% to {SIM_HI}% power at the MDE).

**Verdicts.** TRANSLATES: q below 0.05, interval excludes zero, held-out classes agree. LEANS: interval excludes zero or p below 0.05, but q does not clear. SIZE, NOT SPEED: a raw link of at least 0.30 that falls by half or more. TOO FEW: under 25 players. **NOT DETECTED (low power):** enough players, none of the above; no link larger than the MDE, not no link.
"""))
C.append(md(f"""
## Limitations
- Rookies only (2023 to 2025 classes) with tracked snaps; skipped drills are not random.
- Counts are small: receivers about 60, defensive backs about {n_db}, linemen about 70, tight ends about {te_n}. Tight ends are all too few to tell ({mde_te:.2f} detectable, {pc(pw_te)} power at 0.30).
- The same players produced the leads and test them; three held-out classes are the only out-of-sample check. Burst Score recipes were chosen using game results, so those numbers are optimistic.
- Pooled defensive-line size may partly mean role; edge and interior splits have only 39 and 33 players (about {mde_ed:.2f} and {mde_in:.2f} detectable).
- No blocker or quarterback tracks are linked: pressure and sack results are association, not causation.
"""))
C.append(md("""
## Appendix
Code cells are collapsed. The notebook reads the audited result tables from the `bdb2027-outputs` dataset and the raw competition files; attach both.
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
shutil.copy(OUTD / "figs" / "fig22_scorecard.png", FIGD / "fig7_scorecard.png")
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
(HERE / "writeup_for_kaggle.md").write_text("\n\n".join(parts) + "\n")
print(f"exported writeup_for_kaggle.md; visuals: {len(IMG)} figures + 1 table = {len(IMG) + 1}")
print(f"slope {SLOPE:.3f}; DL share {DL_SHARE:.2f}; classes needed {cls_needed}; DB n {n_db} mde {mde_db} pw {pw_db:.2f}/{pwbh_db:.2f}; sim {SIM_LO}-{SIM_HI}")
print(PT.round(2).to_string())
