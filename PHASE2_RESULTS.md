# Sunday Speed — Phase 2 Results

**NFL Big Data Bowl 2027 · "Which Combine Speed Is Real?"**
Kevin · Results as of Tuesday, Nov 10, 2026 (America/New_York)
Pipeline: `build_dataset.py` → `out/sunday_speed_players.parquet`

This note is written for the project, not as the competition writeup. It records what the reproducible pipeline found, whether Phase 2 changes the story, and what to do next.

**Later update (same day, after the gameplay-success re-definition).** Phase 2 still does not change the Sunday Speed framing. What changed is the *success* definition: playing time is context, not the official outcome. WR Sunday Speed and SSOE remain null against yards per route, deep yards, and deep target share (6-test Holm family, all n.s.). The CB speed tax stays a suggestive playing-time finding; tackle and TFL rates do not follow the 40, and this file has no targets-allowed or completions-allowed field. The new positive Combine-to-performance link is on the defensive line (official 10-yard split → pressure and sack rate in the pooled DL sample, through get-off). Details and numbers are in `RESULTS_LOG.md` and `METRICS.md` §§6–6D, not in this Phase 2 note.

---

## 1. Headline numbers, reproduced

The original exploratory tests used all games (not just regular season), required at least 100 tracked plays, and took Sunday Speed as the 90th percentile of play top speed on deep routes (WR: GO / POST / CORNER / WHEEL, at least 20 such plays) or on coverage tagged MAN or DEEP (CB / S, at least 30 such plays). The pipeline reproduces those results exactly, to the two decimals published in `STRATEGY.md`:

| Position | n | Spearman ρ | p | Partial ρ (draft year) | Translation slope (game yd/s per Combine yd/s) |
|---|---:|---:|---:|---:|---:|
| WR | 68 | **+0.64** | 5.5×10⁻⁹ | **+0.62** | 0.67 |
| CB | 33 | +0.06 | 0.75 | +0.25 | 0.10 |
| S  | 27 | +0.19 | 0.35 | +0.33 | 0.33 |

The raw Spearman values match the stored targets (WR +0.64, CB +0.06, S +0.19). The partial column was redone on draft year only in 11/2026 (the original controlled for log draft pick, which is no longer used): WR +0.62 (unchanged), CB +0.25 (was +0.05, p = 0.16), S +0.33 (was +0.15, p = 0.09). CB and S remain non-significant. The WR result survives any reasonable multiple-testing correction. The CB and S results are null.

## 2. Official Sunday Speed (the metric we should carry forward)

The definition we want in the submission is stricter and closer to a "regular-season" claim: regular-season plays only, plays that stood (`play_nullified_by_penalty == 'N'`), and — for defensive backs — pass plays in man or deep coverage. There is no extra 100-total-play floor; the opportunity-play floors (20 deep routes, 30 coverage plays) already keep the sample honest.

| Position | n | Spearman ρ | p | Partial ρ | Translation slope (95% bootstrap CI) | Median realization |
|---|---:|---:|---:|---:|---|---:|
| WR | 62 | **+0.63** | 3.1×10⁻⁸ | **+0.63** | **0.67** (0.47–0.88) | 82% |
| CB | 33 | +0.06 | 0.73 | +0.24 | 0.09 (−0.13–0.38) | 76% |
| S  | 26 | +0.10 | 0.62 | +0.16 | 0.22 (−0.17–0.59) | 71% |

The story does not change. WR Combine top speed still predicts Sunday Speed after accounting for draft year, and the WR confidence interval on the exchange rate sits well above zero. The CB and S intervals both include zero — we cannot claim a real transfer at either defensive-back spot. Split-half stability (odd vs. even regular-season games) is **r = 0.84** for receivers (n=62) and **r = 0.58** for defensive backs pooled (n=66; CB 0.44, S 0.24). The WR trait is stable week to week; the DB metric is noisier, which is expected given the smaller opportunity counts and the weaker signal.

Coach-facing line, still true: *For receivers, every 1 mph at the Combine is worth about 0.67 mph on go routes. For corners it is worth about 0.1 mph, and we cannot rule out zero.*

## 3. Phase 2 — do the skill drills beat the 40?

**Short answer: no. Phase 2 does not change the framing.** The 40-yard tracked top speed is still the Combine feature that predicts Sunday Speed for receivers. No defensive-back drill clearly takes its place, and the two suggestive DB leads do not survive a multiple-testing correction. Keep the honest null.

### How the tests were run

For each position we correlated official Sunday Speed with (a) 40-yard tracked top speed, (b) the official laser 40 and 10-yard split, (c) 40-yard burst (time to 90% of top speed), and (d) peak speed on the position's skill drills. We also report a pick-controlled partial Spearman, leave-one-out R² from a simple linear model, and — for every drill — the incremental Spearman after residualizing on 40-yard tracked speed (does the drill add anything the 40 did not already tell us?).

The **primary family** is all of those peak-speed tests across WR, CB, and S (26 tests). P-values are Holm-adjusted across that family. Braking and transition times were pre-specified as a **secondary family** and are not used to rescue a headline. Nulls are reported as nulls.

### Wide receivers

| Feature | n | ρ | p (raw) | p (Holm) | Partial ρ | LOO R² | Incremental ρ after the 40 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 40-yard tracked top speed | 62 | **+0.63** | 3.1×10⁻⁸ | **8.0×10⁻⁷** | +0.62 | **+0.34** | — |
| Official 40 time | 63 | −0.55 | 3.3×10⁻⁶ | **8.4×10⁻⁵** | −0.57 | +0.21 | −0.03 (p=0.82) |
| Go-route drill speed | 61 | +0.47 | 1.4×10⁻⁴ | **0.003** | +0.46 | +0.17 | +0.13 (p=0.33) |
| Post-corner / slant / dagger drill speed | 60–69 | +0.00 to +0.16 | ≥0.23 | 1.00 | ~0 | <0 | ~0 |

The go-route drill *does* predict Sunday Speed, and that result survives Holm correction. It is just not as good as the 40 (ρ 0.47 vs. 0.63; leave-one-out R² 0.17 vs. 0.34), and once you already know the player's 40-yard tracked speed, the go-route drill adds nothing reliable. The official laser 40 is real too, but the 10 Hz tracked top speed beats the laser time. That is a useful supporting point for this competition: the sensor data is not just a fancier 40, it is a better 40.

The official 10-yard split does not predict WR Sunday Speed (ρ=−0.16, p=0.22). Tracking-derived 10-yard splits also do not reconstruct the official split well (Spearman ≈ 0.09 vs. the laser time), so we should use the official split if we use a split at all, and we should not lean on a derived split in the writeup.

### Cornerbacks

| Feature | n | ρ | p (raw) | p (Holm) | Partial ρ | LOO R² | Incremental ρ after the 40 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 40-yard tracked top speed | 33 | +0.06 | 0.73 | 1.00 | +0.05 | −0.09 | — |
| Official 40 time | 34 | −0.20 | 0.26 | 1.00 | −0.21 | −0.07 | −0.27 (p=0.13) |
| Gauntlet drill speed | 39 | +0.40 | **0.012** | 0.27 | +0.35 | +0.02 | +0.27 (p=0.13) |
| 45° transition, 90° break, W-drill, box-drill speed | 39 | −0.06 to +0.07 | ≥0.68 | 1.00 | ~0 | <0 | ~0 |

The 45°, 90°, W, and box drills — the ones the strategy originally flagged — are clean nulls for CB Sunday Speed. The gauntlet is the only raw signal (ρ=+0.40, p=0.012). It does **not** survive Holm correction (adjusted p=0.27), the leave-one-out R² is essentially zero (+0.02), and it does not add significant information beyond the 40. Treat it as suggestive, not as a finding. Secondary braking and transition features are also null after correction.

### Safeties

| Feature | n | ρ | p (raw) | p (Holm) | Partial ρ | LOO R² | Incremental ρ after the 40 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 40-yard tracked top speed | 26 | +0.10 | 0.62 | 1.00 | +0.15 | −0.13 | — |
| 45° transition drill speed | 31 | +0.41 | **0.021** | 0.45 | +0.37 | +0.08 | +0.49 (p=0.011) |
| Gauntlet drill speed | 30 | +0.30 | 0.10 | 1.00 | +0.20 | −0.11 | +0.30 (p=0.14) |
| 90° break, W-drill, box-drill speed | 31 | −0.10 to +0.03 | ≥0.58 | 1.00 | ~0 | <0 | ~0 |

Same pattern as corners: a single raw lead (the 45° transition drill, ρ=+0.41, p=0.021) that disappears after Holm (adjusted p=0.45). The incremental test after the 40 looks more interesting (ρ=+0.49, p=0.011), but it was not pre-registered as a primary, family-wide test, the sample is 26–31 players, and we should not promote it. Secondary 45° braking has a similar uncorrected hint (ρ=+0.39, p=0.029) and the same problem.

## 4. What this means for the story

The core contrast is intact and, if anything, cleaner:

- **Receiver Combine speed is real.** It shows up on Sunday deep routes, it is stable across draft classes, the trait is stable week to week, and the 10 Hz tracked 40 is a better predictor than the official laser time or the go-route drill.
- **Corner (and safety) Combine speed is not.** The exchange rate is indistinguishable from zero. The usual DB skill drills do not rescue it. We looked, and we should say so.

That last sentence is the only real change from the draft-day line in `STRATEGY.md`. The original pitch said: *"WR speed: trust it; CB speed: verify it in the DB drills."* Phase 2 does not give us the second half of that sentence. A more accurate coach line is:

> **WR speed: trust the 40. CB speed: do not pay for the 40, and do not assume the standard DB drills will tell you who will actually run on Sunday either.**

The null is the insight. Teams still pay for a 4.3 at corner; that number does not predict coverage speed, and the drills that look more "football-specific" do not clearly predict it either — at least not from peak speed, braking, or a simple transition-time feature in this sample. That is a sharper scouting claim than "just look at a different drill," and it is honest.

Do not claim that Speed Realization or Sunday Speed Over Expected predicts career value or receiving production. Those tests were already null in the first pass. They were re-run against yards per route, deep yards, and deep target share after success was redefined as gameplay, and they are still null after Holm correction.

## 5. What was built after Phase 2, and what is still open

Completed in later sessions (see `RESULTS_LOG.md`): official metric freeze in `METRICS.md`; SSOE scouting-card leaderboard (Figure 4); incremental test of the tracked 40 over `ngs_athleticism_score`; CB speed-tax re-test with a permutation check and a deep dive (`CB_DEEP_DIVE.md`); defensive-line 10-yard split vs get-off (Figure 5); and the gameplay-success re-definition with the Combine-to-pressure chain (Figure 6) and the WR / CB production tests (Figure 7).

Still open for the writeup: the hierarchical model (optional; the position-specific OLS lines with bootstrap CIs already carry the exchange-rate claim), a stability scatter as a finished figure, the hero animation, and the Kaggle notebook draft. The draft-day line above is the one to keep; the DL 10-yard-to-pressure result belongs in its own section so it does not dilute the WR-vs-DB headline.

## 6. Pipeline notes (for reruns)

- Run: `/workspace/bdb2027/.venv/bin/python /workspace/bdb2027/build_dataset.py`
- Add `--rebuild-game` only if the game-tracking cache should be regenerated. The cache is `out/game_play_speed.parquet`.
- Outputs: `out/sunday_speed_players.parquet` and `.csv` (one row per WR / CB / S, 219 players), `out/phase2_tests.csv`, `out/translation_slopes.json`, and the three PNGs under `out/figs/`. Later official layers are `ssoe.py`, `dl_burst.py`, `gameplay_success.py`, and `cb_deep_dive.py` (see `README.md`).
- Sunday Speed is computed from all frames on the opportunity play (same as the original exploration). A snap-to-end-event windowed version is stored as `sunday_speed_window` for a later robustness check; it is not the primary metric.
- `a` is unsigned in the source files. Signed acceleration is `Δs/Δt` after sorting by time, with `|Δs/Δt| > 12` yd/s² dropped as glitches. Speeds are stored in yd/s and also as mph (`× 2.0455`).
- Partial correlations control for draft year only (11/2026). Draft slot, pick and round are not used.
