# Unsupervised track: pre-registration (written 11/2026, before any archetype was compared with a game outcome)

Branch `unsupervised`, forked from `2ad0b80` (the reframed writeup). Nothing on `main` is changed. This is an exploratory
track: its job is to look for structure the correlation grid could miss, and to say honestly whether any of it holds up.

**Hard rules.** Draft slot, pick and round are never read (asserted in `common.py`). No player-to-player comparisons
("athletic comps"); archetypes are described by their centroids only. Groups: WR, TE, DB (CB + S), DL (one group,
Edge / Interior breakout). RB excluded (n = 1). Only aggregate results are committed; per-player tables stay in
`unsupervised/cache/` (gitignored).

**State of knowledge when this was written.** Only feature tables and sample counts had been built
(`u01_combine_features.py`, `u01b_game_features.py`). No clustering had been run and no outcome values had been looked at.
The one thing already seen was the cross-drill reliability of the skill-drill movement features (no outcomes involved),
which sets the tracking feature list below.

## 1. Feature sets (built without any game outcome)

| Set | Contents |
|---|---|
| STD (standard Combine) | 40, 10-yd split, vertical, broad jump, height, weight, arm length, hand size |
| TRK (Combine tracking) | 40-yd tracked top speed (mph), peak acceleration, speed 1.0 s after start, time to 90% of top speed, finish hold (speed at 40 yd ÷ top speed); plus skill-drill composites whose cross-drill reliability (Cronbach-type alpha over that group's drills) is at least 0.6: WR drill peak accel (0.71); TE drill peak turn rate (0.67); DB drill peak speed (0.68); DL drill peak speed (0.86) and drill peak accel (0.62) |
| ALL | STD + TRK. **Primary set for archetypes.** |
| SIZE-ADJ | ALL without height and weight, each feature residualised on height and weight (linear, within group). "Athletic style regardless of body size." **Secondary set.** |

- 3-cone, short shuttle and bench press are excluded from clustering: 55% to 80% missing in every group (`out/feature_missingness.csv`). Imputing that much would invent the agility axis.
- Skill-drill features with alpha < 0.6 (speed kept through cuts, turn rate, braking, duration in most groups) are excluded: across drills they barely agree (mean inter-drill r about 0), so they measure the drill, not the athlete. That is reported as a finding in its own right.
- Times (40, 10-yd split, time to 90%) are sign-flipped so that higher always means more athletic.
- **Missing data.** A player enters if at least 60% of the set's features are observed. The rest are imputed within group with an iterative (Bayesian-ridge) imputer on standardised features. Sensitivity: the same clustering on complete cases only, compared by ARI on the overlap.
- Standardised within position group.

## 2. Dimension reduction
PCA per group on ALL and SIZE-ADJ. Components kept by Horn's parallel analysis (95th percentile of 500 random-data eigenvalues). Loadings interpreted in football terms. t-SNE is used only as a picture, never for inference or clustering. (UMAP is not installed on the box; t-SNE replaces it for the picture.)

## 3. Archetypes
- Methods: k-means (k = 2 to 6, 50 starts), Gaussian mixture (diagonal covariance, k by BIC), Ward hierarchical (k by silhouette), HDBSCAN (min cluster size max(5, n/10)).
- k-means k by silhouette, with the gap statistic reported.
- **Stability:** 200 bootstrap resamples of players; re-cluster with the same method and k; ARI with the reference labels on the resampled players, and Hennig per-cluster Jaccard. A solution is **stable** if median ARI is at least 0.6 and every cluster's mean Jaccard is at least 0.6. Unstable solutions are reported as unstable and enter only the descriptive tables.
- **Primary archetype solution per group and set** = the most stable solution (highest median ARI) that is stable; ties go to k-means.
- Overlap with role is reported (ARI of archetype vs Edge/Interior, CB/S), so "archetypes" that are just positions are flagged.
- Archetypes are named from their centroids in coach language.

## 4. Game styles
The same pipeline (k-means with silhouette, bootstrap stability) on in-game movement and deployment features (`u01b_game_features.py`): WR/TE cut profile, deep-route game speed (WR), cushion, slot / deep-route / short-route shares; DB cut profile, closing speed, coverage game speed, cushion, man / slot / high-safety shares; DL speed at 1 s, NGS get-off, penetration at 2 s (pass and run), edge alignment share. Combine archetype vs game style: ARI and normalised mutual information, permutation p (5,000 label shuffles), BH across groups.

## 5. Pre-registered archetype → outcome tests
Outcomes are the repo's existing scorecard definitions (METRICS §6 to §9; shrunk rates where the repo shrinks):

| Group | Outcomes |
|---|---|
| WR | deep-route game speed (Sunday Speed), separation on all routes, separation on break routes |
| TE | separation on all routes (n about 24: TOO FEW TO TELL, descriptive only) |
| DB | tackle rate, TFL rate, closing speed to the tackle, PFR yards per target, PFR missed-tackle %, coverage game speed |
| DL | pressure rate, sack rate, TFL rate, run-stop rate, speed 1 s after snap (get-off) |

**Family A (primary).** For each group's primary archetype solution on ALL and on SIZE-ADJ (if stable), each outcome:
1. Kruskal-Wallis on the draft-year-demeaned outcome; epsilon-squared with a 2,000-resample player bootstrap CI.
2. **Size control:** Freedman-Lane permutation F test (5,000 shuffles) for archetype dummies on top of draft-year dummies, rank weight, rank height and role (DB: CB/S; DL: Edge/Interior); outcome ranked. Partial eta-squared reported.
3. BH-FDR across every Family A test.
4. **Held-out season:** for each draft class, refit standardising, imputation and clustering (same method and k) on the other two classes' Combine features only, assign the held-out class to the nearest archetype, predict its size-and-year-adjusted outcome from the training classes' archetype means, and score Spearman(prediction, truth) pooled over the three held-out classes (permutation p, 2,000 shuffles within class). **Held-out passes** if pooled ρ > 0 with p < 0.05 and at least 2 of 3 classes have ρ > 0.
5. Minimum detectable effect: eta-squared detectable at 80% power (alpha 0.05) for that n and k (noncentral F).

**Family B (secondary).** Scores on the retained ALL-set PCs (at most 3) × each outcome: rank partial correlation controlling for draft year, weight, height and role; Freedman-Lane permutation p; BH within Family B. The same held-out check, with the PC loadings refit on two classes.

**Family C (pre-declared non-linear patterns).**
- DL "heavy but explosive": weight × explosiveness (mean z of vertical and broad jump) interaction on pressure rate and sack rate.
- WR "slow 40, elite burst": 40 speed × explosiveness interaction on separation (all routes and break routes) and deep-route game speed.
- Rank-based linear model with draft year, weight, height (and role for DL); permutation p for the interaction term; BH within Family C.

**Family D (anomalies).** Isolation forest (300 trees) on the ALL set per group. Anomaly score vs each outcome, size-controlled rank partial correlation, BH within Family D. Which features make the unusual profiles unusual (mean |z| of the top 10% by anomaly score), aggregate only.

## 6. Honesty labels
- **HOLDS UP**: Family-A/B/C/D q < 0.05, survives size control (size-controlled p < 0.05, same sign), and passes the held-out check.
- **EXPLORATORY LEAD**: size-controlled p < 0.05 but misses FDR or held-out.
- **NOT DETECTED (low power)**: otherwise, reported with its MDE.
- **TOO FEW TO TELL**: n < 25.

Anything not listed here that turns up later is labelled **post hoc** in FINDINGS.md.
