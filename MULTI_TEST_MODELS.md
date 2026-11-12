# Which Combine tests translate to Sunday?

**11/2026.** Kevin’s question, for this analysis, is not “does a player’s draft slot explain his rookie year?” Draft slot is out — not as a covariate, not as a baseline, and not as a sensitivity. The question is: **per position, which Combine metric translates to an important in-game success metric?**

This follow-up does three things on top of the year-only matrix:

1. **Merges corners and safeties into one headline group, DB.** Groups are now **WR, TE, DB, and one combined DL**. Running backs are still excluded (the 2023–2025 file has one RB, Sione Vaki). CB vs S, and Edge vs Interior, are small appendixes only — they are not in the heatmap, the models, the Bayesian pool, or the Burst Score.
2. **Leads with the 20-yard split from the 40-yard dash**, for every group. This time is **tracking-derived, not an official electronic 20-yard**. There is no official electronic 20-yard in the file. Times are interpolated from 40-yard-dash tracking (start line = max(x) − 40). Coverage is 80–88% of snap-eligible players in every group.
3. **Builds a coach-readable Burst Score** — a 2- or 3-test composite of the 20-yard and the jumps (broad and/or vertical) — two ways: equal-weight sign-aligned z-scores, and weights learned inside CV folds (ridge / lasso) and scored out-of-fold. The winning recipe is picked by out-of-fold Spearman ρ against the key in-game metric, compared to the 20-yard alone, and scaled 0–100 within the position.

This is a supporting analysis, not a new official metric. Official success definitions still live in `METRICS.md`. The punchline is conservative on purpose: we will not talk a coach into a draft rule the FDR-adjusted tests and the out-of-fold checks do not support.

Script: `combine_to_game.py`. Headline figures: `out/figs/fig10_combine_gameplay_heatmap.png` (Spearman matrix), `out/figs/fig11_bayes_hierarchical.png` (Bayesian forest), `out/figs/fig13_burst_score.png` (Burst Score). Model-comparison chart: `out/figs/fig12_model_comparison.png`.

---

## Coach summary

1. **Defensive linemen remain the one group with a clear Combine-to-success link, and the Burst Score is the cleanest new deliverable there.** A faster official 10-yard split still goes with a higher rookie pressure rate: Spearman ρ = −0.47 after controlling for draft year, n = 72, 95% CI −0.65 to −0.23, Holm p = 0.001, BH-FDR p = 7.3×10⁻⁵. The official 40 is essentially tied (ρ = −0.47). The **tracking 20-yard** is also FDR-significant vs pressure (ρ = −0.31, n = 71, 95% CI −0.53 to −0.08, FDR p = 0.012) but is weaker than the official 10-yard. Combining the 20-yard with both jumps into an equal-weight **DL Burst Score** raises the out-of-fold ρ from +0.31 (20-yard alone, sign-aligned) to **+0.45, 95% CI +0.18 to +0.66, n = 64, p = 0.000**. Adding the broad jump to the 20-yard also helps on a likelihood-ratio test (p = 0.025) and on the same-fold CV AUC (ΔAUC = +0.09). This is a composite a coach can take to a meeting.

2. **Receivers: the 20-yard alone does not translate to yards per route, but the Burst Score does, modestly.** 20-yard vs YPR is ρ = −0.02, n = 68, 95% CI −0.27 to +0.23, p = 0.90. The strongest single YPR lean is still the vertical (ρ = +0.22, n = 67, p = 0.079, FDR = 0.38), not FDR-significant. The **WR Burst Score** (equal-weight 20-yard + vertical + broad) has out-of-fold ρ = **+0.29, 95% CI +0.01 to +0.54, n = 61, p = 0.021**, and beats the 20-yard alone (OOF ρ = +0.02). Adding the vertical to the 20-yard helps on a likelihood-ratio test (p = 0.046) and on same-fold CV AUC (ΔAUC = +0.075). Combine top speed and the official 40 still translate to Sunday Speed (ρ = +0.63 and −0.59, both FDR-significant). Lasso, asked to predict above-median YPR, still sets every Combine coefficient to zero.

3. **Tight ends: the 20-yard split is the lead test, and adding jumps does not help.** Tracking 20-yard vs yards per route is ρ = −0.56 (n = 25, 95% CI −0.85 to −0.11, unadjusted p = 0.004). The CI excludes 0. It does **not** survive BH-FDR across the 51 tight-end cells (FDR p = 0.19, Holm p = 0.19). The Bayesian pool agrees: 20-yard OR = 0.42 per 1 SD (90% CI 0.11–0.85), P(direction) = 0.98. The best Burst recipe (20-yard + broad, equal-weight) has OOF ρ = +0.43, which **does not beat** the 20-yard alone (OOF ρ = +0.56). Multivariable models on n = 22 still fit the training sample almost perfectly (AUC 0.98–1.00) and are not a draft rule.

4. **Defensive backs (corners + safeties): no Combine-to-tackle finding, and a role caveat.** The 20-yard vs tackle rate is ρ = −0.07, n = 65, 95% CI −0.33 to +0.20, p = 0.59. The “best” single test on the key metric is Combine top speed, ρ = −0.24 (n = 65, p = 0.056, FDR = 0.31), which is the **wrong athletic direction** and is not significant. The two FDR-significant DB cells are both Sunday Speed (official 40 ρ = −0.44; weight ρ = −0.52) — a size–speed tradeoff, not a tackle-rate rule. The **DB Burst Score** (20-yard + vertical, equal-weight) OOF ρ = +0.13, 95% CI −0.15 to +0.40, n = 59, p = 0.31, is not distinguishable from chance. **Caveat:** among ≥50-snap eligible DBs, corners have a median tackle rate of 0.081 (n = 42) and safeties 0.100 (n = 34). A pooled DB median can confound role with athleticism. Yards allowed and closing speed are not in this file. Year-only beats every multi-test model on tackle rate.

5. **Equal-weight beat learned weights in every group.** Ridge and lasso weights, fit inside each training fold and scored out-of-fold so they cannot overfit the reported ρ, never beat the simple equal-weight Burst. At DB they go the wrong way (OOF ρ negative). Do not learn Burst weights from this sample. The winning recipe in every group is equal-weight, 1/k on sign-aligned z-scores (20-yard flipped so that faster is higher).

6. **What we recommend Kevin decide.** Kevin leans toward lasso as the safest model. We agree at **DL** (lasso CV AUC 0.674 vs year-only 0.596; surviving official 40, vertical, and weight) and at **WR** (lasso is safest *because* it refuses every test; use the Burst Score as the athletic composite, not a logistic rule). At **TE**, do not deploy a multi-test model; report the 20-yard lean. At **DB**, year-only wins; do not use a Combine multi-test rule for tackle rate.

---

## Who is in the sample

All three Combine classes (2023–2025) are pooled. A player enters a cell if he clears that outcome’s snap (or route) floor and has the Combine test. Pairwise n therefore changes from cell to cell. Draft pick is not used. The DB success median is taken among all corners and safeties with ≥50 defensive snaps, together.

| Group | In the file | Key-outcome eligible | Key floor | 20-yard n (coverage) |
|---|---:|---:|---|---|
| WR | 106 | 77 | ≥20 regular-season routes | 68 / 77 (88%) |
| TE | 42 | 29 | ≥20 regular-season routes | 25 / 29 (86%) |
| DB | 113 (60 CB, 53 S) | 76 (42 CB, 34 S) | ≥50 regular-season defensive snaps | 65 / 76 (86%) |
| DL | 118 | 89 | ≥20 regular-season pass-rush snaps | 71 / 89 (80%) |

Group-wide 20-yard coverage (including players below the snap floor): WR 93/106 (88%), TE 34/42 (81%), DB 96/113 (85%), DL 93/118 (79%).

Binary “success” is above the median of the key metric among snap-eligible players (strict `>`, including those missing a given test). Key metrics: WR/TE yards per route; DB tackle involvement rate (fallback — yards allowed and closing speed are not computable from this file); DL pressure rate.

---

## Lead test: the 20-yard split

The 20-yard split is **tracking-derived from the 40-yard dash, not official electronic.** It is the first row of the heatmap, the first predictor in the joint models, and the first test reported for every group. Year-controlled Spearman vs the key in-game metric, 2,000-bootstrap 95% CIs, seed 2027. Holm and BH-FDR are within the group, across every valid (test × outcome) cell — not just the key-metric column.

| Group | Key metric | n | Coverage | ρ | 95% CI | p | Holm | FDR | FDR-sig? | Best other test on the same metric |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| WR | Yards per route | 68 | 88% | −0.02 | −0.27, +0.23 | 0.90 | 1.00 | 0.98 | no | Vertical, ρ = +0.22, p = 0.079, FDR = 0.38 |
| TE | Yards per route | 25 | 86% | −0.56 | −0.85, −0.11 | 0.004 | 0.19 | 0.19 | no | Official 10-yard, ρ = −0.38, p = 0.064, FDR = 0.66 |
| DB | Tackle rate | 65 | 86% | −0.07 | −0.33, +0.20 | 0.59 | 1.00 | 0.90 | no | Combine top speed, ρ = −0.24, p = 0.056, FDR = 0.31 (wrong direction) |
| DL | Pressure rate | 71 | 80% | −0.31 | −0.53, −0.08 | 0.009 | 0.12 | 0.012 | **yes** | Official 10-yard, ρ = −0.47, p = 2.7×10⁻⁵, FDR = 7.3×10⁻⁵ |

The 20-yard is the **best** key-metric test at TE (a lean, CI excludes 0, not FDR-significant). It is FDR-significant at DL but is second to the official 10-yard. It is essentially zero at WR and DB.

---

## Best single test per group (key metric)

Picked by FDR, then raw p, then |ρ|, among year-controlled Spearmans of every Combine test against the key metric.

| Group | Key metric | Best test | n | ρ | 95% CI | p | FDR | FDR-sig? |
|---|---|---|---:|---:|---|---:|---:|---|
| WR | Yards per route | Vertical | 67 | +0.22 | −0.05, +0.45 | 0.079 | 0.38 | no |
| TE | Yards per route | 20-yard (tracking) | 25 | −0.56 | −0.85, −0.11 | 0.004 | 0.19 | no |
| DB | Tackle rate | Combine top speed | 65 | −0.24 | −0.46, +0.04 | 0.056 | 0.31 | no (wrong direction) |
| DL | Pressure rate | Official 10-yard | 72 | −0.47 | −0.65, −0.23 | 2.7×10⁻⁵ | 7.3×10⁻⁵ | **yes** |

FDR-significant cells overall: **WR 6/66** (all Sunday Speed or size vs deep separation — **none YPR**); **TE 0/51**; **DB 2/33** (official 40 and weight vs Sunday Speed — **none tackle rate**); **DL 37/44**, including the get-off chain (official 10-yard vs speed at 1.0 s, ρ = −0.80).

---

## Burst Score

**Burst Score** is a coach-readable composite, built separately at each position, from the 20-yard split plus the broad jump and/or the vertical. Faster 20-yard times and longer jumps all score higher (the 20-yard is sign-flipped). Two constructions, both evaluated out-of-fold so the reported ρ is not in-sample overfit:

1. **Equal-weight.** Mean of sign-aligned z-scores. In the out-of-fold evaluation, means and SDs come from the training fold only.
2. **Learned.** Ridge and lasso weights are fit on the training fold (on year-residualized key-metric values, so the weights are an athletic composite, not a year effect) and applied to the held-out fold. The player’s score is the average of his out-of-fold predictions.

The winning 2- or 3-test recipe and method is the one with the highest year-controlled out-of-fold Spearman ρ against the key metric. The 20-yard alone is the comparison baseline, not a Burst candidate. The winning score is scaled **0–100 within the position** (percentile rank among players who have the winning recipe’s tests). When equal-weight wins, the named list uses the full-sample equal-weight composite (the weights are not learned from the outcome). When a learned method wins, the named list uses averaged out-of-fold predictions.

**Equal-weight won in every group.** Learned ridge and lasso never beat it out-of-fold.

| Group | Winning Burst Score | Weights | n | OOF ρ | 95% CI | p | 20-yard alone OOF ρ | Beats 20-yard? |
|---|---|---|---:|---:|---|---:|---:|---|
| WR | 20-yard + vertical + broad, equal-weight | 33% / 33% / 33% | 61 | **+0.29** | +0.01, +0.54 | 0.021 | +0.02 | **yes** |
| TE | 20-yard + broad jump, equal-weight | 50% / 50% | 22 | +0.43 | −0.06, +0.77 | 0.046 | **+0.56** | **no** |
| DB | 20-yard + vertical, equal-weight | 50% / 50% | 59 | +0.13 | −0.15, +0.40 | 0.31 | +0.08 | numerically, but CI includes 0 |
| DL | 20-yard + vertical + broad, equal-weight | 33% / 33% / 33% | 64 | **+0.45** | +0.18, +0.66 | 0.000 | +0.31 | **yes** |

On the same common complete-case sample (players with the 20-yard *and* both jumps), adding jumps to the 20-yard:

- **WR** (n = 61): 20-yard + vertical, likelihood-ratio p = 0.046, same-fold ΔCV-AUC = +0.075 (Wilcoxon p = 3×10⁻⁹). Three-test equal-weight ρ = +0.29 (CI just excludes 0). CV R² is negative for every recipe — the Burst is a rank correlation, not a variance-explained claim.
- **TE** (n = 22): adding either jump or both *lowers* CV AUC and equal-weight ρ. Likelihood-ratio tests are not significant. Use the 20-yard alone.
- **DB** (n = 53): adding jumps does not help (LR p ≥ 0.60; ΔCV-AUC negative). The 20-yard + vertical equal-weight ρ = +0.12 is the least-weak combo and is still consistent with zero.
- **DL** (n = 64): 20-yard + broad, LR p = 0.025, ΔCV-AUC = +0.09; 20-yard + vertical, LR p = 0.038, ΔCV-AUC = +0.09; all three, LR p = 0.063, equal-weight ρ = +0.45 (CI +0.18 to +0.66). Standardized year-controlled coefficient on the broad jump in the two-test model is +0.011 pressure-rate points per 1 SD (95% bootstrap CI +0.001 to +0.021).

Figure 13 (`out/figs/fig13_burst_score.png`) shows the out-of-fold ρ comparison (gold outline = winning method) and the 0–100 Burst vs the key metric, with the DB panel colored by role.

### Top 10 by Burst Score, per group

Burst is the 0–100 percentile within the position. 20-yard is in seconds (lower is faster). Vertical and broad are in inches. “Yes” under Key is above-median on the group’s key metric (yards per route, tackle rate, or pressure rate).

**WR** — 20-yard + vertical + broad, equal-weight. Key = yards per route.

| Rk | Player | Year | Burst | YPR | 20-yd | Vert | Broad | Above med.? |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Ricky Pearsall | 2024 | 100 | 1.66 | 2.299 | 42.0 | 129 | yes |
| 2 | Jaylin Noel | 2025 | 98 | 1.48 | 2.472 | 41.5 | 134 | yes |
| 3 | Jalin Hyatt | 2023 | 97 | 0.69 | 2.458 | 40.0 | 135 | no |
| 4 | Jermaine Burton | 2024 | 95 | 1.13 | 2.383 | 38.5 | 133 | no |
| 5 | Demario Douglas | 2023 | 93 | 1.68 | 2.521 | 39.5 | 134 | yes |
| 6 | Jaylin Lane | 2025 | 92 | 1.21 | 2.482 | 40.0 | 132 | yes |
| 7 | Devontez Walker | 2024 | 90 | 2.12 | 2.625 | 40.5 | 134 | yes |
| 8 | Brian Thomas | 2024 | 88 | 2.08 | 2.192 | 38.5 | 126 | yes |
| 9 | Jonathan Mingo | 2023 | 87 | 0.75 | 2.426 | 39.5 | 129 | no |
| 10 | Jason Brownlee | 2023 | 85 | 0.30 | 2.534 | 39.5 | 131 | no |

**TE** — 20-yard + broad, equal-weight. Key = yards per route. This list is a Burst ranking, **not** a recommendation to prefer Burst over the 20-yard alone (the 20-yard wins at TE).

| Rk | Player | Year | Burst | YPR | 20-yd | Vert | Broad | Above med.? |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Elijah Higgins | 2023 | 100 | 1.18 | 2.508 | 35.0 | 126 | yes |
| 2 | Davis Allen | 2023 | 95 | 0.91 | 2.676 | 38.5 | 125 | no |
| 3 | Jackson Hawes | 2025 | 90 | 2.08 | 2.628 | 34.5 | 121 | yes |
| 4 | Terrance Ferguson | 2025 | 86 | 1.39 | 2.687 | 39.0 | 122 | yes |
| 5 | Theo Johnson | 2024 | 81 | 1.15 | 2.856 | 39.5 | 125 | no |
| 6 | Will Mallory | 2023 | 76 | 1.24 | 2.652 | 36.5 | 121 | yes |
| 7 | Tucker Kraft | 2023 | 71 | 1.82 | 2.716 | 34.0 | 122 | yes |
| 8 | Ben Sinnott | 2024 | 67 | 0.74 | 3.057 | 40.0 | 126 | no |
| 9 | Harold Fannin | 2025 | 62 | 1.75 | 2.720 | 34.0 | 118 | yes |
| 10 | Darnell Washington | 2023 | 57 | 1.34 | 2.945 | 31.0 | 122 | yes |

**DB** — 20-yard + vertical, equal-weight. Key = tackle involvement rate. Role is in parentheses. The CI on this Burst includes 0; treat the list as a demonstration, not a ranking to draft from.

| Rk | Player | Role | Year | Burst | Tackle | 20-yd | Vert | Broad | Above med.? |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Quan Martin | S | 2023 | 100 | 0.101 | 2.524 | 44.0 | 133 | yes |
| 2 | Kitan Crawford | S | 2025 | 98 | 0.088 | 2.491 | 41.5 | 128 | yes |
| 3 | Sydney Brown | S | 2023 | 97 | 0.094 | 2.525 | 40.5 | 130 | yes |
| 4 | Maxwell Hairston | CB | 2025 | 95 | 0.053 | 2.430 | 39.5 | 129 | no |
| 5 | Marques Sigle | S | 2025 | 93 | 0.125 | 2.319 | 38.0 | 130 | yes |
| 6 | Marcellas Dial | CB | 2024 | 91 | 0.083 | 2.581 | 40.5 | 129 | no |
| 7 | Deonte Banks | CB | 2023 | 90 | 0.073 | 2.773 | 42.0 | 136 | no |
| 8 | Jaylin Simpson | S | 2024 | 88 | 0.136 | 2.547 | 39.5 | 133 | yes |
| 9 | Cam Hart | CB | 2024 | 86 | 0.079 | 2.573 | 39.5 | 130 | no |
| 10 | Mike Sainristil | CB | 2024 | 84 | 0.087 | 2.638 | 40.0 | 131 | yes |

**DL** — 20-yard + vertical + broad, equal-weight. Key = pressure rate.

| Rk | Player | Year | Burst | Pressure | 20-yd | Vert | Broad | Above med.? |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Adetomiwa Adebawore | 2023 | 100 | 0.092 | 2.443 | 37.5 | 125 | yes |
| 2 | Byron Young | 2023 | 98 | 0.115 | 2.635 | 38.0 | 132 | yes |
| 3 | Yasir Abdullah | 2023 | 97 | 0.074 | 2.627 | 36.5 | 129 | yes |
| 4 | Jalyx Hunt | 2024 | 95 | 0.128 | 2.739 | 37.5 | 128 | yes |
| 5 | Jared Verse | 2024 | 94 | 0.149 | 2.651 | 35.0 | 127 | yes |
| 6 | Princely Umanmielen | 2025 | 92 | 0.058 | 2.783 | 38.0 | 126 | no |
| 7 | Tyler Baron | 2025 | 90 | 0.068 | 2.570 | 35.5 | 121 | no |
| 8 | Isaiah Foskey | 2023 | 89 | 0.069 | 2.626 | 34.0 | 125 | no |
| 9 | YaYa Diaby | 2023 | 87 | 0.115 | 2.685 | 37.0 | 120 | yes |
| 10 | Barryn Sorrell | 2025 | 86 | 0.087 | 2.619 | 34.0 | 121 | yes |

The full scored lists are in `out/combine_to_game_burst_players.csv` and `out/combine_to_game_burst_top10.csv`. Recipe-level out-of-fold ρ for equal-weight, ridge, and lasso is in `out/combine_to_game_burst.csv`. Combo likelihood-ratio tests, standardized coefficients, and same-fold CV are in `out/combine_to_game_combos.csv`.

---

## Model comparison (year only, no draft pick)

Above-median key success, 20×5 RepeatedStratifiedKFold, seed 2027. Predictors: the 20-yard tracking split (lead), official 40, official 10-yard, vertical, broad jump, height, weight, Combine top speed, and a year index. Complete-case n is smaller than the pairwise n because every model test must be present. The year-only logistic is the baseline.

| Group | n (success) | Year only | L2 | Firth | Lasso | Elastic net | NB | Bayes LOO | Bayes 5-fold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WR | 61 (31) | 0.399 | 0.446 | 0.478 | 0.431 | 0.424 | 0.399 | 0.446 | 0.448 |
| TE | 22 (10) | 0.264 | 0.854 | 0.828 | 0.826 | 0.815 | 0.653 | 0.742 | 0.683 |
| DB | 53 (26) | **0.618** | 0.617 | 0.604 | 0.590 | 0.598 | 0.619 | 0.597 | 0.651 |
| DL | 64 (32) | 0.596 | 0.655 | 0.611 | 0.674 | 0.703 | 0.727 | 0.688 | 0.702 |

Train AUCs that flag overfit: TE L2 and Firth train = 1.000 (lasso train = 0.983, C = 1.67, six surviving tests including a 20-yard OR of 0.12). WR lasso C = 0.01, train AUC = 0.500, every Combine coefficient zeroed. DB year-only 0.618 beats lasso 0.590; lasso keeps height (OR 0.72, stability 0.97) and Combine top speed (OR 0.91, stability 0.85) without beating the baseline. DL lasso 0.674 vs year 0.596, overfit gap 0.086; surviving official 40 (OR 0.66, stability 0.76), vertical (OR 1.11, stability 0.72), weight (OR 0.90, stability 0.59). The official 10-yard and the 20-yard are collinear with the official 40 and are zeroed (stability 0.11 and 0.27). DL naive Bayes is 0.727 with a small overfit gap (0.031); Kevin leans lasso as safest, and we agree for a deployable rule.

Continuous ridge / lasso / EN CV R² is negative at WR, TE, and DB, and essentially zero at DL (ridge +0.024). The Burst Score’s claim is a rank correlation, not variance explained.

---

## Bayesian hierarchical logistic

Partial pooling of Combine slopes and intercepts across the four groups, shared year slope, no draft pick. Tests are z-scored within group. PyMC 6 / nutpie, 4×2000+2000, `target_accept=0.9`, seed 2027. Pooled n = 200 (WR 61 + TE 22 + DB 53 + DL 64). max R̂ = 1.002, 0 divergences, 0/200 Pareto k > 0.7. 90% equal-tail credible intervals. P(direction) is the posterior share on the pre-declared athletic side (faster times OR < 1; higher jumps / top speed OR > 1). Height and weight have no pre-declared side.

Stand-outs with P(direction) ≥ 0.90:

- **WR official 40:** OR 0.46 (90% 0.20–0.82), P = 0.98. (This is a Sunday-Speed-adjacent signal; it does not make the official 40 a YPR rule. LOO AUC at WR is 0.45.)
- **TE 20-yard:** OR 0.42 (90% 0.11–0.85), P = 0.98. Official 40 OR 0.50 (90% 0.17–1.00), P = 0.95. This is the Bayesian confirmation of the 20-yard lean, on n = 22, and should be read with the FDR and the overfit caveats above.
- **DL official 40:** OR 0.49 (90% 0.16–1.00), P = 0.95.
- **Pooled official 40:** OR 0.57 (90% 0.26–1.04), P = 0.94.

At DB, Combine top speed has OR 0.52 (90% 0.24–0.90) with P(direction) = 0.03 — the posterior is on the *wrong* athletic side, consistent with the pairwise ρ = −0.24. Height OR 0.57 (90% 0.31–0.86) has no pre-declared direction. Neither is a tackle-rate rule.

PSIS-LOO AUC: WR 0.45, TE 0.74, DB 0.60, DL 0.69, pooled 0.61. One-pass 5-fold: WR 0.45, TE 0.68, DB 0.65, DL 0.70, mean 0.63. Bayesian AUCs are not 20×5 and are not directly comparable to the table above.

---

## Recommendations (for Kevin to decide; he leans lasso)

- **WR — lasso, because it refuses the tests.** Nothing beats chance on above-median YPR. Use the **WR Burst Score** (equal-weight 20-yard + vertical + broad, OOF ρ = +0.29) as the athletic composite, and keep using the official 40 / Combine top speed as a Sunday Speed test. Do not use a logistic basket as a receiving-production grade.
- **TE — no deployable model; report the 20-yard lean.** ρ = −0.56, 95% CI −0.85 to −0.11, n = 25, p = 0.004, FDR = 0.19. The Bayesian 20-yard OR is 0.42 (P = 0.98). The Burst Score does not beat the 20-yard alone. Do not use the lasso (train AUC 0.98, wild ORs) as a rule.
- **DB — year only; no multi-test rule.** Year-only CV AUC 0.618 beats lasso 0.590. The Burst Score is consistent with chance. Document the CB vs S tackle-rate difference (0.081 vs 0.100) before anyone reads a pooled DB median as athleticism.
- **DL — lasso, and use the Burst Score as the companion composite.** Lasso CV AUC 0.674 vs year 0.596; surviving official 40, vertical, and weight. **DL Burst Score** (equal-weight 20-yard + vertical + broad) OOF ρ = +0.45, 95% CI +0.18 to +0.66, n = 64. The official 10-yard remains the best *single* test vs pressure (ρ = −0.47).

---

## Appendix: CB vs S, and Edge vs Interior

**CB vs S** (not in the heatmap, models, Bayes, or Burst). Among ≥50-snap eligible: CB n = 42, median tackle rate = 0.081; S n = 34, median tackle rate = 0.100. The 20-yard vs tackle is ρ = +0.03, n = 36, p = 0.86 at CB, and ρ = −0.03, n = 29, p = 0.88 at S. The closest CB tackle-rate lean is still the broad jump (ρ = +0.34, n = 32, p = 0.058, FDR = 0.49). The closest S lean is height (ρ = −0.33, n = 34, p = 0.060, FDR = 0.54, no pre-declared direction). Zero FDR-significant cells in either role. Full table: `out/combine_to_game_appendix_cb_s.csv`.

**Edge vs Interior** (same as the previous year-only run, still appendix-only). Official 10-yard vs pressure is an Edge lean (ρ = −0.36, n = 39, p = 0.025, FDR = 0.077), not Interior (ρ = −0.15, n = 33, p = 0.41). The 10-yard vs get-off holds in both (Edge ρ = −0.57, FDR = 0.002; Interior ρ = −0.41, FDR = 0.047). The tracking 20-yard vs pressure is a weaker Edge lean (ρ = −0.29, n = 38, p = 0.076) and is near zero at Interior (ρ = +0.03, n = 33). Full table: `out/combine_to_game_appendix_edge_interior.csv`.

---

## How this was computed

- Year-only residualization (draft-year dummies, `drop_first`). No draft pick anywhere.
- Spearman: n ≥ 12, 2,000 bootstrap CIs, seed 2027. Holm and BH-FDR within group across every valid (test × outcome) cell. Heatmap stars are FDR < 0.05. The 20-yard is the first row.
- Burst and combos: sign-aligned z-scores (20-yard × −1, jumps × +1). Equal-weight = mean of aligned z. Learned = RidgeCV / LassoCV inside each training fold of a 20×5 RepeatedKFold (3-fold when n < 25), seed 2027, scored on the held-out fold; one average out-of-fold score per player. Year residualization of the target uses training-fold year dummies only. Pick the 2- or 3-test recipe by out-of-fold ρ. Comparison to the 20-yard alone uses the same protocol. Combo likelihood-ratio tests and standardized coefficients are year-residualized OLS; same-fold CV R² (OLS) and CV AUC (L2 logistic) use one shared split generator per sample; the ΔAUC p-value is a paired Wilcoxon on fold AUCs. 0–100 is the percentile rank within the position.
- Models: 20×5 RepeatedStratifiedKFold, seed 2027; nested `LogisticRegressionCV` (saga) for lasso / elastic net; Firth from `multi_test_models.py`; year-only logistic baseline. Continuous RidgeCV / LassoCV / ElasticNetCV, CV R².
- Bayesian: PyMC 6 / nutpie, non-centered partial pooling, 4×2000+2000, `target_accept=0.9`, seed 2027. PSIS-LOO uses `loo.elpd` (arviz 1.3). One-pass 5-fold is not 20×5.

Reproduce, from the repo root with the venv and the nine official CSVs already in `data/`:

```bash
.venv/bin/python combine_to_game.py
```

`--bayes-only` resumes from the checkpoint after the 20×5 models. `--skip-bayes` writes the Spearman, Burst, and 20×5 outputs without the hierarchical model.

Outputs: `out/combine_to_game_spearman.csv`, `out/combine_to_game_best.csv`, `out/combine_to_game_lead20.csv`, `out/combine_to_game_combos.csv`, `out/combine_to_game_burst.csv`, `out/combine_to_game_burst_players.csv`, `out/combine_to_game_burst_top10.csv`, `out/combine_to_game_auc.csv`, `out/combine_to_game_lasso_stability.csv`, `out/combine_to_game_coefficients.csv`, `out/combine_to_game_continuous.csv`, `out/combine_to_game_bayes.csv`, `out/combine_to_game_recommendations.csv`, `out/combine_to_game_appendix_edge_interior.csv`, `out/combine_to_game_appendix_cb_s.csv`, `out/combine_to_game_players.csv`. No draft-pick column is in any of these analysis files.
