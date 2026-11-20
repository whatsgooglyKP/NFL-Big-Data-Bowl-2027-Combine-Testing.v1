# NFL Big Data Bowl 2027 — Combine Testing v1

Private working repo for Kevin's Open Track entry in the [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027) ("Combine to NFL Performance").

**Deadline:** Wednesday, January 6, 2027, 6:59 PM EST (11:59 PM UTC).

The submission is being built in this repo. Official metric definitions live in [`METRICS.md`](METRICS.md). Session-by-session numbers live in [`RESULTS_LOG.md`](RESULTS_LOG.md) and [`PHASE2_RESULTS.md`](PHASE2_RESULTS.md). The strategy memo is [`STRATEGY.md`](STRATEGY.md).

Raw Kaggle data is **not** in this repository.

## Current headline findings

**Sunday Speed: which Combine speed is real?**

- **Receivers (n=62):** Combine tracked 40 top speed predicts Sunday Speed on deep routes (go / post / corner / wheel). Spearman ρ = +0.63, draft-year-controlled ρ = +0.63. Exchange rate: **0.67 mph on Sunday per Combine mph** (95% bootstrap CI 0.47–0.88). The trait is stable week to week (odd/even-game r = 0.84). The 10 Hz tracked 40 beats the official laser time and the go-route drill; the drill adds nothing once you know the 40.
- **Corners (n=33) and safeties (n=26):** the same 40 does **not** predict coverage Sunday Speed (translation rates 0.09 and 0.22; both CIs include zero). Standard DB skill drills do not clearly take its place after Holm correction.
- **Sunday Speed Over Expected (SSOE)** is a scouting residual in mph: did he play faster or slower than his own 40, at his position, predicted? For receivers that is a real over/under-the-40 flag. For corners and safeties the 40 barely predicts Sunday Speed, so SSOE is close to faster or slower than the position average.

**Success is on-field gameplay, not playing time.** Career snaps and start rate are context. They are not the official success definition.

- **Defensive line (headline is all DL, n=72** with an official 10-yard split and ≥20 pass-rush snaps, 2023–2025 classes pooled; 39 Edge / 33 Interior): a faster official 10-yard split predicts a higher **pressure rate** (draft-year-controlled ρ = −0.47, 95% CI −0.65 to −0.24, Holm p = 0.00016) and a higher **sack rate** (ρ = −0.37, CI −0.57 to −0.11, Holm p = 0.0066). The path runs through get-off (all-DL 10-yard vs speed at 1.0s: partial ρ = −0.80; that get-off link also holds within Edge, ρ = −0.57, and within Interior, ρ = −0.41, both Holm-significant). The direct 10-yard vs pressure link shrinks to ρ = −0.12, p = 0.31 once get-off is in the model. **Caveat:** within Edge alone (n=39, ρ = −0.36, Holm p = 0.099) or Interior alone (n=33, ρ = −0.15, Holm p = 0.81), the split→pressure link is weaker and not significant; part of the pooled effect comes from edges being both faster and better rushers. Playing time stays null. We have no blocker or QB tracks — association, not proof. Named 72-player table: [`DL_PLAYERS.md`](DL_PLAYERS.md) and `out/dl_players_named.csv`.
- **Receivers:** Sunday Speed and SSOE do **not** predict yards per route, deep yards, or deep target share after Holm correction. Sunday Speed is a speed test, not a production grade.
- **Corners / safeties:** this file has no targets-allowed, completions-allowed, PBU, or interception field for a defender, so those tests were not invented. Tackle and tackle-for-loss rates do not follow Combine speed after Holm. The CB “speed tax” (faster 40, fewer starts) is **gone** once draft slot is removed from the controls: it was −0.45 “beyond draft slot”, and year-controlled it is −0.12 (n=44, Holm p = 0.94).

Draft-day lines:

- WR speed: trust the 40 as Sunday Speed. Do not use it, or SSOE, as a receiving-production grade.
- CB speed: do not pay for the 40, and do not assume the standard DB drills will tell you who will actually run on Sunday.
- DL get-off: trust the official 10-yard split as a get-off test. In the all-DL sample, a faster split also shows up as more pressure and more sacks, through get-off — not as more playing time. Do not treat that pressure result as a within-Edge or within-Interior rule.

**Combine gems and the CB speed-tax deep dive were retired (11/2026).** Both were defined by draft slot (“outplayed his draft slot”, “speed tax beyond draft slot”), and draft slot, pick and round are never used here. Their scripts are stubs, their outputs were removed (Figure 8 and the CB deep-dive figures are gone). The CB speed tax was recomputed year-controlled in `ssoe.py`: ρ = −0.12 (n = 44), Holm p = 0.94, i.e. the earlier −0.45 was a draft-slot artifact.

**Which Combine tests translate to Sunday?** (supporting, not a new official finding; **draft slot is out of this analysis entirely** — not a covariate, not a baseline, not a sensitivity). Per group (**WR, TE, DB, and one combined DL**; RB excluded; corners and safeties are one headline DB group), a year-only Spearman matrix of every available Combine test × coach-relevant in-game metrics, with the **tracking-derived 20-yard split** as the lead test, bootstrap CIs and Holm / BH-FDR within the group, plus a coach-readable **Burst Score** (20-yard + jumps; equal-weight and learned-inside-CV, picked by out-of-fold ρ, scaled 0–100 within position), plus lasso, elastic net, ridge, Firth, shallow trees, naive Bayes, and a Bayesian hierarchical logistic (partial pooling across the four groups), all against a **year-only** baseline.

- **DL is the one clear Combine-to-success link:** official 10-yard split vs pressure rate, ρ = −0.47, n = 72, 95% CI −0.65 to −0.23, Holm p = 0.001, FDR p = 7.3×10⁻⁵. The tracking 20-yard is also FDR-significant vs pressure (ρ = −0.31, n = 71, FDR p = 0.012) but weaker. The **DL Burst Score** (equal-weight 20-yard + vertical + broad) has out-of-fold ρ = +0.45, 95% CI +0.18 to +0.66, n = 64, and beats the 20-yard alone (OOF ρ = +0.31). Recommended model: lasso (CV AUC 0.674 vs year-only 0.596).
- **WR:** the 20-yard alone does not translate to yards per route (ρ = −0.02). The **WR Burst Score** (equal-weight 20-yard + vertical + broad) does, modestly: OOF ρ = +0.29, 95% CI +0.01 to +0.54, n = 61. Combine top speed and the official 40 still translate to Sunday Speed (ρ = +0.63 and −0.59, both FDR-significant). Lasso sets every YPR coefficient to zero.
- **TE:** the tracking 20-yard is the lead and the best test vs yards per route (ρ = −0.56, n = 25, p = 0.004, CI excludes 0) and does not survive FDR (0.19). Adding jumps does not help; the Burst Score does not beat the 20-yard alone. No deployable multi-test model (n = 22, train AUC ≈ 1.00).
- **DB (CB + S):** no Combine-to-tackle finding. 20-yard vs tackle ρ = −0.07; Burst Score OOF ρ = +0.13 (CI includes 0). Year-only beats every multi-test model. Safeties have a higher median tackle rate than corners (0.100 vs 0.081) — a pooled DB median can confound role. Yards allowed and closing speed are not in this file. Tackle rate is a fallback.

Details in [`MULTI_TEST_MODELS.md`](MULTI_TEST_MODELS.md). Headline figures: Figure 10 (heatmap), Figure 11 (Bayesian forest), and Figure 13 (Burst Score).

## How to reproduce

Data is kept locally in `data/` (gitignored). From the repo root, with the nine official CSVs already in `data/`:

```bash
python3 -m venv .venv
.venv/bin/pip install pandas numpy scipy scikit-learn statsmodels matplotlib pyarrow pymc arviz nutpie
.venv/bin/python build_dataset.py          # official WR / CB / S Sunday Speed table
.venv/bin/python ssoe.py                   # SSOE scouting card, NGS incremental, CB speed tax
.venv/bin/python dl_burst.py               # DL get-off, pressure / sack success, Figures 5–6
.venv/bin/python gameplay_success.py       # WR production and CB/S tackle tests, Figure 7
.venv/bin/python combine_to_game.py        # Combine → Sunday matrix, year only, no pick; Burst Score; Figures 10–13
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
| `audit_stats.py` | Independent recomputation of every scorecard ρ, p, q-check and bootstrap interval (METRICS.md §11); writes `out/audit_stats.csv` |
| `power_check.py` | Simulation check of the minimum-detectable-effect formula (`out/power_simulation.csv`); MDE and power columns live in `scorecard.py` (METRICS §12) |
| `RESULTS_LOG.md` | Append-only working-session results |
| `PHASE2_RESULTS.md` | Skill-drill tests vs the 40 |
| `STRATEGY.md` | Concept, writeup plan, past-winner framing |
| `DATA_NOTES.md` | Data dictionary and gotchas from the Kaggle Data tab |
| `MULTI_TEST_MODELS.md` | Which Combine tests translate to Sunday (year only, no pick) |
| `build_dataset.py` | Official WR / CB / S player table |
| `ssoe.py` | Scouting-card leaderboard and supporting tests |
| `dl_burst.py` | DL Combine burst, get-off, pressure / sack |
| `gameplay_success.py` | WR production and CB/S tackle / TFL tests |
| `combine_gems.py`, `cb_deep_dive.py` | Retired stubs (draft-slot-defined analyses) |
| `multi_test_models.py` | Multi-test models (draft-year-only baseline), Figure 9 |
| `combine_to_game.py` | Combine → in-game matrix, 20-yard lead, Burst Score, year-only models and Bayesian pool, Figures 10–13 |
| `external/` | Public nflverse caches (not Kaggle), with attribution |
| `explore.py`, `profile.py` | First-pass exploration |
| `out/sunday_speed_players.csv` | Official skill-player table |
| `out/ssoe_leaderboard.csv` | Scouting card |
| `out/dl_burst_players.csv`, `out/dl_burst_tests.csv` | DL player table and tests |
| `out/gameplay_success_players.csv`, `out/gameplay_success_tests.csv` | Gameplay outcomes and tests |
| `out/multi_test_coefficients.csv`, `out/multi_test_auc.csv` | Multi-test outputs (year only) |
| `out/combine_to_game_spearman.csv`, `out/combine_to_game_best.csv`, `out/combine_to_game_lead20.csv` | Year-only Spearman matrix, best test, and 20-yard lead table |
| `out/combine_to_game_combos.csv`, `out/combine_to_game_burst.csv`, `out/combine_to_game_burst_players.csv`, `out/combine_to_game_burst_top10.csv` | Two-test combos and Burst Score (OOF ρ, 0–100, top-10) |
| `out/combine_to_game_auc.csv`, `out/combine_to_game_lasso_stability.csv` | Year-only model comparison and lasso stability |
| `out/combine_to_game_bayes.csv` | Bayesian hierarchical posterior ORs |
| `out/combine_to_game_appendix_cb_s.csv` | Appendix: CB vs S breakout |
| `out/figs/fig1_translation_scatter.png` | Combine vs Sunday Speed, by position |
| `out/figs/fig2_exchange_rate.png` | mph on Sunday per Combine mph |
| `out/figs/fig3_phase2_drills.png` | Do the skill drills beat the 40? |
| `out/figs/fig4_ssoe_leaderboard.png` | SSOE scouting card |
| `out/figs/fig5_dl_burst.png` | 10-yard split vs get-off, Edge vs Interior |
| `out/figs/fig6_combine_to_pressure.png` | Combine 10-yard split → pressure chain |
| `out/figs/fig7_gameplay_success.png` | WR production and CB/S tackle tests |
| `out/figs/fig9_multi_test_models.png` | Multi-test figure (year only) |
| `out/figs/fig10_combine_gameplay_heatmap.png` | Combine test × in-game metric Spearman heatmap (headline) |
| `out/figs/fig11_bayes_hierarchical.png` | Bayesian hierarchical forest (headline) |
| `out/figs/fig12_model_comparison.png` | Year-only all-models CV AUC comparison |
| `out/figs/fig13_burst_score.png` | Burst Score: OOF ρ vs 20-yard alone, and 0–100 scatters |
| `out/figs/cb_speed_tax.png`, `out/figs/cb_gauntlet.png` | CB deep-dive charts |

Owner: whatsgooglyKP. Work happens in this repo and in the Google Drive folder “NFL Big Data Bowl.”

## License

Code in this repository is released under the Apache License 2.0 (see `LICENSE`). Kaggle competition data is not included and remains subject to the competition rules.
