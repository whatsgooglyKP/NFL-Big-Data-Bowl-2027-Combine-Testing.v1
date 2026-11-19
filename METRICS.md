# Official metric definitions — Sunday Speed

Frozen for the NFL Big Data Bowl 2027 submission. These are the numbers a coach can read off a scouting card. If a later robustness check uses a different window, play floor, or regression, it is a sensitivity test — it does not replace this page.

**Units.** Source tracking is in yards per second. Everything we show a coach is in miles per hour:

\[
1\ \text{yd/s} = 2.0455\ \text{mph}.
\]

**Who is in the official sample.** A player needs a 40-yard-dash tracked top speed and enough regular-season opportunity plays that stood (`season_type == REG` and `play_nullified_by_penalty == 'N'`):

- Wide receivers: at least **20** go / post / corner / wheel routes (`route_ran` in `{GO, POST, CORNER, WHEEL}`).
- Cornerbacks and safeties: at least **30** pass plays (`pass_result` not null) whose `coverage_assignment` contains `MAN` or `DEEP`.

Safeties group `FS` and `SS`. Current official samples: **WR 62, CB 33, S 26**.

---

## 1. Combine Top Speed

**Plain English.** The fastest speed the player reached in the 40-yard dash at the Combine, taken from the 10 Hz sensor — not the laser time.

**Formula.** For player \(i\), over every 40-yard-dash attempt \(e\) (PLAYER rows only):

\[
c^{\text{top}}_i = \max_e \big(\max_t s_{iet}\big)
\quad\text{(yd/s)},
\qquad
c^{\text{top, mph}}_i = 2.0455 \cdot c^{\text{top}}_i.
\]

This is the input to every official translation and SSOE number. Official laser 40 time and the 10-yard split are supporting tests, not the official speed input.

---

## 2. Sunday Speed

**Plain English.** How fast the player actually runs on Sundays, on the plays where his job asks for top speed. For a receiver that is a deep route (go, post, corner, wheel). For a corner or safety that is man or deep coverage. We do not use his single fastest frame of the year — that can be a tracking glitch or one junk play. We take the 90th percentile of his per-play top speeds, so it is a speed he repeatedly reaches, not a one-off.

**Formula.** On each opportunity play \(p\), play top speed is the maximum tracked speed on that play:

\[
v_{ip} = \max_t s_{ipt}.
\]

Sunday Speed is the 90th percentile of those play speeds, provided the player meets the play floor above:

\[
\text{SS}_i = P_{90}\{v_{ip}\},
\qquad
\text{SS}^{\text{mph}}_i = 2.0455 \cdot \text{SS}_i.
\]

A snap-to-end-event windowed version is stored as a robustness column (`sunday_speed_window`). It is **not** the official metric.

---

## 3. Speed Translation Rate

**Plain English.** The exchange rate: how many miles per hour of Sunday Speed you get for each mile per hour of Combine Top Speed, at that position. An exchange rate of 0.67 for receivers means a receiver who was 1 mph faster at the Combine is, on average, about 0.67 mph faster on deep routes in games. An exchange rate near zero means Combine speed does not show up on Sunday.

**Formula.** Fit ordinary least squares separately for each position group \(k \in \{\text{WR}, \text{CB}, \text{S}\}\), on the official sample:

\[
\text{SS}_i = \alpha_k + \beta_k \cdot c^{\text{top}}_i + \varepsilon_i.
\]

The Speed Translation Rate is \(\beta_k\). Because both sides are converted by the same 2.0455 factor, \(\beta_k\) is identical in yd/s per yd/s and in mph per mph. We report it as **mph on Sunday per Combine mph**, with a 95% confidence interval from 2,000 player-level bootstrap resamples.

**Locked rates (official sample):**

| Position | n | Translation rate | 95% bootstrap CI |
|---|---:|---:|---|
| WR | 62 | **0.67** | 0.47 – 0.88 |
| CB | 33 | 0.09 | −0.13 – 0.38 |
| S  | 26 | 0.22 | −0.17 – 0.59 |

The WR interval is well above zero. The CB and S intervals both include zero — we cannot claim a real transfer at either defensive-back spot.

A companion descriptor, **Speed Realization**, is \(\text{SS}_i / c^{\text{top}}_i\) (median WR 82%, CB 76%, S 71%). It is a useful “how much of the 40 shows up” percentage. It is **not** a predictor of career value; those tests were already null.

---

## 4. Sunday Speed Over Expected (SSOE)

**Plain English.** Did this player play faster or slower than what his own Combine 40 top speed, at his position, would have led you to expect? Positive SSOE means he outruns his 40. Negative SSOE means he has not.

This is a development / scouting residual, in mph. It is not a claim that SSOE predicts starts, snaps, or receiving production — those tests were null and we do not use SSOE as a value metric.

**Formula.** Using the official position-specific translation line from §3:

\[
\widehat{\text{SS}}_i = \alpha_k + \beta_k \cdot c^{\text{top}}_i,
\]

\[
\text{SSOE}_i = \text{SS}_i - \widehat{\text{SS}}_i,
\qquad
\text{SSOE}^{\text{mph}}_i = 2.0455 \cdot \text{SSOE}_i
= \text{SS}^{\text{mph}}_i - \widehat{\text{SS}}^{\text{mph}}_i.
\]

Official SSOE is **not** adjusted for weight or draft year (draft slot is never used). Those belong in a later hierarchical model if we need a covariate-adjusted residual. The scouting-card number answers one question only: *given the 40 he ran at his position, is he faster or slower on Sunday than that 40 predicts?*

**How to read it at each position.** For receivers the 40 actually predicts Sunday Speed, so SSOE is a meaningful “over/under the 40” flag. For corners and safeties the 40 barely predicts Sunday Speed (translation rate indistinguishable from zero), so SSOE is close to “faster or slower than the position average.” We say that plainly on the scouting card.

**Reliability flag** (for the leaderboard, based on opportunity-play count):

- **High** — 80 or more official opportunity plays.
- **Medium** — 40 to 79 plays.
- **Limited** — below 40 (receivers can appear from 20; defensive backs from 30). Treat Limited names as directional, not as a finished grade.

---

## 5. What these metrics are not

- They are not “Combine speed minus game speed” as a raw gap. The official comparison is the position-specific expected value (SSOE), not an unadjusted subtraction.
- Sunday Speed, the translation rate, and SSOE describe **speed**. They are not themselves success metrics. Receiver production tests (yards per route, deep yards, deep target share, catch rate, separation, YAC-over-expected) were null for both Sunday Speed and SSOE. Do not use SSOE as a value grade.
- They do not use opponent or ball tracking. Game tracking in this competition covers only the 510-player rookie cohort.
- Phase 2 skill-drill tests and the corner “speed tax” check are supporting analyses. They do not change the definitions on this page.

Pipeline: `build_dataset.py` writes the official player table; `ssoe.py` writes the scouting-card leaderboard from that table; `gameplay_success.py` writes the WR / CB / S production tests; `dl_burst.py` writes the defensive-line get-off and pressure tests.

---

## 6. Official success metrics are on-field gameplay, not playing time

Kevin’s decision (2026-11-10, America/New_York): success should not be measured by playing time only. Career defensive snaps, snaps per game, and start rate remain **secondary context**. They tell you whether coaches put a player on the field. They do not tell you what he did there. All-Pro and Pro Bowl flags are too rare in this rookie file (~1–3%) to use.

Every official success definition below uses a field that actually exists in `player_play.csv`. Fields that do not exist are listed so they are not invented later.

**Controls.** Official tests residualize both sides on **draft-year dummies only** (no draft slot, pick or round). 2023 rookies have had three seasons in this file; 2025 rookies have had one. Rates already adjust for opportunity; we still control for draft year so a one-season sample is not treated as interchangeable with a three-season sample. 95% confidence intervals are player-level bootstraps (2,000 resamples). Holm correction is applied inside each pre-declared family.

---

## 6A. Defensive line — pressure and sack rate

**Who.** Defensive linemen only. The **headline sample is one combined DL group**. Subtypes: `DE` and `OLB` as **Edge** (every OLB in this cohort tested in the DL Combine group and almost always lines up as EDGE), `DT` and `NT` as **Interior**. Edge vs Interior is a pre-declared breakout in every table and chart, not a second headline sample. Offensive linemen are out of scope.

**Opportunity snaps.** Regular-season pass plays that stood (`season_type == REG`, `play_nullified_by_penalty == 'N'`), with the player lined up as `EDGE` or `INTERIOR_LINE`, and at least **20** such snaps. Current samples with a rate: **89** players have a tracking get-off median, **88** have an NFL `player_get_off` median.

**Headline sample (official 10-yard split and ≥20 opportunity snaps).** n = **72** (39 Edge / 33 Interior; 28 / 25 / 19 by the 2023 / 2024 / 2025 classes). The named table of all 72 is `out/dl_players_named.csv`, with highlights in [`DL_PLAYERS.md`](DL_PLAYERS.md).

**Sample funnel.** 118 DL in the roster (66 Edge / 52 Interior). 24 have no official 10-yard split: they skipped the Combine 40; this file has no pro-day times, and we do not invent a tracking-derived split for players who never ran the 40 (they still have other DL drills). 22 have a split but fewer than 20 pass-rush snaps. 72 remain.

**Caveat on the all-DL 10-yard → pressure result.** Within Edge alone or Interior alone, that link is weaker and not significant. Part of the pooled effect comes from edges being both faster and better rushers. The 10-yard → get-off (speed at 1.0s) link does hold within subtypes.

**Get-off (the process metric, not the success metric).**

- **1-sec burst speed** (relabelled 11/2026; earlier pages called this “tracking get-off” or “Sunday get-off”): the player’s median speed 1.0 second after the snap, in mph, from the Kaggle tracking. It is **not** the NFL/NGS get-off. Companion views: speed at 1.5s, time to travel 5 yards, first-step acceleration.
- **NFL/NGS get-off time**: the median of `player_get_off` (seconds; lower is faster). A separate measure from 1-sec burst speed; both are reported as separate rows/columns.

Game tracking covers only the 510-player rookie cohort, so these numbers come from the rusher’s own track. There are no blocker or quarterback tracks.

**Primary success outcomes** (coach-readable):

- **Pressure rate** = share of opportunity snaps where `time_to_pressure` is recorded. In English: how often this rusher is credited with a pressure.
- **Sack rate** = sum of `sack` divided by opportunity snaps. `sack` is 1.0 for a solo sack and 0.5 for a shared sack.

**Companion outcomes** (reported, not used to rescue a headline):

- **Hurry rate** = share of opportunity snaps where `time_to_qb_hurry` is recorded. This nearly nests with pressure (only a handful of hurries have no pressure time), so it is a consistency check, not a second headline.
- **Blocked-pressure rate** = pressure rate after dropping snaps flagged `unblocked_pressure == True`. A sensitivity for the “he was already free” concern.
- There is **no quarterback-hit field**. We do not invent one.

**Secondary / context:** career defensive snaps, defensive snaps per game active, start rate.

**Pre-declared Combine-to-success family (6 tests, Holm on year-controlled partial p):** official 10-yard split vs pressure rate and vs sack rate, in All DL, Edge, and Interior. Headline rows are All DL; Edge and Interior remain pre-declared breakouts in the same family (they do not survive Holm). We do not shrink the family to the two All-DL tests, which would quietly change the All-DL sack Holm p. This is the competition-required Combine-to-NFL-performance link.

**Get-off-to-success family (4 tests, Holm on year-controlled partial p, All DL):** tracking speed at 1.0s and NFL get-off time, each vs pressure rate and sack rate. This is the middle of the chain, not a Combine test.

**Mediation (supporting, not in either Holm family):** official 10-yard split vs pressure / sack after residualizing on draft year **and** game get-off. If the direct 10-yard link shrinks to near zero, get-off is carrying the result. This is association, not a causal claim: we cannot see the blocker or the quarterback.

---

## 6B. Wide receivers — production on routes

**Who.** The official Sunday Speed sample: receivers with a tracked 40 and at least **20** regular-season go / post / corner / wheel routes that stood. Current n = **62**.

**Primary success outcomes**, all from `player_play.csv` on regular-season plays that stood, with `route_ran` present:

- **Yards per route** = sum of `rec_yards` (missing treated as 0) / number of routes.
- **Deep yards per deep route** = the same, restricted to `route_ran` in `{GO, POST, CORNER, WHEEL}`.
- **Deep target share** = deep-route targets / all targets, requiring at least **8** targets.

**Companion outcomes:** catch rate (`rec_yards` not null / targets, ≥8 targets), mean `separation_at_pass_forward` on deep routes, YAC over expected (`yards_after_catch − expected_yards_after_catch` on catches), overall target rate.

**Pre-declared family (6 tests, Holm on year-controlled partial p):** Sunday Speed and SSOE, each vs yards per route, deep yards per deep route, and deep target share. Combine top speed vs the same outcomes is reported as a companion Combine-to-production check.

---

## 6C. Cornerbacks and safeties — what we can and cannot measure

**Fields that do not exist** (and will not be invented):

- No `targets allowed`, no `completions allowed`, no pass-breakup / PBU field, and no interception field attributed to a defender.
- `target` is only ever true for offensive skill players (WR / TE, plus a handful of backs).
- `pass_result` (C / I / S / R / IN) is play-level. It appears on a defender’s row, but it is not “this defender allowed that completion or made that interception.” Using it as an allowed-rate would invent a metric the file does not support.

**Fields that do exist:** `tackle` (1 = solo, 0 with `assist` = 1 means a shared tackle; null means this player was not involved), `assist`, `tackle_for_loss`, `caused_forced_fumble`, `recovered_fumble`, `coverage_assignment`, and pre-snap `cushion`.

**Primary success outcomes** we can actually compute, on regular-season snaps that stood, with at least **50** such snaps:

- **Tackle involvement rate** = share of snaps where the player recorded a solo tackle or an assist.
- **Tackle-for-loss rate** = share of snaps where `tackle_for_loss` is true.

**Pre-declared family (4 tests, Holm on year-controlled partial p):** Combine top speed vs tackle involvement rate and vs TFL rate, for CB and for S, on the broader sample (tracked 40 and ≥50 snaps). The CB “speed tax” vs start rate (now year-controlled; the original “beyond draft slot” version is retired) remains a **playing-time** supporting finding, not a gameplay success result.

---

## 6D. How a coach should read the two layers

Sunday Speed answers: *does his Combine speed show up on Sunday?* Success metrics answer: *does that speed, or that get-off, show up as production?* A player can have a real Combine-to-Sunday-Speed (or Combine-to-get-off) link and still have a null to yards, tackles, or even playing time. We report both layers, and we do not promote a null into a value grade.

---

## 7. Robust testing defaults (11/2026, Kevin-approved; supersedes the controls in §6)

**Draft slot is no longer used anywhere.** (Part A, 11/2026: the references above were rewritten to year-only and the scripts rerun; `combine_gems.py` and `cb_deep_dive.py` were retired because they were defined by draft slot.) Any leftover mention of “log draft pick”, “year+pick partial” or “UDFA = 260” in an old doc describes a retired analysis: no draft slot, pick or round is used as a feature, control, filter or label in any new test, and `robust.assert_no_draft_slot` fails the run if such a column reaches an analysis table. Draft **year** (class) is still a control because classes have different amounts of NFL experience.

Module: `robust.py` (generic), `dl_robust.py` (DL), `pos_robust.py` (WR / TE / DB), `forest.py` (Figure 20), `robust_report.py` (tables). Every Combine test × outcome pair gets all of the following by default:

1. **Size control.** Rank partial correlation: rank the test, the outcome and each continuous control, regress both rank vectors on the controls (draft-year dummies, role dummy for DL Edge/Interior and DB CB/S, **weight and height**), then take the Pearson correlation of the residuals. For the weight row the only size control is height, and for the height row only weight (“beyond the other size measure”). Reported next to the **unadjusted Spearman** and a **year + role only** version. Pooled groups use the role dummy; the Edge / Interior / CB / S breakouts do not.
2. **Noisy rate outcomes.** Empirical-Bayes beta-binomial shrinkage: for each role, fit Beta(α, β) to the players’ counts by marginal likelihood, then use the posterior mean (α + k) / (α + β + n) with the player’s own snap count n. Applied to pressure rate, sack rate, TFL rate, run-stop rate, near-line run-stop rate (DL) and tackle rate, TFL rate (DB). The shrunk rate is the **primary** outcome. Sensitivities reported beside it: the unshrunk rate and a snap-weighted rank partial correlation. Players who are below the old snap floors stay excluded. Separation, penetration and speed outcomes are medians/means of continuous per-play values, so they are not beta-binomial; their sensitivity is the snap/route-weighted version.
3. **Out-of-sample check.** Leave-one-draft-class-out (2023, 2024, 2025): fit a size-only ridge model and a size + test ridge model on two classes (both on within-class normal scores of every variable, α = 5, fixed, not tuned) and predict the third. Pooled over the three held-out classes we report out-of-sample R² for both models, **ΔR² = incremental out-of-sample R²** of adding the test, Spearman of predictions vs truth for both models, the number of held-out classes where the test helps, and a permutation p-value (test values shuffled within class, 1,000 permutations, full leave-one-class-out refit each time). The size-only model for DL includes the Edge/Interior dummy.
4. **Inference.** 2,000-resample player-level bootstrap 95% CI (every resample re-ranks and refits); Freedman–Lane permutation p-value (10,000 permutations of the reduced-model residuals); parametric t p-value for reference; BH-FDR on the permutation p across **every** test × outcome cell in the group (273 for DL; DL FDR is also reported over the 5 production outcomes only, `fdr_prod`). Calibration check: 300 simulated null outcomes with a size confounder gave a 5.7% false-positive rate at p < 0.05 for the permutation test and 3.3% for the leave-one-class-out p.
5. **Verdict labels used in the Results Log.** *Survives* = FDR < 0.05, bootstrap CI excludes 0, raw and size-controlled signs agree, unshrunk sign agrees, ΔR² > 0 with permutation p < 0.10 and positive in ≥ 2 of 3 held-out classes. *Lean* = permutation p < 0.05, CI excludes 0, unshrunk sign agrees and the out-of-sample check passes, but FDR ≥ 0.05. *Small n* = fewer than 25 players or fewer than 5 players per fitted parameter: shown but never scored. Weight and height are labelled *size* because they are controls, not athletic tests.
6. **Interpretation limits.** FDR families differ in size (DL 273, DB 152, WR 68, TE 28), so a star in one group is not comparable to a star in another; a global BH across all 521 pooled cells is also reported. Everything is association in a selected sample (players who made an NFL roster and have tracked snaps; players who skipped a drill are not a random subset). With n ≈ 34 the size-controlled fit has 5–6 parameters, so wide CIs are expected, not a bug.

---

## 8. Pre-declaration: WR break-route lead (11/2026, written before any Part-B number was computed)

**Why.** The robust pass (§7) left one lean result: WR vertical jump (+0.38) and Burst Score (+0.39) vs tracking separation on break routes (BH q 0.039 within WR, global q 0.148). It was found on the same 2023–25 sample used here, so this is a **re-test with a sharper, pre-declared design, not an independent replication**. Route-family definitions below are new (the earlier break family also included POST, CORNER and CROSS), so the contrasts are new questions on old data.

**Data.** `data/player_play.csv`: `route_ran`, `separation_at_pass_forward`, `team_coverage_man_zone` (MAN_COVERAGE / ZONE_COVERAGE), `pass_result`. Regular-season plays only (`season_type == REG`), play not nullified by penalty, separation non-missing, coverage label non-missing. Players: WR (`lined_up_position` irrelevant; the player's `pos_group` = WR), draft years 2023–25. No draft slot, pick or round is read. `robust.assert_no_draft_slot` is enforced.

**Route families (this data has no separate COMEBACK or DIG label; HITCH contains curls/hitches/comebacks and IN contains digs):**

- Break: OUT, IN, HITCH, SLANT.
- Vertical: GO, POST, CORNER.
- Secondary only: CROSS (crossers) and SCREEN. FLAT, WHEEL, ANGLE are in no family (too rare or not a separation route).

**Outcome.** Per play, separation minus the mean separation of that route type (and, in coverage splits, of that route type × man/zone cell), so a player is not rewarded for running more screens or hitches, or for facing more zone. Player outcome = mean of that residual over his plays in the split. Primary outcome is **empirical-Bayes shrunk** (normal–normal: shrink toward the split mean with weight τ²/(τ²+σ²ᵢ/nᵢ), τ² from the method of moments, floored at 0). Sensitivity: unshrunk mean (`alt`) and route-count-weighted partial correlation (`weight`).

**Minimum n.** A player enters a split only with ≥ **20** qualifying routes in that split (≥ **10** for SCREEN). A paired contrast (break vs vertical, man vs zone) uses only players who meet the minimum in **both** cells. Every table reports the player n and the median route count.

**Tests (all via `robust.py` defaults: rank partial correlation controlling draft year, weight and height — minus the test itself; player-level bootstrap 95% CI, 2,000 resamples; Freedman–Lane permutation p, 10,000; leave-one-draft-class-out ΔR² with within-class permutation p; BH-FDR).** Quickness tests are oriented so positive ρ means better test → more separation.

| ID | Hypothesis | Cells | Contrast |
|---|---|---|---|
| H1 | 3-cone and short shuttle matter more on break routes than vertical routes | {3-cone, shuttle} × {break, vertical} | ρ(break) − ρ(vertical) > 0, per test |
| H2 | Vertical jump and Burst Score predict break-route separation | {vertical, Burst Score} × {break} (vertical routes shown for contrast) | none (cell test, the original lead) |
| H3 | Quickness tests (3-cone, short shuttle, official 10-yard) matter more vs man than zone | {3-cone, shuttle, 10-yard} × {man, zone} (all routes) | ρ(man) − ρ(zone) > 0, per test |
| S1 (secondary) | Weight costs separation on screens and crossers | weight × {screen, crosser}, controlling year and height only (weight is the test), break and vertical shown as reference | none |

**Formal contrast test.** The difference in partial correlations is tested on the same players with (a) a paired player-level bootstrap (2,000) CI and (b) a within-player swap permutation (10,000) of the two standardized, control-residualized outcomes. **A contrast SURVIVES** if the difference has the predicted sign, the bootstrap 95% CI excludes 0, the swap-permutation p < 0.05 and BH q < 0.05 across the five contrasts (H1 ×2, H3 ×3). LEAN if the first three hold and q ≥ 0.05. Otherwise NOT SUPPORTED (sign opposite to prediction is reported as REVERSED). Two separate correlations that differ in significance are **not** evidence of a difference.

**Cell verdicts** use the §7 rule (SURVIVES / LEAN / small n) with BH q taken across all Part-B cells (H1 4 cells, H2 4 cells — two break plus two vertical-route reference — and H3 6 cells: 14). S1 gets its own BH family (4 cells: weight × screen, crosser, break, vertical). *Erratum added after the run: the pre-declaration above said 6 cells; that was a miscount, the design has 4. No result depended on it.*

**Hypothesis verdicts.** H1 and H3 survive only if at least one of their contrasts SURVIVES. H2 survives only if at least one of vertical jump / Burst Score is a SURVIVES cell for break routes; LEAN is reported as LEAN. We state in advance that with ~55–75 WRs a paired-contrast CI has half-width ≈ 0.30, so a null contrast here is "not detected", not "no difference".

**Man vs zone source.** Provided BDB label `team_coverage_man_zone` (team-level, per play). No external FTN/participation join needed.

---

## 9. Scorecard verdict rules ("What translates and what doesn't", written 11/2026 before the scorecard was built)

**Source.** Every number in `out/scorecard.csv` is copied from `out/dl_robust_tests.csv` (DL, Edge, Interior), `out/pos_robust_tests.csv` (WR, TE, DB) or `out/wr_route_lead_cells.csv` (WR break-route separation, the pre-declared §8 re-test, which supersedes the broader break family in the §7 table). Nothing is recomputed. Draft slot, pick and round are never involved.

**Rows.** One row per group × Combine test × primary outcome. Tests: official 40, official 10-yard, vertical, broad jump, 3-cone, short shuttle, Combine top speed (tracking), Burst Score (tracking), and for DB the two Combine drill metrics (brakes, re-burst). Size variables (weight, height, arm, hand, wingspan) and bench are not scorecard tests; weight is reported separately in `out/scorecard_weight.csv`. Primary outcomes: WR Sunday Speed, all-route separation, break-route separation; TE all-route separation; DB tackle rate, TFL rate, closing speed, PFR yards/target, PFR missed-tackle %, Sunday Speed; DL (all, Edge, Interior) pressure rate, sack rate, TFL rate, run-stop rate, 1-second get-off speed. Outcomes with no better/worse direction (tackle depth) are left out. The full grid is `out/scorecard_full.csv`.

**Which rows go on the card (fixed in advance, not by verdict).** For each group and outcome, the test with the smallest permutation p among tests with n ≥ 25 (or among all tests if none has n ≥ 25). If a group has fewer than 4 rows, the next-best tests by permutation p are added until it has 4, never more than 8. DL Edge and Interior are shown for the same test × outcome pairs picked for all-DL (breakout columns), not re-picked. The false-discovery q is always the one from the full family (hundreds of cells), so picking the best row per outcome does not flatter the verdict.

**Orientation.** ρ is flipped so that **+ always means a better athlete goes with a better result** (faster time, higher jump, higher top speed; more pressure, fewer yards allowed).

**Verdicts (applied in this order).**

1. **TOO FEW TO TELL**: n < 25 (also when n per fitted control < 5).
2. **TRANSLATES**: the §7 "survives all checks" rule: size-controlled bootstrap CI excludes 0, BH q < 0.05, raw and size-controlled signs agree, shrunk and unshrunk signs agree, leave-one-class-out ΔR² > 0 with permutation p < 0.10 and a gain in ≥ 2 of 3 classes.
3. **SIZE, NOT SPEED**: |raw ρ| ≥ 0.30, size-controlled |ρ| ≤ half of raw |ρ|, and the size-controlled CI includes 0 (the effect collapsed). In pooled DL and DB the controlled model also holds role (edge/interior, CB/S) fixed, so a collapse can be size or role. 
4. **LEANS**: size-controlled CI excludes 0 **or** permutation p < 0.05, same sign as raw, but q ≥ 0.05. Rows where more than half of the year-controlled effect disappears after size (and role) control say so in the coach line.
5. **DOESN'T TRANSLATE**: everything else with adequate n (a null, not a proof of zero; the CI is shown).

**Out-of-sample column.** ΔR² of adding the test to a size-only ridge model, trained on two draft classes and scored on the third, plus how many of the three classes improved.

**Combine-tracking gate.** Each row is tagged `combine_source = tracking` for tests derived from the 10 Hz Combine tracking (top speed, tracking splits, Burst Score, DB drill metrics) and `official` for laser/stopwatch results. All outcomes are regular-season game tracking or play data.

**Correction (11/2026, same day, after the first scorecard build).** "Raw ρ" was first taken from the robust tables, where `rho_raw` is a plain Spearman on the pooled sample against the **empirical-Bayes-shrunk** outcome. For DL the shrinkage prior is fit separately for Edge and Interior, so the shrunk outcome carries the Edge-vs-Interior gap in rates, and with no year or role control that inflated the pooled raw ρ (for example 40 → pressure −0.74 instead of the −0.47 reported earlier). That is not the convention used in every earlier report. **"Raw" in the scorecard now means the year-controlled Spearman on the as-reported (unshrunk) outcome**: both sides demeaned within draft-year cells, then Spearman of the residuals, with a 2,000-resample player-level bootstrap CI (same recipe as `dl_burst.py`). The plain pooled/shrunk value is kept as `rho_unadjusted_pooled_shrunk` in `out/scorecard_full.csv`. Thresholds (0.30, one half) and the row-selection rule were not changed; the SIZE rule and the "% of the link" share use the corrected raw. Weight rows use the same raw definition. **Superseded in part by §11 (audit, 11/2026): raw is now the year-controlled Spearman on the same outcome as the size-controlled fit; the as-reported-rate value is kept as `rho_asreported_yearctrl`.**

## 10. Decision: athletic comps dropped (11/2026, Kevin, 11/19/2026)

Athletic comps (KNN nearest-neighbour player comparisons by Combine profile) are removed from the Big Data Bowl 2027 project entirely. They were a scouting illustration, never a test: they carried no verdict, no CI and no out-of-sample check, and they are not part of the scorecard, the writeup or the notebook. The comps pool was not widened.

Removed: `athletic_comps.py`, `out/athletic_comps*.csv`, the comps pool and z-score tables from `dashboard_export.py` and `out/dashboard_data.*`, the comps section of the coach dashboard, and every README / attribution mention. Nothing in the scorecard, size-controlled ρ, verdicts, percentiles or predictions depended on comps, so no result changes. Earlier log entries that mention comps are historical and superseded by this decision.

## 11. Statistical audit of the scorecard and dashboard (11/2026, Kevin: "those p values and margins seem suspect")

`audit_stats.py` re-derives every one of the 208 scorecard rows without calling `robust.py` (precision-matrix partial ρ, analytic t p, Freedman-Lane permutation p with 20,000 shuffles, player-level refit bootstrap with 5,000 resamples in both percentile and BCa form, Fisher-z / Bonett-Wright interval) and writes `out/audit_stats.csv`. `dashboard_export.py` also writes `out/audit_prediction_coverage.csv` (leave-one-out coverage of the 80% ranges).

**Confirmed correct (no change).** Displayed n equals n used in all 208 rows. Size-controlled ρ matches the independent computation to 1e-14. Permutation p matches the independent permutation p within Monte-Carlo noise (max gap 0.015; only the two WR TRANSLATES cells sit at the 0.0001 floor). Analytic t p and permutation p agree (median ratio 1.00; 99% within 2x); both are two-sided. A null simulation of the actual code (n = 25, 40, 70; confounded by weight and role) gives a permutation type-I rate of 5.7%, 6.7%, 5.7% and an analytic one of 5.3%, 6.0%, 5.7%. BH q is recomputed with statsmodels per family (DL, Edge, Interior 273 cells each; WR 68; TE 34; DB 152; WR break-route cells 14): table q matches to 1e-16, q ≥ p everywhere, monotone. Bootstrap CIs resample players (not rows), refit the whole residualization inside each resample (2,000 resamples), contain their point estimate in all 205 cases, and agree with BCa and Fisher-z in sign and, with six borderline exceptions, in exclusion of 0 (percentile CI covers 0 less often than nominal below n ≈ 30 in simulation, so it errs conservative). Percentile CI widths are within 0.81x to 1.33x of the Fisher-z width (median 1.04x).

**Bugs found and fixed.**

1. *Prediction 80% range was on the shrunk scale.* `dashboard_export.models()` fit the empirical-Bayes-shrunk rate (pressure rate, WR break-route separation), whose residual SD is about half the as-reported SD, so the range covered about 50% of as-reported pressure rates, not 80%. Now fit on the as-reported outcome; `ym` and the outcome quantiles are as-reported too.
2. *Range was ±1.28 residual SD (a normal quantile, no estimation variance).* Now a prediction interval for a new player: t(0.90, df) · sd · sqrt(1 + 1/n + z′Cz), where z is the entered (test, weight, height, role) minus the sample mean and C the matching block of (X′X)⁻¹. This adds only 2% to 3% at the typical player but widens for unusual size or test numbers. Leave-one-out coverage of the new ranges: 78% to 87% (target 80%).
3. *SIZE, NOT SPEED compared unlike outcomes.* The raw ρ was year-controlled on the as-reported rate while the size-controlled ρ is on the shrunk rate, so the "at most half of raw" test mixed outcomes. Raw is now the year-controlled Spearman on the same outcome as the size-controlled fit; the as-reported-rate value stays in `scorecard_full.csv` as `rho_asreported_yearctrl`. 12 verdicts change (11 move to SIZE, NOT SPEED; 1 Interior cell moves back to DOESN'T TRANSLATE). Weight rows use the same definition. Because pooled DL raw ρ does not control role, "size" in those rows includes the Edge/Interior gap; coach lines now say "weight, height and role".
4. *p and q printed as 0.000 / 0.00.* Permutation p (10,000 shuffles) cannot go below 1/10,001; it is now shown as "<0.001" (q "<0.01"), and the dashboard export keeps p to 4 decimals and q to 3.
5. *Degenerate CIs.* Below n = 15 the refit bootstrap collapses (endpoints at exactly ±1.00 for n = 12 and 14). The dashboard now hides intervals for n < 15 (5 rows); the CSV keeps them.
6. *Dashboard weight callout overclaimed* for groups where weight is not significant (DB: q 0.90): it now says the link is not established unless q < 0.05 and the interval excludes 0.

**Flags (not code bugs; documented, not changed).**

- Multiple testing: of 164 cells with n ≥ 25, 28 reach permutation p < 0.05 (about 8 expected by chance; cells share players, so the effective number of tests is smaller). Only 2 clear q < 0.05, whichever family is used (per group as published; one BH over all displayed cells gives the same 2). All 26 LEANS rows are nominal-p leads; none would survive BH over the displayed grid (smallest q 0.19).
- The LEANS rule is "CI excludes 0 OR p < 0.05". One row (DL Edge 10-yard split → sack rate, p 0.088, percentile CI lower bound +0.001) qualifies only by the CI; BCa puts it at −0.03. Four rows have p < 0.05 with a CI that includes 0.
- The card shows the best-p test per result, so card ρ is optimistic by construction.
- WR break-route cells use their own pre-declared 14-cell BH family (§8), smaller than the 68-cell WR family; the best two rows have q 0.185 there and about 0.21 under one BH over the whole displayed grid. Neither clears 0.05.
- All 25 SIZE, NOT SPEED rows are DL. In the pooled DL rows the raw link is largely the Edge-vs-Interior gap (raw ρ does not control role), which the size-controlled fit removes.
