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
