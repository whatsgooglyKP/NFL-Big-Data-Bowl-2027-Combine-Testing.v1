# Multi-test Combine models, and athletic comps

**11/2026.** Kevin asked whether a logistic regression that uses the 10-yard split, the broad jump, the vertical, and the 40 — together — can find on-field trends for RBs, WRs, TEs, CBs, and safeties, and how that compares to decision trees and naive Bayes. After the model comparison, we also built K-nearest-neighbor athletic comps against public historical Combine data.

This is a supporting analysis, not a new official metric. Official success definitions still live in `METRICS.md`. The punchline is conservative on purpose: the samples are small, and we will not talk a coach into a draft rule the cross-validation does not support.

Scripts: `multi_test_models.py`, `athletic_comps.py`. Figure: `out/figs/fig9_multi_test_models.png`.

---

## Coach summary

1. **Receivers are good with the 40 as a Sunday Speed test, not as a production test.** Adding the 10-yard split, broad jump, vertical, and weight to a logistic model does **not** identify above-median yards-per-route receivers, and the multi-test model *loses* to a draft-pick + year baseline (CV AUC 0.55 vs 0.62). No Combine test is Holm-significant. The 40's official-sample Sunday Speed result stands; it is not a receiving-production grade.

2. **Tight ends, corners, and safeties: nothing is Holm-significant, and the samples are smaller.** Tight ends show a *lean* on a faster 10-yard split (Firth OR 0.16 per 1 SD slower, Holm p = 0.13; L2 bootstrap CI 0.24–0.79), and an apparent CV-AUC lift (0.75 vs 0.63) that comes with severe overfitting (training AUC 0.96 on n = 22). Corners and safeties use tackle involvement rate because yards allowed is not attributable in this file; no test clears Holm, and safety's earlier gauntlet result was already wrong-signed. Shallow trees mostly split on draft pick and do not cross-validate. Random forests and gradient boosting fit the training sample almost perfectly (AUC 0.88–1.00) and then fall back to chance or worse on held-out folds.

3. **Athletic comps are useful scouting cards, not a prediction rule.** Among the 2023–2025 rookies, the most striking card is **Cedric Johnson** (Edge, 2024, pick 214): his nearest historical athletic neighbor is **Brian Orakpo** (2009, pick 13, 4 Pro Bowls) — same 4.63 40, almost the same vertical, height, and weight. That is a late-round "tests like a star" card. Across positions, a KNN prediction from comps' career Approximate Value does **not** significantly correlate with our rookies' gameplay after year, pick, and Holm correction. Do not turn the names into a draft rule.

**Running backs are excluded from every model.** The 2023–2025 rookie file has one RB, Sione Vaki (26 regular-season snaps, 9 routes, 7 rush plays). That is too few to fit a logistic regression, a tree, or a Bayesian pool. His historical comps are below, clearly labeled as an anecdote.

---

## Who is in the sample

All three Combine classes (2023–2025) are pooled. A player is **snap-eligible** if he clears the position floor below, and **complete-case** if he also has an official 40, 10-yard split, vertical, broad jump, and weight. 3-cone and short shuttle are too sparse for the joint model (WR 24/77 eligible, TE 12/29, CB 11/42, S 6/34); they are in the coverage table only. Height is essentially complete and is reserved for the athletic-comp distances, not the logistic, so the already-tight models do not pick up another predictor.

| Group | In the file | Snap-eligible | Complete case | 40 | 10-yd | Vertical | Broad | 3-cone | Shuttle | Weight / height |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WR | 106 | 77 | 63 | 70 | 70 | 67 | 68 | 24 | 30 | 77 / 77 |
| TE | 42 | 29 | 22 | 25 | 25 | 25 | 24 | 12 | 13 | 29 / 29 |
| CB | 60 | 42 | 30 | 37 | 37 | 35 | 32 | 11 | 16 | 42 / 42 |
| S | 53 | 34 | 24 | 29 | 29 | 28 | 26 | 6 | 6 | 34 / 34 |
| RB | 1 | — | — | 1 | 1 | 1 | 1 | 0 | 0 | 1 / 1 |

Eligible-column counts are among snap-eligible players. Tight ends are feasible. Running backs are not. The lone FB (Robbie Ouzts) was also inspected and is not modeled.

**40 and 10-yard split are only moderately correlated for WR (r = 0.28), TE (0.40), and CB (0.41).** They are *not* the same test for those groups. For safeties they are more collinear (r = 0.71), and the 10-yard vs broad jump correlation is −0.78; we still put both in the joint model, with L2 / Firth shrinkage, and we do not treat those two safety coefficients as independent effects.

---

## Outcomes

Success is **above the position median**, among rookies who clear a minimum-snap (or route) floor. Playing time is not the outcome. The median is computed on every snap-eligible rookie, including those who later drop out of the model because a Combine test is missing. "Above" is strict (`>`). Undrafted players are pick **260**. Year and log draft pick are in every model.

| Group | Outcome (higher is better) | Floor | Eligible median | Why this outcome |
|---|---|---|---:|---|
| WR | Yards per route run | ≥20 regular-season routes | 1.15 ypr | Same production metric used in the earlier WR work. |
| TE | Yards per route run | ≥20 regular-season routes | 1.15 ypr | Same definition as WR. TEs have real route volume (29 with ≥20 routes, median 193). |
| CB | Tackle involvement rate | ≥50 regular-season defensive snaps | 8.1% | **Fallback.** Yards allowed per coverage snap is not computable: this file has no target-allowed or reception-yards field on a defender, and play-level `yards_gained` is not attributed to the covered player. Tackle involvement is the closest existing gameplay metric. |
| S | Tackle involvement rate | ≥50 regular-season defensive snaps | 10.0% | **Fallback**, same attribution problem. The earlier safety gauntlet → tackle-rate link was **wrong-signed** (faster gauntlet, lower tackle involvement after year and pick), so this is a weak coverage proxy. |

RB is excluded, as above.

---

## Do the Combine tests matter?

Odds ratios are from a **Firth** (bias-reduced) logistic regression with all five tests, log draft pick, and year, fit on complete cases. Predictors are standardized, so each OR is for a **1 standard deviation increase**. A slower 40 or 10-yard split should have OR < 1 if speed helps. 95% CIs are bootstrap (2,000 resamples, standardized inside each replicate). p-values are Firth penalized likelihood-ratio tests, **Holm-corrected within each position** across the five Combine predictors.

**No Combine test is Holm-significant at 0.05 at any position.**

| Group | n | Official 40 | 10-yard split | Vertical | Broad jump | Weight |
|---|---:|---|---|---|---|---|
| WR | 63 | 0.80 (0.35–1.59), Holm p = 0.40 | 1.52 (0.90–3.42), 0.14 | 1.16 (0.54–2.60), 0.40 | 1.09 (0.55–2.35), 0.40 | 0.93 (0.47–1.84), 0.40 |
| TE | 22 | 1.66 (0.37–14.46), 0.53 | **0.16 (0.00–1.32), 0.13** | 0.23 (0.01–1.98), 0.13 | 0.81 (0.08–8.55), 0.53 | 0.19 (0.02–1.42), 0.071 |
| CB | 30 | 2.43 (0.81–615), 0.20 | 0.65 (0.00–2.36), 0.39 | 1.85 (0.49–320), 0.39 | 0.74 (0.02–4.85), 0.39 | 0.40 (0.01–1.42), 0.089 |
| S | 24 | 1.10 (0.04–13.19), 0.79 | 0.57 (0.00–10.74), 0.79 | 1.60 (0.24–43.33), 0.58 | 0.27 (0.00–3.22), 0.28 | 0.42 (0.01–1.36), 0.097 |

The TE 10-yard split is the only athletic lean worth a sentence: a 1 SD *slower* split (bad test) has Firth OR 0.16 of being an above-median tight end, and the L2 bootstrap CI (0.24–0.79) excludes 1. The Holm-adjusted Firth p is 0.13, n is 22, the vertical goes the *wrong* way, and the Firth CIs are very wide. Call it a lean, not a finding.

CB and S Firth CIs that run to 300–600 are a small-n warning, not a precise effect. L2 odds ratios are more stable (CB 40: 2.15, CI 0.97–5.04; CB weight: 0.39, CI 0.17–0.82) and are in `out/multi_test_coefficients.csv`. We do not treat an unadjusted L2 CI as a Holm-significant result.

**Continuous robustness (partial Spearman, year + pick, pairwise on snap-eligible players, Holm within position):** nothing is Holm-significant. The closest leans match earlier work: WR official 40 vs yards per route, ρ = −0.12, p = 0.33 (the weak link from Combine gems); TE 10-yard vs yards per route, ρ = −0.37, p = 0.069; CB broad jump vs tackle rate, ρ = +0.34, p = 0.056. Ridge / OLS signs agree; they are in `out/multi_test_ridge.csv` and `out/multi_test_spearman.csv`.

---

## Does the multi-test model beat draft pick + year?

Repeated stratified cross-validation, 20 repeats, 5 folds (the same folds for every model; 3- or 4-fold if a class is thin). Features are standardized on the training fold only. The baseline is an L2 logistic with only log pick and year. Error bars in Figure 9 are the SD across the 100 test-fold AUCs — they are wide because each test fold is small. Training AUC is reported next to CV AUC so overfitting is visible.

| Model | WR (n=63) | TE (n=22) | CB (n=30) | S (n=24) |
|---|---|---|---|---|
| Pick + year (L2) | **0.62** ± 0.14 (train 0.65) | 0.63 ± 0.31 (0.71) | 0.42 ± 0.23 (0.59) | **0.64** ± 0.29 (0.70) |
| L2 logistic, all tests | 0.55 ± 0.12 (0.72), Δ = −0.07 | 0.75 ± 0.28 (0.96), Δ = +0.12 | 0.63 ± 0.24 (0.84), Δ = +0.22 | 0.61 ± 0.30 (0.83), Δ = −0.03 |
| Firth logistic, all tests | 0.55 ± 0.12 (0.72) | 0.79 ± 0.28 (0.98) | 0.62 ± 0.24 (0.85) | 0.58 ± 0.31 (0.86) |
| Decision tree, depth 2 | 0.54 ± 0.13 (0.72) | 0.45 ± 0.25 (0.85) | 0.56 ± 0.17 (0.84) | 0.47 ± 0.23 (0.87) |
| Decision tree, depth 3 | 0.51 ± 0.14 (0.75) | 0.47 ± 0.27 (0.90) | 0.56 ± 0.18 (0.92) | 0.48 ± 0.23 (0.93) |
| Gaussian naive Bayes | 0.54 ± 0.15 (0.74) | 0.51 ± 0.35 (0.97) | 0.81 ± 0.20 (0.96) | 0.59 ± 0.29 (0.86) |
| Random forest, depth 3 | 0.50 ± 0.14 (0.88) | 0.58 ± 0.33 (1.00) | 0.69 ± 0.23 (1.00) | 0.55 ± 0.31 (0.99) |
| Gradient boosting, depth 2 | 0.50 ± 0.15 (0.97) | 0.65 ± 0.33 (1.00) | 0.66 ± 0.22 (1.00) | 0.56 ± 0.30 (1.00) |

**WR, the largest sample, is the clean result:** adding Combine tests *lowers* CV AUC. Only 24% of folds favor the multi-test L2 model over pick + year.

**TE and CB show raw AUC lifts that we will not promote.** TE training AUC is 0.96–0.98 on 22 players — the model is memorizing. The fold-AUC interval is 0.25–1.00. CB's pick+year baseline is itself *below* chance (0.42), which is a small-fold noise flag, and the 0.81 naive-Bayes number comes with a 0.96 training AUC on a fallback tackle-rate outcome. Trees, forests, and boosting overfit at every position (training 0.85–1.00, CV near 0.5). A paired Wilcoxon on repeated folds is anti-conservative (the folds are not independent); we do not quote those p-values as evidence.

**Median imputation sensitivity** (snap-eligible sample, within-position median for missing tests, labeled as a check only): WR still does not beat the baseline (0.61 vs 0.66); TE and CB keep a raw lift; S gets worse (0.36 vs 0.53). The complete-case conclusions do not flip.

---

## Tree rules a coach can read

These are the in-sample depth-2 rules, in raw units. **Trust the CV AUC, not the leaves.** Every tree's first or second split is usually draft pick.

- **WR** (train accuracy 0.70, CV AUC 0.54 ± 0.13): if draft pick ≤ 69 and weight ≤ 196.5 lb → above-median (6 of 6 in the leaf); pick ≤ 69 and heavier → above-median (6 of 9); pick > 69 and broad jump ≤ 131.5 in → below-median (26 of 39); pick > 69 and a longer broad jump → above-median (6 of 9). The tree is mostly reading draft slot.
- **TE** (train 0.82, CV 0.45 ± 0.25): pick ≤ 213 and vertical ≤ 36.75 in → above-median (9 of 12); pick ≤ 213 and a higher vertical → below-median (4 of 5), which is the *wrong* direction for a jump test; pick > 213 → below-median (5 of 5).
- **CB** (train 0.83, CV 0.56 ± 0.17): a 40 of 4.40 s or faster → below-median tackle rate (7 of 8 across two leaves). That matches the logistic's wrong-signed 40 (slower 40, higher tackle-rate odds) and is consistent with a coverage-vs-tackling role split, not with "faster is better." It does not cross-validate as a rule.
- **S** (train 0.83, CV 0.47 ± 0.23): pick ≤ 181 and weight ≤ 204.5 lb → above-median (10 of 13); just about everything else → below-median. Again, draft slot first.

Full depth-2 and depth-3 rules, and feature importances, are in `out/multi_test_tree_rules.txt` and `out/multi_test_importances.csv`.

---

## Method, in brief

- **Primary inference:** Firth logistic on standardized complete cases, with log pick (UDFA = 260) and a numeric year (2023 = 0). Year is numeric, not two dummies, to save a parameter at n = 22–30. L2 logistic (sklearn default, C = 1) is the companion and the prediction model.
- **Missing tests:** complete cases are primary. Median imputation within the snap-eligible position sample is a labeled sensitivity, not the headline.
- **Cross-validation:** `RepeatedStratifiedKFold`, 20 × 5, seed 2027. Same protocol for L2, Firth, depth-2 and depth-3 trees (`min_samples_leaf = max(3, n/10)`), Gaussian naive Bayes, a depth-3 random forest (200 trees), and depth-2 gradient boosting (50 trees).
- **Holm:** within each position, across the five Combine coefficients (Firth PLRT), and separately across the five partial Spearman tests. The two families are not pooled.
- **What we did not do:** we did not invent yards allowed, targets allowed, PBUs, or interceptions. We did not model RBs. We did not use 3-cone or shuttle in the joint model. We did not treat a training-set tree leaf, or a CV-AUC lift on n = 22 with a 0.96 training AUC, as a finding.

---

## Athletic comps

Public historical Combine data is the [nflverse Combine release](https://github.com/nflverse/nflverse-data/releases/tag/combine), courtesy of Pro-Football-Reference, seasons 2000–2022 as the comparison pool (8,968 rows in the cached file, through 2026). Career labels use [nflverse draft_picks](https://github.com/nflverse/nflverse-data/releases/tag/draft_picks): weighted Approximate Value (`w_av`; `car_av` is empty in this snapshot), AP first-team All-Pros, and Pro Bowls. Cached with attribution in `external/`. **This is not Kaggle data and is fine to keep in the repo.**

**The nflverse Combine file has no 10-yard split.** Distances use official 40, vertical, broad jump, 3-cone, short shuttle, height, and weight. Each test is z-scored within position on the 2000–2022 historical pool. Distance is a nan-aware RMS of z-differences on the tests two players both have. We prefer neighbors with **at least four** shared tests; if a rookie only has three (typically a 40 plus height and weight, because he skipped the jumps), we fall back to three and flag the comparison as thin. 22 of 380 rookies still have too few tests for any comp (they skipped the 40 as well).

Position groups match our roster: WR, TE, CB, S (historical S / SAF / FS / SS), Edge (DE / EDGE / OLB), Interior (DT / NT). Ambiguous historical labels (LB, DL, DB) are left out so they do not leak across groups. **RB is anecdote-only** — Sione Vaki gets comps, and is excluded from the correlation test and from every model.

Career labels, pre-declared on 2000–2018 draftees (enough runway for a career to show up):

- **Star:** 1+ AP first-team All-Pro, 3+ Pro Bowls, Hall of Fame, or `w_av` at/above the position 90th percentile (Edge 58, WR 52, CB 47, and so on).
- **Solid:** `w_av` at/above the position median, 1+ Pro Bowl, or 3+ seasons started.
- **Journeyman:** a draft-picks career record below that.
- **No record:** not in the draft-picks file (often undrafted). Some of those players — Rico Dowdle is one — later had real NFL careers this file does not capture.
- Players drafted 2019–2022 are flagged **early-career**: their AV is still accumulating.

The headline phrase ("tests like a star / solid starter / journeyman") follows the comps' *mean* `w_av` relative to the position median and 90th percentile, plus the star count, so a group of two solid starters and three lower-AV players is not automatically called a journeyman.

### Highlight cards

**Cedric Johnson (Edge, 2024, pick 214) — the card worth putting on a board.** 4.63 40, 38.0" vertical, 122" broad, 75", 260 lb. Nearest neighbor: **Brian Orakpo** (2009, pick 13), 4.63 40, 39.5" vertical, 75", 263 lb, 4 Pro Bowls, `w_av` 58, distance 0.24 on four shared tests. The rest of the five: Isaac Hilton (no record), Daniel Te'o-Nesheim (journeyman), George Karlaftis (solid, early-career), Chris Gocong (solid). Mean comp `w_av` 31.5, mean comp pick 91. Cedric's own pressure rate is 14.6% (already a Combine gem). He tests like a solid-to-star pass rusher and was picked in the sixth round. This is a scouting card, not a group rule.

**Chop Robinson (Edge, 2024, pick 21).** 4.48 40, 34.5" vertical, 128" broad, 4.25 shuttle, 75", 254 lb. Comps: Drake Jackson (2022, journeyman, early), Bryan Thomas (2002, solid, pick 22), Eli Harold (2015, journeyman), Kevin Burnett (2005, solid), Malik Jefferson (2018, journeyman). Mean `w_av` 21.2 (above the Edge median of 15), mean pick 56. A solid-starter athletic profile, not a star cluster. He was already a Combine gem on the official 10-yard split (1.54, 13.9% pressure).

**Luther Burden (WR, 2025, pick 39) — thin comparison.** He ran a 4.41 40 at 72" / 206 lb and skipped the jumps and agility tests, so all five comps share only those three measurements. Neighbors include Taylor Jacobs, Taylor Price, and Tre McBride (all journeymen with almost the same 40 and size) and **D.J. Moore** (2018, `w_av` 61) and **Pierre Garçon** (2008, `w_av` 54). Mean `w_av` 23.8. Treat this as "same 40 and same size as D.J. Moore," not as a full athletic twin.

**Brian Thomas (WR, 2024, pick 23).** Comps: Darrius Heyward-Bey (2009, solid — the famous 4.30 40), Javon Walker (2002, solid, 1 Pro Bowl), Erik Ezukanma (journeyman, early), Terrace Marshall Jr. (no record, early), Jeff Webb (journeyman). Mean `w_av` 16.2. A solid, mixed WR athletic neighborhood.

**Will Anderson (Edge, 2023, pick 3) — thin comparison.** 4.60 40 at 75.5" / 253 lb, no jumps on file. Comps on 40 + size: Corey Lemonier (journeyman), Kayvon Thibodeaux (solid, early), Mark Anderson (solid), **Karlos Dansby** (star, `w_av` 81), Chase Winovich (journeyman, early). Mean `w_av` 28.2.

**Jared Verse (Edge, 2024, pick 19).** Comps: Clelin Ferrell (solid, early), Drake Jackson, David Ojabo, Jordan Brailford, and **Vernon Gholston** (the 2008 bust). Mean `w_av` 7.4, below the Edge median. A cautionary athletic neighborhood for a top-20 pick — and, given the null KNN-vs-gameplay result below, not a forecast.

**Sione Vaki (RB, 2024, pick 132) — anecdote only, not modeled.** 26 regular-season snaps. Closest drafted comp is Kerryon Johnson (2018, solid, `w_av` 11). The other four (Brian Herrien, John Crockett, Cierre Wood, Rico Dowdle) have no career record in the draft-picks file; Dowdle later became a useful NFL back, which is a reminder of that file's UDFA gap. Do not write a running-back section around one player.

The full 5-comp lists for every 2023–2025 WR, TE, CB, S, Edge, Interior, and the one RB are in `out/athletic_comps.csv` and `out/athletic_comps_summary.csv`.

### Do comps' careers predict our rookies' gameplay?

For each rookie with a gameplay outcome, we take the mean `w_av` of his historical comps and correlate it with that outcome, raw and after residualizing both sides on year and log pick. RB is excluded. Holm is across the six position groups.

| Group | n | Outcome | Partial ρ (year+pick) | Holm p |
|---|---:|---|---:|---:|
| WR | 72 | Yards per route | +0.08 | 1.00 |
| TE | 27 | Yards per route | +0.09 | 1.00 |
| CB | 40 | Tackle rate | −0.37 | 0.12 |
| S | 29 | Tackle rate | +0.09 | 1.00 |
| Edge | 47 | Pressure rate | −0.01 | 1.00 |
| Interior | 37 | Pressure rate | +0.22 | 0.91 |

**Nothing is Holm-significant.** The CB lean is negative (rookies who test like higher-AV corners have *lower* tackle rates), on a fallback metric, and it moved around when we changed the shared-test floor, so we will not promote it. Interior's raw lean is positive and also does not clear Holm. The names are the deliverable; the group-level test is null.

---

## What a coach should take to draft meetings

- Trust the WR 40 as a Sunday Speed test. Do not use the 40, the 10-yard split, the broad jump, or the vertical — alone or together — as a yards-per-route grade for receivers in this sample.
- A faster 10-yard split is a *lean* for tight-end production, not a rule. n = 22, Holm p = 0.13.
- For corners and safeties, this file cannot measure yards allowed. Tackle rate does not give a Holm-significant Combine story, and shallow trees do not beat a coin flip once you leave the training sample.
- Draft slot still does more work than the multi-test athletic profile in the largest sample (WR), and it is the first split in the trees.
- Athletic comps are a card, not a model. Cedric Johnson testing like Brian Orakpo is worth a look; "tests like a star" as a group does not predict our gameplay outcomes.

Outputs: `out/multi_test_coefficients.csv`, `out/multi_test_auc.csv`, `out/multi_test_spearman.csv`, `out/multi_test_ridge.csv`, `out/multi_test_coverage.csv`, `out/multi_test_players.csv`, `out/multi_test_tree_rules.txt`, `out/multi_test_importances.csv`, `out/multi_test_imputation_sensitivity.csv`, `out/athletic_comps.csv`, `out/athletic_comps_summary.csv`, `out/athletic_comps_correlation.csv`, `out/figs/fig9_multi_test_models.png`.
