# NFL Big Data Bowl 2027 — Combine Testing v1

Private working repo for Kevin's Open Track entry in the [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027) ("Combine to NFL Performance").

**Deadline:** Wednesday, January 6, 2027, 6:59 PM EST (11:59 PM UTC).

The submission is being built in this repo. Official metric definitions live in [`METRICS.md`](METRICS.md). Session-by-session numbers live in [`RESULTS_LOG.md`](RESULTS_LOG.md) and [`PHASE2_RESULTS.md`](PHASE2_RESULTS.md). The strategy memo is [`STRATEGY.md`](STRATEGY.md).

Raw Kaggle data is **not** in this repository.

## Current headline findings

**Sunday Speed: which Combine speed is real?**

- **Receivers (n=62):** Combine tracked 40 top speed predicts Sunday Speed on deep routes (go / post / corner / wheel). Spearman ρ = +0.63, partial (log draft pick) ρ = +0.62. Exchange rate: **0.67 mph on Sunday per Combine mph** (95% bootstrap CI 0.47–0.88). The trait is stable week to week (odd/even-game r = 0.84). The 10 Hz tracked 40 beats the official laser time and the go-route drill; the drill adds nothing once you know the 40.
- **Corners (n=33) and safeties (n=26):** the same 40 does **not** predict coverage Sunday Speed (translation rates 0.09 and 0.22; both CIs include zero). Standard DB skill drills do not clearly take its place after Holm correction.
- **Sunday Speed Over Expected (SSOE)** is a scouting residual in mph: did he play faster or slower than his own 40, at his position, predicted? For receivers that is a real over/under-the-40 flag. For corners and safeties the 40 barely predicts Sunday Speed, so SSOE is close to faster or slower than the position average.

**Success is on-field gameplay, not playing time.** Career snaps and start rate are context. They are not the official success definition.

- **Defensive line (headline is all DL, n=72** with an official 10-yard split and ≥20 pass-rush snaps, 2023–2025 classes pooled; 39 Edge / 33 Interior): a faster official 10-yard split predicts a higher **pressure rate** (year+pick ρ = −0.45, 95% CI −0.62 to −0.19, Holm p = 0.00047) and a higher **sack rate** (ρ = −0.31, CI −0.53 to −0.07, Holm p = 0.039). The path runs through get-off (all-DL 10-yard vs speed at 1.0s: partial ρ = −0.79; that get-off link also holds within Edge, ρ = −0.61, and within Interior, ρ = −0.31, both Holm-significant). The direct 10-yard vs pressure link shrinks to ρ = −0.08, p = 0.49 once get-off is in the model. **Caveat:** within Edge alone (n=39, ρ = −0.24, Holm p = 0.560) or Interior alone (n=33, ρ = −0.12, Holm p = 1.000), the split→pressure link is weaker and not significant; part of the pooled effect comes from edges being both faster and better rushers. Playing time stays null. We have no blocker or QB tracks — association, not proof. Named 72-player table: [`DL_PLAYERS.md`](DL_PLAYERS.md) and `out/dl_players_named.csv`.
- **Receivers:** Sunday Speed and SSOE do **not** predict yards per route, deep yards, or deep target share after Holm correction. Sunday Speed is a speed test, not a production grade.
- **Corners / safeties:** this file has no targets-allowed, completions-allowed, PBU, or interception field for a defender, so those tests were not invented. Tackle and tackle-for-loss rates do not follow Combine speed after Holm. The CB “speed tax” (faster 40, fewer starts than draft slot predicted) remains a suggestive **playing-time** finding, not a gameplay headline.

Draft-day lines:

- WR speed: trust the 40 as Sunday Speed. Do not use it, or SSOE, as a receiving-production grade.
- CB speed: do not pay for the 40, and do not assume the standard DB drills will tell you who will actually run on Sunday.
- DL get-off: trust the official 10-yard split as a get-off test. In the all-DL sample, a faster split also shows up as more pressure and more sacks, through get-off — not as more playing time. Do not treat that pressure result as a within-Edge or within-Interior rule.

**Combine gems** (named shortlist, not a new official finding): players in any draft round, plus UDFAs, who tested in the top third of their position on a pre-declared Combine measure and then outplayed their draft slot. Rounds are not split. UDFAs are flagged in a column (draft-slot value = pick 260) and are in the same list, not a separate tier. Pre-declared measures: official 40 time (WR), broad jump (CB), gauntlet top speed (S), official 10-yard split (combined DL; strong is the top third *within Edge* and *within Interior*). Full-sample correlations are reported; this is a selection caveat, not a confirmatory test. The group-level strong-vs-weak tests are mostly null or modest; the names are the deliverable. Details in [`COMBINE_GEMS.md`](COMBINE_GEMS.md) and Figure 8.

**Multi-test models (WR / TE / CB / S) and athletic comps** (supporting, not a new official finding): a Firth / L2 logistic that uses the 40, 10-yard split, broad jump, vertical, and weight, plus shallow trees, naive Bayes, and random forests / gradient boosting, all against a draft-pick + year baseline. Success is above-median yards per route (WR, TE) or tackle involvement rate (CB, S — yards allowed is not attributable). **No Combine test is Holm-significant. For receivers, the multi-test model loses to pick + year (CV AUC 0.55 vs 0.62).** Tight ends and corners show raw AUC lifts that come with severe overfitting on n = 22–30. Running backs are excluded (one player in the file). Historical athletic comps against the public nflverse Combine (2000–2022) are scouting cards, not a prediction rule; the standout card is Cedric Johnson (Edge, pick 214) testing nearest to Brian Orakpo. Details in [`MULTI_TEST_MODELS.md`](MULTI_TEST_MODELS.md) and Figure 9.

## How to reproduce

Data is kept locally in `data/` (gitignored). From the repo root, with the nine official CSVs already in `data/`:

```bash
python3 -m venv .venv
.venv/bin/pip install pandas numpy scipy scikit-learn statsmodels matplotlib pyarrow
.venv/bin/python build_dataset.py          # official WR / CB / S Sunday Speed table
.venv/bin/python ssoe.py                   # SSOE scouting card, NGS incremental, CB speed tax
.venv/bin/python dl_burst.py               # DL get-off, pressure / sack success, Figures 5–6
.venv/bin/python gameplay_success.py       # WR production and CB/S tackle tests, Figure 7
.venv/bin/python cb_deep_dive.py           # supporting CB speed-tax / gauntlet re-test
.venv/bin/python combine_gems.py           # Combine gems (all rounds + UDFA), Figure 8
.venv/bin/python multi_test_models.py      # Multi-test logistic / trees / NB, Figure 9
.venv/bin/python athletic_comps.py         # KNN historical athletic comps (uses external/nflverse)
```

Optional rebuilds (slow; they re-stream the 2+ GB of game tracking):

```bash
.venv/bin/python build_dataset.py --rebuild-game
.venv/bin/python dl_burst.py --rebuild
```

`explore.py` and `profile.py` are the original first-pass scripts. The official numbers come from the pipeline above, not from those two.

Python 3.10+ is enough. A virtualenv is required in this environment because the system `pip` is locked.

## Data (not in this repo)

Competition data: [Kaggle — NFL Big Data Bowl 2027, Data tab](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data). You must accept the competition rules, then download the nine CSVs into `data/`:

- `players.csv`, `combine_results.csv`, `combine_tracking.csv`
- `player_career_successes.csv`, `games.csv`, `player_play.csv`
- `game_tracking_2023.csv`, `game_tracking_2024.csv`, `game_tracking_2025.csv`

About 2.3 GB total. Licensed CC BY-NC 4.0. Column notes and gotchas are in [`DATA_NOTES.md`](DATA_NOTES.md). Game tracking covers **only the 510-player rookie cohort** — no opponent or ball tracks.

`.gitignore` excludes `data/`, `.venv/`, `__pycache__/`, and `*.parquet` caches. Small result CSVs and the figures are tracked.

## File map

| Path | What it is |
|---|---|
| `METRICS.md` | Frozen official definitions (Sunday Speed, translation, SSOE, and gameplay success) |
| `RESULTS_LOG.md` | Append-only working-session results |
| `PHASE2_RESULTS.md` | Skill-drill tests vs the 40 |
| `STRATEGY.md` | Concept, writeup plan, past-winner framing |
| `DATA_NOTES.md` | Data dictionary and gotchas from the Kaggle Data tab |
| `CB_DEEP_DIVE.md` | CB speed-tax and gauntlet re-test writeup |
| `COMBINE_GEMS.md` | Combine-gem overperformer shortlist and group tests |
| `MULTI_TEST_MODELS.md` | Multi-test logistic / trees / NB, and historical athletic comps |
| `build_dataset.py` | Official WR / CB / S player table |
| `ssoe.py` | Scouting-card leaderboard and supporting tests |
| `dl_burst.py` | DL Combine burst, get-off, pressure / sack |
| `gameplay_success.py` | WR production and CB/S tackle / TFL tests |
| `cb_deep_dive.py` | Supporting CB robustness |
| `combine_gems.py` | Combine gems: pre-declared measures, all-rounds shortlist, Figure 8 |
| `multi_test_models.py` | Multi-test logistic, trees, naive Bayes, RF/GB, Figure 9 |
| `athletic_comps.py` | KNN athletic comps vs nflverse Combine 2000–2022 |
| `external/` | Public nflverse Combine and draft_picks cache (not Kaggle), with attribution |
| `explore.py`, `profile.py` | First-pass exploration |
| `out/sunday_speed_players.csv` | Official skill-player table |
| `out/ssoe_leaderboard.csv` | Scouting card |
| `out/dl_burst_players.csv`, `out/dl_burst_tests.csv` | DL player table and tests |
| `out/gameplay_success_players.csv`, `out/gameplay_success_tests.csv` | Gameplay outcomes and tests |
| `out/combine_gems.csv`, `out/combine_gems_tests.csv` | Combine-gem player table and tests |
| `out/multi_test_coefficients.csv`, `out/multi_test_auc.csv` | Multi-test odds ratios and CV AUCs |
| `out/athletic_comps.csv`, `out/athletic_comps_summary.csv` | Historical athletic comps (5 per rookie) |
| `out/figs/fig1_translation_scatter.png` | Combine vs Sunday Speed, by position |
| `out/figs/fig2_exchange_rate.png` | mph on Sunday per Combine mph |
| `out/figs/fig3_phase2_drills.png` | Do the skill drills beat the 40? |
| `out/figs/fig4_ssoe_leaderboard.png` | SSOE scouting card |
| `out/figs/fig5_dl_burst.png` | 10-yard split vs get-off, Edge vs Interior |
| `out/figs/fig6_combine_to_pressure.png` | Combine 10-yard split → pressure chain |
| `out/figs/fig7_gameplay_success.png` | WR production and CB/S tackle tests |
| `out/figs/fig8_combine_gems.png` | Top-third testers, all rounds, who outplayed their draft slot |
| `out/figs/fig9_multi_test_models.png` | Multi-test odds ratios and model-comparison AUCs |
| `out/figs/cb_speed_tax.png`, `out/figs/cb_gauntlet.png` | CB deep-dive charts |

Owner: whatsgooglyKP. Work happens in this repo and in the Google Drive folder “NFL Big Data Bowl.”

## License

Code in this repository is released under the Apache License 2.0 (see `LICENSE`). Kaggle competition data is not included and remains subject to the competition rules.
