#!/usr/bin/env python3
"""Feasibility check: free public nflverse / Pro-Football-Reference advanced stats.

Downloads (if missing) public nflverse GitHub release files into external/,
joins them to the 510-player Kaggle rookie file, and reports coverage plus a
small exploratory Spearman of Combine / Sunday start-stop traits vs PFR
defensive rates.

Sources are public nflverse releases, not Kaggle. This script does not print
tokens, does not upload raw Kaggle data, and does not push to git or Drive.

Outputs under out/:
  pfr_columns.csv
  pfr_match_rates.csv
  pfr_id_map.csv
  pfr_unmatched.csv
  pfr_coverage.csv
  pfr_def_career.csv
  pfr_rec_career.csv
  pfr_spearman.csv
"""

from __future__ import annotations

import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
EXT = ROOT / "external"
OUT.mkdir(exist_ok=True)
EXT.mkdir(exist_ok=True)

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
FILES = {
    "advstats_season_def.parquet": f"{BASE}/pfr_advstats/advstats_season_def.parquet",
    "advstats_season_rec.parquet": f"{BASE}/pfr_advstats/advstats_season_rec.parquet",
    "advstats_season_rush.parquet": f"{BASE}/pfr_advstats/advstats_season_rush.parquet",
    "advstats_week_def_2023.parquet": f"{BASE}/pfr_advstats/advstats_week_def_2023.parquet",
    "advstats_week_def_2024.parquet": f"{BASE}/pfr_advstats/advstats_week_def_2024.parquet",
    "advstats_week_def_2025.parquet": f"{BASE}/pfr_advstats/advstats_week_def_2025.parquet",
    "advstats_week_rec_2023.parquet": f"{BASE}/pfr_advstats/advstats_week_rec_2023.parquet",
    "advstats_week_rec_2024.parquet": f"{BASE}/pfr_advstats/advstats_week_rec_2024.parquet",
    "advstats_week_rec_2025.parquet": f"{BASE}/pfr_advstats/advstats_week_rec_2025.parquet",
    "players.parquet": f"{BASE}/players/players.parquet",
}

SEASONS = (2023, 2024, 2025)  # aligned with the Kaggle tracking window
POS_GROUP = {
    "WR": "WR",
    "TE": "TE",
    "CB": "CB",
    "FS": "S",
    "SS": "S",
    "DB": "DB",
    "DE": "DL",
    "DT": "DL",
    "NT": "DL",
    "OLB": "EDGE/OLB",
    "ILB": "LB",
    "MLB": "LB",
    "G": "OL",
    "T": "OL",
    "C": "OL",
    "RB": "RB",
    "FB": "RB",
}

# College aliases used only for fallback pfr_id fills, never to override a
# conflicting nfl_id match.
COLLEGE_ALIAS = {
    "texas christian": "tcu",
    "tcu": "tcu",
    "louisiana state": "lsu",
    "lsu": "lsu",
    "central florida": "ucf",
    "ucf": "ucf",
    "miami": "miami",
    "miami fl": "miami",
    "miami florida": "miami",
    "ohio state": "ohio st",
    "ohio st": "ohio st",
    "ohio st.": "ohio st",
    "penn state": "penn st",
    "penn st": "penn st",
    "ole miss": "mississippi",
    "mississippi": "mississippi",
    "north carolina": "north carolina",
    "unc": "north carolina",
    "south carolina": "south carolina",
    "usc": "southern california",
    "southern california": "southern california",
    "texas am": "texas a&m",
    "texas a m": "texas a&m",
    "texas a&m": "texas a&m",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def norm_name(s) -> str:
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v|vi)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_college(s) -> str:
    s = norm_name(s)
    return COLLEGE_ALIAS.get(s, s)


def download_if_missing() -> None:
    import urllib.request

    for name, url in FILES.items():
        dest = EXT / name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        log(f"Downloading {name} …")
        urllib.request.urlretrieve(url, dest)
        log(f"  wrote {dest} ({dest.stat().st_size:,} bytes)")


def update_attribution() -> None:
    path = EXT / "ATTRIBUTION.md"
    extra = """
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
"""
    existing = path.read_text() if path.exists() else ""
    if "advstats_season_def.parquet" in existing:
        return
    path.write_text(existing.rstrip() + "\n" + extra)
    log("  updated external/ATTRIBUTION.md")


def inventory() -> pd.DataFrame:
    rows = []
    wanted = {
        "missed tackles": ["m_tkl", "def_missed_tackles"],
        "missed tackle %": ["m_tkl_percent", "def_missed_tackle_pct"],
        "coverage targets": ["tgt", "def_targets"],
        "completions allowed": ["cmp", "def_completions_allowed"],
        "completion % allowed": ["cmp_percent", "def_completion_pct"],
        "yards allowed": ["yds", "def_yards_allowed"],
        "yards/target allowed": ["yds_tgt", "def_yards_allowed_per_tgt"],
        "yards/completion allowed": ["yds_cmp", "def_yards_allowed_per_cmp"],
        "TDs allowed": ["td", "def_receiving_td_allowed"],
        "passer rating allowed": ["rat", "def_passer_rating_allowed"],
        "depth of target (ADOT)": ["dadot", "def_adot", "adot"],
        "air yards": ["air", "def_air_yards_completed"],
        "yards after catch (allowed or rec)": ["yac", "def_yards_after_catch"],
        "blitzes": ["bltz", "def_times_blitzed"],
        "hurries": ["hrry", "def_times_hurried"],
        "QB knocks/hits": ["qbkd", "def_times_hitqb"],
        "sacks": ["sk", "def_sacks"],
        "pressures": ["prss", "def_pressures"],
        "combined tackles": ["comb", "def_tackles_combined"],
        "batted passes": ["bats"],
        "interceptions": ["int", "def_ints", "receiving_int"],
        "receptions (receiving)": ["rec"],
        "receiving yards": [],  # handled as yds on rec table
        "drops": ["drop", "receiving_drop", "passing_drops"],
        "drop %": ["drop_percent", "receiving_drop_pct", "passing_drop_pct"],
        "broken tackles": ["brk_tkl", "receiving_broken_tackles", "rushing_broken_tackles"],
        "YAC per reception": ["yac_r"],
        "yards before catch": ["ybc", "ybc_r"],
    }
    files = [
        ("season_def", "advstats_season_def.parquet"),
        ("season_rec", "advstats_season_rec.parquet"),
        ("season_rush", "advstats_season_rush.parquet"),
        ("week_def_2023", "advstats_week_def_2023.parquet"),
        ("week_rec_2023", "advstats_week_rec_2023.parquet"),
        ("players", "players.parquet"),
    ]
    schemas = {}
    for label, name in files:
        df = pd.read_parquet(EXT / name)
        schemas[label] = list(df.columns)
        rows.append(
            {
                "file": name,
                "table": label,
                "n_rows": int(len(df)),
                "n_cols": int(df.shape[1]),
                "columns": ", ".join(df.columns),
                "id_fields": ", ".join(
                    c
                    for c in df.columns
                    if c.lower() in {
                        "pfr_id",
                        "pfr_player_id",
                        "gsis_id",
                        "nfl_id",
                        "player",
                        "pfr_player_name",
                        "display_name",
                    }
                ),
            }
        )
    # Concept coverage
    concept_rows = []
    for concept, aliases in wanted.items():
        present = []
        for label, cols in schemas.items():
            hits = [c for c in cols if c in aliases or c.lower() in {a.lower() for a in aliases}]
            # rec yds is just 'yds' on the rec table
            if concept == "receiving yards" and label.startswith("season_rec") and "yds" in cols:
                hits.append("yds")
            if hits:
                present.append(f"{label}:{','.join(hits)}")
        concept_rows.append(
            {
                "concept": concept,
                "present": bool(present),
                "where": "; ".join(present) if present else "NOT IN THESE FILES",
            }
        )
    pd.DataFrame(concept_rows).to_csv(OUT / "pfr_concepts.csv", index=False)
    inv = pd.DataFrame(rows)
    inv.to_csv(OUT / "pfr_columns.csv", index=False)
    log(f"  wrote pfr_columns.csv and pfr_concepts.csv ({len(concept_rows)} concepts)")
    return inv, pd.DataFrame(concept_rows)


def build_id_map(kaggle: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    nv = pd.read_parquet(EXT / "players.parquet")
    nv["nfl_id_num"] = pd.to_numeric(nv["nfl_id"], errors="coerce")
    nv["name_n"] = nv["display_name"].map(norm_name)
    nv["college_n"] = nv["college_name"].map(norm_college)
    nv["birth_date"] = pd.to_datetime(nv["birth_date"], errors="coerce")

    k = kaggle.copy()
    k["pos_group"] = k["nfl_position"].map(POS_GROUP).fillna(k["nfl_position"])
    k["name_n"] = k["display_name"].map(norm_name)
    k["college_n"] = k["college_name"].map(norm_college)
    k["birth_date"] = pd.to_datetime(k["birth_date"], errors="coerce")

    nv_id = nv[nv["nfl_id_num"].notna()].copy()
    nv_id["nfl_id_num"] = nv_id["nfl_id_num"].astype(int)
    m = k.merge(
        nv_id[
            [
                "nfl_id_num",
                "display_name",
                "pfr_id",
                "gsis_id",
                "draft_year",
                "college_name",
                "birth_date",
                "position",
                "rookie_season",
            ]
        ].rename(
            columns={
                "nfl_id_num": "nfl_id",
                "display_name": "nv_display_name",
                "draft_year": "nv_draft_year",
                "college_name": "nv_college",
                "birth_date": "nv_birth_date",
                "position": "nv_position",
            }
        ),
        on="nfl_id",
        how="left",
    )
    m["match_method"] = np.where(m["gsis_id"].notna() | m["nv_display_name"].notna(), "nfl_id", pd.NA)

    # Fill missing pfr_id from the public combine and draft_picks files when
    # name + draft year + college uniquely identify one person.
    comb = pd.read_csv(EXT / "combine.csv")
    picks = pd.read_csv(EXT / "draft_picks.csv")
    comb["name_n"] = comb["player_name"].map(norm_name)
    comb["college_n"] = comb["school"].map(norm_college)
    picks["name_n"] = picks["pfr_player_name"].map(norm_name)
    picks["college_n"] = picks["college"].map(norm_college)

    def unique_pfr(name_n, year, college_n):
        """Require name + draft year + college; never fall back to name+year alone."""
        hits = []
        if name_n and pd.notna(year) and college_n:
            # UDFAs often have combine.season filled but draft_year null.
            year_ok = (comb.draft_year == year) | (comb.draft_year.isna() & (comb.season == year))
            c = comb[
                (comb.name_n == name_n)
                & year_ok
                & (comb.college_n == college_n)
                & comb.pfr_id.notna()
            ]
            if c.pfr_id.nunique() == 1:
                hits.append(("combine_name_year", str(c.pfr_id.iloc[0])))
            p = picks[
                (picks.name_n == name_n)
                & (picks.season == year)
                & (picks.college_n == college_n)
                & picks.pfr_player_id.notna()
            ]
            if p.pfr_player_id.nunique() == 1:
                hits.append(("draft_picks_name_year", str(p.pfr_player_id.iloc[0])))
        ids = {h[1] for h in hits}
        if len(ids) == 1:
            return hits[0]
        return None

    filled = 0
    for i, r in m[m.pfr_id.isna()].iterrows():
        hit = unique_pfr(r.name_n, r.draft_year, r.college_n)
        if hit:
            m.at[i, "pfr_id"] = hit[1]
            if pd.isna(m.at[i, "match_method"]):
                m.at[i, "match_method"] = hit[0]
            else:
                m.at[i, "match_method"] = str(m.at[i, "match_method"]) + "+" + hit[0]
            filled += 1
    log(f"  filled {filled} missing pfr_ids from combine/draft_picks name+year+college")

    # Name+year+college fallback into nflverse players that lack our nfl_id
    still = m[m.match_method.isna()].copy()
    extra = 0
    for i, r in still.iterrows():
        if not r.college_n or pd.isna(r.draft_year):
            continue
        cands = nv[
            (nv.name_n == r.name_n)
            & (nv.draft_year == r.draft_year)
            & (nv.college_n == r.college_n)
            & nv.pfr_id.notna()
        ]
        # birth date agreement when both present
        if pd.notna(r.birth_date) and cands["birth_date"].notna().any():
            cands = cands[cands.birth_date.isna() | (cands.birth_date == r.birth_date)]
        if len(cands) == 1:
            m.at[i, "pfr_id"] = cands.pfr_id.iloc[0]
            m.at[i, "gsis_id"] = cands.gsis_id.iloc[0]
            m.at[i, "nv_display_name"] = cands.display_name.iloc[0]
            m.at[i, "match_method"] = "name_year_college"
            extra += 1
    log(f"  name+year+college fallback matches: {extra}")

    m["match_method"] = m["match_method"].fillna("unmatched")
    m["has_pfr_id"] = m["pfr_id"].notna()
    m["has_gsis_id"] = m["gsis_id"].notna()
    m["has_nflverse_player"] = m["match_method"].ne("unmatched") | m["has_pfr_id"]

    # Match-rate table
    rows = []
    for col, grp in (("nfl_position", m.nfl_position), ("pos_group", m.pos_group)):
        for g, sub in m.groupby(grp):
            rows.append(
                {
                    "group_type": col,
                    "group": g,
                    "n_kaggle": int(len(sub)),
                    "n_matched_nfl_id": int(sub.match_method.str.contains("nfl_id", na=False).sum()),
                    "n_has_pfr_id": int(sub.has_pfr_id.sum()),
                    "n_unmatched": int((sub.match_method == "unmatched").sum()),
                    "match_rate_id": float(sub.match_method.str.contains("nfl_id", na=False).mean()),
                    "pfr_id_rate": float(sub.has_pfr_id.mean()),
                }
            )
    # overall
    rows.append(
        {
            "group_type": "all",
            "group": "ALL_510",
            "n_kaggle": int(len(m)),
            "n_matched_nfl_id": int(m.match_method.str.contains("nfl_id", na=False).sum()),
            "n_has_pfr_id": int(m.has_pfr_id.sum()),
            "n_unmatched": int((m.match_method == "unmatched").sum()),
            "match_rate_id": float(m.match_method.str.contains("nfl_id", na=False).mean()),
            "pfr_id_rate": float(m.has_pfr_id.mean()),
        }
    )
    rates = pd.DataFrame(rows).sort_values(["group_type", "group"])
    rates.to_csv(OUT / "pfr_match_rates.csv", index=False)

    keep = [
        "nfl_id",
        "display_name",
        "draft_year",
        "nfl_position",
        "pos_group",
        "college_name",
        "birth_date",
        "pfr_id",
        "gsis_id",
        "nv_display_name",
        "nv_draft_year",
        "nv_college",
        "nv_position",
        "match_method",
        "has_pfr_id",
    ]
    idmap = m[keep].copy()
    idmap.to_csv(OUT / "pfr_id_map.csv", index=False)
    unmatched = idmap[idmap.match_method.eq("unmatched")].copy()
    unmatched.to_csv(OUT / "pfr_unmatched.csv", index=False)
    log(
        f"  ID map: {int(m.match_method.str.contains('nfl_id', na=False).sum())}/510 by nfl_id, "
        f"{int(m.has_pfr_id.sum())} with pfr_id, {int((m.match_method=='unmatched').sum())} unmatched"
    )
    return idmap, rates


def passer_rating(cmp_, att, yds, td, int_) -> float:
    """NFL passer rating; returns nan if attempts are 0."""
    if not np.isfinite(att) or att <= 0:
        return np.nan
    a = (cmp_ / att - 0.3) * 5
    b = (yds / att - 3) * 0.25
    c = (td / att) * 20
    d = 2.375 - (int_ / att * 25)
    a, b, c, d = (float(np.clip(x, 0, 2.375)) for x in (a, b, c, d))
    return (a + b + c + d) / 6 * 100


def aggregate_def(season_df: pd.DataFrame, seasons: tuple[int, ...]) -> pd.DataFrame:
    d = season_df[season_df.season.isin(seasons) & season_df["pfr_id"].notna()].copy()
    count_cols = [
        "g",
        "gs",
        "int",
        "tgt",
        "cmp",
        "yds",
        "td",
        "air",
        "yac",
        "bltz",
        "hrry",
        "qbkd",
        "sk",
        "prss",
        "comb",
        "m_tkl",
        "bats",
    ]
    for c in count_cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    # Weighted ADOT: dadot * tgt
    d["dadot"] = pd.to_numeric(d["dadot"], errors="coerce")
    d["dadot_w"] = d["dadot"] * d["tgt"]
    g = d.groupby("pfr_id", dropna=True)
    out = g.agg(
        n_seasons=("season", "nunique"),
        seasons=("season", lambda s: ",".join(str(int(x)) for x in sorted(s.unique()))),
        teams=("tm", lambda s: ",".join(sorted({str(x) for x in s.dropna()}))),
        pfr_pos=("pos", "last"),
        pfr_name=("player", "last"),
        **{c: (c, "sum") for c in count_cols},
        dadot_w=("dadot_w", "sum"),
    ).reset_index()
    out["tackle_attempts"] = out["comb"] + out["m_tkl"]
    out["m_tkl_percent"] = np.where(out["tackle_attempts"] > 0, out["m_tkl"] / out["tackle_attempts"], np.nan)
    out["yds_tgt"] = np.where(out["tgt"] > 0, out["yds"] / out["tgt"], np.nan)
    out["yds_cmp"] = np.where(out["cmp"] > 0, out["yds"] / out["cmp"], np.nan)
    out["cmp_percent"] = np.where(out["tgt"] > 0, out["cmp"] / out["tgt"], np.nan)
    out["dadot"] = np.where(out["tgt"] > 0, out["dadot_w"] / out["tgt"], np.nan)
    out["rat"] = [
        passer_rating(c, a, y, t, i)
        for c, a, y, t, i in zip(out["cmp"], out["tgt"], out["yds"], out["td"], out["int"])
    ]
    return out


def aggregate_rec(season_df: pd.DataFrame, seasons: tuple[int, ...]) -> pd.DataFrame:
    d = season_df[season_df.season.isin(seasons) & season_df["pfr_id"].notna()].copy()
    count_cols = ["g", "gs", "tgt", "rec", "yds", "td", "x1d", "ybc", "yac", "brk_tkl", "drop", "int"]
    for c in count_cols:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    g = d.groupby("pfr_id", dropna=True)
    out = g.agg(
        n_seasons=("season", "nunique"),
        seasons=("season", lambda s: ",".join(str(int(x)) for x in sorted(s.unique()))),
        teams=("tm", lambda s: ",".join(sorted({str(x) for x in s.dropna()}))),
        pfr_pos=("pos", "last"),
        pfr_name=("player", "last"),
        **{c: (c, "sum") for c in count_cols if c in d.columns},
    ).reset_index()
    out["catch_rate"] = np.where(out["tgt"] > 0, out["rec"] / out["tgt"], np.nan)
    out["yac_r"] = np.where(out["rec"] > 0, out["yac"] / out["rec"], np.nan)
    out["drop_percent"] = np.where(out["tgt"] > 0, out["drop"] / out["tgt"], np.nan)
    out["yds_tgt"] = np.where(out["tgt"] > 0, out["yds"] / out["tgt"], np.nan)
    return out


def weekly_counts() -> pd.DataFrame:
    parts = []
    for yr in SEASONS:
        w = pd.read_parquet(EXT / f"advstats_week_def_{yr}.parquet")
        w["is_reg"] = w["game_type"].eq("REG")
        parts.append(w)
    w = pd.concat(parts, ignore_index=True)
    # REG-only rollup of count stats
    reg = w[w.is_reg & w["pfr_player_id"].notna()]
    agg = (
        reg.groupby("pfr_player_id", dropna=True)
        .agg(
            week_reg_games=("week", "nunique"),
            week_tgt=("def_targets", "sum"),
            week_yds=("def_yards_allowed", "sum"),
            week_cmp=("def_completions_allowed", "sum"),
            week_m_tkl=("def_missed_tackles", "sum"),
            week_comb=("def_tackles_combined", "sum"),
            week_prss=("def_pressures", "sum"),
            week_sk=("def_sacks", "sum"),
            week_hrry=("def_times_hurried", "sum"),
            week_bltz=("def_times_blitzed", "sum"),
        )
        .reset_index()
        .rename(columns={"pfr_player_id": "pfr_id"})
    )
    agg["week_yds_tgt"] = np.where(agg.week_tgt > 0, agg.week_yds / agg.week_tgt, np.nan)
    agg["week_tkl_att"] = agg.week_comb + agg.week_m_tkl
    agg["week_m_tkl_percent"] = np.where(agg.week_tkl_att > 0, agg.week_m_tkl / agg.week_tkl_att, np.nan)
    return agg


def coverage_and_careers(idmap: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    defn = pd.read_parquet(EXT / "advstats_season_def.parquet")
    rec = pd.read_parquet(EXT / "advstats_season_rec.parquet")
    career_def = aggregate_def(defn, SEASONS)
    career_rec = aggregate_rec(rec, SEASONS)
    week = weekly_counts()

    # Never join on missing pfr_id — pandas can attach a NaN-key aggregate to every unmatched row.
    career_def = career_def[career_def["pfr_id"].notna()].copy()
    career_rec = career_rec[career_rec["pfr_id"].notna()].copy()
    week = week[week["pfr_id"].notna()].copy()
    d = idmap.merge(career_def, on="pfr_id", how="left")
    d = d.merge(week, on="pfr_id", how="left")
    r = idmap.merge(career_rec, on="pfr_id", how="left")

    d["has_def_row"] = d["g"].fillna(0) > 0
    d["usable_cov20"] = d["tgt"].fillna(0) >= 20
    d["usable_tkl15"] = d["tackle_attempts"].fillna(0) >= 15
    d["usable_prss15"] = d["prss"].fillna(0) >= 15
    r["has_rec_row"] = r["g"].fillna(0) > 0
    r["usable_tgt20"] = r["tgt"].fillna(0) >= 20

    d.to_csv(OUT / "pfr_def_career.csv", index=False)
    r.to_csv(OUT / "pfr_rec_career.csv", index=False)

    rows = []
    for gname, sub in d.groupby("pos_group"):
        rec_sub = r[r.pos_group == gname]
        rows.append(
            {
                "pos_group": gname,
                "n_kaggle": int(len(sub)),
                "n_with_pfr_id": int(sub.has_pfr_id.sum()),
                "n_with_def_row_2023_25": int(sub.has_def_row.sum()),
                "n_cov_tgt_ge20": int(sub.usable_cov20.sum()),
                "n_tkl_att_ge15": int(sub.usable_tkl15.sum()),
                "n_both_cov20_tkl15": int((sub.usable_cov20 & sub.usable_tkl15).sum()),
                "n_prss_ge15": int(sub.usable_prss15.sum()),
                "n_with_rec_row_2023_25": int(rec_sub.has_rec_row.sum()),
                "n_rec_tgt_ge20": int(rec_sub.usable_tgt20.sum()),
                "median_tgt": float(sub.loc[sub.has_def_row, "tgt"].median()) if sub.has_def_row.any() else np.nan,
                "median_tkl_att": float(sub.loc[sub.has_def_row, "tackle_attempts"].median()) if sub.has_def_row.any() else np.nan,
                "median_prss": float(sub.loc[sub.has_def_row, "prss"].median()) if sub.has_def_row.any() else np.nan,
            }
        )
    # bigger buckets
    buckets = {
        "CB+S+DB": d.pos_group.isin(["CB", "S", "DB"]),
        "DL (DE/DT/NT)": d.pos_group.eq("DL"),
        "DL+EDGE/OLB": d.pos_group.isin(["DL", "EDGE/OLB"]),
        "WR+TE": d.pos_group.isin(["WR", "TE"]),
        "ALL_510": pd.Series(True, index=d.index),
    }
    for name, mask in buckets.items():
        sub = d[mask]
        rec_sub = r[mask]
        rows.append(
            {
                "pos_group": name,
                "n_kaggle": int(len(sub)),
                "n_with_pfr_id": int(sub.has_pfr_id.sum()),
                "n_with_def_row_2023_25": int(sub.has_def_row.sum()),
                "n_cov_tgt_ge20": int(sub.usable_cov20.sum()),
                "n_tkl_att_ge15": int(sub.usable_tkl15.sum()),
                "n_both_cov20_tkl15": int((sub.usable_cov20 & sub.usable_tkl15).sum()),
                "n_prss_ge15": int(sub.usable_prss15.sum()),
                "n_with_rec_row_2023_25": int(rec_sub.has_rec_row.sum()),
                "n_rec_tgt_ge20": int(rec_sub.usable_tgt20.sum()),
                "median_tgt": float(sub.loc[sub.has_def_row, "tgt"].median()) if sub.has_def_row.any() else np.nan,
                "median_tkl_att": float(sub.loc[sub.has_def_row, "tackle_attempts"].median()) if sub.has_def_row.any() else np.nan,
                "median_prss": float(sub.loc[sub.has_def_row, "prss"].median()) if sub.has_def_row.any() else np.nan,
            }
        )
    cov = pd.DataFrame(rows)
    cov.to_csv(OUT / "pfr_coverage.csv", index=False)
    log(f"  wrote coverage / career tables")
    return d, r, cov


def spearman_row(group, xname, yname, x, y) -> dict:
    m = pd.DataFrame({"x": x, "y": y}).dropna()
    n = int(len(m))
    if n < 5:
        return {
            "group": group,
            "x": xname,
            "y": yname,
            "n": n,
            "rho": np.nan,
            "p": np.nan,
            "note": "exploratory; unadjusted; n<5 not tested",
        }
    rho, p = spearmanr(m["x"], m["y"])
    return {
        "group": group,
        "x": xname,
        "y": yname,
        "n": n,
        "rho": float(rho) if np.isfinite(rho) else np.nan,
        "p": float(p) if np.isfinite(p) else np.nan,
        "note": "exploratory; unadjusted; 2023-2025 PFR season aggregates",
    }


def run_spearman(def_career: pd.DataFrame) -> pd.DataFrame:
    cr = pd.read_csv(DATA / "combine_results.csv")
    tests = cr[
        [
            "nfl_id",
            "forty",
            "ten_yd_split",
            "vertical",
            "broad_jump",
            "three_cone",
            "short_shuttle",
        ]
    ].copy()
    # tracking-derived 20-yard split where we have it
    t20_path = OUT / "combine_to_game_players.csv"
    if t20_path.exists():
        t20 = pd.read_csv(t20_path, usecols=lambda c: c in {"nfl_id", "c_t20_derived"})
        tests = tests.merge(t20, on="nfl_id", how="left")
    else:
        tests["c_t20_derived"] = np.nan

    sunday_path = OUT / "eda_accel_players.csv"
    if sunday_path.exists():
        sun = pd.read_csv(
            sunday_path,
            usecols=lambda c: c
            in {
                "nfl_id",
                "sunday_brakes",
                "sunday_reburst",
                "g_decel",
                "g_accel",
                "usable_sunday",
            },
        )
        tests = tests.merge(sun, on="nfl_id", how="left")
    else:
        tests["sunday_brakes"] = np.nan
        tests["sunday_reburst"] = np.nan
        tests["usable_sunday"] = False

    d = def_career.merge(tests, on="nfl_id", how="left")
    xcols = [
        ("forty", "Official 40"),
        ("ten_yd_split", "Official 10-yard split"),
        ("c_t20_derived", "Tracking-derived 20-yard split"),
        ("vertical", "Vertical"),
        ("broad_jump", "Broad jump"),
        ("three_cone", "3-cone"),
        ("short_shuttle", "Short shuttle"),
        ("sunday_brakes", "Sunday Brakes (0-100)"),
        ("sunday_reburst", "Sunday Re-Burst (0-100)"),
        ("g_decel", "Sunday Brakes raw (yd/s²)"),
        ("g_accel", "Sunday Re-Burst raw (yd/s²)"),
    ]
    ycols = [
        ("m_tkl_percent", "Missed tackle %"),
        ("yds_tgt", "Yards per target allowed"),
    ]
    groups = [
        ("CB (tgt>=20)", d[(d.pos_group == "CB") & d.usable_cov20]),
        ("S (tgt>=20)", d[(d.pos_group == "S") & d.usable_cov20]),
        ("CB+S (tgt>=20)", d[d.pos_group.isin(["CB", "S"]) & d.usable_cov20]),
        ("CB (tkl att>=15)", d[(d.pos_group == "CB") & d.usable_tkl15]),
        ("S (tkl att>=15)", d[(d.pos_group == "S") & d.usable_tkl15]),
        ("CB+S (tkl att>=15)", d[d.pos_group.isin(["CB", "S"]) & d.usable_tkl15]),
        ("DB group CB+S+DB (tgt>=20)", d[d.pos_group.isin(["CB", "S", "DB"]) & d.usable_cov20]),
        ("DB group CB+S+DB (tkl att>=15)", d[d.pos_group.isin(["CB", "S", "DB"]) & d.usable_tkl15]),
        ("EDGE/OLB (tkl att>=15)", d[(d.pos_group == "EDGE/OLB") & d.usable_tkl15]),
        ("LB (tkl att>=15)", d[(d.pos_group == "LB") & d.usable_tkl15]),
        ("DL (prss>=15)", d[(d.pos_group == "DL") & d.usable_prss15]),
    ]
    rows = []
    for gname, sub in groups:
        for x, _xl in xcols:
            # Sunday scores only make sense for WR/CB/S with a usable Sunday profile
            if x.startswith("sunday") or x in {"g_decel", "g_accel"}:
                if "usable_sunday" in sub.columns:
                    use = sub[sub["usable_sunday"].fillna(False).astype(bool)]
                else:
                    use = sub.iloc[0:0]
            else:
                use = sub
            for y, _yl in ycols:
                if x not in use.columns or y not in use.columns:
                    continue
                # For missed tackle % prefer the tackle-attempt samples; for
                # yards/target prefer the coverage-target samples. Still run
                # both so the table is complete, but skip obviously mismatched
                # tiny cells already handled by n<5.
                rows.append(spearman_row(gname, x, y, use[x], use[y]))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "pfr_spearman.csv", index=False)
    log(f"  wrote pfr_spearman.csv ({len(out)} tests)")
    return out


def main() -> int:
    t0 = time.time()
    download_if_missing()
    update_attribution()
    kaggle = pd.read_csv(DATA / "players.csv")
    log("Inventorying PFR / nflverse columns …")
    _inv, concepts = inventory()
    print(concepts.to_string(index=False))
    log("Joining to the 510 Kaggle rookies …")
    idmap, rates = build_id_map(kaggle)
    print(rates[rates.group_type.isin(["pos_group", "all"])].to_string(index=False))
    log("Building 2023-2025 career PFR rates and coverage …")
    d, r, cov = coverage_and_careers(idmap)
    print(cov.to_string(index=False))
    log("Exploratory Spearman …")
    sp = run_spearman(d)
    show = sp[(sp.n >= 8) & sp.rho.notna()].copy()
    show["abs_rho"] = show.rho.abs()
    # Highlight the pre-declared pairs
    focus = show[
        show.x.isin(
            [
                "forty",
                "ten_yd_split",
                "c_t20_derived",
                "vertical",
                "broad_jump",
                "three_cone",
                "short_shuttle",
                "sunday_brakes",
                "sunday_reburst",
            ]
        )
        & show.group.str.contains(r"CB\+|CB \(|S \(|DB group")
    ]
    with pd.option_context("display.width", 160, "display.float_format", lambda v: f"{v:0.3f}"):
        print(focus.sort_values(["group", "y", "p"]).to_string(index=False))
    log(f"Done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
