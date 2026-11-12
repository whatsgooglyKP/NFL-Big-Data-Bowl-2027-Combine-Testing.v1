# Which Combine tests translate to Sunday?

**11/2026.** Kevin’s question, for this analysis, is not “does a player’s draft slot explain his rookie year?” Draft slot is out — not as a covariate, not as a baseline, and not as a sensitivity. The question is: **per position, which Combine metric translates to an important in-game success metric?**

Groups are **WR, TE, CB, S, and one combined DL**. Running backs are excluded (the 2023–2025 file has one RB, Sione Vaki). Edge vs Interior is a small appendix only; it is not in the heatmap, the models, or the Bayesian pool.

This is a supporting analysis, not a new official metric. Official success definitions still live in `METRICS.md`. The punchline is conservative on purpose: we will not talk a coach into a draft rule the FDR-adjusted tests and the cross-validation do not support.

Script: `combine_to_game.py`. Headline figures: `out/figs/fig10_combine_gameplay_heatmap.png` (Spearman matrix) and `out/figs/fig11_bayes_hierarchical.png` (Bayesian forest). Model-comparison chart: `out/figs/fig12_model_comparison.png`.

---

## Coach summary

1. **Defensive linemen are the one group with a clear Combine-to-success link.** A faster official 10-yard split goes with a higher rookie pressure rate: Spearman ρ = −0.47 after controlling for draft year, n = 72, 95% CI −0.66 to −0.23, Holm p = 0.001, BH-FDR p = 7×10⁻⁵. The official 40 is essentially tied (ρ = −0.47). The same tests, plus the jumps and Combine top speed, also line up with get-off (speed 1.0 s after the snap) and with sack rate. This is the cell a coach can take to a meeting.

2. **Receivers: Combine speed shows up as Sunday Speed, not as yards per route.** Combine top speed vs deep-route game speed is ρ = +0.63 (n = 62, 95% CI +0.43 to +0.76, FDR p = 2×10⁻⁶). The official 40 is the same story with the opposite sign (ρ = −0.59, n = 63, FDR p = 9×10⁻⁶). Nothing is FDR-significant for yards per route. The strongest YPR lean is the vertical (ρ = +0.22, n = 67, p = 0.079, FDR = 0.38). Lasso, asked to predict above-median YPR, sets every Combine coefficient to zero. Keep using the 40 as a Sunday Speed test. Do not use it, or a basket of tests, as a receiving-production grade.

3. **Tight ends: a 20-yard lean, not a finding.** The tracking-derived 20-yard split vs yards per route is ρ = −0.56 (n = 25, 95% CI −0.84 to −0.10, unadjusted p = 0.004). That is the strongest key-metric lean outside of the defensive line, and the CI excludes 0. It does **not** survive BH-FDR across the 51 tight-end cells (FDR p = 0.19). Multivariable models on n = 22 fit the training sample almost perfectly (AUC 0.99–1.00) and are not a draft rule.

4. **Corners and safeties: no FDR-significant Combine-to-success cell.** The closest tackle-rate leans are the broad jump for corners (ρ = +0.34, n = 32, p = 0.058) and height for safeties (ρ = −0.33, n = 34, p = 0.060, no pre-declared direction, CI crosses 0). Yards allowed and closing speed are not in this file — we say so below. Tackle rate is a fallback, and the earlier safety gauntlet result was already wrong-signed. Do not build a coverage rule from these numbers.

5. **What we recommend Kevin decide.** Kevin leans toward lasso as the safest model. We agree at **DL** (lasso CV AUC 0.69 vs a year-only 0.60, modest overfit, surviving official 40, vertical, and weight) and at **WR** (lasso is safest *because* it refuses every test). At **TE, CB, and S**, samples are small, overfit is large, and we would not deploy a multi-test rule; the pairwise matrix is the honest report.

---

## Who is in the sample

All three Combine classes (2023–2025) are pooled. A player enters a cell if he clears that outcome’s snap (or route) floor and has the Combine test. Pairwise n therefore changes from cell to cell. Draft pick is not used.

| Group | In the file | Key-outcome eligible | Key floor |
|---|---:|---:|---|
| WR | 106 | 77 | ≥20 regular-season routes (yards per route) |
| TE | 42 | 29 | ≥20 regular-season routes (yards per route) |
| CB | 60 | 42 | ≥50 regular-season defensive snaps (tackle rate) |
| S | 53 | 34 | ≥50 regular-season defensive snaps (tackle rate) |
| DL | 118 | 89 | ≥20 regular-season pass-rush snaps (pressure rate) |
| RB | 1 | — | Excluded from every test and every model |

Sunday Speed uses the official sample already floored in `METRICS.md` (WR 69, CB 39, S 31 with a computed Sunday Speed). Deep-route separation and YAC-over-expected use the floors already applied in `gameplay_success.py`. Tight ends have no official Sunday Speed (that sample is WR / CB / S).

**Combine tests in the matrix:** official 40, official 10-yard split, tracking-derived 20-yard split, vertical, broad jump, 3-cone, short shuttle, height, weight, Combine top speed (40-yard tracking, mph), and 40-yard peak acceleration. There is no official electronic 20-yard time; the 20-yard column is interpolated from 40-yard tracking and is labeled that way. 3-cone and shuttle are sparse (WR 24–30, TE 12–13, CB 11–16, S 6, DL 34–35) and drop out of many cells (grey on the heatmap).

**Joint models** use official 40, official 10-yard, vertical, broad jump, height, weight, and Combine top speed, plus year. 3-cone, shuttle, the tracking 20-yard, and 40-yard accel stay in the pairwise matrix only: the last two are near-collinear with the official 40 and Combine top speed, and 3-cone / shuttle are too thin for a complete-case model.

---

## Outcomes

The **key success metric** at each position is above-median among rookies who clear the snap floor — including players who later drop out of a cell because a Combine test is missing. “Above” is strict (`>`). Year is the only control. Draft pick is not used.

| Group | Key success metric | Companions | What we cannot measure |
|---|---|---|---|
| WR | Yards per route | Deep-route game speed (official Sunday Speed), deep-route separation, YAC over expected, target rate, deep yards per deep route | — |
| TE | Yards per route | Target rate, deep-route separation, YAC over expected, deep yards per deep route | Sunday Speed (not in the official WR/CB/S sample; we did not re-stream game tracking) |
| CB | Tackle involvement rate (**fallback**) | Tackle-for-loss rate; game top speed on coverage plays (official Sunday Speed) | **Yards allowed per coverage snap** is not computable: this file has no target-allowed or reception-yards field on a defender. **Closing / pursuit speed** is not computable: only the 510 rookies are tracked, with no opponent or ball-carrier tracks. |
| S | Tackle involvement rate (**fallback**) | Same companions as CB | Same gaps as CB. The earlier safety gauntlet → tackle-rate link was **wrong-signed**, so tackle rate is a weak coverage proxy. |
| DL | Pressure rate | Sack rate; tracking get-off (speed at 1.0 s, higher is faster); NFL get-off time (lower is faster) | — |

---

## The Spearman matrix (year only)

Every available Combine test is paired with every in-game metric at that position. Both sides are residualized on draft-year dummies (no pick). We report Spearman ρ, a 95% bootstrap CI (2,000 resamples, year residualized inside each replicate, seed 2027), the unadjusted p, a **Holm** p, and a **BH-FDR** p. The multiple-testing family is **every valid (test × outcome) cell at that position** (n ≥ 12). Heatmap stars are BH-FDR < 0.05.

**Best Combine test for each group’s key success metric:**

| Group | Key metric | Best test | n | ρ (year-controlled) | 95% CI | p | Holm | FDR | FDR-sig? |
|---|---|---|---:|---:|---|---:|---:|---:|---|
| WR | Yards per route | Vertical | 67 | +0.22 | −0.05 to +0.45 | 0.079 | 1.00 | 0.38 | No |
| TE | Yards per route | 20-yard (tracking) | 25 | **−0.56** | **−0.84 to −0.10** | 0.004 | 0.19 | 0.19 | No (lean) |
| CB | Tackle rate | Broad jump | 32 | +0.34 | −0.15 to +0.62 | 0.058 | 1.00 | 0.49 | No |
| S | Tackle rate | Height | 34 | −0.33 | −0.59 to +0.03 | 0.060 | 1.00 | 0.54 | No |
| DL | Pressure rate | **Official 10-yard** | 72 | **−0.47** | **−0.66 to −0.23** | 2.7×10⁻⁵ | **0.001** | **7.3×10⁻⁵** | **Yes** |

“Best” is the smallest FDR p, then the smallest unadjusted p, among tests with a valid ρ. For WR, CB, and S, that is a lean at most: the CI includes 0 or the FDR p is large. For safeties the “best” test is height, which had no pre-declared direction.

**FDR-significant cells a coach should actually look at:**

- **DL, many cells (37 of 44).** Official 10-yard and official 40 vs pressure (both ρ = −0.47, n = 72). The same two tests vs sack rate (ρ ≈ −0.37, n = 72, FDR < 0.003). Get-off is even tighter: official 10-yard vs speed at 1.0 s, ρ = −0.80, n = 72, FDR p = 7×10⁻¹⁶; official 40, broad jump, vertical, and Combine top speed all go the expected way and all survive FDR. Weight vs get-off is ρ = −0.85 (n = 89): heavier defensive linemen get off slower, which is close to a physical fact and is not itself a scouting surprise. 3-cone and short shuttle vs pressure also survive FDR (ρ = −0.65 and −0.59) but on n = 34–35.
- **WR, six cells, none of them yards per route.** Combine top speed vs Sunday Speed, ρ = +0.63, n = 62, FDR p = 2×10⁻⁶. Official 40 vs Sunday Speed, ρ = −0.59, n = 63, FDR p = 9×10⁻⁶. Heavier and taller receivers also run slower on Sunday and get less deep-route separation (weight vs Sunday Speed ρ = −0.50, n = 69; weight vs deep separation ρ = −0.48, n = 76; height vs separation ρ = −0.40, n = 76; height vs Sunday Speed ρ = −0.35, n = 69). That is a size–speed tradeoff. It does not flow through to yards per route.
- **TE, CB, S: zero FDR-significant cells.** The tight-end 20-yard lean is the one to remember, and we remember it as a lean.

The full matrix is `out/combine_to_game_spearman.csv` and Figure 10.

---

## Model comparison (year-only baseline, no pick)

Binary outcome: above the position median on the **key** success metric, among snap-eligible rookies. Complete cases on the seven joint-model Combine tests plus year: WR 61, TE 22, CB 29, S 24, DL 64. The baseline is a year-only logistic. Every frequentist model uses the same **20×5 RepeatedStratifiedKFold, seed 2027**. Lasso and elastic net tune `C` (and `l1_ratio`) by nested CV inside each outer training fold. Bayesian AUCs are labeled separately: they are PSIS-LOO or a single 5-fold pass, not 20×5.

CV AUC (mean ± SD of fold AUCs). Train AUC is in parentheses so overfitting is visible.

| Model | WR n=61 | TE n=22 | CB n=29 | S n=24 | DL n=64 |
|---|---:|---:|---:|---:|---:|
| Year only | 0.40 ± 0.07 (0.50) | 0.26 ± 0.20 (0.54) | 0.35 ± 0.13 (0.50) | 0.35 ± 0.22 (0.51) | 0.60 ± 0.14 (0.59) |
| L2 logistic | 0.47 ± 0.15 (0.71) | 0.62 ± 0.29 (0.90) | 0.68 ± 0.21 (0.87) | 0.70 ± 0.26 (0.87) | 0.67 ± 0.13 (0.77) |
| Firth logistic | 0.49 ± 0.15 (0.69) | 0.67 ± 0.25 (1.00) | 0.64 ± 0.21 (0.87) | 0.67 ± 0.27 (0.91) | 0.63 ± 0.10 (0.78) |
| **Lasso L1** | 0.44 ± 0.11 (0.50) | 0.61 ± 0.29 (0.99) | **0.71 ± 0.21 (0.83)** | 0.61 ± 0.27 (0.85) | **0.68 ± 0.12 (0.76)** |
| Elastic net | 0.44 ± 0.12 (0.50) | 0.59 ± 0.28 (0.98) | 0.70 ± 0.21 (0.83) | 0.62 ± 0.28 (0.85) | 0.71 ± 0.12 (0.76) |
| Tree, depth 2 | 0.44 ± 0.14 (0.77) | 0.44 ± 0.23 (0.92) | 0.60 ± 0.19 (0.88) | 0.53 ± 0.19 (0.88) | 0.63 ± 0.14 (0.81) |
| Tree, depth 3 | 0.46 ± 0.15 (0.81) | 0.52 ± 0.27 (0.96) | 0.58 ± 0.20 (0.93) | 0.56 ± 0.20 (0.97) | 0.61 ± 0.16 (0.85) |
| Gaussian NB | 0.42 ± 0.13 (0.69) | 0.38 ± 0.31 (0.93) | 0.76 ± 0.18 (0.91) | 0.65 ± 0.25 (0.93) | 0.73 ± 0.12 (0.76) |
| Bayes, PSIS-LOO † | 0.42 | 0.41 | 0.66 | 0.68 | 0.70 |
| Bayes, 5-fold † | 0.43 | 0.38 | 0.69 | 0.58 | 0.70 |

† Not 20×5, not directly comparable. Pooled Bayesian PSIS-LOO AUC is 0.60; 5-fold mean is 0.60 ± 0.07. Continuous ridge / lasso / EN, on the raw key metric rather than the median split, have **negative CV R²** at WR, TE, CB, and S, and DL ridge R² = +0.03. Those models do not beat predicting the mean.

**Lasso, surviving Combine tests** (nonzero on the full-sample inner-CV fit; stability is the share of 100 outer folds with a nonzero coefficient):

| Group | Chosen C | Surviving tests (full-sample OR per 1 SD) | Notes |
|---|---|---|---|
| WR | 0.01 | **none** (all OR = 1) | Lasso shrinks to the intercept. This is the correct answer for YPR. |
| TE | 35.9 | All seven tests, with wild ORs (height 372, vertical 0.0003) | C ≈ 36 is essentially unpenalized. Not a safe model. |
| CB | 0.60 | Official 40 (OR 1.60, stability 0.84); official 10-yard (1.00, 0.46); vertical (1.00, 0.51); weight (0.39, 0.99) | Tentative. Weight is the stable one. |
| S | 0.60 | Height (0.50, 0.92); weight (0.67, 0.86); Combine top speed (0.74, 0.74) | Sparse, but the outcome is a weak proxy. |
| DL | 0.22 | **Official 40 (0.66, 0.74); vertical (1.11, 0.73); weight (0.90, 0.63)** | The pairwise 10-yard winner is collinear with the 40 (stability 0.13) and is absorbed by it. |

---

## Bayesian hierarchical logistic

One model, five groups (WR, TE, CB, S, DL), n = 200 complete cases. Combine-test slopes are partially pooled: each group’s slope is a draw from a shared mean and a shared variance. Intercepts are also pooled. Year is a single shared coefficient. **No draft pick.** Combine tests are z-scored within group, so each odds ratio is per 1 SD at that position. Sampling: 4 chains × 2,000 draws after 2,000 tune, nutpie NUTS, seed 2027. max R̂ = 1.002, 0 divergences. PSIS-LOO: elpd = −139.9 (SE 5.5), 1 of 200 observations with Pareto k > 0.70. Figure 11.

**Headline posterior OR per 1 SD, 90% equal-tail credible interval, P(direction)** (P(direction) is the posterior share on the pre-declared athletic side: faster times OR < 1, higher jumps / top speed OR > 1; omitted for height and weight):

| Group | Strongest P(direction) | OR | 90% CI | P(dir) |
|---|---|---:|---|---:|
| WR | Official 40 | 0.57 | 0.27–1.01 | **0.95** |
| TE | Official 40 | 0.64 | 0.26–1.21 | 0.89 |
| CB | Vertical | 1.29 | 0.70–2.16 | 0.72 |
| S | Official 40 | 0.75 | 0.33–1.46 | 0.81 |
| DL | Official 40 | 0.62 | 0.24–1.22 | 0.89 |
| **Pooled** | Official 40 | 0.69 | 0.34–1.22 | 0.88 |

The WR official-40 interval just touches 1 (0.27–1.01) and is the only group-level interval with P(direction) ≥ 0.90 — a filled marker on Figure 11. Most other 90% intervals include 1, which is the honest small-n answer: the hierarchical model shrinks the wild frequentist ORs (especially at TE) toward a shared, modest “faster 40 helps a little” mean, and it does not claim precision it does not have. Pooled weight has OR 0.63 (90% CI 0.36–0.97), a heavier-player penalty whose meaning is mixed across positions (it is more a DL / CB story than a WR story) and should not be read as a single physical effect. Combine top speed, once the official 40 is already in the model, does not have an independent direction (pooled P(OR > 1) = 0.11); the two are collinear.

Per-group PSIS-LOO AUCs — 0.42 WR, 0.41 TE, 0.66 CB, 0.68 S, 0.70 DL — agree with the frequentist picture: the hierarchical model is doing real work at DL (and modestly at CB), and it is not predicting receiver or tight-end production.

---

## Recommendation, for Kevin to decide

Kevin leans toward lasso as the safest model. Our recommendations, flagged as recommendations:

| Group | Recommendation | Why |
|---|---|---|
| **WR** | **Lasso — because it shrinks to zero.** Do not use a multi-test YPR model. | No model beats chance on yards per route. Lasso’s answer is “use nothing.” The Combine finding at WR is Sunday Speed, already in `METRICS.md`. |
| **TE** | **No deployable model.** Report the 20-yard lean as a lean. | n = 22, train AUCs of 0.99–1.00, lasso failed to shrink (C = 35.9, height OR 372). FDR on the 20-yard lean is 0.19. |
| **CB** | **Lasso, tentative.** | CV AUC 0.71 vs year 0.35, modest overfit, n = 29. No FDR-significant pairwise cell. Tackle rate is a fallback. |
| **S** | **No deployable model.** | Weak outcome, n = 24, earlier wrong-signed gauntlet, no FDR-significant cell. |
| **DL** | **Lasso.** | Pairwise 10-yard → pressure is FDR- and Holm-significant. Lasso CV AUC 0.69 vs year 0.60, overfit 0.08. Surviving: official 40, vertical, weight. Elastic net (0.71) and naive Bayes (0.73) are close; Kevin’s preference for lasso is reasonable. |

---

## Appendix: Edge vs Interior (not in the headline)

DL is one combined group everywhere above. For the record, year-only Spearman *within* subtype, official 10-yard split:

| Subtype | vs pressure | vs get-off (mph) | vs NFL get-off time |
|---|---|---|---|
| Edge | ρ = −0.36, n = 39, p = 0.025, FDR = 0.077 | ρ = −0.57, n = 39, p = 1.4×10⁻⁴, FDR = 0.002 | ρ = +0.50, n = 39, p = 0.001, FDR = 0.007 |
| Interior | ρ = −0.15, n = 33, p = 0.41, FDR = 0.49 | ρ = −0.41, n = 33, p = 0.017, FDR = 0.047 | ρ = +0.41, n = 32, p = 0.019, FDR = 0.047 |

The 10-yard → get-off link holds in both subtypes. The 10-yard → pressure link is clearly an Edge story in the breakout and is not significant inside Interior, which is the same pattern reported in the earlier DL work. These numbers are in `out/combine_to_game_appendix_edge_interior.csv`. They are not in Figure 10, the models, or the Bayesian pool.

---

## Athletic comps (prior supporting work)

K-nearest-neighbor historical athletic comps against public nflverse Combine data (2000–2022) are in `out/athletic_comps.csv` and were built by `athletic_comps.py`. They are scouting cards, not a prediction rule: a KNN prediction from comps’ career Approximate Value did not significantly correlate with our rookies’ gameplay after multiple-testing correction. Highlight cards (Cedric Johnson / Brian Orakpo, and others) are unchanged. Running back comps, if listed, remain an anecdote.

---

## Method, in brief

- **Control:** draft-year dummies only. Draft slot is not a covariate, not a baseline, and not a sensitivity.
- **Spearman:** pairwise, residualized on year, n ≥ 12, 2,000 bootstrap CIs, Holm and BH-FDR within each position across every valid cell. Heatmap stars = FDR < 0.05.
- **Models:** 20×5 RepeatedStratifiedKFold, seed 2027, same complete-case predictors, year-only baseline. Lasso / elastic-net hyperparameters are chosen by nested CV. Firth is bias-reduced logistic. Trees are depth 2–3 with `min_samples_leaf = max(3, n/10)`.
- **Bayesian:** PyMC 6 / nutpie, non-centered partial pooling of Combine slopes and intercepts across the five groups, shared year slope, 90% equal-tail credible intervals, PSIS-LOO and a single 5-fold CV (seed 2027) for predictive checks.
- **Reproducibility:** from the repo root, with the nine official CSVs already in `data/` and the existing derived tables in `out/` (`gameplay_success_players.csv`, `sunday_speed_players.csv`, `dl_burst_players.csv`):

```bash
.venv/bin/pip install pandas numpy scipy scikit-learn statsmodels matplotlib pyarrow pymc arviz nutpie
.venv/bin/python combine_to_game.py
```

RB is excluded. DL is one combined group. Closing speed and defender yards-allowed are not computable from this file, and we do not invent them.
