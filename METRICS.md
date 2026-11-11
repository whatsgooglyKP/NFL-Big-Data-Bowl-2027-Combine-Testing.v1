# Official metric definitions — Sunday Speed

Frozen for the NFL Big Data Bowl 2027 submission. These are the numbers a coach can read off a scouting card. If a later robustness check uses a different window, play floor, or regression, it is a sensitivity test — it does not replace this page.

**Units.** Source tracking is in yards per second. Everything we show a coach is in miles per hour:

\[
1\ \text{yd/s} = 2.0455\ \text{mph}.
\]

**Who is in the official sample.** A player needs a 40-yard-dash tracked top speed and enough regular-season opportunity plays that stood (`season_type == REG` and `play_nullified_by_penalty == 'N'`):

- Wide receivers: at least **20** go / post / corner / wheel routes (`route_ran` in `{GO, POST, CORNER, WHEEL}`).
- Cornerbacks and safeties: at least **30** pass plays (`pass_result` not null) whose `coverage_assignment` contains `MAN` or `DEEP`.

Safeties group `FS` and `SS`. Undrafted players are treated as pick **260** whenever we control for draft slot. Current official samples: **WR 62, CB 33, S 26**.

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

Official SSOE is **not** adjusted for weight, draft year, or draft slot. Those belong in a later hierarchical model if we need a covariate-adjusted residual. The scouting-card number answers one question only: *given the 40 he ran at his position, is he faster or slower on Sunday than that 40 predicts?*

**How to read it at each position.** For receivers the 40 actually predicts Sunday Speed, so SSOE is a meaningful “over/under the 40” flag. For corners and safeties the 40 barely predicts Sunday Speed (translation rate indistinguishable from zero), so SSOE is close to “faster or slower than the position average.” We say that plainly on the scouting card.

**Reliability flag** (for the leaderboard, based on opportunity-play count):

- **High** — 80 or more official opportunity plays.
- **Medium** — 40 to 79 plays.
- **Limited** — below 40 (receivers can appear from 20; defensive backs from 30). Treat Limited names as directional, not as a finished grade.

---

## 5. What these metrics are not

- They are not “Combine speed minus game speed” as a raw gap. The official comparison is the position-specific expected value (SSOE), not an unadjusted subtraction.
- They are not a draft-value or career-success metric. Translation and SSOE describe speed. Starts, snaps, separation, and YAC were tested and did not follow SSOE.
- They do not use opponent or ball tracking. Game tracking in this competition covers only the 510-player rookie cohort.
- Phase 2 skill-drill tests and the corner “speed tax” check are supporting analyses. They do not change the definitions on this page.

Pipeline: `build_dataset.py` writes the official player table; `ssoe.py` writes the scouting-card leaderboard from that table.

---

## 6. Supporting analysis: defensive-line get-off (not a Sunday Speed metric)

This section does not change Sunday Speed, Speed Translation Rate, or SSOE. It records how we will judge whether a pass rusher's get-off on Sunday relates to career opportunity.

**Who.** Defensive linemen only: `DE` and `OLB` as **Edge** (every OLB in this cohort tested in the DL Combine group and almost always lines up as EDGE), `DT` and `NT` as **Interior**. Offensive linemen are out of scope.

**Get-off (the input).** On regular-season pass plays that stood, with the player lined up as EDGE or interior DL, and at least 20 such snaps:

- Tracking get-off: the player's median speed 1.0 second after the snap, in mph. Companion views: speed at 1.5s, time to travel 5 yards, first-step acceleration.
- NFL get-off time: the median of `player_get_off` (seconds; lower is faster).

Game tracking covers only the 510-player rookie cohort, so these numbers come from the rusher's own track.

**Career success (the outcome).** Primary outcomes are **career defensive snaps** (`career_defensive_snaps`) and **defensive snaps per game active** (`career_defensive_snaps / career_games_active`). Snaps measure opportunity. Start rate (`career_games_started / career_games_active`) is secondary, as are sack rate and pressure rate on the same pass-rush plays.

**Draft year.** 2023 rookies have had three seasons in this file; 2025 rookies have had one. Raw career snap totals are not comparable across classes. Official career tests therefore residualize both sides on **draft-year dummies and log draft pick** (UDFA = 260) before the Spearman correlation. Snaps per game already adjusts for career length; we still control for draft year so a one-season sample is not treated as interchangeable with a three-season sample.

The primary career family is four All-DL tests (two get-off measures × two snap outcomes). Holm correction is applied to those four year-and-pick partial p-values. Subtype (Edge / Interior) and the secondary outcomes are reported, but they are not used to rescue a headline.
