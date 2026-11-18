#!/usr/bin/env python3
"""Builds notebook/bdb2027_writeup.ipynb (scorecard format, 11/2026). Prose lives here; numbers come from out/*.csv.
Old skeleton kept as notebook/bdb2027_writeup_v1_skeleton_backup.ipynb."""
import json, re, pathlib

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}
code = lambda s: {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n").splitlines(True)}
C = []

C.append(md("""
<!-- WORD BUDGET CAPS (whole notebook < 2,000 incl. captions): 1 Hook 200 | 2 Data+link 300 | 3 Methods 260 | 4 Scorecard 560 (WR 160, DL 210, DB 120, TE 70) | 5 Weight 170 | 6 Doesn't translate 180 | 7 Scout use 130 | 8 Limits 120 -->
# What translates from the Combine, and what doesn't
*NFL Big Data Bowl 2027 · Combine tracking → regular-season game tracking · by position group*
"""))

C.append(md("""
## 1. Why a scout should care
Every spring, a 4.3 forty moves a prospect up the board. Almost nobody checks whether that speed shows up on Sundays.

We checked, one position group at a time, using the 10 Hz Combine tracking and three regular seasons of game tracking (2023 to 2025 rookies). We graded every Combine test against every on-field result with one rule: **a test only "translates" if it survives body size, a false-discovery correction, and a draft class the model never saw.**

The answer is not "Combine good" or "Combine bad". It is a scorecard.

- **Receivers:** the 40 is real. It shows up as faster game speed on deep routes.
- **Defensive line:** speed matters, but about half of the raw link is body size.
- **Defensive backs:** the headline tests do not translate. That is useful to know.
- **Tight ends:** too few players to say.

Draft slot is never used, as a control or a label. We ask what the *athlete* tells you, not what the market already paid for.
"""))

C.append(md("""
## 2. Data, and the link from Combine tracking to game performance
**Combine side:** official results plus 10 Hz tracking of the 40 and position drills, for 2023 to 2025 Combine invitees. From the tracking we derive top speed, split times, a Burst Score, and DB drill braking and re-burst.

**Game side:** regular-season tracking and play data for the same players. Outcomes are on-field: Sunday Speed (a receiver's 90th-percentile speed on deep routes), route separation, pressure, sack, tackle-for-loss and run-stop rates, get-off speed, and tackle rate and closing speed for defensive backs.

**The explicit link (the competition's gate).** The cell below takes each receiver's tracked Combine top speed and compares it with his regular-season Sunday Speed. If the link fails, the project fails. It passes: ρ +0.63 raw, **+0.58 after size control** (n 62, 95% CI +0.37 to +0.74, false-discovery q 0.003, better on held-out classes in 3 of 3). The exchange rate is **0.67 mph on Sunday per Combine mph**.
"""))

C.append(code("""
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy import stats
from IPython.display import Image, Markdown, display

def find_out():
    for p in [Path("out"), Path("../out"), Path("/kaggle/input/bdb2027-outputs/out"), Path("/kaggle/working/out")]:
        if (p / "scorecard.csv").exists():
            return p
    raise FileNotFoundError("Attach the bdb2027 outputs dataset (out/ folder) or run from the repo.")
OUT = find_out(); FIGS = OUT / "figs"
card = pd.read_csv(OUT / "scorecard.csv"); full = pd.read_csv(OUT / "scorecard_full.csv"); weight = pd.read_csv(OUT / "scorecard_weight.csv")

# --- Gate: Combine tracking -> regular-season game performance (receivers) ---
wr = pd.read_csv(OUT / "wr_te_robust_players.csv").query("pos_group == 'WR'")[["c_top_mph", "sunday_speed_mph"]].dropna()
rho, p = stats.spearmanr(wr.c_top_mph, wr.sunday_speed_mph)
gate = full.query("group == 'WR' and test == 'c_top_mph' and outcome == 'sunday_speed_mph'").iloc[0]
print(f"WR Combine tracked top speed vs regular-season Sunday Speed: n={len(wr)}, raw rho={rho:+.2f} (p={p:.1e})")
print(f"Size-controlled rho={gate.rho_size:+.2f} (CI {gate.ci_lo:+.2f} to {gate.ci_hi:+.2f}), q={gate.fdr_q:.3f}, held-out classes {gate.classes_helped}")
print("GATE:", "PASS" if gate.verdict == "TRANSLATES" else "FAIL")
display(Image(str(FIGS / "fig1_translation_scatter.png")))
"""))
C.append(md("*Figure 1. Receivers' Combine top speed against their regular-season Sunday Speed. Corners and safeties are flat.*"))

C.append(md("""
## 3. Methods, in plain language
- **Size control.** Big players are slower and sometimes win differently, so a speed "effect" can be a body-size effect. Every correlation is repeated holding weight, height and draft year fixed (plus CB vs safety, edge vs interior where relevant). The gap between the hollow and filled dots in Figure 2 is body size.
- **Shrinkage.** Rates built on few snaps are noisy. We pull them toward the group average by how many snaps each player has, so a hot 40-snap sample cannot top a leaderboard.
- **Held-out draft class.** Train on two classes, predict the third, and ask whether adding the Combine test beats a size-only model. We report how many of the three classes improved.
- **False-discovery control.** Hundreds of tests were run. Every p-value carries a Benjamini-Hochberg q across its whole family, with 10,000 permutations and player-level bootstrap intervals.
- **Pre-declaration.** The verdict rules, and the receiver route and man-vs-zone hypotheses, were written into the repo before the numbers were computed.

**Verdicts.** TRANSLATES: survives size, q < 0.05 and held-out classes. LEANS: the interval excludes zero or p < 0.05, but q does not clear. SIZE, NOT SPEED: a real raw link that collapses with size control. DOESN'T TRANSLATE: enough players, no signal. TOO FEW: under 25 players.
"""))
C.append(code("""
display(Image(str(FIGS / "fig20_forest_size_controlled.png")))
"""))
C.append(md("*Figure 2. Every Combine test against the main outcome per group: raw ρ (hollow) and size-controlled ρ (filled).*"))

C.append(md("""
## 4. The scorecard
"""))
C.append(code("""
display(Image(str(FIGS / "fig22_scorecard.png")))
"""))
C.append(md("*Figure 3. The scorecard. One row per result, best test shown. Right means a better athlete does better.*"))

C.append(md("""
### Receivers: the 40 translates
A faster 40 shows up as faster game speed on deep routes (ρ +0.52, n 63), and the tracked top speed is stronger still (+0.58). Both hold on held-out classes and the trait is stable week to week (split-half r 0.84).

The lead worth chasing is **explosiveness on break routes**: vertical jump (+0.34, n 58) and Burst Score (+0.31, n 54) go with more separation. It leans but does not clear the false-discovery bar, and we cannot show it is specific to breaks (Figure 4).
"""))
C.append(code("""
display(Image(str(FIGS / "fig21_wr_route_lead.png")))
"""))
C.append(md("*Figure 4. Receiver route-family and man-vs-zone tests, pre-declared. Panel C shows the contrasts that matter.*"))

C.append(md("""
### Defensive line: speed leans, size explains half
A faster 40 goes with a higher pressure rate (+0.35, n 72), but the raw link was +0.74, so **about half is body size**. For sacks the raw +0.72 collapses to +0.23: size, not speed. The mechanism is get-off: a faster 10-yard split goes with a faster first second (+0.32, raw +0.81).

Edge and interior look alike on get-off (+0.46 and +0.42). Interior rushers show the cleaner 40-to-sack lean (+0.40), though the interval touches zero. Both edge and interior samples are small (39 and 33).
"""))
C.append(code("""
display(Image(str(FIGS / "fig19_dl_recheck.png")))
"""))
C.append(md("*Figure 5. DL heat map, size-controlled, edge and interior split.*"))

C.append(md("""
### Defensive backs: nothing clears
No test translates. A faster 40 goes with faster deep-coverage speed only before size control (+0.41 raw, +0.22 after, interval crosses zero). The corner "speed tax" disappears once draft slot is dropped (-0.12). Drill braking leans toward closing speed (+0.25), nowhere near the false-discovery bar.

### Tight ends: too few
Twenty-one players. Every test is labelled too few.
"""))

C.append(md("""
## 5. The hidden variable: weight
Weight is the quiet driver. Holding height fixed, heavier players are slower on Sunday than their Combine suggests.
"""))
C.append(code("""
t = weight.query("group in ['WR','DL'] and outcome in ['player_get_off','speed_1s_mph','sunday_speed_mph','ssoe_mph'] and fdr_q < 0.05").copy()
t["rho (height held)"] = t.apply(lambda r: f"{r.rho_height_ctrl:+.2f} ({r.ci_lo:+.2f} to {r.ci_hi:+.2f})", axis=1)
t["q"] = t.fdr_q.round(2)
display(t[["group", "outcome_label", "n", "rho_raw", "rho (height held)", "q"]].round(2))
"""))
C.append(md("""
*Table 1. Weight against on-field results; negative means heavier players do worse.*

- **Receivers:** heavier receivers run slower on deep routes (ρ -0.43, q 0.01) and slower than their own 40 predicts (-0.38, q 0.04). The cost appears on every route type (about -0.25 to -0.29), not just screens and crossers.
- **Defensive line:** heavier linemen get off slower (-0.49 to -0.53, q 0.01).

Scouts already adjust a 40 for weight by feel. These numbers say how much: a large share of "fast for his size" is simply size.
"""))

C.append(md("""
## 6. What doesn't translate
Negative results are the point of a scorecard.
"""))
C.append(code("""
nul = card.query("verdict in [\\"DOESN'T TRANSLATE\\", 'SIZE, NOT SPEED'] and not breakout")[["group", "test_label", "outcome_label", "n", "rho_raw", "rho_size", "verdict"]]
display(nul.round(2))
"""))
C.append(md("""
*Table 2. Best-looking test per result that still does not translate (n at least 25).*

- **3-cone and shuttle do not separate break routes from vertical routes** for receivers (differences -0.24 and -0.11, intervals wide). Only 22 to 27 receivers have those drills.
- **Quickness against man coverage:** no clean man-versus-zone edge. The 10-yard difference is +0.15, interval -0.13 to +0.41.
- **The corner "speed tax"** (fast 40, fewer starts) was draft slot in disguise.
- **Defensive-back tackling and coverage numbers** do not follow the 40, the jumps or Burst Score.
- **Defensive-line run stops** do not follow Burst Score (+0.09).
"""))

C.append(md("""
## 7. How a scout uses it
The dashboard takes a prospect's Combine line and returns, per test, a tag and a one-line read, using only tests that earned one. Illustrative examples (not real players):

- A receiver with a 4.35 forty and 22.8 mph tracked top speed gets "**translates:** expect elite deep-route game speed" and the 0.67 exchange rate.
- A 290-pound lineman with a fast 40 gets "**leans, size-adjusted:** compare his get-off with other 290-pounders, not with edges."
- A corner's 40 gets "does not translate on this sample." Look at tape and drill braking.

Every tag links back to its row in the scorecard, with n and interval, so nobody mistakes a lean for a verdict.
"""))

C.append(md("""
## 8. Limitations
- Rookies only: 2023 to 2025 classes, players who made rosters, with tracked snaps. Skipped drills are not random.
- Counts are small (receivers about 60, defensive backs about 70, linemen 72, tight ends 21). Intervals are wide; "doesn't translate" means no evidence, not proof of zero.
- The same players generated the leads and test them. Held-out draft classes are the only out-of-sample check, and there are three.
- No blocker or quarterback tracks: pressure and sack rates are association, not causation.
- Man versus zone is a team-level play label.
- Hundreds of tests ran. The false-discovery correction helps, but treat every LEANS as a hypothesis.
"""))

NB = {"cells": C, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
p = pathlib.Path(__file__).with_name("bdb2027_writeup.ipynb"); p.write_text(json.dumps(NB, indent=1, ensure_ascii=False) + "\n")
# word count of markdown prose (HTML comment excluded)
words = 0; per = []
for c in C:
    if c["cell_type"] == "markdown":
        t = re.sub(r"<!--.*?-->", "", "".join(c["source"]), flags=re.S)
        n = len(re.findall(r"\S+", t)); words += n; per.append(n)
print("markdown words:", words, per)
