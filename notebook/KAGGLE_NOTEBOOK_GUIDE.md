# How to run this notebook on Kaggle

This is a beginner walkthrough for Kevin. You do not need to have used a Kaggle notebook before. The file in this folder, `bdb2027_writeup.ipynb`, is a bare skeleton: it loads the competition data, draws a few preview charts, and leaves a TODO in each results section. It is not the submission yet.

Official documentation checked in 11/2026:

- [How to Use Kaggle Notebooks](https://www.kaggle.com/docs/notebooks) — create a notebook, use the editor, add data sources, and save a version with **Save & Run All**
- [How to Use Kaggle Datasets](https://www.kaggle.com/docs/datasets) — create a dataset and upload files
- [How to Use Kaggle Competitions](https://www.kaggle.com/docs/competitions) — joining, rules, and (for prediction contests) submitting from a notebook
- [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027) — our competition. Read the **Overview**, **Submission Requirements**, **Evaluation**, **Data**, and **Rules** tabs before you submit. Those tabs are the source of truth if anything in this guide ever disagrees with them.

## 1. What you are building

This is an analytics hackathon, not a “upload a prediction CSV” contest. Judges score a write-up that uses the provided player tracking data and links Combine tracking to regular-season performance.

In practice that means:

1. A Kaggle notebook that runs from top to bottom.
2. Later, a short write-up on the competition page with that notebook attached, following whatever the official **Submission Requirements** tab says (word limits, figure limits, track selection, and how to attach the notebook). Confirm those details there before January.

The private GitHub repo is our workshop. The notebook on Kaggle is what judges can actually open.

## 2. One-time setup

1. Sign in at [kaggle.com](https://www.kaggle.com). Use one account only.
2. Open the [competition page](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027) and join / accept the official rules. You cannot attach the data until you accept the rules.
3. Download `notebook/bdb2027_writeup.ipynb` from this repo to your computer. You do not need to download the raw competition CSVs for Kaggle — Kaggle already hosts them.

## 3. Create a Kaggle notebook and import this file

**Easiest path (recommended):** start from the competition so the official data is ready to attach.

1. Open the competition **[Code](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/code)** tab.
2. Click **New Notebook**. This opens the Kaggle notebook editor in Python and is the usual way to start a notebook that will use competition data.
3. In the editor menu, choose **File → Import Notebook**. (Some accounts show **File → Upload Notebook**. The official File menu also has **Import Notebook**, including a local-file option.)
4. Upload `bdb2027_writeup.ipynb` from your computer.
5. Rename the notebook if you want. Click the title at the top of the editor to change it.

**Other path:** from almost any Kaggle page, use **Create → New Notebook** ([docs](https://www.kaggle.com/docs/notebooks)), then import the file the same way, then attach the competition data in the next step.

Leave the language set to Python (**File → Language**). You do not need a GPU for this skeleton. Keep **Internet** off unless a later cell truly needs it; this skeleton runs from attached files alone.

## 4. Attach the official competition data

Competition files are not in the GitHub repo, and they should not be re-uploaded as your own dataset. Attach the official input instead.

1. In the notebook editor, open the **Input** pane (right-hand sidebar).
2. Click **Add Input**.
3. Search for **NFL Big Data Bowl 2027** under Competitions, or paste the competition URL.
4. Add it. If you have not already accepted the rules, Kaggle will prompt you to do that first ([docs on adding competition data](https://www.kaggle.com/docs/notebooks)).

The files are mounted at `/kaggle/input/<competition-slug>/`. The slug for this contest is `nfl-big-data-bowl-2027`, so the usual path is:

```text
/kaggle/input/nfl-big-data-bowl-2027/
```

Do not hard-code a guessed path in new cells until you have seen it. The first data cell in our notebook lists `/kaggle/input`, finds `players.csv`, and uses that folder. Locally, the same cell falls back to `./data`.

You should see the nine official CSVs, including `players.csv`, `combine_results.csv`, `combine_tracking.csv`, `player_play.csv`, `games.csv`, `player_career_successes.csv`, and `game_tracking_2023.csv` / `2024` / `2025`.

## 5. Run the notebook

1. Click **Run All**, or run cells one at a time with Shift+Enter, starting at the top.
2. The setup and data-loading cells should print the data path and a file list. Each results section should show a preview chart and a short “preview only” note.
3. If a path error appears, go back to **Input** and confirm the competition data is attached, then rerun from the top.

This first pass is intentionally light: it does not read the large tracking files yet. Later sections will. A full tracking pass can take several minutes.

## 6. Save a version

Kaggle does not treat unsaved editor work as the official copy.

1. Click **Save Version**.
2. Choose **Save & Run All**.
3. Wait until the version finishes. That run is a snapshot of the code, logs, outputs, and attached data sources ([docs](https://www.kaggle.com/docs/notebooks)).

Use this often once the real write-up is in the notebook. The latest successful version is what other people (and later, judges) see when the notebook is public.

When it is time to submit, follow the official **Submission Requirements** tab. Recent Big Data Bowl contests have used a **Writeups** tab: you write a short markdown write-up, attach a **public** Kaggle notebook, choose your track (Open Track for us), and click **Submit**. Confirm that process on the official page; do not rely only on this paragraph.

## 7. Attach external data (nflverse Next Gen Stats) as a Kaggle dataset

The skeleton’s NGS section is optional. If the files are missing, that cell prints a skip message and the rest of the notebook still runs.

External data is allowed when it is public and free for every participant (see the official **Rules**, including the external-data section). We use the free Next Gen Stats receiving tables that [nflverse](https://github.com/nflverse) publishes, plus the attribution file in this repo at `external/ATTRIBUTION.md`. Do not attach paid PFF data.

**Create the dataset** ([official steps](https://www.kaggle.com/docs/datasets)):

1. Go to the Kaggle [Datasets](https://www.kaggle.com/datasets) listing and click **New Dataset**.
2. Give it a clear title, for example `BDB 2027 nflverse Next Gen Stats`, and leave or edit the auto-filled URL slug.
3. Upload the public cache files from this repo’s `external/` folder. A zip is fine; Kaggle unzips archives so the files are readable in notebooks. Include at least:
   - `ngs_receiving.parquet` (required for the skeleton plot)
   - `ATTRIBUTION.md`
   - optionally `ngs_passing.parquet`, `ngs_rushing.parquet`, and `ngs_timestamp.json`
4. Click **Create Dataset** and wait for processing to finish.
5. Make the dataset **public** so every participant can use the same source. That is the clean way to stay inside the external-data rule.
6. In the dataset description, say that the files come from nflverse / Next Gen Stats and point to `ATTRIBUTION.md`. Do not upload the official Kaggle competition CSVs into this dataset. Those already come from the competition input.

**Attach it to the notebook:**

1. Back in the notebook editor, open **Input → Add Input**.
2. Search for the dataset you just created and add it.
3. It will appear under `/kaggle/input/<your-dataset-slug>/`. The notebook searches `/kaggle/input` for `ngs_receiving.parquet`, so you do not have to hard-code the slug.
4. **Save Version → Save & Run All** again so the new input is part of the snapshot.

To refresh the numbers later, re-download the public nflverse files, create a new dataset version (same official “New Dataset” / version flow), and save a new notebook version.

## 8. Practical cautions

- Never put a Kaggle API token, `kaggle.json`, or any secret in the notebook, in a dataset, or in git.
- Never upload the repo’s `data/` folder to Kaggle or to git. Attach the official competition input instead.
- Keep the GitHub repo private if that is still what you want. The *Kaggle* notebook will need to be public when you submit, because judges have to open it.
- Phone verification is only required for Internet / GPU features ([docs](https://www.kaggle.com/docs/notebooks)). This skeleton does not need either.

## 9. Local check (optional)

From the repo root, with the project virtualenv and `./data` present:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute notebook/bdb2027_writeup.ipynb \
  --output /tmp/bdb2027_writeup.executed.ipynb \
  --ExecutePreprocessor.timeout=600
```

That confirms the notebook runs against local `./data`. Do not commit an executed copy that prints raw data rows. The repo should keep the unevaluated source notebook.
