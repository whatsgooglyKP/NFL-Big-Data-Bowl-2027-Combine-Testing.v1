# Results log — Sunday Speed build

Append-only notes from the working sessions. Official metric definitions live in `METRICS.md`. Official headline numbers (WR translation, Phase 2 drills) live in `PHASE2_RESULTS.md`.

---

## 2026-11-10 (America/New_York) — SSOE scouting card, NGS incremental, CB speed tax, DL burst

Scripts: `ssoe.py`, `dl_burst.py`. Outputs: `out/ssoe_leaderboard.csv`, `out/ssoe_tests.csv`, `out/dl_burst_players.csv`, `out/dl_burst_tests.csv`, `out/figs/fig4_ssoe_leaderboard.png`, `out/figs/fig5_dl_burst.png`. Definitions frozen in `METRICS.md`.

### 1. Official metric freeze

Sunday Speed, Speed Translation Rate, and Sunday Speed Over Expected are frozen in `METRICS.md`. SSOE is actual Sunday Speed minus the speed expected from the player's Combine 40-yard tracked top speed at his position, in mph. It is not adjusted for weight, draft year, or draft slot. Recomputed SSOE matched the official player table (max abs error 3.3e-15 mph). Official samples unchanged: WR 62, CB 33, S 26. Locked translation rates: WR 0.67 (0.47–0.88), CB 0.09 (−0.13–0.38), S 0.22 (−0.17–0.59).

Reliability flag on the scouting card: High (≥80 opportunity plays), Medium (40–79), Limited (<40).

### 2. SSOE scouting-card leaderboard

121 players. Figure 4 shows the top 15 and bottom 15 at WR (n=62) and CB (n=33). Safeties (n=26) are fewer than 30 unique players, so the figure and the tables below show the full roster once, split at the zero line (11 faster than the 40 predicted, 15 slower). For receivers this is a true over/under-the-40 flag. For corners and safeties the 40 barely predicts Sunday Speed, so SSOE is close to faster or slower than the position average — the figure caption says so. Draft slot and round are not used on the scouting card.

**Top 15 SSOE, wide receivers (n=62)**

| Player | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---:|---:|---:|---:|---:|---|
| Ronnie Bell | Michigan | 22.02 | 18.08 | 19.30 | **+1.22** | 73 | Medium |
| Devontez Walker | North Carolina | 23.14 | 18.83 | 19.91 | **+1.07** | 42 | Medium |
| Jalen Brooks | South Carolina | 22.00 | 18.06 | 19.12 | **+1.05** | 114 | High |
| Marvin Mims | Oklahoma | 22.81 | 18.61 | 19.49 | **+0.88** | 361 | High |
| Jimmy Horn | Colorado | 23.21 | 18.88 | 19.66 | **+0.78** | 36 | Limited |
| Jermaine Burton | Alabama | 23.24 | 18.90 | 19.57 | **+0.67** | 73 | Medium |
| Tez Johnson | Oregon | 22.58 | 18.46 | 19.08 | **+0.62** | 133 | High |
| Kyle Williams | Washington State | 22.89 | 18.66 | 19.23 | **+0.57** | 92 | High |
| Jacob Cowing | Arizona | 22.84 | 18.63 | 19.13 | **+0.50** | 28 | Limited |
| Arian Smith | Georgia | 23.48 | 19.07 | 19.54 | **+0.48** | 109 | High |
| Tre Tucker | Cincinnati | 23.45 | 19.05 | 19.51 | **+0.47** | 650 | High |
| Konata Mumpfield | Pittsburgh | 21.45 | 17.70 | 18.11 | **+0.41** | 67 | Medium |
| Derius Davis | Texas Christian | 23.91 | 19.35 | 19.74 | **+0.40** | 62 | Medium |
| Troy Franklin | Oregon | 23.30 | 18.94 | 19.31 | **+0.37** | 330 | High |
| Luther Burden | Missouri | 22.80 | 18.61 | 18.92 | **+0.31** | 67 | Medium |

**Bottom 15 SSOE, wide receivers (n=62)**

| Player | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---:|---:|---:|---:|---:|---|
| Andrei Iosivas | Princeton | 23.12 | 18.82 | 18.37 | **−0.45** | 460 | High |
| Jaylin Noel | Iowa State | 23.18 | 18.86 | 18.38 | **−0.48** | 65 | Medium |
| Chimere Dike | Florida | 23.37 | 18.99 | 18.48 | **−0.51** | 157 | High |
| Jonathan Mingo | Mississippi | 23.17 | 18.85 | 18.34 | **−0.52** | 296 | High |
| Ricky Pearsall | Florida | 22.79 | 18.60 | 18.07 | **−0.53** | 195 | High |
| Ryan Flournoy | Southeast Missouri | 22.68 | 18.52 | 17.96 | **−0.56** | 137 | High |
| Jason Brownlee | Southern Mississippi | 22.27 | 18.25 | 17.67 | **−0.57** | 89 | High |
| Jamari Thrash | Louisville | 22.27 | 18.25 | 17.66 | **−0.59** | 98 | High |
| Devaughn Vele | Utah | 22.48 | 18.39 | 17.77 | **−0.61** | 179 | High |
| Rakim Jarrett | Maryland | 23.49 | 19.07 | 18.33 | **−0.74** | 66 | Medium |
| Malik Washington | Virginia | 22.52 | 18.42 | 17.59 | **−0.82** | 159 | High |
| Xavier Legette | South Carolina | 23.43 | 19.03 | 18.18 | **−0.85** | 321 | High |
| Elic Ayomanor | Stanford | 22.82 | 18.62 | 17.66 | **−0.96** | 177 | High |
| Mitch Tinsley | Penn State | 22.23 | 18.22 | 17.23 | **−1.00** | 65 | Medium |
| Rashee Rice | Southern Methodist | 22.37 | 18.32 | 17.12 | **−1.20** | 121 | High |

**Top 15 SSOE, cornerbacks (n=33)**

| Player | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---:|---:|---:|---:|---:|---|
| Billy Bowman | Oklahoma | 23.13 | 17.38 | 18.72 | **+1.33** | 51 | Medium |
| Andru Phillips | Kentucky | 22.45 | 17.32 | 18.02 | **+0.69** | 314 | High |
| Cam Hart | Notre Dame | 22.16 | 17.29 | 17.92 | **+0.62** | 392 | High |
| Terrion Arnold | Alabama | 22.05 | 17.28 | 17.77 | **+0.49** | 581 | High |
| Upton Stout | Western Kentucky | 22.93 | 17.36 | 17.86 | **+0.49** | 91 | High |
| Kris Abrams-Draine | Missouri | 22.19 | 17.30 | 17.77 | **+0.48** | 142 | High |
| Clark Phillips | Utah | 22.72 | 17.34 | 17.81 | **+0.46** | 285 | High |
| Nehemiah Pritchett | Auburn | 23.33 | 17.40 | 17.85 | **+0.45** | 88 | High |
| Myles Harden | South Dakota | 22.27 | 17.30 | 17.73 | **+0.42** | 172 | High |
| Trey Amos | Mississippi | 22.82 | 17.35 | 17.68 | **+0.33** | 198 | High |
| Kei'Trel Clark | Louisville | 22.87 | 17.36 | 17.68 | **+0.32** | 222 | High |
| Riley Moss | Iowa | 23.22 | 17.39 | 17.71 | **+0.32** | 851 | High |
| Renardo Green | Florida State | 22.63 | 17.34 | 17.58 | **+0.24** | 516 | High |
| Jarrian Jones | Florida State | 23.07 | 17.38 | 17.62 | **+0.24** | 318 | High |
| Kelee Ringo | Georgia | 24.01 | 17.47 | 17.55 | **+0.09** | 231 | High |

**Bottom 15 SSOE, cornerbacks (n=33)**

| Player | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---:|---:|---:|---:|---:|---|
| Mike Sainristil | Michigan | 22.00 | 17.28 | 17.18 | **−0.10** | 560 | High |
| Nohl Williams | California | 22.64 | 17.34 | 17.22 | **−0.12** | 162 | High |
| Maxwell Hairston | Kentucky | 24.25 | 17.49 | 17.23 | **−0.25** | 109 | High |
| Alex Austin | Oregon State | 22.43 | 17.32 | 17.06 | **−0.26** | 231 | High |
| Deonte Banks | Maryland | 22.91 | 17.36 | 17.07 | **−0.30** | 808 | High |
| Cam Smith | South Carolina | 23.29 | 17.40 | 17.07 | **−0.33** | 63 | Medium |
| Darien Porter | Iowa State | 23.89 | 17.45 | 17.05 | **−0.40** | 190 | High |
| Chau Smith-Wade | Washington State | 21.82 | 17.26 | 16.83 | **−0.43** | 145 | High |
| Quincy Riley | Louisville | 22.66 | 17.34 | 16.88 | **−0.46** | 271 | High |
| Josh Newton | Texas Christian | 22.74 | 17.35 | 16.88 | **−0.47** | 280 | High |
| Max Melton | Rutgers | 23.36 | 17.41 | 16.86 | **−0.55** | 355 | High |
| Darrell Luter | South Alabama | 22.87 | 17.36 | 16.78 | **−0.58** | 126 | High |
| Jaylon Jones | Texas A&M | 22.38 | 17.31 | 16.63 | **−0.68** | 760 | High |
| Julius Brents | Kansas State | 22.22 | 17.30 | 16.50 | **−0.79** | 242 | High |
| Denzel Burke | Ohio State | 22.51 | 17.33 | 15.96 | **−1.36** | 210 | High |

Three corners sit between these lists and are not shown: Quinyon Mitchell +0.06 (High, 750 plays); Cobee Bryant +0.02 (Limited, 34 plays); Cameron Mitchell +0.01 (High, 324 plays).

**Safeties (n=26): full roster**

The safety sample is smaller than 15 top + 15 bottom, so nobody is listed twice. The 11 players above the dashed line in Figure 4 were faster than the 40 predicted; the 15 below it were slower.

**Faster than the 40 predicted, safeties (n=11 of 26)**

| Player | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---:|---:|---:|---:|---:|---|
| Brandon Joseph | Notre Dame | 21.97 | 16.08 | 16.89 | **+0.81** | 78 | Medium |
| Brian Branch | Alabama | 22.49 | 16.19 | 16.91 | **+0.71** | 666 | High |
| Sydney Brown | Illinois | 23.41 | 16.39 | 17.02 | **+0.62** | 168 | High |
| Calen Bullock | Southern California | 22.54 | 16.20 | 16.79 | **+0.58** | 713 | High |
| Antonio Johnson | Texas A&M | 22.11 | 16.11 | 16.59 | **+0.48** | 455 | High |
| Jonas Sanker | Virginia | 22.77 | 16.25 | 16.57 | **+0.32** | 305 | High |
| Quan Martin | Illinois | 22.54 | 16.20 | 16.44 | **+0.23** | 745 | High |
| Anthony Johnson | Iowa State | 22.55 | 16.21 | 16.43 | **+0.22** | 145 | High |
| Chamarri Conner | Virginia Tech | 22.35 | 16.16 | 16.34 | **+0.17** | 435 | High |
| Cole Bishop | Utah | 22.02 | 16.09 | 16.24 | **+0.15** | 420 | High |
| Kaevon Merriweather | Iowa | 21.92 | 16.07 | 16.21 | **+0.14** | 149 | High |

**Slower than the 40 predicted, safeties (n=15 of 26)**

| Player | College | Combine mph | Expected | Actual | SSOE | Plays | Flag |
|---|---|---:|---:|---:|---:|---:|---|
| Marques Sigle | Kansas State | 23.53 | 16.42 | 16.42 | **−0.00** | 107 | High |
| Craig Woodson | California | 22.67 | 16.23 | 16.18 | **−0.05** | 289 | High |
| Javon Bullard | Georgia | 22.56 | 16.21 | 16.14 | **−0.06** | 278 | High |
| Tykee Smith | Georgia | 22.43 | 16.18 | 16.10 | **−0.08** | 346 | High |
| Dadrion Taylor-Demerson | Texas Tech | 23.00 | 16.30 | 16.21 | **−0.09** | 217 | High |
| Malaki Starks | Georgia | 23.12 | 16.33 | 16.19 | **−0.14** | 425 | High |
| Rayuan Lane | Navy | 22.74 | 16.25 | 16.05 | **−0.20** | 50 | Medium |
| Kitan Crawford | Nevada | 23.31 | 16.37 | 16.10 | **−0.27** | 33 | Limited |
| Jordan Battle | Alabama | 22.72 | 16.24 | 15.89 | **−0.35** | 632 | High |
| Demani Richardson | Texas A&M | 22.00 | 16.09 | 15.70 | **−0.39** | 125 | High |
| R.J. Mickens | Clemson | 23.10 | 16.32 | 15.94 | **−0.39** | 82 | High |
| Kamren Kinchens | Miami | 22.11 | 16.11 | 15.65 | **−0.46** | 446 | High |
| DeMarcco Hellams | Alabama | 22.70 | 16.24 | 15.73 | **−0.51** | 158 | High |
| Jay Ward | Louisiana State | 22.30 | 16.15 | 15.51 | **−0.65** | 71 | Medium |
| Evan Williams | Oregon | 21.98 | 16.08 | 15.26 | **−0.82** | 442 | High |

Do not treat Limited names (Jimmy Horn, 36 deep routes; Jacob Cowing, 28; Kitan Crawford, 33; Cobee Bryant, 34 coverage plays, not shown in the CB top/bottom 15) as a finished grade. Do not claim SSOE predicts starts or production; those tests were already null.

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

---

## 11/2026 (America/New_York) — Multi-test models (WR / TE / CB / S) and athletic comps

Kevin's question: can a logistic regression that incorporates the 10-yard split, broad jump, vertical, and 40 find on-field trends for RBs, WRs, TEs, CBs, and safeties, and how do trees and naive Bayes compare? After the model comparison, KNN athletic comps against public nflverse Combine data (2000–2022).

Scripts: `multi_test_models.py`, `athletic_comps.py`. Outputs: `out/multi_test_coefficients.csv`, `out/multi_test_auc.csv`, `out/multi_test_spearman.csv`, `out/multi_test_coverage.csv`, `out/multi_test_players.csv`, `out/multi_test_tree_rules.txt`, `out/athletic_comps.csv`, `out/athletic_comps_summary.csv`, `out/athletic_comps_correlation.csv`, `out/figs/fig9_multi_test_models.png`. Writeup: `MULTI_TEST_MODELS.md`. Public historical data (not Kaggle) is cached in `external/` with attribution.

### 1. Sample and outcomes

Success = above the position median among rookies clearing a snap/route floor. UDFA = pick 260. Year and log pick in every model. Complete cases are primary (40, 10-yard, vertical, broad, weight). 3-cone and shuttle are too sparse for the joint model.

| Group | In file | Eligible | Complete | Outcome | Floor | Median |
|---|---:|---:|---:|---|---|---:|
| WR | 106 | 77 | 63 | Yards per route | ≥20 routes | 1.15 |
| TE | 42 | 29 | 22 | Yards per route | ≥20 routes | 1.15 |
| CB | 60 | 42 | 30 | Tackle involvement rate | ≥50 def snaps | 8.1% |
| S | 53 | 34 | 24 | Tackle involvement rate | ≥50 def snaps | 10.0% |
| RB | 1 | — | — | **Excluded from every model** | — | — |

RB is Sione Vaki (26 REG snaps, 9 routes, 7 rush plays, 18 rush yards). Too few to fit or to pool. His athletic comps are an anecdote only.

CB yards allowed is not computable (no target-allowed or reception-yards field on a defender; play-level yards_gained is not attributed). Tackle rate is the fallback. Same for S, with the earlier wrong-signed gauntlet → tackle-rate result noted.

### 2. Firth odds ratios per 1 SD (multivariable, Holm within position)

**No Combine test is Holm-significant at any position.**

- WR (n=63): 40 OR 0.80 (CI 0.35–1.59, Holm p=0.40); 10-yard 1.52 (0.90–3.42, 0.14, wrong-signed); vertical 1.16; broad 1.09; weight 0.93. All CIs include 1.
- TE (n=22): 10-yard OR 0.16 (0.00–1.32, Holm p=0.13) is a lean — L2 bootstrap CI 0.24–0.79 excludes 1, but Holm-Firth does not, n is 22, and vertical goes the wrong way (OR 0.23). Weight Holm p=0.071.
- CB (n=30): nothing significant. 40 OR 2.43 is wrong-signed with a huge Firth CI (0.81–615). Weight lean Holm p=0.089.
- S (n=24): nothing significant; CIs very wide.

Partial Spearman (year+pick, pairwise, Holm) is also all null. Closest leans: TE 10-yard ρ=−0.37, p=0.069; CB broad jump ρ=+0.34, p=0.056 (same as Combine gems); WR 40 ρ=−0.12, p=0.33 (the known weak production link).

### 3. Model comparison, repeated stratified CV (20×5) vs pick+year baseline

- **WR, the largest sample:** L2 multi-test CV AUC 0.55 ± 0.12 vs pick+year 0.62 (Δ=−0.07). Adding tests *hurts*. Trees 0.51–0.54, NB 0.54, RF 0.50, GB 0.50. Training AUCs 0.72–0.97 vs those CV numbers — overfitting, especially RF/GB.
- **TE:** L2 0.75 vs 0.63 looks like a lift, but training AUC is 0.96 on n=22 and the fold SD is 0.28. Not a finding.
- **CB:** L2 0.63 vs a below-chance baseline of 0.42; Gaussian NB 0.81 (train 0.96) on the fallback tackle-rate outcome. Not a draft rule.
- **S:** L2 0.61 vs pick+year 0.64. Does not beat the baseline.

Depth-2 tree rules (in-sample; CV AUCs near 0.45–0.56): WR and S split first on draft pick; TE's higher vertical goes to *below*-median (wrong direction); CB's faster 40 (≤4.40) goes to below-median tackle rate. Trust the CV, not the leaves.

Imputation sensitivity does not flip the complete-case conclusions (WR still loses to the baseline).

### 4. Athletic comps (nflverse Combine 2000–2022, K=5)

Z-score within position; nan-aware RMS distance on 40, vertical, broad, 3-cone, shuttle, height, weight. (No 10-yard split in the public file.) Prefer 4 shared tests; fall back to 3 and flag as thin. Career labels from draft_picks `w_av`, All-Pros, Pro Bowls. 380 rookies (WR/TE/CB/S/Edge/Interior + the one RB); 22 have too few tests for a comp.

Headline cards:

- **Cedric Johnson** (Edge, 2024, pick 214): nearest comp is **Brian Orakpo** (2009, pick 13, 4 Pro Bowls, 4.63 40 like Cedric's 4.63, 39.5" vs 38" vertical, 75"/263 vs 75"/260). Mean comp w_av 31.5. Cedric's pressure rate 14.6%. The card of the set.
- **Chop Robinson** (Edge, pick 21): Drake Jackson, Bryan Thomas, Eli Harold, Kevin Burnett, Malik Jefferson. Mean w_av 21.2 (above Edge median 15). Solid-starter profile.
- **Luther Burden** (WR, pick 39): thin (40 + size only). Comps include D.J. Moore and Pierre Garçon (stars) and three journeymen with the same 4.40-ish 40 at 72"/~206. Flag as thin.
- **Brian Thomas** (WR, pick 23): Darrius Heyward-Bey, Javon Walker, and three lesser WRs. Solid, mixed.
- **Will Anderson** (Edge, pick 3): thin (40 + size). Kayvon Thibodeaux, Karlos Dansby (star), Mark Anderson, and two journeymen.
- **Jared Verse** (Edge, pick 19): Clelin Ferrell, Drake Jackson, Ojabo, Brailford, Vernon Gholston. Mean w_av 7.4. Cautionary neighborhood, not a forecast.
- **Sione Vaki** (RB, pick 132): anecdote. Kerryon Johnson plus four no-record (mostly UDFA) RBs.

KNN mean-w_av vs our gameplay, year+pick partial Spearman, Holm across six groups: **all null.** CB lean ρ=−0.37, Holm p=0.12, on the fallback tackle metric, unstable to the shared-test floor. Interior lean ρ=+0.22, Holm p=0.91. Names are the deliverable.

Coach line: *receivers stay good with the 40 as Sunday Speed, not as production. A multi-test logistic, a shallow tree, and naive Bayes do not beat draft slot for WR gameplay and do not produce a Holm-significant test at any skill position in this sample. Athletic comps — especially Cedric Johnson / Brian Orakpo — are scouting cards, not a group prediction rule. RBs are out (n=1).*


## 11/2026 (America/New_York) — Which Combine tests translate to Sunday? (year only, no draft pick)

Kevin reframed the multi-test question. Draft slot is out of this analysis entirely — not a covariate, not a baseline, not a sensitivity. The question is: per position group, which Combine metric translates to an important in-game success metric? Groups are WR, TE, CB, S, and **one combined DL**. Edge vs Interior is an appendix only. RB is excluded (n=1). Script: `combine_to_game.py`. Headline figures: `out/figs/fig10_combine_gameplay_heatmap.png`, `out/figs/fig11_bayes_hierarchical.png`. Model chart: `out/figs/fig12_model_comparison.png`. Writeup: `MULTI_TEST_MODELS.md`.

**Method.** Pairwise Spearman of every available Combine test (official 40, official 10-yard, tracking 20-yard, vertical, broad, 3-cone, shuttle, height, weight, Combine top speed, 40-yard peak accel) × each group's in-game metrics, residualized on draft-year dummies only, 2,000 bootstrap CIs, Holm and BH-FDR within the group across every valid cell. Then a model comparison on the key binary success metric (above-median among snap-eligible rookies) with a **year-only** baseline, 20×5 RepeatedStratifiedKFold seed 2027: L2, Firth, nested-CV lasso and elastic net, shallow trees, Gaussian NB, plus continuous ridge / lasso / EN, plus a Bayesian hierarchical logistic (PyMC / nutpie) that partially pools Combine-test slopes across the five groups. Joint models use official 40, official 10-yard, vertical, broad, height, weight, and Combine top speed, plus year. Closing speed and defender yards-allowed are not in this file and were not invented.

**Best Combine test for each group's key success metric** (year-controlled Spearman):

| Group | Key metric | Best test | n | ρ | 95% CI | p | Holm | FDR | FDR-sig? |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| WR | Yards per route | Vertical | 67 | +0.22 | −0.05 to +0.45 | 0.079 | 1.00 | 0.38 | No |
| TE | Yards per route | 20-yard (tracking) | 25 | −0.56 | −0.84 to −0.10 | 0.004 | 0.19 | 0.19 | No (lean) |
| CB | Tackle rate | Broad jump | 32 | +0.34 | −0.15 to +0.62 | 0.058 | 1.00 | 0.49 | No |
| S | Tackle rate | Height | 34 | −0.33 | −0.59 to +0.03 | 0.060 | 1.00 | 0.54 | No |
| DL | Pressure rate | Official 10-yard | 72 | −0.47 | −0.66 to −0.23 | 2.7×10⁻⁵ | 0.001 | 7.3×10⁻⁵ | Yes |

**FDR-significant cells.** DL: 37 of 44 cells, including official 10-yard and official 40 vs pressure (both ρ = −0.47, n = 72), vs sack (ρ ≈ −0.37), and a very tight get-off chain (10-yard vs speed at 1.0 s: ρ = −0.80, n = 72). WR: 6 of 66 cells, **none of them yards per route** — Combine top speed vs Sunday Speed ρ = +0.63, n = 62, FDR p = 2×10⁻⁶; official 40 vs Sunday Speed ρ = −0.59, n = 63; plus a size–speed tradeoff (heavier / taller receivers run slower on Sunday and get less deep separation). TE, CB, S: zero FDR-significant cells.

**Model comparison (CV AUC vs year-only baseline).** WR: nothing beats chance (Firth 0.49, lasso 0.44, year 0.40); lasso shrinks every test to zero (C=0.01). TE: Firth 0.67 and lasso 0.61 on n=22 with train AUC 0.99–1.00 and wild lasso ORs (height 372) — not deployable; lasso failed to shrink (C=35.9). CB: lasso 0.71 vs year 0.35, n=29, overfit 0.13; surviving official 40, 10-yard, vertical, weight. S: L2 0.70, lasso 0.61, n=24, weak outcome. DL: lasso 0.685 vs year 0.596, overfit 0.075, n=64; surviving official 40 (OR 0.66), vertical (1.11), weight (0.90); the pairwise 10-yard winner is collinear with the 40 (stability 0.13). Continuous CV R² is negative except DL ridge +0.03.

**Bayesian hierarchical (n=200, 4×2000+2000 nutpie, max R̂=1.002, 0 divergences, 1/200 Pareto k>0.7).** Pooled official-40 OR 0.69 per 1 SD (90% CI 0.34–1.22), P(direction)=0.88. WR official 40 OR 0.57 (0.27–1.01), P(dir)=0.95, the only filled marker. DL official 40 OR 0.62 (0.24–1.22), P=0.89. PSIS-LOO AUC pooled 0.60 (WR 0.42, TE 0.41, CB 0.66, S 0.68, DL 0.70). 5-fold (one pass) mean AUC 0.60 ± 0.07.

**Recommendations, flagged for Kevin (he leans lasso as safest).** WR: lasso, because it refuses the tests; the WR finding is Sunday Speed, not YPR. TE: no deployable model; report the 20-yard lean as a lean. CB: lasso, tentative. S: no deployable model. DL: lasso (we agree with Kevin's preference).

**Appendix (not in headline).** Official 10-yard vs pressure is an Edge lean (ρ=−0.36, n=39, p=0.025, FDR=0.077) and is not significant in Interior (ρ=−0.15, n=33, p=0.41). 10-yard vs get-off holds in both (Edge ρ=−0.57, FDR=0.002; Interior ρ=−0.41, FDR=0.047).

Outputs: `out/combine_to_game_spearman.csv`, `out/combine_to_game_best.csv`, `out/combine_to_game_auc.csv`, `out/combine_to_game_lasso_stability.csv`, `out/combine_to_game_coefficients.csv`, `out/combine_to_game_continuous.csv`, `out/combine_to_game_bayes.csv`, `out/combine_to_game_recommendations.csv`, `out/combine_to_game_appendix_edge_interior.csv`, `out/combine_to_game_players.csv`. No draft-pick column is in any of these analysis files.

## 11/2026 (America/New_York) — DB group, 20-yard lead test, and Burst Score

Kevin asked for three follow-ups on the year-only, no-pick analysis (previous entry, commit 87bef32): (1) merge CB and S into one headline group **DB**; (2) put the **20-yard split from the 40-yard dash first** as the lead test for every group, with coverage, and say clearly it is tracking-derived, not official electronic; (3) build a new coach-readable **Burst Score** — a 2- or 3-test composite of the 20-yard plus broad and/or vertical — two ways (equal-weight sign-aligned z-mean, and weights learned inside CV folds with ridge/lasso and evaluated out-of-fold), pick the best recipe per group by out-of-fold ρ, compare to the 20-yard alone, scale 0–100 within position, and report weights, OOF ρ with CI, n, and a top-10 named list. Groups are now **WR, TE, DB, DL**. DL stays one combined group. RB excluded. No draft pick. CB vs S and Edge vs Interior are appendix-only. A pooled DB tackle-rate median can confound role (safeties typically tackle more than corners); that is documented.

Script still `combine_to_game.py` (edited in place). New outputs: `out/combine_to_game_lead20.csv`, `out/combine_to_game_combos.csv`, `out/combine_to_game_burst.csv`, `out/combine_to_game_burst_players.csv`, `out/combine_to_game_burst_top10.csv`, `out/combine_to_game_appendix_cb_s.csv`, `out/figs/fig13_burst_score.png`. Figures 10–12 regenerated with the four-group framing and the 20-yard as the first heatmap row. Docs: `MULTI_TEST_MODELS.md` rewritten; this log; `README.md`.

**Sample.** Assembled 379 players: WR 106, TE 42, DB 113 (60 CB, 53 S), DL 118. Key-outcome eligible: WR 77 (≥20 routes), TE 29 (≥20 routes), DB 76 (42 CB + 34 S, ≥50 def snaps), DL 89 (≥20 rush). 20-yard coverage among eligible: WR 68/77 (88%), TE 25/29 (86%), DB 65/76 (86%), DL 71/89 (80%). Model complete-case (all MODEL_TESTS, now including the 20-yard first): WR 61, TE 22, DB 53, DL 64. Pooled Bayes n = 200.

**Lead 20-yard (tracking-derived, year-controlled) vs the key metric.** WR YPR: ρ=−0.02, n=68, 95% CI −0.27 to +0.23, p=0.90, FDR=0.98 (not sig); best other = vertical +0.22. TE YPR: ρ=−0.56, n=25, 95% CI −0.85 to −0.11, p=0.004, Holm=0.19, FDR=0.19 (lean, CI excludes 0; this is the best TE test). DB tackle: ρ=−0.07, n=65, 95% CI −0.33 to +0.20, p=0.59, FDR=0.90; best other = Combine top speed −0.24 (wrong direction, p=0.056, FDR=0.31). DL pressure: ρ=−0.31, n=71, 95% CI −0.53 to −0.08, p=0.009, Holm=0.12, FDR=0.012 (**FDR-significant**); best other = official 10-yard −0.47, n=72, Holm=0.001, FDR=7.3×10⁻⁵.

**Best single test on the key metric (new groups).** WR vertical vs YPR ρ=+0.22, n=67, p=0.079, FDR=0.38 (not sig). TE 20-yard vs YPR as above. DB Combine top speed vs tackle ρ=−0.24 (not sig, wrong direction). DL official 10-yard vs pressure as above (YES). FDR-significant cells: WR 6/66 (Sunday Speed and size–deep-sep; **none YPR** — Combine top speed vs Sunday Speed ρ=+0.63, n=62, FDR p=2×10⁻⁶; official 40 ρ=−0.59); TE 0/51; DB 2/33 (official 40 and weight vs Sunday Speed; **none tackle**); DL 37/44 including the get-off chain.

**Burst Score (picked by out-of-fold ρ; 0–100 within position).** Equal-weight won in every group; ridge and lasso, fit inside training folds and scored OOF, never beat it. WR: 20-yard + vertical + broad, equal-weight 33/33/33, n=61, OOF ρ=+0.29, 95% CI +0.01 to +0.54, p=0.021, **beats** 20-yard alone (OOF ρ=+0.02). TE: 20-yard + broad, 50/50, n=22, OOF ρ=+0.43, 95% CI −0.06 to +0.77, p=0.046, **does not beat** 20-yard alone (OOF ρ=+0.56). DB: 20-yard + vertical, 50/50, n=59, OOF ρ=+0.13, 95% CI −0.15 to +0.40, p=0.31 (CI includes 0; numerically above 20-yard OOF ρ=+0.08). DL: 20-yard + vertical + broad, 33/33/33, n=64, OOF ρ=+0.45, 95% CI +0.18 to +0.66, p=0.000, **beats** 20-yard alone (OOF ρ=+0.31). Same-fold combo tests (common complete case): WR adding vertical, LR p=0.046, ΔCV-AUC=+0.075; DL adding broad, LR p=0.025, ΔCV-AUC=+0.09; TE and DB, adding jumps does not help (often lowers CV AUC). Top-10 named lists (Burst, key metric, 20-yd, vert, broad) are in `out/combine_to_game_burst_top10.csv` and in `MULTI_TEST_MODELS.md`. WR #1 Ricky Pearsall (Burst 100, YPR 1.66); TE #1 Elijah Higgins (100, YPR 1.18) — TE list is a Burst ranking, not a recommendation over the 20-yard; DB #1 Quan Martin (S, 100, tackle 0.101); DL #1 Adetomiwa Adebawore (100, pressure 0.092), with Jared Verse at 94 (pressure 0.149).

**DB role caveat.** ≥50-snap eligible: CB n=42, median tackle rate=0.081; S n=34, median=0.100. Appendix 20-yard vs tackle: CB ρ=+0.03, n=36, p=0.86; S ρ=−0.03, n=29, p=0.88. Zero FDR cells in either role. Closest leans remain CB broad jump vs tackle ρ=+0.34, n=32, p=0.058, FDR=0.49, and S height vs tackle ρ=−0.33, n=34, p=0.060, FDR=0.54.

**Models (20×5, seed 2027, year only; 20-yard now in MODEL_TESTS).** WR: year 0.399, Firth 0.478, lasso 0.431 (C=0.01, train 0.500, all tests zeroed). TE: year 0.264, L2 0.854 (train 1.000), lasso 0.826 (train 0.983, C=1.67, six surviving tests, 20-yard OR 0.12) — overfit, n=22, not deployable. DB: year **0.618** beats lasso 0.590 and matches L2 0.617; lasso keeps height and Combine top speed without beating year. DL: year 0.596, lasso 0.674 (overfit gap 0.086), EN 0.703, NB 0.727 (overfit 0.031); lasso surviving official 40 (OR 0.66, stability 0.76), vertical (OR 1.11, 0.72), weight (OR 0.90, 0.59); 10-yard and 20-yard zeroed (stability 0.11 and 0.27, collinear with the 40). Continuous CV R² negative at WR/TE/DB, ridge +0.024 at DL.

**Bayes (4 groups, 8 tests including the 20-yard, n=200).** max R̂=1.002, 0 divergences, 0/200 Pareto k>0.7. PSIS-LOO AUC WR 0.45, TE 0.74, DB 0.60, DL 0.69, pooled 0.61. 5-fold (one pass) mean 0.63. P(dir)≥0.90: WR official 40 OR 0.46 (90% 0.20–0.82) P=0.98; TE 20-yard OR 0.42 (90% 0.11–0.85) P=0.98, official 40 OR 0.50 P=0.95; DL official 40 OR 0.49 (90% 0.16–1.00) P=0.95; pooled official 40 OR 0.57 (90% 0.26–1.04) P=0.94. DB Combine top speed OR 0.52 (90% 0.24–0.90) P(dir)=0.03 (wrong side).

**Recommendations, flagged for Kevin (he leans lasso as safest).** WR: lasso, because it refuses the tests; the useful new WR deliverable is the Burst Score (OOF ρ=+0.29), and Sunday Speed remains the pairwise WR finding. TE: no deployable model; report the 20-yard lean; Burst does not beat the 20-yard. DB: year-only, no multi-test rule; Burst is consistent with chance; document the CB vs S tackle-rate confound. DL: lasso (we agree with Kevin), and the DL Burst Score (OOF ρ=+0.45) is the companion composite; official 10-yard remains the best single test vs pressure.

**Appendix Edge/Interior (unchanged story).** Official 10-yard vs pressure is an Edge lean (ρ=−0.36, n=39, p=0.025, FDR=0.077), not Interior (ρ=−0.15, n=33, p=0.41). 10-yard vs get-off holds in both. Tracking 20-yard vs pressure is a weaker Edge lean (ρ=−0.29, n=38, p=0.076) and near zero at Interior.

Outputs as listed in `MULTI_TEST_MODELS.md`. No draft-pick column is in any of these analysis files. Never committed raw Kaggle data.

## 11/2026 (America/New_York) — Route COD, Sunday Re-Burst/Brakes, and PFR coverage

Three explorations after the Burst Score work. All are labeled exploratory. No draft slot. No raw Kaggle data was committed. Scripts: `explore_route_cod.py`, `eda_accel_decel.py`, `explore_pfr.py`. Figures: `out/figs/fig14_accel_decel_profiles.png`, `fig15_combine_vs_game_cod.png`, `fig16_archetypes.png`. Public nflverse/PFR caches live in `external/` with `ATTRIBUTION.md`.

### 1. Route running and coverage: can we measure change of direction vs in-game separation?

Feasibility audit of the competition-page example. Game tracking is 10 Hz and covers only the 510-rookies cohort (no football entity, no veterans). Official `separation_at_pass_forward` is separation at throw, not at arrival, and is charted for WR/TE only. There is no general nearest-defender separation. DB cushion is pre-snap. Coverage assignment is a scheme role, not a receiver identity.

Cut detection used rolling heading-change peaks (≥50° over ~0.6 s) with an entry-speed filter, then peak deceleration into the break and peak acceleration out. Combine 3-cone and shuttle tracking is thin for DBs; WR and DB skill-drill tracking is rich.

**Exploratory findings (unadjusted).** Official 3-cone vs all-throw separation for WRs: ρ=−0.42, n=24, p=0.044 — a hint only, small n. WR route-drill change-of-direction vs separation is a null at usable n: peak decel vs all-throw sep ρ=−0.00, n=76, p=0.99; vs target sep ρ=+0.18, n=75, p=0.13; peak accel vs all-throw sep ρ=−0.11, n=76, p=0.34. The Kaggle data supports building our own start/stop traits. It does not, by itself, support a clean “cuts vs separation” success metric for defensive backs.

Outputs: `out/route_cod_*.csv`.

### 2. Acceleration and deceleration EDA, and original Sunday cards

Kevin’s brief: we do not need to tie accel/decel to an existing NFL success metric; we can create our own. Speed positions are WR, CB, and S, with TE as a comparison and RB (Sione Vaki) anecdote only. RB remains excluded from headline groups (n=1).

**Sunday Re-Burst** and **Sunday Brakes** are 0–100 within-position percentiles of game peak acceleration out of cuts and peak deceleration into cuts, among players meeting the play floor (20 opportunity plays for WR/TE, 30 for CB/S). Usable Sunday samples: WR 73, CB 42, S 34, TE 25.

**Position style (holds at the Combine and on Sunday).** Receivers are brake-dominant plant-and-cutters (Sunday brakes-to-gas median 1.82, n=73). Corners and safeties are more gas-dominant and snappier (CB median 1.21, n=42; S median 1.08, n=34). Tight ends sit in between (median 1.62, n=25). Pooled WR+CB+S correlations are inflated by this style gap — always read within-position tests.

**Combine skill-drill cuts mostly do not translate to Sunday cuts, within a position (exploratory, unadjusted).** Combine Re-Burst vs Sunday Re-Burst: WR ρ=−0.07, n=73, p=0.56; CB ρ=−0.11, n=42, p=0.50; S ρ=−0.16, n=34, p=0.38; TE ρ=+0.08, n=25, p=0.70. Combine Brakes vs Sunday Brakes: WR is a modest exception, ρ=+0.24, n=73, p=0.042; CB ρ=−0.14, n=42, p=0.38; S ρ=+0.04, n=34, p=0.82; TE ρ=+0.20, n=25, p=0.34. A named example is Quinyon Mitchell (CB, 2024, Toledo): Combine Brakes 95 and Combine Re-Burst 98, but Sunday Brakes 21 and Sunday Re-Burst 12, on 1,143 coverage plays and 313 cuts.

**Split-half reliability (even/odd plays, Spearman-Brown; exploratory).** Sunday Re-Burst is stable: WR SB 0.94, CB 0.86, S 0.84, TE 0.92. Sunday Brakes is usable but noisier, especially for corners: WR 0.74, CB 0.64, S 0.89, TE 0.78.

**Three Combine movement archetypes (k-means, k=3, silhouette 0.23; exploratory).** Explosive two-way cutters (n=57; examples Tre Tucker, Ja'Lynn Polk, Myles Harden; extreme: Jordan Addison). Heavy brakes, slow restart (n=47; Jay Ward, Julius Brents, Cedric Tillman; extreme: Brian Branch). Snappy, short turns, gas-dominant (n=85; Nehemiah Pritchett, Ladd McConkey, Jha'Quan Jackson; extreme: Elijhah Badger).

**Secondary links to existing outcomes (exploratory, unadjusted, not a success claim).** WR Sunday Re-Burst vs target separation at throw: ρ=+0.31, n=73, p=0.009. Other WR Re-Burst links (all-throw sep, yards per route, target rate) are not significant. WR Sunday Brakes vs target rate ρ=−0.23, n=73, p=0.049. CB Sunday Brakes vs pre-snap cushion ρ=−0.35, n=42, p=0.024 (more braking, slightly tighter cushion — interpret cautiously).

Coach-facing recommendation from this EDA: lead with the Sunday Re-Burst and Sunday Brakes 0–100 card. Do not use Combine Re-Burst to predict Sunday Re-Burst. Combine Brakes is only a weak WR pre-draft hint.

Outputs: `out/eda_accel_*.csv` (draft-pick columns were stripped from the player table). Figures 14–16.

### 3. Free PFR / nflverse coverage for the 510 rookies

Public nflverse GitHub release data (`pfr_advstats` season and weekly defense/receiving for 2023–2025, plus `players.parquet` as the ID map). There is no `ff_playerids` release under nflverse-data. PFF grades are not in these free files. Primary window is 2023–2025 to line up with Kaggle tracking; 2026 rows exist in the files (partial as of 11/16/2026) and were not used in the Spearman.

**Columns present** on season defense: missed tackles, missed-tackle %, coverage targets, completions and yards allowed, yards/target, passer rating allowed, ADOT, air yards, YAC allowed, blitzes, hurries, QB knocks, sacks, pressures, combined tackles. Batted passes start in 2024. Season receiving has drops, drop %, broken tackles, YAC, and YAC/reception. Weekly defense has the same ideas; weekly receiving is thinner. Season published rates are the primary totals (split rows from mid-season trades were summed). Weekly REG `comb`/games can disagree with the season file.

**Join to Kaggle `nfl_id`.** Direct match on nflverse `players.nfl_id`: **485/510 (95.1%)**. Name disagreements are almost all Jr/II/III suffixes. Missing `pfr_id` values were filled only when name + combine/draft year + college uniquely agreed (combine `season` used when `draft_year` is blank for UDFAs). Never last-name + college alone. This correctly keeps Myles Murphy 2024 North Carolina DT (`MurpMy01`) apart from the 2023 Clemson DE (`MurpMy00`). After that fill: **505/510 (99.0%) have a `pfr_id`**. Still unmatched: Alan Ali, D.J. Dale, Rashad Torrence, Mello Dotson. Gabe Hall matches by `nfl_id` but has no `pfr_id`. Almost none of the late fills have 2023–2025 advstats.

**Usable 2023–2025 season samples.** CB: 50 with a def row; **38 with ≥20 coverage targets and the same 38 with ≥15 tackle attempts** (median 68.5 targets, 7.21 yards/target allowed, 9.1% missed tackles). S: 39 with a def row; **23 with ≥20 targets, 33 with ≥15 tackle attempts** (coverage-floor medians: 68 targets, 8.40 yards/target, 7.9% missed tackles). The five generic “DB” rookies have no PFR stats. DL (DE/DT/NT): 0 at ≥20 coverage targets; 46 at ≥15 tackle attempts; **13 at ≥15 pressures**. EDGE/OLB: 18 at ≥15 tackle attempts, **9 at ≥15 pressures**. Off-ball LB: only 2 of 3 reach 15 tackle attempts. WR: **58 with ≥20 receiving targets** (median drop % 4.8, 3.92 YAC/rec). TE: **19 with ≥20 receiving targets**.

**Exploratory Spearman vs missed-tackle % and yards/target allowed (unadjusted, 2023–2025 season aggregates).** Missed-tackle % is mostly a null against official Combine tests and against Sunday Re-Burst. A soft safety hint only: Sunday Brakes vs missed-tackle % ρ=−0.36, n=23, p=0.094. Coverage efficiency: faster official 40 for CBs goes with fewer yards allowed per target, ρ=−0.47, n=33, p=0.006; longer broad jump goes the other way, ρ=+0.47, n=29, p=0.010. Faster tracking-derived 20-yard split for safeties goes with fewer yards/target, ρ=−0.53, n=20, p=0.018, and in pooled CB+S ρ=−0.31, n=52, p=0.025. Sunday Re-Burst has no relationship with either outcome in these samples. Sunday Brakes is not significant for CBs; at the safety tackle floor vs yards/target ρ=−0.32, n=32, p=0.071. 3-cone and shuttle are too thin (CB n=11 and 16; safeties n=3–5). A later “test every Combine measure against DB outcomes” sweep is feasible at these floors, but it should stay within-position and keep the sample-size cuts.

Outputs: `out/pfr_*.csv`. Caches: `external/advstats_season_{def,rec,rush}.parquet`, weekly def/rec 2023–2025, `external/players.parquet`. The play-level Sunday cache `out/eda_accel_game_plays.parquet` is gitignored (derived Kaggle tracking, not a summary table).

## 11/2026 (America/New_York) — Next Gen Stats receiving tie-in for WR and TE

Kevin asked to solidify a tie-in to NFL Next Gen Stats (the AWS-powered public stats). This is supporting / validation evidence only. The writeup still has to rest on the provided Kaggle tracking data. Script: `explore_ngs.py`. Figure: `out/figs/fig17_ngs_receiving.png`. Public nflverse caches live in `external/` with `ATTRIBUTION.md`. No draft slot. No raw Kaggle data was committed. RB remains excluded.

**Source and method.** Free public nflverse `nextgen_stats` release (`ngs_receiving`, plus `ngs_rushing` and `ngs_passing` inventoried; there are no NGS defensive tables). Window is regular-season 2023–2025, aligned with Kaggle tracking; 2026 rows exist in the release (last updated 11/16/2026) and were not used. Week-0 regular-season rows are official NGS season totals and are used when present. Player-seasons without a week-0 row are a target-weighted aggregate of weekly rows (NGS typically publishes a receiving week only at ≥5 targets, so low-usage weeks are missing from those careers). Each rookie's seasons are pooled from draft year through year 3, inside 2023–2025. Analysis floor: ≥20 observed NGS targets on that career pool. Primary Spearman is unadjusted, with a 2,000-player bootstrap 95% CI and BH-FDR / Holm within position across all Combine/Sunday × NGS pairs (10 traits × 6 NGS metrics). Year-residualized Spearman is a sensitivity. Draft slot is not used.

**Join to Kaggle `nfl_id`.** Direct match on nflverse `players.nfl_id` to `gsis_id`: **485/510 (95.1%)**. Name + draft year + college fallback into nflverse players added **0**. WR: **100/106 (94.3%)** have a `gsis_id`; TE: **41/42 (97.6%)**. Still unmatched at WR/TE: Jadon Haselwood, Trey Knox, Kaden Prather, Elijhah Badger, Roc Taylor, Kobe Hudson, Jacolby George — none of them appear in the NGS receiving files either. (The broader 25 unmatched Kaggle rookies lack an nflverse player row under our `nfl_id` or a unique name+year+college key; we did not use draft-pick tables to fill IDs.)

**Usable 2023–2025 receiving samples.** Any NGS receiving row in the rookie-to-year-3 window: WR 58/106, TE 16/42. At the ≥20-target floor: **WR 37** (median 114 observed NGS targets; 24 week-0 only, 11 mixed, 2 weekly-only) and **TE 11** (median 69; 4 week-0 only, 4 mixed, 3 weekly-only). TE is a small sample and is flagged as such. Tracking-derived 20-yard coverage at the floor: WR 34/37, TE 8/11. Burst Score: WR 31, TE 6 (TE Burst tests not computed). 3-cone and short shuttle remain thin (WR n=10 and 13; TE not computable).

**Validation (pre-declared, not in the FDR family): our tracking vs NGS.** This is the solid tie-in. Official charting of separation at throw on targeted plays vs NGS average separation: **WR ρ=+0.89, n=37, 95% CI +0.76 to +0.94, p<0.001**; TE ρ=+0.95, n=11, 95% CI +0.71 to +1.00, p<0.001 (small n); pooled WR+TE ρ=+0.92, n=48, 95% CI +0.86 to +0.96. All-throw separation is a bit weaker (WR ρ=+0.74, n=37, 95% CI +0.48 to +0.87). Pre-snap cushion vs NGS average cushion also holds: **WR ρ=+0.78, n=37, 95% CI +0.55 to +0.90, p<0.001**; TE ρ=+0.66, n=11, 95% CI +0.06 to +0.92, p=0.026 (small n); pooled ρ=+0.79, n=48, 95% CI +0.63 to +0.89. Year-controlled results are essentially the same. The two sources are close cousins, not identical — ours is separation at throw; NGS publishes its own average separation — but they move together tightly enough to use NGS as a check on our tracking metrics.

**Combine / Sunday traits vs NGS (exploratory supporting evidence).** No pair survives BH-FDR (0 of 96 tests with enough n; the within-position families are large). Unadjusted hints whose bootstrap CI excludes 0, all FDR ≈ 0.61, not a headline:

- WR tracking-derived 20-yard vs NGS cushion: ρ=−0.40, n=34, 95% CI −0.63 to −0.09, p=0.019 (faster 20-yard goes with more cushion). Year-controlled is the same (ρ=−0.40, p=0.019).
- WR official 40 vs NGS cushion: ρ=−0.37, n=34, 95% CI −0.64 to −0.04, p=0.031; year-controlled ρ=−0.45, p=0.008.
- WR Sunday Re-Burst vs NGS intended air yards: ρ=−0.37, n=37, 95% CI −0.65 to −0.02, p=0.023 (more re-burst, shorter airmass — a possible role effect). Year-controlled weakens to ρ=−0.30, p=0.067.

**Nulls and leans that do not hold.** WR 20-yard vs NGS separation is a null (ρ=−0.15, n=34, 95% CI −0.46 to +0.17, p=0.39). Burst Score vs separation, cushion, and YAC over expected are not significant. Sunday Brakes and Re-Burst vs separation and YAC over expected are nulls. Catch percentage is a null against the official tests and our composites. Official 10-yard is a null across these NGS metrics at WR. WR 20-yard vs YAC over expected is only a borderline lean (ρ=+0.34, n=34, 95% CI −0.05 to +0.65, p=0.050; CI includes 0). TE Combine tests are too small to lean on (typical n=8–11). A TE 10-yard vs catch-percentage correlation at n=8 is a curiosity only.

Coach-facing takeaway: NGS is now a documented, reproducible external check that our tracking separation and cushion are measuring the same underlying thing as the public Next Gen numbers. It does not, after multiple-testing correction, add a new Combine-to-NGS success headline. Keep NGS in the supporting layer; keep the writeup on the Kaggle tracking story (DL Burst, 20-yard lead test, Sunday Re-Burst/Brakes).

Outputs: `out/ngs_columns.csv`, `out/ngs_match_rates.csv`, `out/ngs_id_map.csv`, `out/ngs_unmatched.csv`, `out/ngs_coverage.csv`, `out/ngs_player_seasons.csv`, `out/ngs_career.csv`, `out/ngs_validation.csv`, `out/ngs_spearman.csv`. Caches: `external/ngs_{receiving,rushing,passing}.parquet`, `external/ngs_timestamp.json`. No draft-pick column is in any of these analysis files.

## 11/2026 (America/New_York) — DB tackling sweep and DL re-check (every Combine measure)

Kevin approved two runs: (1) every Combine measure vs DB tackling, (2) every Combine measure vs wider DL outcomes beyond pressure. Draft slot / round is not loaded anywhere (asserted in code). RB excluded. Scripts: `track_extract.py` (one pass over game tracking → gitignored caches in `out/cache/`), `bdb_stats.py` (shared stats), `db_tackling.py`, `dl_recheck.py`. Figures: `out/figs/fig18_db_tackling.png`, `out/figs/fig19_dl_recheck.png`.

**Method (both runs).** Spearman ρ controlled for draft year (both variables demeaned within draft-year cells, then rank-correlated), 2,000-player bootstrap 95% CI, BH-FDR across every cell in the pooled family. Sensitivity: pooled group controlled for year × role (CB vs S) or year × subtype (Edge vs Interior) cells, which removes the "safeties tackle more / edges rush in space" composition. Breakouts (CB, S, Edge, Interior) are secondary with their own FDR. Outcome reliability is odd/even-play split-half with Spearman-Brown (SB). Minimum n = 12 per cell. Tests: 12 official (10-yard, 40, vertical, broad, 3-cone, shuttle, bench, arm, hand, wingspan, weight, height) + tracking 20-yard and 10-yard splits, Combine top speed, 40-yard peak accel, Burst Score; DB adds Combine Brakes / Re-Burst (DB drill peak decel / accel); DL adds 3-cone and shuttle tracked Brakes / Re-Burst.

### 1. DB tackling (CB + SS + FS + DB, n = 118: 65 CB, 53 S)

**Outcomes and floors.** REG snaps that stood, on defense. Per-snap rates need ≥100 snaps (69 eligible: 38 CB, 31 S): tackles (solo + assist), solo, assisted, solo share (≥10 tackles), TFL, forced fumbles. Tracking (80% of 5,756 involved plays have a tracked tackle frame): tackle depth = tackler's x at the `tackle` event minus the line of scrimmage, in yards downfield (median 6.0 yd; LOS formula validated — DL sit 0.6 yd off it at the snap); run-play tackle depth (≥8 run tackles, n = 56); closing speed = his mean speed in the 1.0 s before the tackle; closing rate = straight-line distance to the tackle spot covered in that 1.0 s (≥10 tracked tackles, n = 69). Game tracking has no ball and almost no ball carriers (rookies only), so closing is "toward where the tackle happened", not a true carrier-relative approach. PFR (nflverse): missed tackle % (≥15 attempts, n = 71) and yards per target allowed (≥20 targets, n = 61).

**Reliability (SB).** Tackle rate 0.78, assist 0.68, run-tackle depth 0.64, solo 0.61, closing rate 0.40, closing speed 0.38, TFL 0.31, yards gained on his tackles 0.30, tackle depth 0.24, forced fumbles 0.02. TFL and forced fumbles are too rare for DBs to rank players; all-tackle depth is mostly alignment / role.

**Headline: no Combine measure survives FDR for DB tackling.** 247 pooled cells, 19 at raw p < 0.05 (≈12 expected by chance), 0 at FDR < 0.05 (smallest FDR 0.058). Same with year × role control (0/247, min 0.086), CB (0/234, min 0.075) and S (0/219, min 0.99).

Strongest cells (pooled DB, year-controlled):

| Combine | Outcome | n | ρ | 95% CI | FDR | Read |
|---|---|---:|---:|---|---:|---|
| Weight | PFR yards / target allowed | 61 | +0.44 | +0.17 to +0.61 | 0.058 | Composition: vanishes with role control (ρ +0.03) |
| Height | Tackle depth (tracking) | 69 | +0.41 | +0.17 to +0.60 | 0.058 | Holds with role control (+0.40, FDR 0.086); CB +0.55, n=38, FDR 0.075 — longer DBs make tackles deeper downfield (deployment, low-reliability outcome) |
| Wingspan | Tackle depth | 69 | +0.38 | +0.14 to +0.57 | 0.097 | Same story as height |
| Combine Brakes (DB drill) | Closing rate to tackle spot | 69 | +0.27 | +0.03 to +0.46 | 0.46 | **Best athletic test in the good direction**; holds with role control (+0.25, CI +0.01 to +0.47) |
| Official 40 | Closing speed, last 1 s | 59 | −0.28 | −0.53 to −0.02 | 0.51 | Faster 40, faster closing (lean) |
| Broad jump | PFR yards / target | CB 29 | +0.58 | +0.18 to +0.82 | 0.075 | CB only; longer broad, more yards/target (counter-intuitive, small n) |
| Official 40 | PFR yards / target | CB 33 | −0.43 | −0.76 to −0.01 | 0.42 | CB only; faster 40, fewer yards/target (matches the PFR exploration) |

**Notable nulls.** Lead 20-yard split vs tackle rate ρ = −0.12 (n = 58, CI −0.40 to +0.16, FDR 0.83); official 10-yard vs tackle rate +0.06 (n = 59); Burst Score vs tackle rate +0.16 (n = 53, FDR 0.83); Combine Re-Burst vs every tackling outcome (|ρ| ≤ 0.14); nothing predicts PFR missed tackle % in pooled DB (best 40-yard accel +0.21, FDR 0.71). Bench, hand size, 3-cone and shuttle have too few DBs (n ≈ 15–30) to say anything.

**Answer for DB.** No Combine test translates to DB tackling production after multiple-testing correction. If a coach wants one athletic number, Combine Brakes (peak decel in the DB drill) is the most consistent lean: harder Combine brakers close faster to the tackle spot (ρ +0.27, n = 69, CI excludes 0, FDR 0.46). Keep it a lean.

### 2. DL re-check (DE + DT + NT + OLB, n = 118: 66 Edge, 52 Interior)

**Outcomes and floors.** REG snaps that stood, lined up EDGE or INTERIOR_LINE (49,766 snaps; 20,966 run snaps). Reference: pressure rate, sack rate, Sunday get-off (speed at 1.0 s), ≥20 pass-rush snaps, n = 89 (from `dl_burst.py`). New: median time to pressure (≥5 pressures, n = 70); TFL per snap (≥100 snaps, n = 76); run stops per run snap (tackle or assist on a run that is an offensive failure: < 40% of distance on 1st, < 60% on 2nd, < 100% on 3rd/4th; ≥50 run snaps, n = 78); run tackles at ≤2 yards per run snap (n = 78); run-tackle depth past LOS (tracking, ≥8, n = 74); penetration = yards upfield past the LOS toward the offense's backfield, from the snap to 2.0 s (max and value at 2.0 s; all snaps, run-only and pass-only; ≥50 tracked snaps, n = 86–88). Median DL starts 0.6 yd on his side of the LOS and is 2.25 yd past it at 2.0 s.

**Reliability (SB).** Get-off 0.97, penetration 0.93–0.96, TFL 0.64, run stops 0.58, run-tackle depth 0.54, near-line run tackles 0.48, **time to pressure 0.12** (not a stable player trait in these samples).

**Reference chain reproduced (year-controlled).** Official 10-yard → get-off ρ = −0.80 (n = 72, CI −0.87 to −0.65); 10-yard → pressure −0.47 (n = 72, CI −0.65 to −0.24, FDR 1e-4); get-off → pressure +0.51 (n = 89, CI +0.31 to +0.68). Controlling Sunday get-off, the 10-yard → pressure partial falls to −0.12 (p = 0.31). With year × subtype control, 10-yard → pressure is only −0.25 (FDR 0.20), so part of the pooled 10-yard result is still Edge-vs-Interior composition.

**FDR counts.** Pooled DL 79/252 cells (23 of them production outcomes, the rest get-off / penetration); year × subtype 31/252 (only **one** production cell); Edge 8/246; Interior 27/227.

**Beyond the 10-yard — the strongest new finding is the 3-cone vs pressure.**

| Combine | Outcome | Group | n | ρ | 95% CI | FDR |
|---|---|---|---:|---:|---|---:|
| **3-cone** | **Pressure rate** | DL, year | 34 | **−0.65** | −0.83 to −0.36 | **0.0002** |
| 3-cone | Pressure rate | DL, year × subtype | 34 | −0.57 | −0.81 to −0.19 | **0.006** (only production cell to survive subtype control) |
| 3-cone | Pressure rate | Interior | 16 | −0.60 | −0.91 to 0.00 | 0.096 |
| 3-cone | Pressure rate | Edge | 18 | −0.52 | −0.88 to +0.08 | 0.33 |
| Short shuttle | Pressure rate | DL, year | 35 | −0.59 | −0.81 to −0.25 | 0.001 |

The 3-cone link is not just the 10-yard or weight in disguise: partial ρ controlling the 10-yard = −0.52 (n = 30, p = 0.003), controlling weight = −0.41 (p = 0.015), controlling Sunday get-off = −0.43 (p = 0.011), controlling the official 40 = −0.34 (p = 0.067). Caveat: only 34 of 89 rushers ran the 3-cone (18 Edge, 16 Interior) — players who skip it are not a random subset.

**New outcomes.** TFL rate: Burst Score ρ = +0.43 (n = 54, CI +0.16 to +0.63, FDR 0.006); 20-yard split −0.37 (n = 59, CI −0.57 to −0.10, FDR 0.017); vertical +0.34 (n = 68, FDR 0.017); 10-yard −0.28 (n = 60, FDR 0.089). With subtype control Burst vs TFL is +0.31 (CI +0.02 to +0.55, FDR 0.16), and Burst still holds after controlling weight (partial +0.35, p = 0.010) and get-off (+0.30, p = 0.027). Penetration in the first 2 s: almost every speed / power test and weight correlate strongly (e.g., broad jump vs pass-play penetration +0.79, n = 74; with subtype control +0.57, FDR < 0.001; Interior +0.70, n = 33, FDR 0.002), but penetration is essentially a longer get-off (get-off vs pass-play penetration ρ = +0.93), so it is a movement outcome, not production. Interior Combine top speed vs sack rate +0.48 (n = 33, FDR 0.038).

**Notable nulls.** Run stops: no Combine test survives FDR in any group (best pooled 3-cone −0.39, n = 28, FDR 0.11; Interior arm length +0.37, n = 35, FDR 0.16). The 10-yard does not predict run stops (+0.08, n = 62). Faster DL make slightly *fewer* near-line run tackles (Combine top speed −0.26, n = 61, FDR 0.11) — a pass-rush-vs-run-fit trade-off, not a clean Combine signal. Time to pressure: nothing (and SB 0.12). Bench, arm length, hand size, wingspan, height: no pressure or sack link (e.g., arm length vs pressure −0.06, n = 89; bench vs pressure 0.00, n = 42). Tracked 3-cone / shuttle Brakes and Re-Burst: no FDR cells.

**Answer for DL beyond the 10-yard.** The 3-cone is the best additional Combine test: it predicts pressure rate more strongly than the 10-yard, survives Edge/Interior control (the 10-yard does not), and adds information beyond the 10-yard, weight and Sunday get-off — on a small, self-selected 34-player sample. For a new outcome, the Burst Score is the best Combine predictor of TFL rate.

Outputs: `out/db_tackle_{players,tests,reliability,qc,outcome_n}.csv`, `out/dl_recheck_{players,tests,chain,reliability,qc,outcome_n}.csv`. Tracking caches `out/cache/*.parquet` are gitignored (derived Kaggle tracking). No draft-pick column is in any of these files.

## 11/2026 (America/New_York) — SSOE scouting card expanded to top / bottom 15

Kevin asked to change the per-position results from top 5 to top 15. Figure 4 and the Section 2 tables above now show top 15 and bottom 15 SSOE at WR (n=62) and CB (n=33). Safeties (n=26) are fewer than 30 unique players, so the figure and tables show the full roster once, split at the zero line (11 faster than the 40 predicted, 15 slower). Draft slot and round are not used on the scouting card or in Figure 4. Limited names remain directional only.

Outputs: `out/ssoe_leaderboard.csv`, `out/figs/fig4_ssoe_leaderboard.png`.

## 11/2026 (America/New_York) — Figure 19 re-oriented for coaches

Kevin asked to redo the DL heat map so it reads cleanly for coaches: red always means "better athlete goes with better on-field result," with rows split into Speed & agility vs Power, size & length, and columns split into pass rush vs TFL & run defense. The Spearman values, CIs, p-values and FDR stars are unchanged — only the display signs and layout changed. Redraw with `python3 dl_recheck.py --figure-only`, which reads the saved CSVs and does not rerun the tests.

**Orientation.** Timed drills (official 10-yard, official 40, 3-cone, short shuttle, tracking 10- and 20-yard splits) are sign-flipped so faster = higher. Two outcomes where lower is better are also flipped: time to pressure, and run-tackle depth (shallower / closer to the LOS = better). Jumps, Burst Score, top speed, peak accel, Brakes / Re-Burst, bench, and length measures are shown as-is (higher = more). Weight and height have no assumed "better" direction; red would mean heavier / taller with a better result. The two scatter panels still use raw (unflipped) values; the 3-cone axis is labeled "← faster" so the published ρ = −0.65 still matches the downward slope.

**How to read it now.** The pass-rush block is almost uniformly red for speed, agility, jumps and Burst Score. The TFL & run-defense block is mostly pale, except TFL itself and run-play penetration (a movement outcome, not production). Length measures stay near zero. The headline cells are the same as before, just easier to see: 3-cone vs pressure is now +0.65**, official 10-yard vs pressure +0.47**, Burst Score vs TFL +0.43**.

TFL is grouped with run defense because it is a production outcome that can come from either a pass rush or a run stuff, not because it is a pure run-defense stat. The previous figure is archived as `out/figs/fig19_dl_recheck_v1.png`.

Outputs: `out/figs/fig19_dl_recheck.png`, `out/figs/fig19_dl_recheck_v1.png`.


## 11/2026 (America/New_York) — Robust-testing pass: size control, shrinkage, out-of-sample (DL first, then WR / TE / DB)

Kevin approved rebuilding the pipeline so that size control, shrinkage of noisy rates and leave-one-season-out validation are on by default (new defaults documented in `METRICS.md` §7). Draft slot / pick / round is not used anywhere, including as a control (asserted in code). New code: `robust.py` (module), `dl_robust.py`, `pos_robust.py`, `forest.py`, `robust_report.py`. Figures: `out/figs/fig19_dl_recheck.png` (redone), `out/figs/fig19_dl_recheck_v2_presize.png` (the previous version, kept), `out/figs/fig20_forest_size_controlled.png` (new). Full tables for every test × outcome: `out/dl_robust_tests.csv`, `out/pos_robust_tests.csv`, `out/robust_tables.md`.

**What each number means.** *raw ρ* = plain Spearman. *year+role ρ* = rank partial correlation controlling draft year and Edge/Interior (DL) or CB/S (DB). **size-controlled ρ** = the same plus weight and height (the weight row controls height only and the height row weight only). Rates are shrunk (beta-binomial, toward the role mean, using the player's snaps); *unshrunk ρ* and *snap-weighted ρ* are the sensitivities. CI = 2,000-resample player bootstrap. *perm p* = Freedman–Lane permutation p; *FDR q* = BH over every cell in the group. *Out-of-sample ΔR²* = gain in R² from adding the test to a size-only model, trained on two draft classes and tested on the third (pooled over 2023 / 2024 / 2025; "3/3" = helps in all three held-out classes).

**Label fix.** The "−0.80 / +0.51 get-off" chain was speed in the first second after the snap from tracking, not the NFL/NGS get-off. It is now called **1-sec burst speed**. The NFL/NGS get-off time (`player_get_off`) is a separate row. Size-controlled chain (n; 95% CI): official 10-yard → 1-sec burst speed −0.32 (72; −0.54 to −0.08; was −0.80 with year control only); 1-sec burst speed → pressure rate +0.33 (89; +0.13 to +0.51); official 10-yard → NGS get-off time +0.30 (71; +0.05 to +0.53; slower 10-yard, slower get-off); NGS get-off time → pressure rate −0.34 (88; −0.54 to −0.12).

### 1. DL: the headline numbers got smaller, and none of the athletic tests clears FDR once size is held fixed

273 cells in the pooled DL family. 20 have permutation p < 0.05 (about 14 expected by chance); **5 clear FDR < 0.05 and all five are weight vs a movement outcome** (weight vs 1-sec burst speed −0.53, NGS get-off +0.49, penetration at 2 s −0.45 / −0.46, pass-play penetration −0.59): heavier linemen are slower off the ball, which is a size effect, not a Combine test. No athletic test clears FDR for any production outcome (best FDR q = 0.16, official 40 vs pressure rate; over the five production outcomes only the best q is 0.43). Edge alone: 2 of 267 cells clear (both weight vs movement); Interior alone: 0 of 248.

**Earlier headline cells, before vs after** (old = year control only, unshrunk; new = size-controlled, shrunk):

| Pair | Old ρ (CI, FDR) | New size-controlled ρ (CI) | Unshrunk | perm p | FDR q | Out-of-sample ΔR² | Verdict |
|---|---|---|---:|---:|---:|---|---|
| 3-cone → pressure rate (n = 34) | −0.65 (−0.83 to −0.36, 0.0002) | **−0.31** (−0.67 to +0.13) | −0.43 | 0.106 | 0.75 | +0.050 (p 0.046, 2/3) | not significant after size control |
| Official 10-yard → pressure rate (72) | −0.47 (−0.65 to −0.24, 0.0002) | **−0.25** (−0.45 to −0.01) | −0.16 | 0.047 | 0.64 | +0.047 (p 0.015, 3/3) | lean |
| Official 40 → pressure rate (72) | −0.47 (−0.66 to −0.23, 0.0002) | **−0.35** (−0.54 to −0.11) | −0.25 | 0.004 | 0.16 | +0.056 (p 0.008, 3/3) | lean (best DL production cell) |
| Broad jump → pressure rate (76) | +0.45 (+0.21 to +0.64, 0.0003) | **+0.27** (+0.03 to +0.49) | +0.17 | 0.026 | 0.44 | +0.056 (p 0.010, 2/3) | lean |
| Burst Score → TFL per snap (54) | +0.43 (+0.16 to +0.63, 0.006) | **+0.32** (+0.03 to +0.55) | +0.31 | 0.027 | 0.44 | +0.069 (p 0.009, 3/3) | lean |
| Short shuttle → pressure rate (35) | −0.59 (−0.81 to −0.25, 0.001) | **−0.29** (−0.64 to +0.16) | −0.40 | 0.115 | 0.75 | −0.043 (p 0.83, 2/3) | not significant, does not help out of sample |

**Read.** The direction of every pass-rush link survives (faster, more explosive, more pressure) and the pooled sign holds in both Edge and Interior for all four lean production cells (CIs inside each subtype include zero). But a quarter to a half of each earlier correlation was body size and Edge-vs-Interior composition: the 10-yard correlation with pressure roughly halved (−0.47 to −0.25), the 40's fell from −0.47 to −0.35, the 3-cone's fell to −0.31 with a CI that now includes zero (n = 34, five-parameter fit), and nothing survives multiple-testing correction. The 3-cone is still the best *candidate* on the unshrunk rate (−0.43, CI −0.71 to −0.05, perm p 0.02) and it improves out-of-sample prediction in two of three classes, but it is a lean on 34 self-selected players, not a finding. The 3-cone story should be told as "most promising, unproven".

**Does shrinkage change things?** Modestly. Across 105 scored DL cells the shrunk and unshrunk size-controlled ρ correlate 0.92, the median change is 0.04, 11 near-zero cells flip sign, and mean |ρ| goes from 0.128 to 0.137. It matters for specific cells: 40 → pressure −0.25 unshrunk vs −0.35 shrunk; 10-yard → pressure −0.16 vs −0.25; 3-cone → pressure −0.43 vs −0.31. Prior strength: pressure-rate prior is worth about 130 snaps for Edge and 170 for Interior (median rusher has 230 / 146 snaps), so low-snap rushers are pulled hard toward their role mean. Snap-weighted versions agree on direction (mean |ρ| 0.18). Stable conclusions do not depend on this choice; the 3-cone and 40 magnitudes do.

**Out of sample.** Of 79 scored DL production cells (excluding weight and height), 32 have positive incremental out-of-sample R² and 13 of those have permutation p < 0.05, but the gains are small (best +0.09 R² on top of a size-only model; typical +0.04). Adding the official 40 to a size-only model improves pressure-rate prediction in all three held-out classes (+0.056); for pressure rate, vertical, bench, arm length, hand size, wingspan and height never help (ΔR² ≤ 0.00 in each case). Run stops: no test helps out of sample in any meaningful way (median ΔR² −0.01, best +0.06 for tracked 3-cone Brakes at n = 31, p 0.065), and none of the 30 scored run-stop cells has permutation p below 0.10 (best: Combine top speed vs near-line run tackles −0.22, p 0.108).

**Nulls that hold.** Arm length, wingspan, hand size and height vs pressure / sack / TFL / run stops: all |size-controlled ρ| ≤ 0.16 (largest: wingspan vs TFL +0.16), every permutation p ≥ 0.18, CIs span zero, out-of-sample ΔR² ≤ 0.04. Bench reps (n = 42): +0.17, CI −0.21 to +0.56, no gain. Tracked 3-cone / shuttle Brakes and Re-Burst: no cell. Time to pressure: nothing stable (split-half reliability 0.12).

#### DL · pressure rate (shrunk), all tests

| Combine test | n | raw ρ | year+role ρ | size-controlled ρ | 95% CI | unshrunk ρ | snap-wtd ρ | perm p | FDR q | out-of-sample ΔR² (perm p, classes +) | verdict |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| Official 10-yard | 72 | -0.70 | -0.34 | **-0.25** | -0.45 to -0.01 | -0.16 | -0.27 | 0.047 | 0.64 | +0.047 (p 0.015, 3/3) | lean |
| Official 40 | 72 | -0.74 | -0.41 | **-0.35** | -0.54 to -0.11 | -0.25 | -0.50 | 0.004 | 0.16 | +0.056 (p 0.008, 3/3) | lean |
| Vertical | 78 | +0.54 | +0.25 | **+0.14** | -0.09 to +0.35 | +0.10 | +0.27 | 0.227 | 0.81 | -0.062 (p 0.980, 0/3) |  |
| Broad jump | 76 | +0.71 | +0.33 | **+0.27** | +0.03 to +0.49 | +0.17 | +0.37 | 0.026 | 0.44 | +0.056 (p 0.010, 2/3) | lean |
| 3-cone | 34 | -0.73 | -0.48 | **-0.31** | -0.67 to +0.13 | -0.43 | -0.26 | 0.106 | 0.75 | +0.050 (p 0.046, 2/3) |  |
| Short shuttle | 35 | -0.72 | -0.38 | **-0.29** | -0.64 to +0.16 | -0.40 | -0.49 | 0.115 | 0.75 | -0.043 (p 0.831, 2/3) |  |
| Bench reps | 42 | -0.15 | +0.12 | **+0.17** | -0.21 to +0.56 | +0.24 | +0.13 | 0.303 | 0.84 | -0.066 (p 0.910, 0/3) |  |
| Arm length | 89 | -0.02 | -0.10 | **-0.08** | -0.30 to +0.16 | -0.07 | -0.22 | 0.490 | 0.90 | -0.018 (p 0.763, 0/3) |  |
| Hand size | 89 | -0.25 | -0.09 | **-0.04** | -0.28 to +0.19 | -0.05 | +0.02 | 0.688 | 0.92 | +0.000 (p 0.271, 1/3) |  |
| Wingspan | 89 | -0.11 | -0.07 | **-0.04** | -0.27 to +0.18 | -0.05 | -0.09 | 0.687 | 0.92 | -0.093 (p 1.000, 0/3) |  |
| Weight | 89 | -0.71 | -0.23 | **-0.20** | -0.39 to -0.00 | -0.15 | -0.29 | 0.059 | 0.64 | +0.014 (p 0.068, 2/3) | size |
| Height | 89 | -0.07 | -0.13 | **-0.08** | -0.32 to +0.16 | -0.07 | -0.12 | 0.455 | 0.86 | -0.042 (p 0.959, 0/3) | size |
| 20-yard split (tracking) | 71 | -0.34 | -0.19 | **-0.12** | -0.39 to +0.15 | -0.09 | -0.10 | 0.324 | 0.85 | +0.042 (p 0.013, 3/3) |  |
| 10-yard split (tracking) | 71 | -0.16 | -0.12 | **-0.08** | -0.36 to +0.19 | -0.06 | -0.06 | 0.530 | 0.91 | +0.021 (p 0.062, 3/3) |  |
| Combine top speed | 71 | +0.70 | +0.34 | **+0.25** | -0.01 to +0.48 | +0.14 | +0.41 | 0.044 | 0.64 | +0.008 (p 0.172, 2/3) |  |
| 40-yard peak accel | 71 | +0.37 | +0.07 | **+0.02** | -0.22 to +0.27 | +0.03 | +0.02 | 0.898 | 0.94 | -0.003 (p 0.389, 2/3) |  |
| 3-cone Brakes (tracked peak decel) | 37 | +0.27 | +0.17 | **+0.24** | -0.16 to +0.56 | +0.34 | +0.60 | 0.185 | 0.81 | -0.087 (p 0.964, 0/3) |  |
| 3-cone Re-Burst (tracked peak accel) | 37 | +0.10 | -0.02 | **+0.11** | -0.26 to +0.50 | +0.29 | +0.21 | 0.568 | 0.91 | +0.012 (p 0.165, 2/3) |  |
| Shuttle Brakes (tracked peak decel) | 28 | +0.44 | +0.27 | **+0.18** | -0.36 to +0.57 | +0.32 | +0.05 | 0.399 | 0.86 | +0.014 (p 0.220, 2/3) | small n |
| Shuttle Re-Burst (tracked peak accel) | 28 | +0.50 | +0.05 | **-0.10** | -0.57 to +0.50 | +0.01 | -0.29 | 0.634 | 0.92 | +0.017 (p 0.203, 2/3) | small n |
| Burst Score (0-100) | 64 | +0.62 | +0.31 | **+0.22** | -0.03 to +0.46 | +0.14 | +0.28 | 0.083 | 0.71 | +0.043 (p 0.031, 3/3) |  |

(Sack, TFL, run-stop, 1-sec burst speed, NGS get-off tables: `out/robust_tables.md`.)

### 2. WR: Sunday Speed from the 40 holds up; the new lean is vertical and Burst Score → separation on break routes

Outcomes: tracking route separation (mean over routes, ≥30 routes), Sunday Speed and SSOE (official sample). 68 cells; FDR is BH over those 68. Global BH over all 521 pooled cells is noted as "global q".

- **Combine top speed → Sunday Speed +0.58** (n = 62; CI +0.37 to +0.74; q 0.003; ΔR² +0.25, 3/3) and **official 40 → Sunday Speed −0.52** (n = 63; CI −0.68 to −0.30; q 0.003; ΔR² +0.20, 3/3) survive every check. Obvious but real, and it survives size control. These are the translation-rate result again.
- **Vertical → separation on break routes +0.38** (n = 61; CI +0.13 to +0.58; perm p 0.003; q 0.039; global q 0.15; ΔR² +0.14, 3/3) and **Burst Score → separation on break routes +0.39** (n = 57; CI +0.11 to +0.62; q 0.039; global q 0.15; ΔR² +0.09, 3/3) pass every check inside the WR family. Weighting by routes shrinks them (+0.21, +0.30) but keeps the sign. They fail a global BH across all groups and neither was pre-declared, so this is the strongest *new* lead, not a settled result. The same two tests are lean for separation on all routes (vertical +0.30, Burst +0.37).
- **Weight → SSOE −0.38** (n = 62; q 0.039; ΔR² +0.15, 3/3): heavier receivers run slower on Sunday than their 40 predicts. Weight is a size control, not an athletic test, so it is a role/size note for the scouting card, not a Combine-test finding.
- **Size explained the "long arms hurt separation" pattern.** Arm length, hand size and wingspan vs all-route separation are −0.32 to −0.35 unadjusted and +0.02 to +0.13 once weight and height are held fixed.
- The 3-cone (n = 23) is not scored (small n): −0.25 vs break-route separation, CI −0.66 to +0.32.
- Official 10-yard and 40 do **not** predict separation after size control (|ρ| ≤ 0.19 on all routes and break routes). The tracking 10- and 20-yard splits show a weak lean on break routes (−0.29 / −0.28, CIs touching zero, FDR q 0.21 / 0.22), nothing on all routes.

### 3. TE: nothing can be claimed

n is 18–24 for most tests and 7–11 for 3-cone, shuttle and bench. All tests are labelled small n and not scored. For the record, Combine top speed vs separation is −0.51 (n = 21; CI −0.79 to +0.07) and weight vs separation +0.37 (n = 24; CI −0.12 to +0.77): CIs span zero. Not for the writeup beyond "too few TEs have tracked Combine data and game routes".

### 4. DB (CB + S combined, CB/S role control): clean null

152 cells, 0 clear FDR; 9 have permutation p < 0.05 (7–8 expected by chance) and 3 pass the lean rules. Tackle rate (shrunk): official 40 −0.05 (n = 59; CI −0.32 to +0.22), 20-yard split +0.05, Burst Score +0.17, Combine Brakes −0.16, none with a meaningful out-of-sample gain (ΔR² ≤ 0.003). The three lean cells are not credible: broad jump → PFR yards per target allowed has the *wrong* sign (longer jump, more yards allowed, +0.35), arm length → Sunday Speed (−0.29) and Combine Brakes → closing rate (+0.25, the same lean as before; CI +0.01 to +0.45, FDR q 0.79, tiny out-of-sample gain +0.02, p 0.09). Height → tackle rate is −0.31 (size variable). **Answer for DB: no Combine test translates to tackling or coverage proxies once size and role are held fixed.**

### 5. Figures

`fig19_dl_recheck.png`: the DL heat map with size-controlled ρ, same orientation as before (timed drills flipped; "Speed & agility" vs "Power, size & length" row blocks; pass rush vs TFL & run defense column blocks). New marks: ◆ = lean, * = permutation p < 0.05 only, ** = FDR < 0.05 (only the weight row). New columns: 1-sec burst speed (relabelled) and NFL/NGS get-off time. `fig20_forest_size_controlled.png`: six panels (DL pressure, DL TFL, WR separation all / break routes, TE separation, DB tackle rate), each test with the unadjusted (grey) and size-controlled (colour) estimates and 95% CIs, oriented so right = better athlete goes with higher outcome.

### 6. What survives and what dies

- **Survives every check:** WR Combine top speed and official 40 → Sunday Speed; WR vertical and Burst Score → break-route separation (within the WR family only; not under global BH); weight → movement outcomes at DL (size).
- **Lean (nominal, direction consistent, out-of-sample support, FDR not cleared):** DL official 40, 10-yard and broad jump → pressure rate; DL Burst Score → TFL; DL 40 / 10-yard / jumps / Burst → 1-sec burst speed and NGS get-off (movement, not production).
- **Dies or weakens to not significant:** DL 3-cone and short shuttle → pressure (CI includes 0 after size control); DL run stops; DL length measures; DB everything; TE (underpowered).

**Caveats.** (1) Every correlation here is among players who made rosters and have tracked snaps; players who skipped a drill are not random (only 34 of 89 rushers ran the 3-cone). (2) With 34 players and 5–6 fitted terms, CIs are wide; a CI including zero is "can't tell", not "zero effect". (3) FDR family sizes differ by group. (4) Leave-one-class-out uses three classes of 10–30 players each; ΔR² values of +0.05 are small and noisy. (5) Shrinkage priors are fit per role on the same data (not refit inside each bootstrap), so CIs slightly understate uncertainty on the rate outcomes. (6) Older logs above that mention draft-pick controls (RESULTS_LOG 11/10–11/11 sections, `dl_burst.py`, `gameplay_success.py`, `multi_test_models.py`, `combine_gems.py` outputs) predate the no-draft-slot rule; their `out/*_players.csv` files still carry pick columns. They were not changed here.

---

## 11/2026 — Draft slot removed everywhere (Part A)

**Rule (Kevin):** draft slot, pick and round are never used, not as a control, a baseline, a filter, a label or a column. Draft **year** stays as a control.

**Changed:** `build_dataset.py`, `ssoe.py`, `gameplay_success.py`, `dl_burst.py`, `multi_test_models.py`, `athletic_comps.py`, `explore.py` now control for draft year only and no longer write pick, round or UDFA columns. Pick/round columns are gone from `out/sunday_speed_players.*`, `dl_burst_players.csv`, `gameplay_success_players.csv`, `dl_players_named.csv`, `multi_test_players.csv`, `athletic_comps*.csv` (historical-comp pick columns too) and `DL_PLAYERS.md`. `out/pfr_columns.csv` no longer lists the `draft_round`/`draft_pick` columns of the public players file. `external/draft_picks.csv` is still read, only for the career Approximate Value / Pro Bowl / All-Pro columns and the PFR ID join, never for slot. METRICS.md §6 rewritten to year-only.

**Retired (cannot be reproduced without draft slot, files removed):** `combine_gems.py` (“outplayed his draft slot”; `COMBINE_GEMS.md`, `out/combine_gems*.csv`, `fig8_combine_gems.png`) and `cb_deep_dive.py` (Finding A “speed tax beyond draft slot”; Finding B gauntlet-vs-Sunday-Speed went with it; `CB_DEEP_DIVE.md`, `out/cb_deep_dive_*`, `cb_speed_tax.png`, `cb_gauntlet.png`). The scripts are stubs that exit with a message. The gauntlet-vs-Sunday-Speed check is not rerun; if wanted it can be rebuilt year-only with `robust.py`.

**Reruns:** all from raw data still on the box (`build_dataset` → `ssoe`, `gameplay_success`, `dl_burst` → `multi_test_models`, `athletic_comps`). Nothing is marked stale. `dl_robust`, `pos_robust`, fig 19 and fig 20 never read a slot column, so they are unchanged. Other docs (README, PHASE2_RESULTS, DATA_NOTES, STRATEGY notice) updated; the older entries above in this log describe pick-controlled numbers and are superseded by this section.

**Headline numbers that changed:**

| Result | Before (year + log pick) | Now (year only) |
|---|---|---|
| CB “speed tax”, Combine top speed vs start rate (n = 44) | ρ −0.45, Holm p = 0.006 (“beyond draft slot”) | ρ −0.12, Holm p = 0.94. **It was a draft-slot artifact.** n = 33 official sample: −0.39 → −0.14 |
| S / WR speed tax | −0.05 / −0.10 | +0.17 / +0.07 (null) |
| CB Combine speed vs start rate (gameplay_success companion) | −0.41, CI −0.70 to −0.05 | −0.18, CI −0.49 to +0.23 |
| DL 10-yard → pressure, All DL (n = 72) | ρ −0.45 (pick+year), CI −0.62 to −0.19, Holm 0.0005 | **−0.47**, CI −0.65 to −0.24, Holm 0.00016 |
| DL 10-yard → sack, All DL | −0.31, CI −0.53 to −0.07, Holm 0.039 | **−0.37**, CI −0.57 to −0.11, Holm 0.0066 (stronger) |
| DL Edge → pressure | −0.24, Holm 0.56 | −0.36, Holm 0.099 (CI −0.63 to +0.00) |
| DL Interior → sack | −0.25, Holm 0.56 | −0.35, Holm 0.135 |
| DL 10-yard → speed at 1.0s (get-off), All / Edge / Interior | −0.79 / −0.61 / −0.31 | −0.80 / −0.57 / −0.41 |
| DL direct 10-yard → pressure after get-off | −0.08, p = 0.49 | −0.12, p = 0.31 (mediation conclusion unchanged) |
| WR Combine top speed → Sunday Speed partial | +0.62 | +0.63 (headline unchanged; official 40 −0.57 → −0.60) |
| CB / S Combine top speed → Sunday Speed partial | +0.05 / +0.15 | +0.24 (p = 0.18) / +0.16 (p = 0.44), still null |
| Athletic comps vs gameplay, CB | −0.37, Holm 0.116 | −0.37, Holm 0.109 (none significant) |
| Multi-test models (`multi_test_models.py`) | beat a “pick + year” baseline for TE and CB only | baseline is now year only and scores **below chance** (CV AUC 0.26–0.40), so “beats baseline” deltas are inflated (+0.08 to +0.38). Read the absolute AUCs instead: WR 0.48, TE 0.63, CB 0.66, S 0.56 (L2 logistic) |

Unchanged to two decimals: WR yards per route / deep route / target share outcomes (|Δρ| ≤ 0.03) and no Holm significance flag flipped in `phase2_tests`, `gameplay_success_tests` or `ssoe_tests`.

---

## 11/2026 — WR break-route lead re-test (Part B; pre-declared in METRICS.md §8 before any number was computed)

**Design.** `wr_route_lead.py`: regular-season WR plays, `route_ran` × `team_coverage_man_zone` from the provided data (no external source needed), separation minus the route × coverage mean, empirical-Bayes shrunk per player (unshrunk and route-weighted as sensitivity), ≥20 routes per split (≥10 screens). robust.py defaults for every cell (size control, bootstrap CI, 10,000 Freedman–Lane permutations, leave-one-class-out ΔR², BH-FDR) plus formal paired contrasts (paired bootstrap CI and within-player swap permutation, BH over the 5 contrasts). Outputs: `out/wr_route_lead_{cells,contrasts,players,plays_summary}.csv`, **fig 21** `out/figs/fig21_wr_route_lead.png`.

**Caveats first.** Same 2023–25 sample that produced the lead, so this is a re-test, not an independent replication. 3-cone and short shuttle exist for only 21–30 WRs, so H1 and H3 are badly underpowered (paired-contrast CI half-width about 0.4–0.6). Data have no separate COMEBACK or DIG label (HITCH holds curls/hitches/comebacks, IN holds digs). Man vs zone is the team-level label on the play.

| Hypothesis | Key numbers (size-controlled rank partial ρ; oriented so + = better test, more separation) | Verdict |
|---|---|---|
| **H1** 3-cone, shuttle matter more on break than vertical routes | 3-cone: break +0.02 (n = 23), vertical +0.23 (n = 22), diff −0.24 (CI −0.77 to +0.39, swap p 0.33). Shuttle: break −0.17, vertical −0.06 (n = 27), diff −0.11 (CI −0.59 to +0.54, p 0.63) | **Dies.** Wrong sign or null; underpowered to rule out a moderate effect |
| **H2** Vertical jump and Burst Score → break-route separation | Vertical **+0.34** (n = 58, CI +0.03 to +0.57, perm p 0.014, BH q 0.185, ΔR² +0.13, p 0.002). Burst **+0.31** (n = 54, CI +0.03 to +0.54, p 0.026, q 0.185, ΔR² +0.11, p 0.009). On vertical routes: +0.08 (n = 61) and +0.17 (n = 56), both null | **LEAN, not SURVIVES.** Direction and out-of-sample check hold, FDR does not clear in a 14-cell family. Specificity to break routes is **not** shown: break − vertical is +0.23 (CI −0.09 to +0.55, p 0.14) for vertical jump and +0.08 (CI −0.22 to +0.42) for Burst |
| **H3** Quickness matters more vs man than zone | Official 10-yard: man +0.25 (n = 59, p 0.066), zone +0.11 (n = 66), diff +0.15 (CI −0.13 to +0.41, swap p 0.27, q 0.54). 3-cone: man −0.24 (n = 21), zone +0.38 (n = 24), diff −0.46 (CI −0.99 to +0.07, swap p 0.006, q 0.03). Shuttle: man −0.33, zone −0.05, diff −0.04 (p 0.78) | **Dies.** The only direction-consistent contrast (10-yard) is not distinguishable from zero. The 3-cone contrast points the **opposite** way, with n = 21 and a bootstrap CI that includes 0, so we do not call it REVERSED and do not trust it |
| **S1** (secondary) weight cost on screens and crossers | Weight → crossers −0.29 (n = 49, p 0.051, q 0.069); screens +0.06 (n = 27, null). Same cost on break routes −0.25 (n = 66) and vertical routes −0.28 (n = 69, p 0.022). Crosser − vertical diff −0.02 (CI −0.35 to +0.31) | Heavier receivers have lower separation on **every** route type (about −0.25 to −0.29, LEAN-sized, q ≈ 0.07); no screen/crosser-specific cost |

Sensitivity: man vs zone on break routes only shows no contrast either (diffs +0.10, +0.01, +0.02, all CIs span 0). The older lean (vertical +0.38 and Burst +0.39 on a broader break family, q 0.039 within WR) was an easier family; with the narrower pre-declared break family and a 14-cell correction it is LEAN, not SURVIVES.

---

## 11/2026 — "What translates and what doesn't" scorecard, fig 22, notebook restructure **(Raw-ρ numbers in this section were corrected the same day; see the correction section below.)**

**Built.** `scorecard.py` reads only the saved robust outputs (`dl_robust_tests`, `pos_robust_tests`, `wr_route_lead_cells`) and writes `out/scorecard.csv` (card, 4–6 rows per group plus DL Edge/Interior breakout rows), `out/scorecard_full.csv` (every group × test × primary outcome, 10 tests), `out/scorecard_weight.csv` and `out/scorecard.md`. Verdict rules and the row-selection rule were written in METRICS.md §9 before building. Nothing was recomputed or invented. WR break-route separation uses the pre-declared §8 re-test (vertical jump +0.34 LEANS), which supersedes the §7 break family (+0.38, q 0.039).

**Card result.** TRANSLATES: WR 40 → deep-route game speed (+0.52, n 63) and WR tracked top speed → deep-route game speed (+0.58, n 62). Both q 0.003, held-out 3/3. LEANS: WR vertical → break-route separation (+0.34, q 0.185), WR Burst Score → all-route separation (+0.37, q 0.057), DL 40 → pressure (+0.35, raw +0.74), DL 10-yard → get-off speed (+0.32, raw +0.81), DL Burst Score → TFL (+0.32), DB drill braking → closing speed (+0.25), DB 40 → yards allowed per target (−0.35, the wrong way, q 0.75). SIZE, NOT SPEED: DL 40 → sack rate (raw +0.72 → +0.23). TE: every row TOO FEW (n ≤ 21). DB: no outcome translates.

**Figure.** `out/figs/fig22_scorecard.png` (`scorecard_fig.py`). Recommended headline: fig 22 (answers the question in five seconds, honest about size via the raw-vs-controlled diamond). Fig 20 is the supporting methods figure (full grid, dense).

**Notebook.** `notebook/bdb2027_writeup.ipynb` restructured into the 8-section scorecard outline (draft prose 1,363 words, caps total under 2,000), built by `notebook/build_writeup_notebook.py`; the old skeleton is `notebook/bdb2027_writeup_v1_skeleton_backup.ipynb`. Plan: 5 figures (fig 1, 20, 22, 21, 19) + 2 tables = 7 of the 9 allowed. Code cells load saved CSVs only, include the explicit Combine-tracking → regular-season gate (PASS), and expect `out/` to be attached as a Kaggle dataset. Also removed an unused `UDFA_PICK` constant from `ssoe.py`.

## 11/2026 — CORRECTION: scorecard "raw ρ" redefined as year-controlled only

**Problem.** In the first scorecard build (commit 188c068) the DL raw ρ looked inflated against earlier reports (40 → pressure +0.74 vs the earlier year-controlled 0.47; 40 → sack +0.72 vs 0.37; Burst → TFL +0.64 vs +0.43; 10-yard → get-off +0.81 vs 0.80, which was fine).

**Cause.** The card took `rho_raw` from the robust tables. That is a plain Spearman on the **pooled Edge + Interior sample against the empirical-Bayes-shrunk outcome**, with no year or role control. The shrinkage prior is fit separately per subtype, so the shrunk rates carry the Edge-vs-Interior gap and have compressed within-role spread, which inflates a pooled correlation. The earlier numbers were year-controlled Spearman on the as-reported rates (`dl_burst.py` recipe). Nothing else in the pipeline was wrong; size-controlled ρ, CIs, p, q and out-of-sample columns are unchanged.

**Fix.** "Raw" now means the year-controlled Spearman (both sides demeaned within draft year) on the as-reported (unshrunk) outcome, with a 2,000-resample player-level bootstrap CI. The old plain value is kept as `rho_unadjusted_pooled_shrunk` in `out/scorecard_full.csv`. Thresholds, selection rule and the size-controlled model are unchanged (METRICS §9). Fig 20's hollow markers were the same plain pooled Spearman and are redrawn the same way; fig 22 regenerated. The reproduction check matches earlier reports: 10-yard → pressure +0.474 (earlier −0.474), 10-yard → sack +0.371 (−0.371), Burst → TFL +0.426 (earlier +0.43).

| DL pooled, oriented | First build raw | Corrected raw (year-controlled) | Size-controlled | Share lost to size/role (new) | Verdict |
|---|---:|---:|---:|---:|---|
| 40 → pressure (n 72) | +0.74 | **+0.47** | +0.35 | 25% | LEANS (unchanged) |
| 40 → sack (n 72) | +0.72 | **+0.37** | +0.23 | 38% | SIZE, NOT SPEED → **DOESN'T TRANSLATE** |
| Burst → TFL (n 54) | +0.64 | **+0.43** | +0.32 | 26% | LEANS (unchanged) |
| 10-yard → get-off (n 72) | +0.81 | **+0.80** | +0.32 | 60% | LEANS (unchanged) |

**Verdict impact.** On the card, one change: DL 40 → sack rate goes from SIZE, NOT SPEED to DOESN'T TRANSLATE (size-controlled +0.23 is 62% of raw, not ≤ half; CI −0.04 to +0.48, perm p 0.060). The card no longer carries any SIZE, NOT SPEED row. In the full grid 14 of 208 rows change, all SIZE, NOT SPEED → DOESN'T TRANSLATE (13) or LEANS (1, DL top speed → pressure); 15 SIZE, NOT SPEED rows remain, all DL, six of them against get-off speed (raw +0.66 to +0.77 → +0.06 to +0.20). The "about half is body size" hook for pressure no longer holds (about a quarter). In pooled DL and DB the controlled model also holds role fixed, so a collapse can be size or role; the rule text says so.

**Caveat on the stale numbers.** The statements "raw +0.74", "raw +0.72" and "raw +0.81" in the first scorecard section above, in the first uploaded fig 22 and scorecard Google Doc, and in the first notebook draft are superseded by this table.

## 11/2026 — Coach dashboard v2 (scorecard-based) and Drive hygiene

- Dashboard v2 replaces v1 in the same Page: tabs WR / TE / DB / DL (DL has an edge vs interior toggle), every scorecard cell with its verdict badge, size-controlled ρ with 95% CI, n, raw ρ and the coach line; a weight "hidden variable" callout per group; and a scout entry tool (within-group percentiles vs the 2023–25 sample, size-adjusted predictions for TRANSLATES and LEANS cells only with a confidence label, nearest athletic comps by year-only Combine profile, and a "don't overweight this" note on every test that doesn't translate).
- All embedded numbers come from `dashboard_export.py` (reads `out/scorecard.csv`, `scorecard_full.csv`, `scorecard_weight.csv`, the robust player tables and the public nflverse combine release). It writes `out/dashboard_data.json` and `out/dashboard_data.ts.txt` (the literals pasted into the Page source). A guard asserts no draft slot, pick or round column enters the export.
- Predictions: one OLS per TRANSLATES/LEANS cell, result ~ test + weight + height + role + draft-year dummies, year effects at the sample mean, 80% range = ±1.28 residual SD. Percentiles use 11-point quantile tables. Comps: nearest 5 by RMS z-distance on 40, vertical, broad, 3-cone, shuttle, height, weight (≥3 shared), pool = 64 most recent historical Combine athletes per group with ≥6 of 7 measurements.
- Only DB 40 and broad jump → yards allowed are LEANS with a negative sign (wrong way); the page labels them DO NOT USE.
- Drive: superseded scorecard figures/CSV/notebook, pre-fix fig 19/20, retired-analysis figures (combine_gems, cb_deep_dive, fig8, cb_speed_tax, cb_gauntlet, fig 1/4/5/6/7/9) renamed with a "SUPERSEDED – " prefix. Nothing deleted. A dated 11/2026 correction section was appended to the Results Log Google Doc.

## 11/2026 — Athletic comps dropped (Kevin, 11/19/2026)

Athletic comps (KNN player comparisons) are removed from the project: `athletic_comps.py` and `out/athletic_comps*.csv` deleted, the comps section and bundled comps data removed from the coach dashboard and `dashboard_export.py`, README and attribution mentions removed. The decision is recorded in METRICS.md §10. No scorecard, verdict, percentile or prediction depended on comps, so no result changes. Earlier entries in this log that mention comps are historical and superseded.

## 11/2026 (11/19/2026): statistical audit of p-values, q-values, CIs and prediction ranges

Trigger: Kevin, "those p values and margins seem suspect". Method and full findings are in METRICS.md §11; `audit_stats.py` -> `out/audit_stats.csv`, `out/audit_prediction_coverage.csv`.

**Wrong or misleading displayed numbers, old vs new**

| Item | Old | New | Cause |
|---|---|---|---|
| 80% prediction range, DL pressure rate (10-yd, 40, broad jump) | ±2.0 to 2.3 pts at the typical player | ±3.9 to 4.2 pts | model fit on the shrunk rate (SD ~0.018 vs 0.032 as reported); old range covered ~50% of real rates |
| 80% prediction range, WR break-route separation (vertical) | ±0.154 yd | ±0.305 yd | same: shrunk-scale fit |
| 80% range, the other 6 models | ±1.28 SD | +2% to 3% wider at the typical player, wider still off-center | normal quantile and no estimation variance; now t quantile and leverage term |
| "Typical player" and percentiles of predictions, pressure rate / break route | 7.95% median / shrunk quantiles | 7.22% median / as-reported quantiles | same |
| Permutation p of the two WR TRANSLATES cells | printed 0.000 (dashboard 0.0) | <0.001 (floor 0.0001) | rounding of a bounded permutation p |
| q of the same cells and weight rows | printed 0.00 | <0.01 | rounding |
| CI shown for n = 12 and 14 (Interior short shuttle -> run stops; DB 3-cone -> yards allowed) | -1.00 to +1.00 | hidden (n < 15) | bootstrap collapses |
| Raw (year-only) ρ for rate outcomes, pooled DL e.g. 40 -> sack rate | +0.37 (as-reported rate) | +0.72 (same outcome as size-controlled) | SIZE test compared as-reported raw with shrunk size-controlled |
| Raw (year-only) ρ, DB tackle / TFL weight rows | +0.23 / +0.06 | +0.35 / +0.09 | same |
| DB weight callout "heavier DBs tend to post worse results" | stated as fact (q 0.90) | "not established" unless q < 0.05 and CI excludes 0 | callout ignored its own q |

**Verdicts that changed (12).** To SIZE, NOT SPEED: DL pooled 10-yd -> sack, 40 -> sack, vertical -> sack, 3-cone -> sack, shuttle -> sack, Burst -> sack, 10-yd -> TFL, 40 -> TFL, broad jump -> TFL, top speed -> TFL (from DOESN'T TRANSLATE) and top speed -> pressure (from LEANS). DL Interior top speed -> TFL went back to DOESN'T TRANSLATE. TRANSLATES (2 WR rows) unchanged.

**Fine as published.** n in all 208 rows; size-controlled ρ; permutation p (two-sided, matches an independent 20,000-shuffle run and the analytic t p); BH q (per-group families, monotone, q ≥ p); bootstrap CIs (player-level, refit, 2,000 resamples, contain the point estimate, agree with BCa and Fisher-z intervals except six borderline rows).

**Multiple-testing flags.** 28 of 164 cells with n ≥ 25 reach p < 0.05 (about 8 by chance); only the two WR Sunday-Speed cells clear q < 0.05 under any family choice. All 26 LEANS rows are nominal leads (smallest whole-grid q 0.19).

## 11/2026 (11/19/2026): reframe to "The Combine works, but read it right"; power and MDE added
Kevin approved the reframe. (1) Verdict "DOESN'T TRANSLATE" renamed "NOT DETECTED (low power)" (same rule; METRICS §9 note). (2) Every scorecard row now has `mde80`, `mde80_bh`, `alpha_bh`, `power_rho03`, `power_rho03_bh` (Fisher-z, rank variance factor 1.06; simulation check 77% to 82% power at the MDE; METRICS §12). Medians, n 25+ rows: receivers n 62 MDE 0.37 (0.51 under BH); DL all n 64 0.37 (0.56); edge n 38 0.48 (0.69); interior n 33 0.51 (0.73); DB n 59 0.38 (0.56); TE about n 20 about 0.66. Power at a true rho of 0.30: 61% WR, 61% DL, 57% DB before correction; 18%, 7%, 7% after. (3) Writeup rebuilt as five findings (WR confirmed; DL mostly through size; consistent leads with honest q; DB weak guide, not detected; weight), 1,832 words, 7 figures + 1 table, GATE PASS. No verdict changed; no numbers changed.

---

## 11/2026 (America/New_York) — Subgroup prelim: safeties vs corners, edge rushers vs interior linemen (new private notebook)

Branch `subgroups`. Private Kaggle notebook `kevinpolymath/bdb2027-subgroups-prelim` v1, COMPLETE (competition data only). Main entry, public notebook and `bdb2027-outputs` untouched. Full summary: `subgroups/SUBGROUPS_PRELIM.md`.

- Sample (players / core n / smallest detectable ρ): S 53 / 26 / 0.58; CB 60 / 32 / 0.52; EDGE 66 / 38 / 0.48; IDL 52 / 33 / 0.51. Subgroup gaps need about 0.62–0.71 to be detected.
- 198 subgroup cells: 0 TRANSLATES, 16 LEAD, 4 SIZE, NOT SPEED, 139 NOT DETECTED (low power), 39 TOO FEW TO TELL. 99 interaction tests: 0 real differences, 3 LEAD, 75 NOT DETECTED (low power), 21 TOO FEW TO TELL.
- Leads: EDGE get-off ← official 10-yard (+0.46, q 0.14, held-out 3/3) and broad (+0.42); IDL sacks ← tracked top speed (+0.45, q 0.29, held-out 3/3) but not EDGE (−0.08; gap p 0.03, q 0.38); pooled line dilutes get-off (broad: +0.42 / +0.39 / pooled +0.19); S vs CB peak acceleration → tackles (+0.47 vs −0.29; gap p 0.003, q 0.10; safety link alone fails held-out); coverage speed same for S and CB.
