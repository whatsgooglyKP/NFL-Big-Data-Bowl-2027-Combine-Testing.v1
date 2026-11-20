# Unsupervised track: what the data shows on its own (11/2026)

Branch `unsupervised` (forked from `2ad0b80`). This is exploratory work; `main` and the writeup are untouched. Every
test was declared in [`PLAN.md`](PLAN.md) before any outcome was looked at, except the ones marked **post hoc**.
No draft slot, pick or round anywhere. No player-to-player comparisons. Only aggregate numbers are reported.

**How to read the numbers.** ρ is a rank correlation, + means the more athletic profile goes with the better result.
"Beyond size" means draft year, weight, height and role (Edge/Interior, CB/S) are held fixed. q is the BH-FDR value
within the pre-declared family. "Held-out" means the pattern was learned on two draft classes and checked on the third,
for all three classes. Labels follow PLAN §6: **HOLDS UP**, **EXPLORATORY LEAD**, **NOT DETECTED (low power)**,
**TOO FEW TO TELL**.

## The short version for coaches

1. **There are no hidden Combine "types" at WR, TE or DB.** Their test profiles form one continuous spread, not
   separate groups. Only the defensive line splits into two real body types, and that split is mostly edge build
   vs interior build.
2. **The strongest pattern the unsupervised search found is WR long speed carrying to Sunday deep routes.** It holds up
   on every check, but it is the same 40 / top-speed link the writeup already leads with, found again from scratch.
   That makes it an independent confirmation, not a new insight.
3. **"Fast for his size" defensive linemen pressure more.** That holds after size and role, and it repeats on held-out
   classes, but it misses the false-discovery bar. It's a lead. It is also basically the 40 again.
4. **Weight changes how receivers are used.** At the same height, heavier rookie WRs run fewer deep routes and more
   short ones (post hoc, a lead).
5. **Some Combine tracking can't be trusted for scouting.** Skill-drill braking, cut-speed and turn-rate numbers don't
   repeat from drill to drill, and the tracked first second of the 40 barely agrees with the official 10-yard split.
   Tracked top speed is reliable.

## Ranked findings

| # | Finding | n | Effect (95% CI) | q | Beyond size | Held-out | Label |
|---|---|---|---|---|---|---|---|
| 1 | Combine profiles are a continuum at WR / TE / DB; DL has 2 real body types | 34–99 per group | DL k=2 silhouette 0.31 vs one-blob 95th pct 0.285 (p 0.01), bootstrap ARI 0.94; WR/TE/DB k=2 p 0.19–0.86 | n/a (structure) | n/a | n/a | Robust structural result |
| 2 | WR "long speed + jumps" axis (PC3) → deep-route game speed | 63 | ρ +0.50 (+0.27 to +0.66) | 0.004 | yes | yes: ρ +0.44, p 0.001, 3/3 classes | **HOLDS UP**, but not new: holding tracked top speed fixed it drops to +0.22 (−0.06 to +0.47) (post hoc) |
| 3 | WR "lean burner" vs "big-bodied" archetype → deep-route game speed | 63 | median 19.0 vs 18.2 mph; ε² 0.27 (0.10 to 0.48) | KW q < 0.001; beyond-size q 0.14 | yes (p 0.005, partial η² 0.12) | yes: ρ +0.24, p 0.015, 3/3 | **EXPLORATORY LEAD** (misses FDR after size) |
| 4 | DL "fast for his size" archetype → pressure rate | 72 | median 8.3% vs 6.8% (n 48 vs 24); partial η² 0.10 | 0.17 | yes (p 0.011) | yes: ρ +0.23, p 0.008, 3/3 | **EXPLORATORY LEAD** |
| 5 | DL all-round athleticism (PC1: lighter, faster, jumps) → pressure rate | 72 | ρ +0.30 (+0.04 to +0.51) | 0.17 | yes | yes: ρ +0.56, p 0.001, 3/3 | **EXPLORATORY LEAD**; post hoc, the 40 alone does as well (+0.36 on the same 65 players) |
| 6 | WR "long speed + jumps" axis (PC3) → separation on break routes | 61 | ρ +0.34 (+0.06 to +0.57) | 0.17 | yes | yes: ρ +0.34, p 0.007, 3/3 | **EXPLORATORY LEAD**; post hoc, holding the vertical fixed it drops to +0.12, so it is the existing vertical lead |
| 7 | Combine shape lines up with in-game movement/deployment style | WR 67, DB 64, DL 70 | RV 0.19 / 0.18 / 0.64 vs null 0.09 / 0.08 / 0.03; archetype × style ARI 0.11 / 0.08 / 0.46 | RV q ≤ 0.003; ARI q 0.006 / 0.028 / 0.001 | DB: no (post hoc, PC1 vs man / high-safety / slot share is null once CB/S is held fixed); DL is mostly Edge/Interior | not tested | Real association; mostly role at DB and DL |
| 8 | Heavier WRs (same height) run fewer deep routes | 73 | ρ −0.32 (−0.49 to −0.08); short-route share +0.25 (+0.01 to +0.45) | post hoc q 0.046 / 0.12 | height held fixed | not tested | **Post hoc EXPLORATORY LEAD** (deployment, not success) |
| 9 | Tracking data quality (see below) | 30–106 | drill α ≤ 0.42 for braking, speed kept in cuts, turn rate (except TE turn 0.67); tracked launch vs official 10-yd ρ 0.06–0.18 (WR/TE/DB), 0.34–0.38 (DL) | n/a | n/a | n/a | Method finding |

## What each finding means, in coach language

**1. Archetypes are mostly a myth outside the defensive line.** We tried k-means, Gaussian mixtures, Ward and HDBSCAN.
Only 2-way splits were stable (bootstrap ARI 0.60 to 0.94); every 3+ group solution fell apart under resampling, except
a post hoc DL size-adjusted 3-way split (ARI 0.70) that predicts nothing (all beyond-size p ≥ 0.07). More important, at WR, TE
and DB even the stable 2-way split is no more distinct than cutting a single blob in half (one-blob test p 0.19 to 0.86).
A WR is not a "burner" or a "possession" type at the Combine. He sits somewhere on a sliding scale of size against speed.
The DL is the exception: lean explosive edge builds and heavy anchors really are two groups (ARI vs Edge/Interior 0.69).
HDBSCAN found no dense clusters in any group. Complete-case reruns agree with the imputed ones (ARI 0.84 to 1.00; TE
size-adjusted 0.69).

**2–3. WR speed is the one thing that carries over, and unsupervised methods find it on their own.** PCA's third WR axis
(40, top speed, broad jump, vertical) predicts deep-route game speed beyond size and on held-out classes. The two-group
version (lean burners at 19.0 mph on deep routes vs big-bodied at 18.2) points the same way. Post hoc, once tracked top
speed is held fixed the axis adds little. It's the same signal the writeup already leads with.

**4–5. DL: test athletic for your size, and you pressure more.** Among linemen of the same size and role, the
"fast for his size" group had a median pressure rate of 8.3% against 6.8%. The all-round athleticism axis shows the same
thing (+0.30) and is the best held-out predictor in the whole study (+0.56, all three classes). But neither clears
false-discovery correction, and the 40 alone does as well as the composite. Read it as support for the existing DL 40
lead, not a new test.

**6. Break-route separation.** The same WR axis leans toward break-route separation, but post hoc that's the vertical
jump lead already on the scorecard.

**7–8. Combine shape predicts how players are used more than how well they play.** In every group the whole Combine
profile is related to the whole in-game movement and deployment profile (RV test). At DL that is edge vs interior
alignment. At DB it is CB vs S. For receivers, lean burners mostly became "vertical outside" players (19 of 38), while
big-bodied receivers mostly became "slot / short" players (18 of 29). Post hoc, the driver is weight, not height: at
the same height, a heavier WR runs fewer go / post / corner / wheel routes (−0.32) and more hitches, slants, flats and
screens (+0.25). At the same weight, a taller WR runs more deep routes (+0.24, p 0.04). This fits the writeup's weight
story: heavier WRs are slower on deep routes (−0.43), and coaches seem to use them shorter. It's about deployment, not
success. It's post hoc, and we didn't run a held-out check.

**9. Where Combine tracking can and can't be trusted.** Before clustering we checked whether each skill-drill movement
trait repeats across a position's drills (Cronbach-type α over 8 to 13 drills). Peak speed repeats (DL α 0.86, DB 0.68),
and so does WR peak acceleration (0.71). Braking, speed kept through cuts, turn rate and drill duration mostly don't
(α −0.18 to 0.42). Those measure the drill, not the athlete. Likewise, the tracked "launch" in the 40 (speed 1 s after
the start, peak acceleration) barely agrees with the official 10-yard split at WR, TE and DB (ρ 0.06 to 0.18). At 10 frames
a second, the tracked 10-yard time can only be 1.9 s or 2.0 s for most players. PCA puts that noise on its own second
axis, and isolation-forest "unusual profiles" at WR, TE and DB are mostly players with extreme tracked-launch values.
Practical rule: **trust tracked top speed (agrees 0.96 to 0.99 with the repo's version) and drill peak speed; don't
scout off tracked first-step or cut metrics.**

## What didn't pan out

- **"Heavy but explosive" DL** (weight × jumps): not detected. Pressure interaction p 0.16 (q 0.44), sack p 0.96. Only 7 linemen were both above-median weight and above-median explosiveness.
- **"Slow 40 but elite burst" WR** (40 × jumps): not detected. Separation p 0.27, break-route separation p 0.25, deep-route speed p 0.57 (all q ≥ 0.44).
- **Unusual Combine profiles** (isolation forest): unusual players did not fare better or worse in any group. The best was DB yards per target, ρ −0.35 (−0.62 to −0.02), p 0.019, q 0.29, and that rests on only 5 unusual players. NOT DETECTED.
- **DB:** no archetype, axis or anomaly link survives (all Family A beyond-size q ≥ 0.31). DB PC3 (length) → TFL rate was nominal (p 0.037, q 0.28). NOT DETECTED (low power).
- **Run stops, TFL, sacks (DL), tackles and closing speed (DB):** no archetype link beyond size.
- **The tracked-launch axis (PC2)** predicts nothing. Its one nominal hit, DL launch → game get-off at −0.25, goes the wrong way and fails held-out.
- **TE:** n = 18 to 21 with outcomes. TOO FEW TO TELL. The "slower build" group separated more (3.49 vs 3.32 yd), but MDE η² is about 0.30.
- **Minimum detectable effects** (Family A, 80% power): η² ≈ 0.10–0.12 (WR, DL), 0.12–0.15 (DB), 0.30–0.34 (TE). Smaller archetype effects would be missed.

## Recommendation for the writeup

Nothing here is a new, judge-ready headline. Two things are worth adding, briefly:
1. **One sentence of independent confirmation** for Finding 1 of the writeup. An unsupervised search that never saw an
   outcome rediscovers WR long speed → deep-route game speed (ρ +0.50, q 0.004, held-out +0.44).
2. **One sentence on data quality** as a methods strength. Combine profiles are a continuum (no hidden "types" outside
   DL), and the tracked first-step and cut metrics don't repeat across drills, so we didn't build on them.

The WR weight → deployment result is the most non-obvious item. It's post hoc with no held-out check, so it belongs in
"leads for more seasons" at most.

## Files

| Script | What it does |
|---|---|
| `u01_combine_features.py` | Combine standard + tracking features, missingness, drill reliability (no outcomes) |
| `u01b_game_features.py` | In-game style features and the pre-declared outcomes (cache only) |
| `u02_reduce_cluster.py` | PCA with parallel analysis; k-means / GMM / Ward / HDBSCAN; bootstrap stability; complete-case sensitivity |
| `u02b_cluster_null.py` | One-blob test: are there types at all? |
| `u03_game_styles.py` | Game styles; Combine archetype × game style ARI / NMI / RV with permutation p |
| `u04_link_outcomes.py` | Families A–D (archetype, axes, interactions, anomalies) with size control, BH, held-out classes, MDE |
| `u05_posthoc.py` | Post hoc checks (incremental value, deployment, launch vs 10-yd) |
| `u06_figures.py` | Figures |

Run in order from `unsupervised/` with `python3` (set `BDB_DATA` if the Kaggle CSVs aren't at `/workspace/bdb2027/data`).
The per-player caches go to `unsupervised/cache/`, which is gitignored. Aggregate results are in `out/` and figures in `figs/`:

- `u_fig1_pca_biplot.png`: PCA biplot per group
- `u_fig2_types_or_continuum.png`: stability by k, and real data vs one blob
- `u_fig3_archetype_centroids.png`: what the archetypes look like
- `u_fig4_archetype_vs_outcome.png`: archetype medians with CIs
- `u_fig5_combine_vs_game_style.png`: Combine archetype vs game style crosstab
- `u_fig6_latent_axes_forest.png`: latent axes vs outcomes
- `u_fig7_tracking_reliability.png`: where tracking can be trusted
- `u_fig8_tsne_picture.png`: picture only
