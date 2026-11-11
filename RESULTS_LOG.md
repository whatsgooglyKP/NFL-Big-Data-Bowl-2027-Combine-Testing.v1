# Results log — Sunday Speed build

Append-only notes from the working sessions. Official metric definitions live in `METRICS.md`. Official headline numbers (WR translation, Phase 2 drills) live in `PHASE2_RESULTS.md`.

---

## 2026-11-10 (America/New_York) — SSOE scouting card, NGS incremental, CB speed tax, DL burst

Scripts: `ssoe.py`, `dl_burst.py`. Outputs: `out/ssoe_leaderboard.csv`, `out/ssoe_tests.csv`, `out/dl_burst_players.csv`, `out/dl_burst_tests.csv`, `out/figs/fig4_ssoe_leaderboard.png`, `out/figs/fig5_dl_burst.png`. Definitions frozen in `METRICS.md`.

### 1. Official metric freeze

Sunday Speed, Speed Translation Rate, and Sunday Speed Over Expected are frozen in `METRICS.md`. SSOE is actual Sunday Speed minus the speed expected from the player's Combine 40-yard tracked top speed at his position, in mph. It is not adjusted for weight, draft year, or draft slot. Recomputed SSOE matched the official player table (max abs error 3.3e-15 mph). Official samples unchanged: WR 62, CB 33, S 26. Locked translation rates: WR 0.67 (0.47–0.88), CB 0.09 (−0.13–0.38), S 0.22 (−0.17–0.59).

Reliability flag on the scouting card: High (≥80 opportunity plays), Medium (40–79), Limited (<40).

### 2. SSOE scouting-card leaderboard

121 players. Figure 4 shows the top 5 and bottom 5 at each position. For receivers this is a true over/under-the-40 flag. For corners and safeties the 40 barely predicts Sunday Speed, so SSOE is close to faster or slower than the position average — the figure caption says so.

**Top 5 SSOE, wide receivers (n=62)**

| Player | Draft | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---|---:|---:|---:|---:|---:|---|
| Ronnie Bell | 2023 R7 #253 | Michigan | 22.02 | 18.08 | 19.31 | **+1.22** | 73 | Medium |
| Devontez Walker | 2024 R4 #113 | North Carolina | 23.14 | 18.83 | 19.90 | **+1.07** | 42 | Medium |
| Jalen Brooks | 2023 R7 #244 | South Carolina | 22.00 | 18.06 | 19.12 | **+1.05** | 114 | High |
| Marvin Mims | 2023 R2 #63 | Oklahoma | 22.81 | 18.61 | 19.49 | **+0.88** | 361 | High |
| Jimmy Horn | 2025 R6 #208 | Colorado | 23.21 | 18.88 | 19.66 | **+0.78** | 36 | Limited |

Largest WR unders: Rashee Rice −1.20 (High, 121 plays), Mitch Tinsley −1.00 (Medium), Elic Ayomanor −0.96 (High), Xavier Legette −0.85 (High), Malik Washington −0.82 (High).

**Top 5 SSOE, cornerbacks (n=33)**

| Player | Draft | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---|---:|---:|---:|---:|---:|---|
| Billy Bowman | 2025 R4 #118 | Oklahoma | 23.13 | 17.38 | 18.72 | **+1.33** | 51 | Medium |
| Andru Phillips | 2024 R3 #70 | Kentucky | 22.45 | 17.32 | 18.02 | **+0.69** | 314 | High |
| Cam Hart | 2024 R5 #140 | Notre Dame | 22.16 | 17.29 | 17.92 | **+0.62** | 392 | High |
| Terrion Arnold | 2024 R1 #24 | Alabama | 22.05 | 17.28 | 17.78 | **+0.49** | 581 | High |
| Upton Stout | 2025 R3 #100 | Western Kentucky | 22.93 | 17.37 | 17.86 | **+0.49** | 91 | High |

Largest CB unders: Denzel Burke −1.36, Julius Brents −0.79, Jaylon Jones −0.68, Darrell Luter −0.58, Max Melton −0.55 (all High).

**Top 5 SSOE, safeties (n=26)**

| Player | Draft | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---|---:|---:|---:|---:|---:|---|
| Brandon Joseph | UDFA | Notre Dame | 21.97 | 16.08 | 16.89 | **+0.81** | 78 | Medium |
| Brian Branch | 2023 R2 #45 | Alabama | 22.49 | 16.19 | 16.91 | **+0.71** | 666 | High |
| Sydney Brown | 2023 R3 #66 | Illinois | 23.41 | 16.39 | 17.02 | **+0.62** | 168 | High |
| Calen Bullock | 2024 R3 #78 | Southern California | 22.54 | 16.20 | 16.79 | **+0.58** | 713 | High |
| Antonio Johnson | 2023 R5 #160 | Texas A&M | 22.11 | 16.11 | 16.59 | **+0.48** | 455 | High |

Largest S unders: Evan Williams −0.82, Jay Ward −0.65 (Medium), DeMarcco Hellams −0.51, Kamren Kinchens −0.46, Demani Richardson −0.39.

Do not treat Limited names (Jimmy Horn, 36 deep routes) as a finished grade. Do not claim SSOE predicts starts or production; those tests were already null.

### 3. Incremental test over `ngs_athleticism_score`

The column exists for every official-sample player. The 10 Hz tracked 40 still does all the work for receivers. NGS athleticism does not predict Sunday Speed, even though it correlates with Combine top speed.

| Position | n | Combine → SS | NGS → SS | Combine vs NGS | Combine → SS after NGS | after NGS + log pick |
|---|---:|---|---|---|---|---|
| WR | 62 | ρ=+0.63, p=3.1e-08 | ρ=+0.12, p=0.342 | ρ=+0.46 | ρ=+0.64, p=2.8e-08 | ρ=+0.64, p=3.0e-08 |
| CB | 33 | ρ=+0.06, p=0.726 | ρ=−0.04, p=0.840 | ρ=+0.67 | ρ=+0.16, p=0.369 | ρ=+0.16, p=0.386 |
| S  | 26 | ρ=+0.10, p=0.620 | ρ=+0.19, p=0.363 | ρ=+0.51 | ρ=+0.07, p=0.739 | ρ=+0.06, p=0.787 |

Coach line: *for receivers, the tracked 40 tells you something about Sunday Speed that the NGS athleticism score does not.* For corners and safeties, neither number predicts Sunday Speed.

### 4. CB "speed tax" (suggestive)

Beyond-draft-slot Combine speed = Combine top speed residualized on log draft pick (UDFA = 260). The official partial residualizes start rate the same way.

Broader sample (every player with a 40 and a start rate):

| Position | n | Raw ρ | Partial ρ | Partial p | Holm p (3-position family) |
|---|---:|---:|---:|---:|---:|
| WR | 75 | +0.02 | −0.10 | 0.390 | 0.780 |
| **CB** | **44** | −0.10 | **−0.45** | **0.002** | **0.006** * |
| S  | 38 | +0.18 | −0.05 | 0.753 | 0.780 |

CB permutation p (5,000 shuffles of the speed residual) = 0.003. On the official Sunday Speed sample the CB partial is −0.39, n=33, p=0.025.

**Multiple-testing note.** The CB result survives Holm correction inside this pre-specified 3-test speed-tax family, and the permutation test agrees. It does **not** survive the original program-wide family (~45 first-pass tests; Bonferroni cutoff ≈ .001). We still label it **suggestive**, not a headline finding. WR and S are null.

### 5. Defensive line: Combine burst vs Sunday get-off

OL skipped entirely. Universe is the 118 players who tested in the DL Combine group: Edge = DE (36) + OLB (30); Interior = DT (47) + NT (5). OLB are included as Edge because they ran the DL drills and almost always line up as EDGE on Sundays.

Get-off sample: regular-season pass plays that stood, lined up EDGE or INTERIOR_LINE, at least 20 snaps. 28,800 such snaps, 98 players; 89 have a tracking speed-at-1s median, 88 have an NFL `player_get_off` median. Game tracking covers only the 510 rookies — get-off is from the rusher's own track.

**Primary family (12 tests):** official 10-yard split, 40-yard peak acceleration, 40 time to 15 mph, and pass-rush-drill peak acceleration, each vs median speed 1.0s after the snap, in All DL / Edge / Interior. Holm on raw Spearman p. Positive oriented ρ below means "better Combine burst, faster get-off."

| Group | Feature | n | ρ (raw) | p | Partial ρ (log pick) | Holm p |
|---|---|---:|---:|---:|---:|---:|
| All DL | Official 10-yard split | 72 | −0.81 | 7.0e-18 | −0.79 | **8.4e-17** * |
| All DL | 40 time to 15 mph | 71 | −0.55 | 6.4e-07 | −0.55 | **7.0e-06** * |
| All DL | Pass-rush drill peak accel | 86 | +0.35 | 0.001 | +0.39 | **0.008** * |
| All DL | 40-yard peak acceleration | 71 | +0.37 | 0.001 | +0.38 | **0.012** * |
| **Edge** | **Official 10-yard split** | **39** | **−0.63** | **1.5e-05** | **−0.61** | **0.000** * |
| Edge | Other three primary features | 38–47 | \|ρ\| ≤ 0.18 | ≥ 0.23 | — | n.s. |
| **Interior** | **Official 10-yard split** | **33** | **−0.46** | **0.007** | −0.31 (p=0.076) | **0.048** * |
| **Interior** | **40 time to 15 mph** | **33** | **−0.46** | **0.008** | −0.39 (p=0.025) | **0.048** * |
| Interior | Other two primary features | 33–39 | — | ≥ 0.056 | — | n.s. |

**Verdict.** The official 10-yard split is real get-off information. A faster split comes with a faster first second on pass-rush snaps, and that holds **inside Edge** (ρ=−0.63, n=39) and, more weakly, **inside Interior** (ρ=−0.46, n=33; pick-controlled partial is only suggestive). The huge All-DL correlation (ρ=−0.81) is partly a composition effect — Edge players both run faster 10-yard splits (median 1.65s vs 1.76s) and play in more space (median speed at 1.0s: 7.2 mph vs 5.1 mph) — so the within-subtype numbers are the ones to trust. The other burst features (40 peak accel, pass-rush drill accel) look real only when Edge and Interior are pooled; they do not survive inside either group. Interior time-to-15-mph barely clears Holm (0.048) and should not be oversold.

The same 10-yard pattern shows up against NFL get-off time, speed at 1.5s, time to 5 yards, and first-step acceleration (All-DL and Edge; Interior mixed). Tracking-derived 10-yard splits remain a poor substitute; use the official laser split.

Coach line: *for defensive linemen, trust the 10-yard split as a get-off test. Do not expect the 40's peak acceleration or the pass-rush drill to tell you who will actually get off on Sunday once you already know whether he is an edge or an interior player.*

### 6. Does DL get-off relate to career success?

Primary outcomes, per Kevin: **career defensive snaps** and **defensive snaps per game active**. Start rate is secondary, as are sack rate and pressure rate. Official partial residualizes on draft-year dummies (2023 rookies have had three seasons, 2025 rookies one) and log draft pick. Holm is on the four primary All-DL year+pick partial p-values.

**Primary (All DL) — null.**

| Get-off | Outcome | n | Raw ρ | Year+pick ρ | Year+pick p | Holm p |
|---|---|---:|---:|---:|---:|---:|
| Speed at 1.0s | Career defensive snaps | 89 | +0.17 | +0.03 | 0.792 | 1.000 |
| Speed at 1.0s | Snaps per game active | 89 | +0.12 | +0.00 | 0.977 | 1.000 |
| NFL get-off time | Career defensive snaps | 88 | −0.13 | +0.05 | 0.645 | 1.000 |
| NFL get-off time | Snaps per game active | 88 | −0.06 | +0.11 | 0.310 | 1.000 |

Faster get-off does not predict more defensive snaps, once draft year and draft slot are in the model. Start rate is also null (speed-at-1s year+pick ρ=−0.06, p=0.568).

**Secondary, worth reporting but not a headline.** On the same pass-rush snaps, faster get-off *does* travel with production:

- Speed at 1.0s vs pressure rate: n=89, ρ=+0.51, year+pick ρ=+0.50, p=5.8e-07
- NFL get-off time vs pressure rate: n=88, ρ=−0.59, year+pick ρ=−0.57, p=8.2e-09
- Speed at 1.0s vs sack rate: n=89, ρ=+0.36, year+pick ρ=+0.30, p=0.005
- NFL get-off time vs sack rate: n=88, ρ=−0.39, year+pick ρ=−0.29, p=0.006

Caveat: we do not have blocker or QB tracks, so speed at 1.0s can be higher when a rusher is unblocked. NFL get-off time is measured earlier in the snap and shows the same pressure pattern, which makes a pure "he was already free" explanation less comfortable — but this is still a secondary family, and we should not promote it past the snaps null.

### 7. What this changes in the story

Sunday Speed for WR / CB / S is unchanged. The new wrinkle is a second position-specific Combine-to-Sunday link: **DL 10-yard split → get-off**, with a clean snaps null and a suggestive pressure/sack companion. That is a second "which Combine number is real?" contrast, not a new named metric, and it should stay in its own section so it does not dilute the WR-vs-DB headline.

---

## 2026-11-10 (America/New_York) — Gameplay outcomes are the official success metrics

Kevin: success should not be measured by playing time only. Playing time (career defensive snaps, snaps per game, start rate) is now secondary context. Official success metrics are on-field gameplay outcomes that actually exist in `player_play.csv`. Definitions frozen in `METRICS.md` §§6–6D. Scripts: `dl_burst.py` (updated), new `gameplay_success.py`. Outputs: `out/dl_burst_players.csv`, `out/dl_burst_tests.csv`, `out/gameplay_success_players.csv`, `out/gameplay_success_tests.csv`, `out/figs/fig5_dl_burst.png` (updated caption), `out/figs/fig6_combine_to_pressure.png`, `out/figs/fig7_gameplay_success.png`.

### 1. Gameplay fields that exist (and that do not)

Inspected every column of `player_play.csv`. Nothing below was invented.

**Defensive line (on REG standing pass-rush snaps, lined up EDGE or INTERIOR_LINE):** `player_get_off`, `sack` (1.0 solo / 0.5 shared), `time_to_pressure` (pressure is this field being present), `time_to_qb_hurry` (hurry), `quick_pressure`, `unblocked_pressure`, plus `tackle` / `assist` / `tackle_for_loss`. There is **no quarterback-hit field**. `pressure_allowed` / `sack_allowed` are offensive-line fields, not rusher credits.

**Wide receivers:** `target`, `rec_yards`, `yards_after_catch`, `expected_yards_after_catch`, `separation_at_pass_forward`, `route_ran`, `cushion`. Receptions are rows with `target` and `rec_yards` not null (those are exactly the `pass_result == C` targets).

**Cornerbacks and safeties:** `tackle`, `assist`, `tackle_for_loss`, `caused_forced_fumble`, `recovered_fumble`, `coverage_assignment`, `cushion`. **No** targets-allowed, completions-allowed, PBU, or interception field is attached to a defender. `target` is never true for a DB in this file. `pass_result` is play-level and is not attributed to the covered defender, so we did not turn it into an allowed-rate.

### 2. Defensive line: the Combine-to-pressure chain

Opportunity floor is 20 REG standing pass-rush snaps (same floor as get-off). Official partials control for draft year and log draft pick. CIs are 2,000-player bootstraps. Two pre-declared Holm families.

**Family A — get-off → success (4 All-DL tests, year+pick partial p).** All four survive Holm. Faster get-off travels with more pressures and more sacks.

| Get-off | Outcome | n | Raw ρ | Year+pick ρ | Year+pick p | 95% CI | Holm p |
|---|---|---:|---:|---:|---:|---|---:|
| Speed at 1.0s | Pressure rate | 89 | +0.51 | **+0.50** | 5.8e-07 | +0.29 – +0.66 | **1.7e-06** * |
| Speed at 1.0s | Sack rate | 89 | +0.36 | **+0.30** | 0.005 | +0.08 – +0.48 | **0.010** * |
| NFL get-off time | Pressure rate | 88 | −0.59 | **−0.57** | 8.2e-09 | −0.70 – −0.39 | **3.3e-08** * |
| NFL get-off time | Sack rate | 88 | −0.39 | **−0.29** | 0.006 | −0.50 – −0.09 | **0.010** * |

Hurry rate tracks pressure almost one-for-one (speed-at-1s year+pick ρ=+0.51). Dropping unblocked pressures does not erase the link (year+pick ρ=+0.40, p=9.3e-05). Playing time stays null: speed-at-1s vs career defensive snaps year+pick ρ=+0.03, p=0.79; vs snaps per game ρ=+0.00, p=0.98; vs start rate ρ=−0.06, p=0.57.

**Family B — official 10-yard split → success (6 tests: pressure and sack × All DL / Edge / Interior).** This is the competition-required Combine-to-NFL-performance link.

| Group | Outcome | n | Raw ρ | Year+pick ρ | Year+pick p | 95% CI | Holm p |
|---|---|---:|---:|---:|---:|---|---:|
| **All DL** | **Pressure rate** | **72** | −0.50 | **−0.45** | **7.8e-05** | **−0.62 – −0.19** | **0.00047** * |
| **All DL** | **Sack rate** | **72** | −0.40 | **−0.31** | **0.008** | **−0.53 – −0.07** | **0.039** * |
| Edge | Pressure rate | 39 | −0.34 | −0.24 | 0.140 | −0.54 – +0.11 | 0.560 |
| Edge | Sack rate | 39 | −0.13 | +0.08 | 0.617 | −0.30 – +0.43 | 1.000 |
| Interior | Pressure rate | 33 | −0.19 | −0.12 | 0.504 | −0.51 – +0.28 | 1.000 |
| Interior | Sack rate | 33 | −0.42 | −0.25 | 0.159 | −0.59 – +0.13 | 0.560 |

The All-DL 10-yard split now predicts both pressure rate and sack rate after year, pick, Holm, and a CI that stays on the “faster split, more production” side of zero. The same tests **inside Edge and inside Interior do not clear the bar**, so some of the pooled result is composition: Edge players run faster 10-yard splits and post higher pressure rates because they rush in more space. That is the same caution we already attach to the All-DL get-off correlation. Trust the All-DL Combine-to-pressure number as a pooled scouting fact; do not oversell it as a within-position rule until a larger sample says so.

**Mediation.** After residualizing on draft year, log pick, **and** game get-off (speed at 1.0s), the All-DL 10-yard split vs pressure rate shrinks to ρ=−0.08, p=0.49, CI −0.32 – +0.17 (n=72). The sack path also vanishes (ρ=−0.14, p=0.23). Get-off is carrying the Combine-to-pressure link. Caveat: we have no blocker or QB tracks, so this is association, not a causal mediation claim. A rusher who is already free can also look faster at 1.0s. The unblocked-pressure sensitivity still leaving a 10-yard vs blocked-pressure link (year+pick ρ=−0.39, p=0.001, CI −0.57 – −0.13) makes a pure “he was already free” story less comfortable, but it does not prove the opposite.

Companion: All-DL 10-yard split vs hurry rate year+pick ρ=−0.46, p=5.3e-05, CI −0.63 – −0.23 (not in the Holm family; almost the same as pressure).

Coach line: *for defensive linemen, the official 10-yard split is real get-off information, and in the pooled DL sample a faster split also shows up as a higher pressure rate and a higher sack rate on Sunday. That production link runs through get-off, and it is not yet a clean within-Edge or within-Interior rule. Do not use get-off, or the 10-yard split, as a playing-time predictor.*

### 3. Wide receivers: Sunday Speed still does not predict production

Official Sunday Speed sample, n=62 (61 for deep target share, which needs ≥8 targets). Pre-declared 6-test family: Sunday Speed and SSOE vs yards per route, deep yards per deep route, and deep target share. Holm on year+pick partial p.

| Predictor | Outcome | n | Raw ρ | Year+pick ρ | Year+pick p | 95% CI | Holm p |
|---|---|---:|---:|---:|---:|---|---:|
| Sunday Speed | Yards per route | 62 | −0.02 | +0.03 | 0.833 | −0.25 – +0.28 | 1.000 |
| Sunday Speed | Deep yards / deep route | 62 | +0.00 | +0.06 | 0.659 | −0.22 – +0.31 | 1.000 |
| Sunday Speed | Deep target share | 61 | +0.28 | +0.27 | 0.039 | −0.03 – +0.55 | 0.233 |
| SSOE | Yards per route | 62 | +0.01 | +0.03 | 0.830 | −0.23 – +0.28 | 1.000 |
| SSOE | Deep yards / deep route | 62 | −0.01 | −0.02 | 0.898 | −0.24 – +0.26 | 1.000 |
| SSOE | Deep target share | 61 | +0.14 | +0.13 | 0.309 | −0.14 – +0.44 | 1.000 |

**All six are null after Holm.** The only uncorrected hint is Sunday Speed vs deep target share (ρ=+0.27, p=0.039), and its CI includes zero. Catch rate, deep separation, YAC-over-expected, overall target rate, and Combine top speed vs the same production outcomes are also null. This confirms the earlier first-pass nulls against a cleaner, pre-declared family.

Coach line: *for receivers, trust the 40 as a Sunday Speed test. Do not treat Sunday Speed, or SSOE, as a receiving-production grade.*

### 4. Cornerbacks: the speed tax is still a playing-time finding, not a coverage-or-tackle finding

We cannot test completion percentage allowed or targets allowed — those fields are not in the file. The pre-declared 4-test gameplay family is Combine top speed vs tackle involvement rate and TFL rate, for CB and S, on players with a tracked 40 and at least 50 REG snaps that stood.

| Pos | Outcome | n | Raw ρ | Year+pick ρ | Year+pick p | 95% CI | Holm p |
|---|---|---:|---:|---:|---:|---|---:|
| CB | Tackle involvement rate | 36 | −0.27 | −0.31 | 0.066 | −0.60 – +0.11 | 0.265 |
| CB | TFL rate | 36 | −0.18 | −0.23 | 0.183 | −0.54 – +0.18 | 0.549 |
| S | Tackle involvement rate | 29 | −0.16 | +0.06 | 0.770 | −0.43 – +0.57 | 1.000 |
| S | TFL rate | 29 | +0.13 | +0.03 | 0.876 | −0.37 – +0.41 | 1.000 |

**All four are null after Holm.** The CB tackle-rate lean (ρ=−0.31, p=0.066) is in the same direction as the speed tax but does not clear the bar, and the CI includes zero.

The original speed tax vs **start rate** is still there as playing-time context, on the same 50-snap sample: CB n=36, year+pick ρ=−0.41, p=0.013, CI −0.70 – −0.05. On the official Sunday Speed sample it is ρ=−0.38, n=33, p=0.029, CI −0.67 – +0.03 (the interval now touches zero). It remains a **suggestive playing-time** result, not a gameplay-success headline, and it still does not survive the original program-wide family.

Coach line, unchanged in spirit: *CB speed: do not pay for the 40. We cannot see targets or completions allowed in this file, and the tackle / TFL rates we can see do not follow the 40 either.*

### 5. What this changes in the story

Sunday Speed for WR / CB / S is unchanged: the 40 is real for receivers as a speed test and is not a production test. The defensive-line half of the project gets sharper. The 10-yard split was already honest get-off information. With gameplay — not snaps — as the success definition, that split also predicts pressure rate and sack rate in the pooled DL sample, the path runs through get-off, and playing time stays a clean null. The honest limits travel with the finding: no blocker or QB tracks, and the Combine-to-pressure link is not yet a within-Edge or within-Interior rule.

Draft-day lines, current:

- **WR speed: trust the 40 as Sunday Speed. Do not use it, or SSOE, as a receiving-production grade.**
- **CB speed: do not pay for the 40, and do not assume the standard DB drills will tell you who will actually run on Sunday. We also cannot grade CB speed against targets or completions allowed in this file.**
- **DL get-off: trust the official 10-yard split. In the pooled DL sample, a faster split also shows up as more pressure and more sacks, through get-off — not as more playing time.**

---

## 2026-11-11 (America/New_York) — Late-round gems

Script: `late_round_gems.py`. Outputs: `out/late_round_gems.csv`, `out/late_round_gems_tests.csv`, `out/figs/fig8_late_round_gems.png`, `LATE_ROUND_GEMS.md`.

Kevin's question: among later-round picks (rounds 4–7; UDFA separate), who had a strong Combine test and then overperformed in the NFL — and apply that idea at every position group, not just the 10-yard split.

### 1. Measure selection (pre-declared shortlists, early-round sample)

The primary Combine measure in each group is the shortlist entry with the highest *oriented* pick-partial Spearman ρ (better test ↔ better gameplay) on **rounds 1–3 only**, and only if n ≥ 12. That keeps selection off the late-round contrast. Full-sample correlations are reported and cannot win. This is a selection step, not an independent confirmatory test.

Shortlists: WR — tracked 40 top speed, official 40, official 10-yard (Sunday Speed is a game measure, not a Combine candidate). CB/S — shuttle, 3-cone, vertical, broad, 10-yard, official 40 / tracked top speed, gauntlet and backpedal-45 drills. DL — official 10-yard split (established burst measure), 3-cone, broad, bench; official 40 is listed as a cousin of the 10-yard but cannot replace it. An Edge/Interior alternate had to beat the 10-yard by more than 0.10 ρ on the early-round sample to take its place.

| Group | Outcome | Chosen measure | n early | Oriented pick-partial ρ | p | Weak link? |
|---|---|---|---:|---:|---:|---|
| WR | Yards per route (≥20 routes) | Official 40 time | 29 | +0.10 | 0.609 | Yes |
| CB | Tackle involvement rate (≥50 snaps) | Broad jump | 18 | +0.42 | 0.084 | No |
| S | Tackle involvement rate (≥50 snaps) | Gauntlet drill top speed | 12 | +0.30 | 0.342 | Yes |
| Edge | Pressure rate (≥20 pass-rush snaps) | Official 10-yard split | 13 | +0.68 | 0.011 | No |
| Interior | Pressure rate (≥20 pass-rush snaps) | Official 10-yard split | 12 | +0.27 | 0.391 | Yes |

A weak link means ρ < 0.20 or p ≥ 0.10 on the early-round sample. Shuttle and 3-cone missed the early-round n floor at every DB and DL group (most players skip them). Interior 3-cone vs pressure is a striking full-sample number (ρ=+0.64, p=0.007, n=16) but only seven early-round interior players ran it, so it was not selected — a lead, not a primary.

### 2. Group-level test: late-round strong vs weak testers

Strong = top third of the *whole position* (Edge / Interior split) on the chosen measure, not the top third of late-round only. Overperformed = positive residual of the primary outcome vs log draft pick (UDFA = 260). Mann-Whitney is one-sided (strong > weak). Rounds 4–7 only.

| Group | n late (strong / mid / weak) | Median strong | Median weak | MW p | Late pick-partial ρ | Notes |
|---|---|---:|---:|---:|---|---|
| WR | 34 (11 / 14 / 9) | 0.99 ypr | 0.74 ypr | 0.086 | +0.25 (p=0.161) | weak link; lean only |
| CB | 13 (2 / 5 / 6) | 8.1% | 7.9% | NA | −0.12 (p=0.707) | underpowered |
| S | 18 (5 / 6 / 7) | 9.6% | 9.3% | 0.622 | −0.40 (p=0.099) | weak link; null |
| Edge | 19 (4 / 7 / 8) | 8.3% | 8.1% | 0.404 | +0.07 (p=0.770) | underpowered |
| Interior | 16 (7 / 4 / 5) | 5.4% | 5.3% | 0.500 | +0.09 (p=0.745) | weak link; null |

**No group-level claim.** The receiver contrast leans the expected way (p=0.086) but official 40 time was a weak-link pick from a null shortlist. Edge 10-yard is the one early-round relationship that clearly clears the bar (ρ=+0.68, p=0.011), but the late-round strong-vs-weak cell is only 4 vs 8 and does not itself reject the null. The deliverable is a named shortlist, not a new official finding.

### 3. Named shortlist (rounds 4–7), plus UDFA separately

A gem is a rounds 4–7 pick in the top third of his position on the chosen measure, with a positive draft-slot residual on the primary gameplay outcome.

- **WR (official 40, weak link):** Devontez Walker (2024 R4 #113, 4.36, 2.12 ypr, residual +0.937, also +1.07 SSOE on 74 routes — limited sample, also above the R1–3 median); Jacob Cowing (R4 #135, 4.38, 1.29 ypr, +0.157, 62 routes); Troy Franklin (R4 #102, 4.41, 1.36 ypr, +0.145, 715 routes); Jaylin Lane (2025 R4 #128, 4.34, 1.21 ypr, +0.061, 186 routes). UDFA: Isaiah Bond (4.39, 0.95 ypr, residual only +0.009, 333 routes).
- **CB (broad jump):** no late-round player cleared both cuts. The two top-third testers, Cam Hart (2024 R5 #140, 130-inch broad, 7.9% tackle rate, residual −0.005 on 1,039 snaps) and Marcellas Dial (R6 #180, 129 inches, 8.3%, −0.002 on 60 snaps), finished essentially at draft-slot expectation.
- **S (gauntlet, weak link):** Chamarri Conner (2023 R4 #119, 18.49 mph gauntlet, 11.4% tackle rate, residual +0.011, 1,805 snaps, also above the R1–3 median); Evan Williams (2024 R4 #111, 18.57 mph, 10.4%, +0.002, 1,306 snaps). Williams is a reminder that this is a tackle-rate card, not a speed card — his SSOE is −0.82.
- **Edge (official 10-yard):** Cedric Johnson (2024 R6 #214, 1.61 split, 14.6% pressure, residual +0.071, 192 pass-rush snaps, also above the R1–3 median, 1.6% sack rate); Robert Beal (2023 R5 #173, 1.62, 9.2% pressure, +0.013, 131 snaps). UDFA: Tyrus Wheat (1.59, 8.1% pressure, +0.010, 123 snaps).
- **Interior (official 10-yard, weak link):** Adetomiwa Adebawore (2023 R4 #110, 1.61 split, z +2.32, 9.2% pressure, residual +0.036, 479 snaps, above the R1–3 median); Brandon Dorlus (2024 R4 #109, 1.68, 9.6% pressure, +0.040, 303 snaps, 2.8% sack rate); Mekhi Wingo (2024 R6 #189, 1.64, 6.8%, +0.017, 132 snaps); Zeek Biggers (2025 R7 #253, 1.74, 5.4%, residual only +0.005, 130 snaps — a thin over-slot).

Coach line: *the names are useful scouting cards — especially Cedric Johnson on the edge and Adebawore / Dorlus inside — but late-round strong testers do not, as a group, reliably outproduce late-round weak testers in this sample. Do not turn the shortlist into a draft rule.*

---

## 2026-11-11 (America/New_York) — DL headline is one combined group, with Edge vs Interior breakouts

Kevin's decision: defensive linemen are **one combined DL group** for the headline analysis (n=72 with an official 10-yard split and ≥20 pass-rush snaps, 2023–2025 classes pooled), with the ability to break out Edge vs Interior in every DL table and chart. Caveat to state plainly: within Edge alone or Interior alone, the split→pressure link is weaker and not significant; part of the pooled effect comes from edges being both faster and better rushers.

Scripts: `dl_burst.py`, `late_round_gems.py`, light caption pointer in `gameplay_success.py` Figure 7. New outputs: `out/dl_players_named.csv`, `DL_PLAYERS.md`. Refreshed figures: `out/figs/fig5_dl_burst.png`, `out/figs/fig6_combine_to_pressure.png`, `out/figs/fig8_late_round_gems.png` (Figure 7 caption only). Docs: `METRICS.md` §6A, `README.md`, `STRATEGY.md`, `LATE_ROUND_GEMS.md`. The pre-declared 6-test Combine-to-success Holm family is unchanged (All DL / Edge / Interior × pressure / sack); headline rows are All DL.

### 1. Sample funnel

118 DL in the roster (66 Edge / 52 Interior). 24 have no official 10-yard split (skipped the Combine 40; this file has no pro-day times; no tracking-derived split was invented for players who never ran the 40). 22 have a split but fewer than 20 pass-rush snaps. **72 final** (39 Edge / 33 Interior; 28 / 25 / 19 by 2023 / 2024 / 2025). All 72 are named, sorted by official 10-yard split, in `out/dl_players_named.csv`.

### 2. Headline numbers (6-test family, year+pick partial Spearman, Holm, 2,000 bootstrap)

| Subgroup | n | 10-yd vs pressure ρ (CI) | Holm p | 10-yd vs sack ρ (CI) | Holm p |
|---|---:|---|---:|---|---:|
| All DL | 72 | −0.45 (−0.62 to −0.19) | 0.00047 * | −0.31 (−0.53 to −0.07) | 0.039 * |
| Edge | 39 | −0.24 (−0.54 to +0.11) | 0.560 | +0.08 (−0.30 to +0.43) | 1.000 |
| Interior | 33 | −0.12 (−0.51 to +0.28) | 1.000 | −0.25 (−0.59 to +0.13) | 0.560 |

10-yard vs get-off (speed at 1.0s) remains strong even within subtypes: All DL partial ρ = −0.79; Edge −0.61 (Holm-significant); Interior −0.31 (Holm p ≈ 0.048). Mediation: 10-yard vs pressure after year + pick + get-off shrinks to ρ = −0.08 (p = 0.49). Edge median 10-yard 1.65 / pressure 8.3%; Interior 1.76 / 5.6% — that composition is part of the pooled pressure link.

### 3. Late-round gems, now one combined DL shortlist

The primary Combine measure is still the official 10-yard split, now chosen on the early-round *all-DL* sample (n early = 25, oriented pick-partial ρ = +0.64, p = 0.001, not a weak link). Strong = top third **within Edge** and **within Interior** (a within-subtype z-score). We do not take the top third of raw 10-yard times among all DL, because that list would be almost all edges. The draft-slot residual is fit on the combined all-DL sample.

Late-round strong vs weak remains null as a group (All DL: 35 late, 11 strong / 13 weak, median pressure 6.8% vs 7.2%, MW p = 0.614). Edge and Interior breakouts of that contrast are also null (Edge underpowered, 4 vs 8).

Combined R4–7 shortlist (ordered by residual):

- Cedric Johnson (Edge, 2024 R6 #214, 1.61, 14.6% pressure, residual +0.083, 192 snaps, also above the R1–3 median)
- Robert Beal (Edge, 2023 R5 #173, 1.62, 9.2%, +0.026, 131 snaps, above the R1–3 median)
- Brandon Dorlus (Interior, 2024 R4 #109, 1.68, 9.6%, +0.022, 303 snaps, above the R1–3 median)
- Adetomiwa Adebawore (Interior, 2023 R4 #110, 1.61, z +2.32, 9.2%, +0.019, 479 snaps, above the R1–3 median)
- Yasir Abdullah (Edge, 2023 R5 #136, 1.56, 7.4%, +0.004, 122 snaps)
- Mekhi Wingo (Interior, 2024 R6 #189, 1.64, 6.8%, +0.004, 132 snaps)
- Tyler Baron (Edge, 2025 R5 #176, 1.61, 6.8%, +0.003, **44 snaps — early look**)

UDFA: Tyrus Wheat (Edge, 2023, 1.59, 8.1%, +0.022, 123 snaps).

Abdullah and Baron are new relative to the earlier split-group lists, because the residual is now fit on all DL and “strong” is within-subtype. Zeek Biggers (Interior, 2025 R7 #253, 1.74, 5.4%, 130 snaps) drops off: residual is now −0.006 vs the all-DL slot fit (it was a thin +0.005 vs the interior-only fit).

Coach line is unchanged in spirit: *the names are useful scouting cards — especially Cedric Johnson on the edge and Adebawore / Dorlus inside — but late-round strong testers do not, as a group, reliably outproduce late-round weak testers. Do not turn the shortlist into a draft rule. And do not read the all-DL pressure result as a within-Edge or within-Interior rule.*

---

## 2026-11-11 (America/New_York) — Combine gems, all rounds (no early/late split)

Kevin's change: stop designating late rounds (4–7) vs early rounds (1–3). The earlier late-round shortlist is replaced by an all-rounds **Combine gems** list covering every eligible drafted player (rounds 1–7) plus undrafted players. UDFAs are flagged in a column, not held out as a separate tier.

Script: `combine_gems.py` (git mv from `late_round_gems.py`). Outputs: `out/combine_gems.csv`, `out/combine_gems_tests.csv`, `out/figs/fig8_combine_gems.png`, `COMBINE_GEMS.md`. This supersedes `LATE_ROUND_GEMS.md` and Figure 8's late-round framing.

### 1. Definitions

- **Strong** = top third of the position on a pre-declared Combine measure. For DL, top third *within Edge* and *within Interior* (within-subtype z of the official 10-yard split).
- **Overperformed** = positive residual of the primary gameplay outcome vs log draft pick, fit on every eligible player in the group. **UDFA = pick 260**, the slot after a seven-round draft, used consistently in that fit.
- **Group test** = one-sided Mann-Whitney (strong > weak) on the **year+pick residual**, across all eligible players including UDFAs. Raw-outcome medians are a companion.

Because rounds are no longer split, measure selection no longer uses an early-round hold-out. Each group has a **pre-declared** measure, locked to the earlier writeup: official 40 time (WR), broad jump (CB), gauntlet drill top speed (S), official 10-yard split (DL). Full-sample correlations are reported for transparency. **Selection caveat:** these measures were chosen with knowledge of the earlier shortlist exercise; the correlations are descriptive, not a confirmatory test, and were not used to pick a different primary here.

A weak-link flag means the pre-declared measure’s oriented year+pick Spearman ρ is < 0.20 or p ≥ 0.10 on the full eligible sample.

### 2. Pre-declared measures, full-sample

| Group | Measure | n | Oriented year+pick ρ | p | Weak link? |
|---|---|---:|---:|---:|---|
| WR | Official 40 time | 70 | +0.12 | 0.326 | Yes |
| CB | Broad jump | 32 | +0.34 | 0.056 | No |
| S | Gauntlet drill top speed | 33 | −0.36 | 0.037 | Yes (wrong-signed) |
| DL | Official 10-yard split | 72 | +0.45 | 7.8e-05 | No |

The safety gauntlet relationship on the full sample is actually negative (faster gauntlet, lower tackle involvement after year and pick). That is a hard weak-link flag: the four safety names below are not a group-level recommendation.

### 3. Group-level test: strong vs weak, all eligible players

| Group | n (strong / mid / weak) | Median outcome strong / weak | Median year+pick residual strong / weak | MW p (resid) | Notes |
|---|---|---|---|---:|---|
| WR | 70 (25 / 23 / 22) | 1.21 / 0.94 ypr | +0.099 / −0.087 | 0.141 | weak link; lean only |
| CB | 32 (13 / 9 / 10) | 7.9% / 7.7% | −0.001 / −0.010 | 0.050 | modest lean, not a claim |
| S | 33 (12 / 10 / 11) | 9.5% / 9.3% | −0.006 / −0.009 | 0.779 | weak link; null |
| DL | 72 (26 / 22 / 24) | 8.5% / 7.2% | +0.008 / −0.001 | 0.205 | null |
| DL Edge | 39 (13 / 13 / 13) | 11.5% / 7.9% | +0.028 / +0.017 | 0.062 | lean only |
| DL Interior | 33 (13 / 9 / 11) | 5.9% / 5.3% | −0.010 / −0.022 | 0.343 | null |

**No new group-level finding.** CB and Edge lean the expected way (p=0.050 and 0.062) but we will not promote them. The names are the deliverable.

### 4. Named shortlists (top residual), plus Chop Robinson

A gem is eligible, in the top third on the pre-declared measure, with a positive draft-slot residual. UDFAs can make the same list.

- **WR (official 40, weak link):** Luther Burden (2025 R2 #39, 4.41, 2.80 ypr, residual +1.305, 233 routes); Devontez Walker (2024 R4 #113, 4.36, 2.12 ypr, +0.937, 74 routes — limited sample); Brian Thomas (2024 R1 #23, 4.33, 2.08 ypr, +0.438, 954 routes); Marvin Mims (2023 R2 #63, 4.38, 1.75 ypr, +0.395, 687); Ladd McConkey (2024 R2 #34, 4.39, 1.92 ypr, +0.389, 1,008); Jaylin Noel (2025 R3 #79, 4.39, 1.48 ypr, +0.194, 197); Adonai Mitchell (2024 R2 #52, 4.34, 1.57 ypr, +0.164, 486); Jacob Cowing (2024 R4 #135, 4.38, 1.29 ypr, +0.157, 62). Also on the full list: Troy Franklin, Ricky Pearsall, Jaylin Lane, Tai Felton (only 20 routes — early look), and UDFA Isaiah Bond (residual only +0.009).
- **CB (broad jump):** Cam Smith (2023 R2 #51, 134-inch broad, 12.5% tackle rate, residual +0.045, 144 snaps — smaller sample); Andru Phillips (2024 R3 #70, 135 inches, 10.7%, +0.026, 1,277 snaps); Julius Brents (2023 R2 #44, 138 inches, 9.2%, +0.012, 655); Mike Sainristil (2024 R2 #50, 131 inches, 8.7%, +0.007, 1,919); Renardo Green (2024 R2 #64, 130 inches, 8.4%, +0.003, 1,433).
- **S (gauntlet, weak link, wrong-signed full-sample ρ):** Chamarri Conner (2023 R4 #119, 18.49 mph, 11.4% tackle rate, residual +0.011, 1,805 snaps); Brian Branch (2023 R2 #45, 18.97 mph, 11.4%, +0.011, 2,270); Tyler Nubin (2024 R2 #47, 18.27 mph, 11.3%, +0.010, 1,522); Evan Williams (2024 R4 #111, 18.57 mph, 10.4%, +0.002, 1,306). Names only; the group test is null and the measure itself goes the wrong way after year and pick.
- **DL (official 10-yard, within-subtype strong):** Cedric Johnson (Edge, 2024 R6 #214, 1.61, 14.6% pressure, residual +0.083, 192 snaps); Jalyx Hunt (Edge, 2024 R3 #94, 1.60, 12.8%, +0.052, 492); Jared Verse (Edge, 2024 R1 #19, 1.60, 14.9%, +0.048, 958); Will Anderson (Edge, 2023 R1 #3, 1.61, 17.8%, +0.047, 1,167); **Chop Robinson (Edge, 2024 R1 #21, 1.54, z +2.16, 13.9%, +0.040, 610) — #5 on the combined DL list**; YaYa Diaby (Edge, 2023 R3 #82, 1.56, 11.5%, +0.037, 1,292); Byron Young (Edge, 2023 R3 #77, 1.62, 11.5%, +0.036, 1,464); Robert Beal (Edge, 2023 R5 #173, 1.62, 9.2%, +0.026, 131). Also on the full 15-name list: Brandon Dorlus, Tyrus Wheat (UDFA), Adetomiwa Adebawore, Laiatu Latu, Yasir Abdullah, Mekhi Wingo, and Tyler Baron (44 snaps — early look).

**Chop Robinson requested check:** he clears both cuts. Official 10-yard 1.54 (fastest of the 72, top third within Edge, z +2.16), 13.9% pressure on 610 pass-rush snaps, draft-slot residual +0.040 (year+pick residual +0.037). He is a gem, ranked 5th among the 15 combined DL gems by residual.

Coach line: *the names are useful scouting cards — including first-rounders such as Brian Thomas, Will Anderson, Jared Verse, and Chop Robinson, and later-round standouts such as Cedric Johnson — but strong testers do not, as a group, reliably outproduce weak testers in this sample. Do not turn the shortlist into a draft rule. Official 40 time for receivers and the gauntlet for safeties are weak links.*
