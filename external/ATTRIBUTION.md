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

- `advstats_season_def.parquet`, `advstats_season_rec.parquet`, `advstats_season_rush.parquet` — Pro-Football-Reference advanced season stats (defense, receiving, rushing), 2018 onward.
  Source: https://github.com/nflverse/nflverse-data/releases/tag/pfr_advstats
  Access: `nflreadr::load_pfr_advstats()` / `nflreadpy.load_pfr_advstats()` / https://github.com/nflverse/nflverse-data/releases/download/pfr_advstats/

- `advstats_week_def_2023/2024/2025.parquet`, `advstats_week_rec_2023/2024/2025.parquet` — weekly PFR advanced defense and receiving, 2023–2025.
  Same release tag as above.

- `players.parquet` — nflverse player information and ID map (`nfl_id`, `pfr_id`, `gsis_id`, plus names, college, birth date, draft year).
  Source: https://github.com/nflverse/nflverse-data/releases/tag/players
  Access: `nflreadr::load_players()` / https://github.com/nflverse/nflverse-data/releases/download/players/players.parquet
  This is the nflverse go-to ID map; a separate `ff_playerids` release is not published under nflverse-data.

Downloaded 11/2026 for `explore_pfr.py`.
