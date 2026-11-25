# Verification of the handed-over v2 package (11/23/2026, branch v2-review)

Everything here was recomputed live from the nine competition CSVs (re-downloaded with the Kaggle CLI 11/2026), seed 2027. The code is `v2/v2_analysis.py` and `v2/bdb2027_v2.ipynb`. Aggregates only; no player IDs or names.

## Restore
- Repo recloned. main is at dc3d22d, the subgroups worktree is at 33b9e0c (bd6db0e below it), and the unsupervised branch is at 8df8aa7. The competition data are in the gitignored `data/`.
- The v1 notebook (`kaggle_upload/kernel/bdb2027_writeup.ipynb`) was rerun locally: n 62, ρ +0.63 year-fixed, +0.58 size-adjusted, q 0.003, **GATE PASS**, 7 figures.
- The v1 gate cell falls back to a saved PNG and still prints PASS when the data are missing (confirmed in the code). The v2 gate raises an error instead.

## Claims
| Claim | Verdict | Live number |
|---|---|---|
| (a) "164 tests" → 104 cells, 16 at p<.05 vs ~5, 2 survive best-of-N | **PARTLY** | 164 was a correct count of the v1 grid: 164 cells with n≥25, 28 at p<.05 vs 8.2 expected, 2 at q<.05. The real problem was that the 2 survivors are one measurement (laser 40 and tracked 40). The 104/16 can't be rebuilt because the 26 OL tests and the DB outcome list were never written down, and the spec contradicts itself (DB "8 × 6" = 48 cells, not 36). Pieces that do check: WR 12 cells with 3 at p<.05, and the audited DL 6 × 5 = 30 cells with 5 at p<.05. Live families here (WR 12, DL 18, OL 29, DB 8 = 67 cells): 9 at p<.05 vs 3.4 expected, and **the same 2 survive best-of-N**: WR top speed → Sunday Speed (p 0.0005) and OL slide-drill acceleration (q 0.003, p 0.004). |
| (b) DL share explained by size 69% → 54% (CI 20–100%) | **PARTLY** | Old 69% reproduced from the scorecard: shrunk "raw" +0.68 → +0.21. With as-reported rates, the 21 cells (7 drills × pressure/sack/TFL, n 34–78) go +0.36 → **+0.17** (+role) → +0.17 (+weight/height). Share **53%**, resampling range **13%–99%**. v2's middle rung (+0.21) is wrong: role alone accounts for nearly all of the share. The judge review's own figure was 49% (all 32 cells) or 39% (rate cells). |
| (c) Heavier WRs −0.20 mph per 10 lb (CI −0.30 to −0.09) | **CONFIRMED** | **−0.20** mph per 10 lb (CI −0.30 to −0.10), partial ρ −0.38 (−0.57 to −0.14), n 62, same sign in all 3 classes (−0.21 / −0.10 / −0.17). Holds only with height held fixed (−0.14 without it). |
| (d) Fig1 title drop "drafted": 7 of 62 undrafted | **CONFIRMED** | 7 of 62 undrafted (11%) vs 30 of 106 (28%). The word "drafted" is in the v2 fig1 draft, not the v1 submitted fig1. Same problem in the v2 fig4 footnote ("Defensive linemen drafted": 12 of 89 undrafted) and the fig5 footnote ("Offensive linemen drafted": 3 of 66). All fixed. |

## Other material claims (e)
- Confirmed: funnel 106 → 93 → 69 → 62; class-only +0.62 (v2 said +0.63); laser 40 +0.52; rookie season only +0.69 (n 57); first 20 / 30 deep routes +0.50 / +0.46; per class +0.49 / +0.76 / +0.60; slope 0.67 (0.46–0.88); Theil–Sen 0.73.
- Confirmed: NGS class-only +0.12 (v2 said +0.13); NGS size-adjusted +0.37; NGS given top speed −0.03; top speed given NGS +0.48; weight vs 40 top speed −0.19 (with height held fixed); yards per route null.
- Confirmed: DL 40 → pressure +0.25 (CI 0.00 to +0.48); within role, edge +0.22 (n 39) and interior +0.36 (n 33); weight → pressure −0.15 (role held fixed); DB 40 → yards/target −0.35 (n 53, from the audited v1 table); DB MDE 0.38.
- Confirmed: OL slide drill −0.50 (CI −0.67 to −0.26, n 66), 2023+24 −0.57, 2025 +0.04, median snaps 975 / 740 / 452.
- **WRONG / misleading:** "Top speed beats the score by +0.51 (CI +0.25 to +0.75)". The +0.51 is (top | NGS) − (NGS | top), and its CI is really +0.06 to +0.89. The plain size-adjusted difference is **+0.21 (CI +0.03 to +0.39)**. Replaced.
- **PARTLY:** OL by class −0.43 / −0.76 (v2 said −0.47 / −0.74); class-difference p 0.010 (v2 said 0.007). Both depend on definitions.
- **PARTLY:** Table 2. WR Sunday Speed held-out gain +0.19 (v2 said +0.261), same p 0.003. Break-route separation +0.066 (p 0.03) and all-route separation +0.045 (p 0.05) agree in direction. DL and OL show no held-out gain in either version.
- **Not reproducible:** deep-target share +0.30 (the definition was not given; targets per deep route gives +0.05); YACOE −0.31; DL draft-year-only +0.27. All dropped.
- **Rule violation:** the Table 1 draft-pick and draft-round rows, "drafted players only", and "draft capital". Removed and not computed.
- Judge review, v1 claims: confirmed 164 / 28 / 8 and the by-group counts, 69% vs 49% / 39%, and that "Rookies only" was wrong. Outdated: "notebook not pushed, private". It is public v3.

## Handed-over v2 vs the submitted writeup (dc3d22d), and rule check
- **What v2 changes:** a new title ("Does the Combine Carry to Sunday?…"); NGS-score, weight-vs-40 and production-null findings added; OL slide drill added; TE dropped; DL reframed as a lead with an as-reported ladder; Burst Score, "3/3 held-out" and "Rookies only" dropped; a best-of-N figure and Table 2 added; the scorecard, leads, DB-power table and unsupervised paragraph removed. Six figures plus two tables replace seven figures plus one table.
- **Counts:** submitted v1 is 1,894 strict tokens with 7 figures + 1 table = 8 visuals. Handed-over v2 is 1,903 strict tokens with 6 figures + 2 tables = 8 visuals. Both are under the limits.
- **Rule breaks in the handed-over v2:**
  1. Uses draft pick or round as variables: Table 1 rows "Add log draft pick", "Add draft-round dummies", "Drafted players only", and the phrase "draft capital".
  2. Has no "NOT DETECTED (low power)" labels and almost no MDEs: only the DB MDE (0.38), none for the NGS, production or DL nulls.
  3. Drops the "the Combine works, but read it right" framing.
  4. Loses the attribution line (the F5 fix): no CC BY-NC 4.0 credit and no nflverse credit, though it still cites the PFR yards/target.
  5. Brings back an H1 heading, undoing the F6 fix.
  6. Is less coach-friendly: Theil–Sen, Westfall–Young, Bonferroni, within-class normal scores, R² gain, Fisher-z.
  7. Its reproducibility bullet describes a notebook that did not exist yet.
  8. Changes scope from WR/TE/DB/DL to WR/DL/OL/DB (OL added, TE dropped). That needs Kevin's OK.
  - No comps. No dated text, so MM/YYYY is not at issue. No 0–100 composite (Burst Score dropped).
- **Corrected v2** (`v2/writeup_for_kaggle_v2.md`): every number is rendered from the live `results_v2.json`. 1,702 strict tokens (1,597 words only); 6 figures + 2 tables = 8 visuals. Breaks 1–7 are fixed. The OL scope change is kept but flagged for Kevin. The cover was not regenerated.

## Table 2 DL/OL negative held-out gains (11/25/2026)
- **Verdict: real.** The 11/23 reconstruction had two weak spots, both fixed now:
  - It chose the test by |ρ|, so it could choose one running the "wrong" way. It now chooses only in the pre-declared direction (+ = better athlete).
  - It allowed sparsely measured drills, which cut one OL fold to 13 players. It now requires a test measured for 80%+ of players.
  - Neither weak spot caused the negatives.
- **Defensive line:** held-out gain **−0.070** (was −0.171), luck 95th pct +0.034, p 0.86.
  - Hold out 2023 → chooses broad jump (training ρ +0.11), fold gain −0.005.
  - Hold out 2024 → chooses vertical (+0.29), held-out ρ −0.17, fold gain −0.031.
  - Hold out 2025 → chooses vertical (+0.27), held-out ρ −0.15, fold gain −0.185.
  - The 40's pressure link sits in the 2023 class: within-class +0.40 vs +0.15 (2024) and +0.10 (2025).
  - One test named in advance (the 40): +0.03.
- **Offensive line:** held-out gain **−0.131** (was −0.083), luck +0.102, p 0.64.
  - Hold out 2023 → chooses slide-drill acceleration (training +0.45), held-out +0.44, fold gain +0.016.
  - Hold out 2024 → chooses screen-drill deceleration (+0.35), held-out −0.57, fold gain −0.344.
  - Hold out 2025 → slide drill (+0.53), held-out +0.04, fold gain −0.055.
  - Slide drill named in advance: +0.071, but that drill was itself chosen after seeing all three classes.
- **Not the cause:**
  - Sign convention: the OL outcome is negated so + = fewer pressures, and R² gain doesn't depend on sign.
  - Leakage: normal scores are computed within class, and selection happens inside the training classes only.
- **Receivers after the fix:** Sunday Speed +0.190 (luck +0.062, p 0.003); break-route separation +0.066 (p 0.017); all-route separation +0.045 (p 0.047).
- **Writeup:** the line rows now read "Does not hold up out of sample yet", with the per-class explanation.

## Kaggle run, v2 (11/2026)

- Pushed `kaggle_upload/kernel_v2` as **version 4** of the public notebook `kevinpolymath/read-the-combine-through-body-size` (is_private false, competition data attached) on 11/25/2026, 6:14 PM ET.
- Status: **COMPLETE**. Log: `GATE (Combine tracking -> regular-season performance): PASS`; 6 of 6 figures written (fig1 to fig6); notebook total 1,284 s (about 21 min).
- The Kaggle `results_v2.json` matches the local `v2/results_v2.json` on every number (within 0.005 or 1%), so the writeup numbers match the public notebook.
- Cover image not regenerated (Kevin's call); see `kaggle_upload/writeup_v2/TITLE_AND_COVER.md`.
