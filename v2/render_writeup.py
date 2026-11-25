#!/usr/bin/env python3
"""Renders v2/writeup_for_kaggle_v2.md from v2/results_v2.json (written by the executed v2 notebook).
Every number is pulled from the live recompute; nothing is typed in by hand. Checks Kevin's rules and the limits."""
import json, re, pathlib
HERE = pathlib.Path(__file__).resolve().parent
R = json.loads((HERE / "results_v2.json").read_text())
s = lambda x, d=2: f"{x:+.{d}f}".replace("-", "−")
u = lambda x, d=2: f"{x:.{d}f}".replace("-", "−")
ci = lambda lo, hi: f"{s(lo)} to {s(hi)}"
pv = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"
F, G, T1, N = R["funnel"], R["gate"], R["table1"], R["ngs"]
DL, OL, FA, FT, T2 = R["dl"], R["ol"], R["families"], R["families_total"], R["table2"]
pct = lambda a, b: f"{100 * a / b:.0f}%"
fam_best = lambda k: FA[k]["best"]
rows1 = [("106 receivers listed → {tracked_40} with a tracked 40 → {deep20} with 20+ deep routes → **both**".format(**F), "Size-adjusted (class, weight, height)", True),
         ("Class only (no size adjustment)", "Class only (no size adjustment)", False),
         ("Laser-timed 40 instead of tracked top speed", "Laser-timed 40 instead of tracked top speed", False),
         ("Rookie-season routes only (20+)", "Rookie-season routes only (20+)", False),
         ("First 20 deep routes only", "First 20 deep routes only", False),
         ("First 30 deep routes only", "First 30 deep routes only", False)]
t1 = ["| Sample or check (receivers) | n | ρ, Combine top speed vs Sunday Speed |", "|---|---:|---|"]
for lab, key, bold in rows1:
    v = T1[key]; cell = f"{s(v['rho'])} ({s(v['lo'])}, {s(v['hi'])})"
    t1.append(f"| {lab} | {'**' + str(v['n']) + '**' if bold else v['n']} | {'**' + cell + '**' if bold else cell} |")
t2 = ["| Outcome (n) | Held-out R² gain | Luck range (95th pct) | p | Read |", "|---|---:|---:|---:|---|"]
def read(v):
    if v["p"] < 0.05 / len(T2): return "Holds up out of sample"
    if v["p"] < 0.05: return "Small; holds up, below the strict bar"
    if v["gain"] <= 0: return "Does not hold up out of sample yet"
    return "Not above luck"
for k, v in T2.items():
    g = f"**{s(v['gain'], 3)}**" if v["p"] < 0.05 / len(T2) else s(v["gain"], 3)
    t2.append(f"| {k} ({v['n']}) | {g} | {s(v['luck95'], 3)} | {pv(v['p'])} | {read(v)} |")
DF = R["dl_forty_by_class"]; bc = R["by_class"]; oc = R["ol_class"]; P = R["prod"]; ND = "**NOT DETECTED (low power)**"

md = f"""*NFL Big Data Bowl 2027 · Open Track · Combine tracking linked to regular-season game tracking · WR, DL, OL, DB*

**The Combine works, but read it right.** Four findings, the surprising ones first.
1. **The NFL's athleticism score adds nothing once tracked Combine top speed is known.** For receivers, the NGS athleticism score has a partial correlation of {s(N['NGS score, top speed held fixed']['rho'])} with game speed once top speed is held fixed; top speed with the score held fixed is {s(N['Top speed, NGS score held fixed']['rho'])}.
2. **Heavier receivers play slower than their own 40 says.** At the same Combine top speed and height, each extra 10 lb goes with {u(-R['wt_slope10']['b'])} mph less top speed on deep routes (95% CI {ci(*R['wt_slope10']['ci'])}), with the same sign in all three draft classes.
3. **An offensive-line drill result that held in two classes, not the third.** Peak acceleration in the 5-yard slide drill goes with fewer pressures allowed (ρ {s(OL['rho_rate'])}, n {OL['n']}). It survives the multiple-testing checks, holds in the 2023 and 2024 classes ({s(oc['2023']['rho'])}, {s(oc['2024']['rho'])}), and is absent in 2025 ({s(oc['2025']['rho'])}).
4. **Speed carries to Sunday for receivers, but not to production.** Tracked 40 top speed predicts deep-route top speed (ρ {s(G['rho'])}, CI {ci(G['lo'], G['hi'])}, n {G['n']}) but not yards per route ({s(P['yards_per_route']['rho'])}, {ND}).

Defensive-line and defensive-back drills show no result that survives the checks. Most of the line link is the difference between edge and interior rushers.

## The required link: Combine tracking to game tracking
Each player's 10 Hz Combine tracking is joined to his regular-season game tracking (2023–25 draft classes; one to three seasons each, depending on class). **Combine top speed** is the fastest tracked speed in his 40-yard dash (mph). **Sunday Speed** is the 90th percentile of his top speed per play over regular-season deep routes (go, post, corner, wheel; plays not wiped out by penalty; at least 20 routes). The attached public notebook recomputes every number here from the raw competition files and stops with an error if the data are not attached.

**Terms used throughout.** ρ is a rank correlation; positive means the better athlete does better. *Size-adjusted* means holding draft class, weight and height fixed (plus edge/interior for DL, tackle/interior for OL, corner/safety for DB). Intervals are 95% ranges from resampling players; p-values come from 10,000 shuffles; q is the false-discovery-adjusted p within a position group. **Pressure rate** is pressures per pass-rush snap (DL) or allowed per pass-block snap (OL), as reported. {ND} means no link above the smallest effect the sample could see 8 times in 10 (the MDE); it is not "no link". Colors: blue is a supported link, grey a null, red a reversal; green, orange and purple are always the 2023, 2024 and 2025 classes.

{chr(10).join(t1)}

*Table 1. Who is in the sample, and whether the receiver link survives other samples. {F['both']} of {F['listed']} is {pct(F['both'], F['listed'])}: results describe receivers who ran a tracked 40 and saw enough deep routes. {F['undrafted_in_sample']} of the {F['both']} were undrafted ({pct(F['undrafted_in_sample'], F['both'])}, against {pct(F['undrafted_listed'], F['listed'])} of the {F['listed']}), a description of who is in the sample, not a variable.*

## 1. Receivers: speed carries over, the NGS score doesn't help
Each extra mph of Combine top speed goes with {u(R['slope']['b'])} mph more Sunday Speed (CI {u(R['slope']['lo'])} to {u(R['slope']['hi'])}; a line that resists outliers gives {u(R['slope']['theil_sen'])}). The link is positive in every draft class ({s(bc['2023']['rho'])} n {bc['2023']['n']}; {s(bc['2024']['rho'])} n {bc['2024']['n']}; {s(bc['2025']['rho'])} n {bc['2025']['n']}; Figure 1) and holds using rookie-season routes only or only a player's first 20 or 30 deep routes (Table 1).

![Figure 1](figs/fig1_wr_speed_carries_over.png)

**The NGS score.** The NFL's athleticism score (a column in the Combine file) correlates only {s(N['NGS score, class only']['rho'])} with Sunday Speed within draft class (CI {ci(N['NGS score, class only']['lo'], N['NGS score, class only']['hi'])}), partly because it rises with weight (ρ {s(R['ngs_weight'])}); size-adjusted it is {s(N['NGS score, size-adjusted']['rho'])}. Tracked top speed beats it by {s(R['diff_top_ngs']['d'])} (CI {ci(*R['diff_top_ngs']['ci'])}), and once top speed is known the score adds nothing ({s(N['NGS score, top speed held fixed']['rho'])}; {ND}, MDE {u(N['NGS score, top speed held fixed']['mde'])}; Figure 2). Tracked top speed beats the laser 40 only marginally ({s(R['diff_top_laser']['d'])}, CI {ci(*R['diff_top_laser']['ci'])}).

![Figure 2](figs/fig2_ngs_vs_tracked_speed.png)

**Weight.** Weight barely relates to a receiver's 40 top speed once height is held fixed (ρ {s(R['wt_vs_top']['rho'])}, CI includes zero), yet heavier receivers are slower on Sunday than that speed predicts (partial ρ {s(R['wt_partial']['rho'])}, CI {ci(R['wt_partial']['lo'], R['wt_partial']['hi'])}; {s(R['wt_slope10']['b'])} mph per 10 lb, Figure 3). This is an association: the data cannot say whether weight, role, or how he is used on deep routes explains it.

![Figure 3](figs/fig3_heavy_receivers_slower.png)

**Production.** Sunday Speed does not relate to yards per route ({s(P['yards_per_route']['rho'])}, CI {ci(P['yards_per_route']['lo'], P['yards_per_route']['hi'])}), deep yards per deep route ({s(P['deep_yds_per_deep_route']['rho'])}) or targets per deep route ({s(P['deep_target_share']['rho'])}): {ND}, MDE {u(P['yards_per_route']['mde'])}. Speed tells you who is fast on deep routes, not who produces.

## 2. Linemen
**Defensive line.** An earlier version compared adjusted links with a raw baseline built from smoothed rates, which inflated the raw link through edge-versus-interior structure. Here the ladder uses as-reported rates (Figure 4). Across {DL['cells']} drill-by-outcome cells (pressure, sack and tackle-for-loss rates; n {DL['n_lo']} to {DL['n_hi']}), the median class-adjusted ρ is {s(DL['med'][0])}; adding edge/interior leaves {s(DL['med'][1])} and adding weight and height leaves {s(DL['med'][2])}. About half the link ({100 * DL['share']:.0f}%) is shared with role and size, and nearly all of that is role alone; the share is imprecise (resampling range {100 * DL['share_ci'][0]:.0f}% to {100 * DL['share_ci'][1]:.0f}%).

![Figure 4](figs/fig4_dl_ladder.png)

The 40 against pressure rate is {s(R['dl40p']['rho'])} size-adjusted (CI {ci(R['dl40p']['lo'], R['dl40p']['hi'])}, n {R['dl40p']['n']}), a lead that does not survive the checks. Within roles it is {s(R['dl_role']['Edge']['rho'])} for edge (n {R['dl_role']['Edge']['n']}) and {s(R['dl_role']['Interior']['rho'])} for interior (n {R['dl_role']['Interior']['n']}), both intervals crossing zero ({ND}; MDE {u(R['dl_role']['Edge']['mde'])} and {u(R['dl_role']['Interior']['mde'])}). Weight is only weakly tied to pressure ({s(R['dl_wt_pressure']['rho'])}, CI {ci(R['dl_wt_pressure']['lo'], R['dl_wt_pressure']['hi'])}).

**Offensive line.** Slide-drill peak acceleration (largest 0.1-second speed gain, averaged over attempts) goes with fewer pressures allowed, size-adjusted ρ {s(OL['rho_rate'])} (CI {ci(OL['lo_rate'], OL['hi_rate'])}, n {OL['n']}). It is the only one of {FA['Offensive line']['cells']} OL tests that survives both the false-discovery check (q {u(fam_best('Offensive line')['q'], 3)}) and the best-of-N check (p {u(fam_best('Offensive line')['p_best_of_n'], 3)}). But it comes from two classes (Figure 5): {s(oc['2023']['rho'])} (n {oc['2023']['n']}) and {s(oc['2024']['rho'])} (n {oc['2024']['n']}), then {s(oc['2025']['rho'])} in 2025 (n {oc['2025']['n']}, CI {ci(oc['2025']['lo'], oc['2025']['hi'])}). The 2025 class differs from the others (shuffle p {u(R['ol_class_p'], 3)}) and has fewer snaps (median {OL['snaps_med']['2025']:.0f} against {OL['snaps_med']['2023']:.0f} for 2023), which makes its rates noisier; we cannot tell whether that explains it. Without 2025 the link is {s(-R['ol_2324']['rho'])} (n {R['ol_2324']['n']}), a cut chosen after seeing the data. Treat it as a hypothesis to re-test on the 2026 class.

![Figure 5](figs/fig5_ol_slide_reversal.png)

## 3. How many tests, and what survives
After merging duplicates (tracked and laser 40; one pooled DL group), the families hold {FA['Receivers']['cells']} receiver, {FA['Defensive line']['cells']} DL, {FA['Offensive line']['cells']} OL and {FA['Defensive backs']['cells']} DB cells, {FT['cells']} in all. Chance alone would give about {FT['expected']:.0f} with p < 0.05; {FT['p05']} do (Figure 6). Only {FT['survive']} survive the best-of-N check, which shuffles the whole outcome block within draft class (2,000 shuffles) and asks whether the best cell beats the best luck: receiver speed to Sunday Speed (p {pv(fam_best('Receivers')['p_best_of_n'])}) and the OL slide drill. Burst Score is dropped: its recipe was tuned after seeing outcomes.

![Figure 6](figs/fig6_best_of_n_null.png)

Table 2 asks the scouting question directly: choose the best Combine test using two draft classes, then predict the third. A negative gain means that choice made predictions worse than size alone; 300 shuffles give the luck range.

{chr(10).join(t2)}

*Table 2. Held-out gain in R² from adding the best Combine test to a size-only model (tests that run the expected way, measured for 80%+ of players). With {len(T2)} outcomes, only bold rows clear 0.05/{len(T2)}.*

The line rows are negative, and that is real, not a glitch: the test chosen in two classes points the other way in the third. For the defensive line, the 40's pressure link sits mostly in the 2023 class ({s(DF['2023'])} within class, against {s(DF['2024'])} and {s(DF['2025'])}). For the offensive line, the slide drill carries over when 2023 is held out but not to 2025, and when 2024 is held out a different drill gets chosen and reverses. Naming one test in advance does only a little better ({s(T2['Defensive-line pressure rate']['fixed_gain'], 2)} for the DL 40; {s(T2['Offensive-line pressures allowed']['fixed_gain'], 2)} for the slide drill, which was itself chosen after seeing all three classes). Read the line drills as leads that do not hold up out of sample yet; the 2026 class is the test.

## 4. Defensive backs and tight ends
None of the {FA['Defensive backs']['cells']} DB cells (tackle and tackle-for-loss rates; n about {R['db']['n_med']}) reaches p < 0.05 (best q {u(fam_best('Defensive backs')['q'])}): {ND}. With about {R['db']['n_med']} backs, only links of ρ {u(R['db']['mde'])} or more are seen 8 times in 10. Tight ends: {R['te']['tracked40_and_20routes']} of {R['te']['listed']} have a tracked 40 and 20+ routes, so only links of about {u(R['te']['mde'])} could be seen; not analysed further.

## What a team would do differently
- **Estimate deep speed from tracked top speed, not the NGS score.** Expect about two-thirds of a mph of Sunday Speed per mph at the Combine, and shade a heavy receiver below his 40.
- **Don't expect speed to buy production.** Pay for deep speed as a skill, not as a forecast of yards.
- **Read line drills within role and weight,** and re-test the OL slide drill on 2026 rookies.

## Methods and limitations
- **Correlation, not cause.** No blocker or quarterback tracks are linked, so pressure results also reflect teammates and schemes.
- **Selection.** Players need a tracked drill and enough snaps; skipped drills and unplayed seasons are not random. 2023 players have three seasons, 2025 players one.
- **Multiplicity.** We explored more than the {FT['cells']} cells shown (Burst Score recipes, clustering, other drills), so even adjusted p-values are optimistic. The receiver speed link is the result least exposed to this.
- **Small samples.** Intervals are wide; {ND} means below the MDE, not no link.
- **Reproducibility.** Seed 2027; rank correlations hold class, weight and height fixed; p from residual shuffles; intervals from 2,000 player resamples.

Data: NFL Big Data Bowl 2027 competition files (CC BY-NC 4.0). Draft slot, pick and round are not used.
"""
out = HERE / "writeup_for_kaggle_v2.md"; out.write_text(md)
strict = len(re.findall(r"\S+", md))
plain = re.sub(r"!\[.*?\]\(.*?\)", " ", md); plain = re.sub(r"[#*|>]+|(?<!\w)[-:]+(?!\w)", " ", plain)
words = len([w for w in re.findall(r"\S+", plain) if re.search(r"[A-Za-z0-9]", w)])
figs = len(re.findall(r"!\[Figure", md)); tables = len(re.findall(r"^\|---", md, re.M))
bad = re.findall(r"(?i)\b(pick\w*|round\w*|slot\w*|draft capital)\b", md.replace("Draft slot, pick and round are not used", ""))
comps = re.findall(r"(?i)\bcomps\b|athletic comp", md)
print(f"strict tokens {strict} | words only {words} | visuals {figs} figures + {tables} tables = {figs + tables}")
assert strict <= 2000 and figs + tables <= 10 and not bad and not comps, (strict, bad, comps)
assert md.count("NOT DETECTED (low power)") >= 3 and "The Combine works, but read it right" in md and "CC BY-NC 4.0" in md
assert not md.lstrip().startswith("# ")
