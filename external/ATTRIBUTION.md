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

Downloaded 11/2026.

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

- `ngs_receiving.parquet`, `ngs_rushing.parquet`, `ngs_passing.parquet` — NFL Next Gen Stats (powered by AWS) receiving, rushing, and passing, 2016 onward, as published in the free public nflverse release. Week 0 regular-season rows are season totals; weekly rows cover weeks that meet NGS's publishing floor (typically ≥5 targets in a week for receiving).
  Source: https://github.com/nflverse/nflverse-data/releases/tag/nextgen_stats
  Access: `nflreadr::load_nextgen_stats()` / `nflreadpy.load_nextgen_stats()` / https://github.com/nflverse/nflverse-data/releases/download/nextgen_stats/
  Original public source: https://nextgenstats.nfl.com/
  These files are supporting / validation evidence only. The competition writeup still has to be built on the provided Kaggle tracking data.

- `ngs_timestamp.json` — nflverse release timestamp for the nextgen_stats tag.

Downloaded 11/2026 for `explore_ngs.py`.
