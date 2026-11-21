# Subgroup prelim: S vs CB, EDGE vs IDL (11/2026)

Exploratory companion to the main entry. **Private** Kaggle notebook: `kevinpolymath/bdb2027-subgroups-prelim` (v1, COMPLETE). The main entry, its public notebook and its dataset are untouched.

**Read the Combine through body size.** Every link is a rank correlation (ρ) with draft year, weight and height held fixed; positive = the better athlete does better. Everything below is a **preliminary lead**: nothing clears q < 0.05 with held-out support.

## Sample sizes (players with size, tracked 40 and the main game result)
| Subgroup | Players | Core n | Smallest detectable ρ (80% power) |
|---|---:|---:|---:|
| S (SS + FS) | 53 | 26 | 0.58 |
| CB | 60 | 32 | 0.52 |
| EDGE (DE + OLB) | 66 | 38 | 0.48 |
| IDL (DT + NT) | 52 | 33 | 0.51 |
Per-test n runs 26 to 50. Differences between subgroups need gaps of about 0.62 to 0.65 (EDGE vs IDL) and 0.66 to 0.71 (S vs CB) to be detected. 3-cone and shuttle are under 25 players everywhere (TOO FEW TO TELL).

## Top preliminary findings
1. **EDGE: explosive tests show up in get-off** (speed 1 s after the snap). Official 10-yard split ρ +0.46 (CI +0.05 to +0.75, n 39, q 0.14, held-out 3/3); broad jump +0.42 (n 42, q 0.14, held-out 2/3); 40 +0.43; vertical +0.40. LEAD.
2. **IDL: straight-line speed shows up in sacks; not for EDGE.** Tracked top speed ρ +0.45 (CI +0.06 to +0.70, n 33, q 0.29, held-out 3/3); 40 +0.41 (q 0.29, held-out 3/3). EDGE top speed → sacks −0.08. Gap −0.53, interaction p 0.03, q 0.38 (MDE 0.65). LEAD; difference NOT DETECTED (low power) after correction.
3. **Pooling the line dilutes get-off.** 10-yard split: EDGE +0.46, IDL +0.42, pooled +0.32; broad jump: +0.42, +0.39, pooled +0.19. Slopes do not differ, so rank a lineman against his own sub-position.
4. **S vs CB on tackling.** Peak 40 acceleration → tackles per snap: S +0.47 (n 26), CB −0.29 (n 32). Gap +0.76 (CI +0.05 to +1.32), interaction p 0.003, q 0.10 (MDE 0.71). The safety link alone crosses zero (q 0.90) and fails held-out. LEAD for the difference only.
5. **Coverage speed reads the same for S and CB.** 40 / top speed → game speed in man/deep coverage about +0.1 to +0.2 in both; gap ≈ 0 (MDE 0.66). NOT DETECTED (low power).

**Real vs not detected:** 0 of 99 interaction tests clear q < 0.05. 3 leads at p < 0.05; 75 NOT DETECTED (low power); 21 TOO FEW TO TELL.

## Files
- `kernel/bdb2027_subgroups_prelim.ipynb` + `kernel/kernel-metadata.json` (is_private true; competition data only)
- `subgroups_lib.py`, `subgroups_figs.py`, `notebook_text.md`, `build_nb.py` (builds the notebook)
- `out_sub/` aggregate results from the Kaggle run (no player rows); `figs/` four figures
- `bdb2027_subgroups_prelim_executed_local.ipynb` local run (verdicts identical to Kaggle; ρ within 0.01)
- Per-player tables stay in memory or in the git-ignored `cache/`.
