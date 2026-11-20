# How to submit the Big Data Bowl 2027 writeup (rebuilt 11/2026, reframed: "the Combine works, but read it right")

Rules checked against the official Kaggle pages (Overview, Evaluation, Submission Requirements, Rules) via the Kaggle API on 11/2026. Re-read the competition's **Rules** and **Submission Requirements** tabs yourself before you submit; those tabs are the source of truth.

**Deadline: 6:59 PM ET on 01/06/2027 (11:59 PM UTC).** Hackathon: one submission per team, and the Writeup only counts once you press **Submit**.

## What the rules require (and where we stand)
| Rule | Our status |
|---|---|
| Writeup at most 2,000 words, fewer than 10 tables or figures | 1,826 markdown words (about 1,945 if a counter also counts the table's markup); 7 figures + 1 table = 8 |
| Explicitly link Combine tracking to regular-season game performance (pass/fail gate) | Stated at the top and recomputed in the GATE cell |
| Readable markdown, embedded visuals, attached **public** Kaggle notebook (pass/fail gate) | Notebook ready; you make it public and attach it |
| Must use the provided player tracking data (otherwise not scored) | GATE cell reads `combine_tracking`, `game_tracking_2023/24/25`, `player_play` |
| Most code in an appendix or linked notebook | Code cells are collapsed in the notebook |
| Pick a track | Choose **Open Track** (not the Grand Prize track) |
| External data must be public and free | Only free nflverse / Pro-Football-Reference season stats (two DB outcomes) |
| Do not redistribute Competition Data | The dataset below holds only aggregate result tables and figures, no player rows or names |

Judging (0 to 10 each): Football 30%, Data Science 30%, Writeup 20%, Visualization 20%.

## Step 1. Create the dataset `bdb2027-outputs` (public)
Kaggle: **Datasets, New Dataset**, name it `bdb2027-outputs`. Upload a folder named `out` with exactly these files (all in this repo under `out/`):

- `out/scorecard.csv`
- `out/scorecard_full.csv`
- `out/scorecard_weight.csv`
- `out/figs/fig1_gate_wr.png` (fallback only: shown in the gate cell if the competition data is not attached; every other figure is drawn from the three CSVs)

The notebook finds `scorecard_full.csv` anywhere under `/kaggle/input`, so the folder layout just has to keep `out/` and `out/figs/`.

## Step 2. Import and run the notebook
1. Competition **Code** tab, **New Notebook**, then **File, Import Notebook** and upload `notebook/bdb2027_writeup.ipynb`.
2. **Input pane, Add Input**: add the competition **NFL Big Data Bowl 2027** and your `bdb2027-outputs` dataset. Both are needed.
3. Internet off, no GPU. **Save Version, Save & Run All.** It takes about a minute or two. Check the GATE cell prints `GATE (...): PASS` and `n=62`.
4. Make the notebook **Public** (Share).

## Step 3. Create the Writeup
1. Competition page, **Writeups** tab, **New Writeup**.
2. Title: *Read the Combine through body size: three positions, three different stories*. Subtitle: *Receiver speed is real and shows up on Sunday; linemen's drills work mostly through body size; for defensive backs the Combine alone is a weak guide at this sample size.* First line of the body is the hook: **Read Combine numbers through body size, and three positions tell three different stories.**
3. Paste `notebook/writeup_for_kaggle.md` into the body. Upload the seven PNGs from `notebook/writeup_figs/` where the image lines are (fig1 to fig7, in order). Figure 1 is the receiver gate scatter; Table 1 is already a markdown table.
4. Select the **Open Track**, attach your public notebook, and add any cover image the form offers (use `fig7_scorecard.png` or `fig1_gate_wr.png`).
5. Check the word count the form shows, then press **Submit**. Confirm it says Submitted, not Draft.

Optional: a short YouTube video link. Any external link must be viewable without logging in.

## Writeup structure (five findings)
Hook and gate; 1 Receivers (Fig 1, Fig 2); 2 Defensive line, raw vs size-adjusted (Fig 3); 3 Consistent leads, honest q (Fig 4); 4 Defensive backs, not detected with MDE and power (Table 1, Fig 5); 5 Weight (Fig 6); how a scout uses it (Fig 7); methods; limitations. The verdict once called "DOESN'T TRANSLATE" is now "NOT DETECTED (low power)" (same rule; see METRICS 9 and 12).

## Figure review (11/20/2026)
All seven figures were audited against the best-practice checklist and rebuilt: one colour-blind-safe palette, a zero line on every effect plot, 95% intervals with n and q on the plot (interval hidden and flagged below 15 players), + always = better athlete, footnotes for the Burst Score circularity and for best-test-per-result selection, and fonts sized for the Kaggle column. Figure 7 is now drawn live from `scorecard.csv`, so `fig22_scorecard.png` is no longer needed in the dataset. Upload the PNGs in `notebook/writeup_figs/` again; the earlier uploads are superseded.
