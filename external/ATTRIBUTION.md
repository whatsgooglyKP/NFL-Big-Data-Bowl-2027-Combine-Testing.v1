# Public historical data (not Kaggle)

These files are **not** from the NFL Big Data Bowl Kaggle competition. They are public nflverse releases, courtesy of [Pro-Football-Reference](https://www.pro-football-reference.com/) and the [nflverse](https://github.com/nflverse/nflverse-data) project, and are cached here so the athletic-comp script is reproducible.

- `combine.csv` — NFL Combine measurements, seasons 2000 onward.  
  Source: https://github.com/nflverse/nflverse-data/releases/tag/combine  
  Access: `nflreadr::load_combine()` / https://github.com/nflverse/nflverse-data/releases/download/combine/combine.csv  
  This snapshot does **not** include 10-yard splits.

- `draft_picks.csv` — NFL draft picks since 1980, with career Approximate Value, Pro Bowls, and All-Pro counts.  
  Source: https://github.com/nflverse/nflverse-data/releases/tag/draft_picks  
  Access: `nflreadr::load_draft_picks()` / https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv  
  We use weighted Approximate Value (`w_av`); the `car_av` column is empty in this snapshot.

Downloaded 11/2026. If you refresh the files, re-run `athletic_comps.py`.
