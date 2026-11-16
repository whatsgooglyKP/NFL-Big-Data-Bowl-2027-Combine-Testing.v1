#!/usr/bin/env python3
"""Tie-in to free public NFL Next Gen Stats (AWS-powered) via nflverse.

Downloads (if missing) the public nflverse `nextgen_stats` release into
external/, joins NGS receiving to the 2023–2025 Kaggle rookies, and
reports coverage plus within-position Spearman of Combine / Sunday
start-stop traits vs NGS receiving metrics for WR and TE.

NGS is supporting / validation evidence only. The Kaggle writeup still
has to rest on the provided player tracking data. This script does not
print tokens, does not upload raw Kaggle data, and does not use draft
slot or draft round.

Sources are public nflverse releases, not Kaggle.

Outputs under out/:
  ngs_columns.csv
  ngs_match_rates.csv
  ngs_id_map.csv
  ngs_unmatched.csv
  ngs_coverage.csv
  ngs_player_seasons.csv
  ngs_career.csv
  ngs_validation.csv
  ngs_spearman.csv
  figs/fig17_ngs_receiving.png
"""

from __future__ import annotations

import re
import sys
import time
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
EXT = ROOT / "external"
FIGS = OUT / "figs"
OUT.mkdir(exist_ok=True)
EXT.mkdir(exist_ok=True)
FIGS.mkdir(exist_ok=True)

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
FILES = {
    "ngs_receiving.parquet": f"{BASE}/nextgen_stats/ngs_receiving.parquet",
    "ngs_rushing.parquet": f"{BASE}/nextgen_stats/ngs_rushing.parquet",
    "ngs_passing.parquet": f"{BASE}/nextgen_stats/ngs_passing.parquet",
    "ngs_timestamp.json": f"{BASE}/nextgen_stats/timestamp.json",
    # ID map already cached by explore_pfr.py; re-download if missing.
    "players.parquet": f"{BASE}/players/players.parquet",
}

SEASONS = (2023, 2024, 2025)  # aligned with the Kaggle tracking window
MIN_TARGETS = 20  # career NGS targets, rookie through year 3
MIN_SPEARMAN_N = 8
N_BOOT = 2000
BOOT_SEED = 2027

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

# College aliases used only for fallback gsis_id fills, never to override
# a conflicting nfl_id match.
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

# Rate / average columns to target-weight when pooling seasons or weeks.
RATE_COLS = [
    "avg_cushion",
    "avg_separation",
    "avg_intended_air_yards",
    "percent_share_of_intended_air_yards",
    "avg_yac",
    "avg_expected_yac",
    "avg_yac_above_expectation",
]

COMBINE_X = [
    ("ten_yd_split", "Official 10-yard split"),
    ("c_t20_derived", "Tracking-derived 20-yard split"),
    ("forty", "Official 40-yard dash"),
    ("vertical", "Vertical jump"),
    ("broad_jump", "Broad jump"),
    ("three_cone", "3-cone"),
    ("short_shuttle", "Short shuttle"),
    ("burst_0_100", "Burst Score (0–100)"),
    ("sunday_brakes", "Sunday Brakes (0–100)"),
    ("sunday_reburst", "Sunday Re-Burst (0–100)"),
]

NGS_Y = [
    ("avg_separation", "NGS average separation"),
    ("avg_cushion", "NGS average cushion"),
    ("avg_yac_above_expectation", "NGS YAC over expected"),
    ("avg_intended_air_yards", "NGS average intended air yards"),
    ("percent_share_of_intended_air_yards", "NGS share of intended air yards"),
    ("catch_percentage", "NGS catch percentage"),
]


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
- `ngs_receiving.parquet`, `ngs_rushing.parquet`, `ngs_passing.parquet` — NFL Next Gen Stats (powered by AWS) receiving, rushing, and passing, 2016 onward, as published in the free public nflverse release. Week 0 regular-season rows are season totals; weekly rows cover weeks that meet NGS's publishing floor (typically ≥5 targets in a week for receiving).
  Source: https://github.com/nflverse/nflverse-data/releases/tag/nextgen_stats
  Access: `nflreadr::load_nextgen_stats()` / `nflreadpy.load_nextgen_stats()` / https://github.com/nflverse/nflverse-data/releases/download/nextgen_stats/
  Original public source: https://nextgenstats.nfl.com/
  These files are supporting / validation evidence only. The competition writeup still has to be built on the provided Kaggle tracking data.

- `ngs_timestamp.json` — nflverse release timestamp for the nextgen_stats tag.

Downloaded 11/2026 for `explore_ngs.py`.
"""
    existing = path.read_text() if path.exists() else ""
    if "ngs_receiving.parquet" in existing:
        return
    path.write_text(existing.rstrip() + "\n" + extra)
    log("  updated external/ATTRIBUTION.md")


def inventory() -> pd.DataFrame:
    rows = []
    for fname, tag in (
        ("ngs_receiving.parquet", "receiving"),
        ("ngs_rushing.parquet", "rushing"),
        ("ngs_passing.parquet", "passing"),
    ):
        d = pd.read_parquet(EXT / fname)
        seasons = sorted(int(s) for s in d["season"].dropna().unique()) if "season" in d.columns else []
        weeks = sorted(int(w) for w in d["week"].dropna().unique()) if "week" in d.columns else []
        st = d["season_type"].value_counts().to_dict() if "season_type" in d.columns else {}
        w0 = int(((d["week"] == 0) & (d["season_type"] == "REG")).sum()) if "week" in d.columns else 0
        for col in d.columns:
            rows.append(
                {
                    "file": fname,
                    "table": tag,
                    "column": col,
                    "dtype": str(d[col].dtype),
                    "n_non_null": int(d[col].notna().sum()),
                    "n_rows": int(len(d)),
                    "seasons": ",".join(str(s) for s in seasons),
                    "season_types": ",".join(f"{k}:{v}" for k, v in st.items()),
                    "weeks": ",".join(str(w) for w in weeks),
                    "n_week0_reg": w0,
                }
            )
    inv = pd.DataFrame(rows)
    inv.to_csv(OUT / "ngs_columns.csv", index=False)
    log(f"  wrote ngs_columns.csv ({len(inv)} columns across 3 NGS tables)")
    return inv


def build_id_map(kaggle: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map Kaggle nfl_id → nflverse gsis_id. Draft slot is not used."""
    nv = pd.read_parquet(EXT / "players.parquet")
    nv["nfl_id_num"] = pd.to_numeric(nv["nfl_id"], errors="coerce")
    nv["name_n"] = nv["display_name"].map(norm_name)
    nv["college_n"] = nv["college_name"].map(norm_college)
    nv["birth_date"] = pd.to_datetime(nv["birth_date"], errors="coerce")

    k = kaggle.copy()
    # Never carry draft round / pick into the ID map.
    drop_picks = [c for c in k.columns if re.search(r"draft_(round|pick|overall)|(^pick$)", c)]
    k = k.drop(columns=drop_picks, errors="ignore")
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
                "gsis_id",
                "pfr_id",
                "draft_year",
                "college_name",
                "birth_date",
                "position",
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

    still = m[m.match_method.isna()].copy()
    extra = 0
    for i, r in still.iterrows():
        if not r.college_n or pd.isna(r.draft_year):
            continue
        cands = nv[
            (nv.name_n == r.name_n)
            & (nv.draft_year == r.draft_year)
            & (nv.college_n == r.college_n)
        ]
        if pd.notna(r.birth_date) and cands["birth_date"].notna().any():
            cands = cands[cands.birth_date.isna() | (cands.birth_date == r.birth_date)]
        if len(cands) == 1:
            m.at[i, "gsis_id"] = cands.gsis_id.iloc[0]
            m.at[i, "pfr_id"] = cands.pfr_id.iloc[0] if "pfr_id" in cands.columns else pd.NA
            m.at[i, "nv_display_name"] = cands.display_name.iloc[0]
            m.at[i, "nv_draft_year"] = cands.draft_year.iloc[0]
            m.at[i, "nv_college"] = cands.college_name.iloc[0]
            m.at[i, "nv_position"] = cands.position.iloc[0]
            m.at[i, "match_method"] = "name_year_college"
            extra += 1
    log(f"  name+year+college fallback matches: {extra}")

    m["match_method"] = m["match_method"].fillna("unmatched")
    m["has_gsis_id"] = m["gsis_id"].notna()

    rows = []
    for col, grp in (("nfl_position", m.nfl_position), ("pos_group", m.pos_group)):
        for g, sub in m.groupby(grp):
            rows.append(
                {
                    "group_type": col,
                    "group": g,
                    "n_kaggle": int(len(sub)),
                    "n_matched_nfl_id": int(sub.match_method.str.contains("nfl_id", na=False).sum()),
                    "n_has_gsis_id": int(sub.has_gsis_id.sum()),
                    "n_unmatched": int((sub.match_method == "unmatched").sum()),
                    "match_rate_id": float(sub.match_method.str.contains("nfl_id", na=False).mean()),
                    "gsis_id_rate": float(sub.has_gsis_id.mean()),
                }
            )
    rows.append(
        {
            "group_type": "all",
            "group": "ALL_510",
            "n_kaggle": int(len(m)),
            "n_matched_nfl_id": int(m.match_method.str.contains("nfl_id", na=False).sum()),
            "n_has_gsis_id": int(m.has_gsis_id.sum()),
            "n_unmatched": int((m.match_method == "unmatched").sum()),
            "match_rate_id": float(m.match_method.str.contains("nfl_id", na=False).mean()),
            "gsis_id_rate": float(m.has_gsis_id.mean()),
        }
    )
    rates = pd.DataFrame(rows).sort_values(["group_type", "group"])
    rates.to_csv(OUT / "ngs_match_rates.csv", index=False)

    keep = [
        "nfl_id",
        "display_name",
        "draft_year",
        "nfl_position",
        "pos_group",
        "college_name",
        "birth_date",
        "gsis_id",
        "nv_display_name",
        "nv_draft_year",
        "nv_college",
        "nv_position",
        "match_method",
        "has_gsis_id",
    ]
    idmap = m[keep].copy()
    idmap.to_csv(OUT / "ngs_id_map.csv", index=False)
    unmatched = idmap[idmap.match_method.eq("unmatched")].copy()
    unmatched.to_csv(OUT / "ngs_unmatched.csv", index=False)
    log(
        f"  ID map: {int(m.match_method.str.contains('nfl_id', na=False).sum())}/510 by nfl_id, "
        f"{int(m.has_gsis_id.sum())} with gsis_id, {int((m.match_method=='unmatched').sum())} unmatched"
    )
    return idmap, rates


def _weighted_avg(df: pd.DataFrame, col: str, weights: pd.Series) -> float:
    mask = df[col].notna() & weights.notna() & (weights > 0)
    if mask.sum() == 0 or weights[mask].sum() == 0:
        return np.nan
    return float(np.average(df.loc[mask, col], weights=weights[mask]))


def aggregate_weekly(weekly: pd.DataFrame) -> pd.DataFrame:
    """Target-weighted weekly rollup for player-seasons with no week-0 row."""
    if weekly.empty:
        return pd.DataFrame()

    def _one(g: pd.DataFrame) -> pd.Series:
        targets = pd.to_numeric(g["targets"], errors="coerce")
        recs = pd.to_numeric(g["receptions"], errors="coerce")
        yards = pd.to_numeric(g["yards"], errors="coerce")
        tds = pd.to_numeric(g["rec_touchdowns"], errors="coerce")
        t = float(targets.sum(min_count=1)) if targets.notna().any() else np.nan
        r = float(recs.sum(min_count=1)) if recs.notna().any() else np.nan
        out = {
            "n_weeks": int(len(g)),
            "teams": ",".join(sorted({str(x) for x in g["team_abbr"].dropna().unique()})),
            "player_position": g["player_position"].dropna().iloc[-1] if g["player_position"].notna().any() else pd.NA,
            "player_display_name": g["player_display_name"].dropna().iloc[-1] if g["player_display_name"].notna().any() else pd.NA,
            "targets": t,
            "receptions": r,
            "yards": float(yards.sum(min_count=1)) if yards.notna().any() else np.nan,
            "rec_touchdowns": float(tds.sum(min_count=1)) if tds.notna().any() else np.nan,
            "catch_percentage": (100.0 * r / t) if np.isfinite(t) and t > 0 and np.isfinite(r) else np.nan,
            "source": "weekly_agg",
        }
        for c in RATE_COLS:
            out[c] = _weighted_avg(g, c, targets) if c in g.columns else np.nan
        return pd.Series(out)

    out = (
        weekly.groupby(["player_gsis_id", "season"], dropna=True)
        .apply(_one, include_groups=False)
        .reset_index()
    )
    return out


def season_receiving() -> pd.DataFrame:
    """2023–2025 REG receiving: week 0 when present, else weekly aggregate."""
    rec = pd.read_parquet(EXT / "ngs_receiving.parquet")
    sub = rec[(rec.season.isin(SEASONS)) & (rec.season_type == "REG")].copy()
    for c in ["targets", "receptions", "yards", "rec_touchdowns", "catch_percentage", *RATE_COLS]:
        if c in sub.columns:
            sub[c] = pd.to_numeric(sub[c], errors="coerce")

    w0 = sub[sub.week == 0].copy()
    w0["source"] = "week0"
    w0["n_weeks"] = np.nan
    w0["teams"] = w0["team_abbr"]

    weekly = sub[sub.week > 0]
    # Player-seasons already represented by a week-0 row.
    have = set(zip(w0["player_gsis_id"], w0["season"]))
    key = list(zip(weekly["player_gsis_id"], weekly["season"]))
    weekly_only = weekly.loc[[k not in have for k in key]].copy()
    agg = aggregate_weekly(weekly_only)

    keep = [
        "player_gsis_id",
        "season",
        "player_display_name",
        "player_position",
        "teams",
        "source",
        "n_weeks",
        "targets",
        "receptions",
        "yards",
        "rec_touchdowns",
        "catch_percentage",
        *RATE_COLS,
    ]
    parts = [w0[[c for c in keep if c in w0.columns]]]
    if not agg.empty:
        parts.append(agg[[c for c in keep if c in agg.columns]])
    out = pd.concat(parts, ignore_index=True)
    log(
        f"  NGS REG 2023-2025 player-seasons: {len(out)} "
        f"({int((out.source=='week0').sum())} week-0, "
        f"{int((out.source=='weekly_agg').sum())} weekly-agg)"
    )
    return out


def pool_career(seasons: pd.DataFrame) -> pd.DataFrame:
    """Target-weighted career rollup across the rookie-to-year-3 window."""

    def _one(g: pd.DataFrame) -> pd.Series:
        targets = pd.to_numeric(g["targets"], errors="coerce")
        recs = pd.to_numeric(g["receptions"], errors="coerce")
        yards = pd.to_numeric(g["yards"], errors="coerce")
        tds = pd.to_numeric(g["rec_touchdowns"], errors="coerce")
        t = float(targets.sum(min_count=1)) if targets.notna().any() else np.nan
        r = float(recs.sum(min_count=1)) if recs.notna().any() else np.nan
        sources = ",".join(sorted({str(x) for x in g["source"].dropna().unique()}))
        out = {
            "n_seasons": int(g["season"].nunique()),
            "seasons": ",".join(str(int(s)) for s in sorted(g["season"].unique())),
            "teams": ",".join(sorted({t_ for s in g["teams"].dropna() for t_ in str(s).split(",") if t_})),
            "ngs_pos": g["player_position"].dropna().iloc[-1] if g["player_position"].notna().any() else pd.NA,
            "ngs_name": g["player_display_name"].dropna().iloc[-1] if g["player_display_name"].notna().any() else pd.NA,
            "source": sources,
            "n_week0_seasons": int((g["source"] == "week0").sum()),
            "n_weekly_seasons": int((g["source"] == "weekly_agg").sum()),
            "targets": t,
            "receptions": r,
            "yards": float(yards.sum(min_count=1)) if yards.notna().any() else np.nan,
            "rec_touchdowns": float(tds.sum(min_count=1)) if tds.notna().any() else np.nan,
            "catch_percentage": (100.0 * r / t) if np.isfinite(t) and t > 0 and np.isfinite(r) else np.nan,
        }
        for c in RATE_COLS:
            out[c] = _weighted_avg(g, c, targets) if c in g.columns else np.nan
        return pd.Series(out)

    out = (
        seasons.groupby("nfl_id", dropna=True)
        .apply(_one, include_groups=False)
        .reset_index()
    )
    return out


def tracking_separation() -> pd.DataFrame:
    """Player-level official charting from provided player_play (REG 2023–2025)."""
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season", "season_type"])
    pp = pd.read_csv(
        DATA / "player_play.csv",
        usecols=[
            "game_id",
            "nfl_id",
            "target",
            "route_ran",
            "separation_at_pass_forward",
            "cushion",
        ],
    )
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp[pp.season.isin(SEASONS) & (pp.season_type == "REG")].copy()
    g = pp.groupby("nfl_id", dropna=True)
    out = g.agg(
        n_routes=("route_ran", lambda s: int(s.notna().sum())),
        n_targets=("target", lambda s: int(s.fillna(False).astype(bool).sum())),
        sep_all_n=("separation_at_pass_forward", lambda s: int(s.notna().sum())),
        sep_all_mean=("separation_at_pass_forward", "mean"),
        cushion_n=("cushion", lambda s: int(s.notna().sum())),
        cushion_mean=("cushion", "mean"),
    ).reset_index()
    tgt = pp[pp["target"].fillna(False).astype(bool)]
    tgt_agg = tgt.groupby("nfl_id", dropna=True).agg(
        sep_tgt_n=("separation_at_pass_forward", lambda s: int(s.notna().sum())),
        sep_tgt_mean=("separation_at_pass_forward", "mean"),
    ).reset_index()
    out = out.merge(tgt_agg, on="nfl_id", how="left")
    return out


def attach_traits(career: pd.DataFrame, idmap: pd.DataFrame) -> pd.DataFrame:
    d = career.merge(
        idmap[
            [
                "nfl_id",
                "display_name",
                "draft_year",
                "nfl_position",
                "pos_group",
                "college_name",
                "gsis_id",
                "match_method",
            ]
        ],
        on="nfl_id",
        how="left",
        suffixes=("", "_id"),
    )
    comb = pd.read_csv(
        DATA / "combine_results.csv",
        usecols=[
            "nfl_id",
            "ten_yd_split",
            "forty",
            "vertical",
            "broad_jump",
            "three_cone",
            "short_shuttle",
        ],
    )
    d = d.merge(comb, on="nfl_id", how="left")

    t20_path = OUT / "combine_to_game_players.csv"
    if t20_path.exists():
        t20 = pd.read_csv(t20_path, usecols=lambda c: c in {"nfl_id", "c_t20_derived"})
        d = d.merge(t20.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    else:
        d["c_t20_derived"] = np.nan

    burst_path = OUT / "combine_to_game_burst_players.csv"
    if burst_path.exists():
        burst = pd.read_csv(burst_path, usecols=lambda c: c in {"nfl_id", "burst_0_100"})
        d = d.merge(burst.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    else:
        d["burst_0_100"] = np.nan

    accel_path = OUT / "eda_accel_players.csv"
    if accel_path.exists():
        accel = pd.read_csv(
            accel_path,
            usecols=lambda c: c
            in {"nfl_id", "sunday_brakes", "sunday_reburst", "usable_sunday"},
        )
        d = d.merge(accel.drop_duplicates("nfl_id"), on="nfl_id", how="left")
    else:
        d["sunday_brakes"] = np.nan
        d["sunday_reburst"] = np.nan

    tr = tracking_separation()
    d = d.merge(tr, on="nfl_id", how="left")

    # Safety: never leak draft slot / pick into the career table.
    drop_picks = [c for c in d.columns if re.search(r"draft_(round|pick|overall)|(^pick$)", c)]
    if drop_picks:
        d = d.drop(columns=drop_picks)
    return d


def coverage_table(idmap: pd.DataFrame, career: pd.DataFrame) -> pd.DataFrame:
    wrte = idmap[idmap.nfl_position.isin(["WR", "TE"])].copy()
    rows = []
    for pos, sub in list(wrte.groupby("nfl_position")) + [("WR+TE", wrte)]:
        has_gsis = sub.has_gsis_id
        joined = sub.merge(career[["nfl_id", "targets", "source", "n_seasons"]], on="nfl_id", how="left")
        any_ngs = joined.targets.notna()
        floor = joined.targets.fillna(0) >= MIN_TARGETS
        rows.append(
            {
                "group": pos,
                "n_kaggle": int(len(sub)),
                "n_has_gsis": int(has_gsis.sum()),
                "gsis_rate": float(has_gsis.mean()),
                "n_any_ngs": int(any_ngs.sum()),
                "any_ngs_rate": float(any_ngs.mean()),
                "n_targets_ge20": int(floor.sum()),
                "floor_rate": float(floor.mean()),
                "median_targets_any": float(joined.loc[any_ngs, "targets"].median()) if any_ngs.any() else np.nan,
                "median_targets_floor": float(joined.loc[floor, "targets"].median()) if floor.any() else np.nan,
                "n_week0_only": int(((joined.source == "week0") & floor).sum()) if "source" in joined else 0,
                "n_weekly_or_mixed": int((joined.source.fillna("").str.contains("weekly") & floor).sum()),
            }
        )
    cov = pd.DataFrame(rows)
    cov.to_csv(OUT / "ngs_coverage.csv", index=False)
    return cov


def year_controls(year: pd.Series) -> np.ndarray:
    dummies = pd.get_dummies(year, prefix="y", drop_first=True)
    return dummies.to_numpy(dtype=float)


def residualize(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if X is None or X.size == 0 or X.shape[1] == 0:
        return y - np.nanmean(y)
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def spearman_pair(x: pd.Series, y: pd.Series, year: pd.Series | None = None) -> dict:
    frame = pd.DataFrame({"x": x, "y": y})
    if year is not None:
        frame["draft_year"] = year
    d = frame.dropna().copy()
    out = {
        "n": int(len(d)),
        "rho": np.nan,
        "p": np.nan,
        "rho_year": np.nan,
        "p_year": np.nan,
    }
    if len(d) < MIN_SPEARMAN_N or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    if "draft_year" in d.columns and d["draft_year"].nunique() >= 2:
        X = year_controls(d["draft_year"])
        rx = residualize(d["x"].to_numpy(dtype=float), X)
        ry = residualize(d["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
            pr, pp = spearmanr(rx, ry)
            out["rho_year"], out["p_year"] = float(pr), float(pp)
    else:
        out["rho_year"], out["p_year"] = out["rho"], out["p"]
    return out


def bootstrap_ci(
    x: pd.Series,
    y: pd.Series,
    year: pd.Series | None = None,
    *,
    year_adj: bool = False,
    n_boot: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> tuple[float, float, int]:
    frame = pd.DataFrame({"x": x, "y": y})
    if year is not None:
        frame["draft_year"] = year
    base = frame.dropna().reset_index(drop=True)
    if len(base) < MIN_SPEARMAN_N:
        return np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    rhos: list[float] = []
    n = len(base)
    x_arr = base["x"].to_numpy(dtype=float)
    y_arr = base["y"].to_numpy(dtype=float)
    yr = base["draft_year"].to_numpy() if "draft_year" in base.columns else None
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        xb, yb = x_arr[idx], y_arr[idx]
        if np.unique(xb).size < 2 or np.unique(yb).size < 2:
            continue
        if year_adj and yr is not None and np.unique(yr[idx]).size >= 2:
            dtmp = pd.DataFrame({"draft_year": yr[idx]})
            X = year_controls(dtmp["draft_year"])
            rx = residualize(xb, X)
            ry = residualize(yb, X)
            if np.unique(rx).size < 2 or np.unique(ry).size < 2:
                continue
            rho, _ = spearmanr(rx, ry)
        else:
            rho, _ = spearmanr(xb, yb)
        if np.isfinite(rho):
            rhos.append(float(rho))
    if len(rhos) < max(50, n_boot // 20):
        return np.nan, np.nan, len(rhos)
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return float(lo), float(hi), len(rhos)


def run_validation(career: pd.DataFrame) -> pd.DataFrame:
    """Pre-declared check: our tracking separation / cushion vs NGS."""
    rows = []
    pairs = [
        ("sep_tgt_mean", "avg_separation", "Tracking sep at throw (targets) vs NGS avg separation"),
        ("sep_all_mean", "avg_separation", "Tracking sep at throw (all charted) vs NGS avg separation"),
        ("cushion_mean", "avg_cushion", "Tracking pre-snap cushion vs NGS avg cushion"),
    ]
    sample = career[career.targets >= MIN_TARGETS].copy()
    groups = [("WR", sample[sample.nfl_position == "WR"]), ("TE", sample[sample.nfl_position == "TE"]),
              ("WR+TE", sample[sample.nfl_position.isin(["WR", "TE"])])]
    for gname, sub in groups:
        for xname, yname, label in pairs:
            sp = spearman_pair(sub[xname], sub[yname], sub["draft_year"])
            lo, hi, n_ok = bootstrap_ci(sub[xname], sub[yname], sub["draft_year"], year_adj=False)
            lo_y, hi_y, n_ok_y = bootstrap_ci(sub[xname], sub[yname], sub["draft_year"], year_adj=True, seed=BOOT_SEED + 1)
            rows.append(
                {
                    "group": gname,
                    "x": xname,
                    "y": yname,
                    "label": label,
                    "n": sp["n"],
                    "rho": sp["rho"],
                    "rho_lo": lo,
                    "rho_hi": hi,
                    "p": sp["p"],
                    "rho_year": sp["rho_year"],
                    "rho_year_lo": lo_y,
                    "rho_year_hi": hi_y,
                    "p_year": sp["p_year"],
                    "n_boot_ok": n_ok,
                    "n_boot_ok_year": n_ok_y,
                    "min_targets": MIN_TARGETS,
                    "note": "pre-declared validation; not in the Combine-vs-NGS FDR family",
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "ngs_validation.csv", index=False)
    log(f"  wrote ngs_validation.csv ({len(out)} tests)")
    return out


def run_spearman(career: pd.DataFrame) -> pd.DataFrame:
    sample = career[career.targets >= MIN_TARGETS].copy()
    rows = []
    for pos in ("WR", "TE"):
        sub = sample[sample.nfl_position == pos]
        for x, xlab in COMBINE_X:
            if x not in sub.columns:
                continue
            for y, ylab in NGS_Y:
                sp = spearman_pair(sub[x], sub[y], sub["draft_year"])
                lo, hi, n_ok = bootstrap_ci(sub[x], sub[y], sub["draft_year"], year_adj=False)
                lo_y, hi_y, n_ok_y = bootstrap_ci(
                    sub[x], sub[y], sub["draft_year"], year_adj=True, seed=BOOT_SEED + 1
                )
                rows.append(
                    {
                        "group": f"{pos} (NGS tgt>={MIN_TARGETS})",
                        "pos": pos,
                        "x": x,
                        "x_label": xlab,
                        "y": y,
                        "y_label": ylab,
                        "n": sp["n"],
                        "rho": sp["rho"],
                        "rho_lo": lo,
                        "rho_hi": hi,
                        "p": sp["p"],
                        "rho_year": sp["rho_year"],
                        "rho_year_lo": lo_y,
                        "rho_year_hi": hi_y,
                        "p_year": sp["p_year"],
                        "n_boot_ok": n_ok,
                        "n_boot_ok_year": n_ok_y,
                        "small_n": bool(sp["n"] < 12),
                        "min_targets": MIN_TARGETS,
                        "note": (
                            "exploratory supporting evidence; unadjusted Spearman is primary; "
                            "year-residualized reported as sensitivity; "
                            "BH-FDR within position across Combine/Sunday × NGS pairs"
                        ),
                    }
                )
    out = pd.DataFrame(rows)
    out["fdr_p"] = np.nan
    out["sig_fdr_05"] = False
    out["holm_p"] = np.nan
    out["sig_holm_05"] = False
    for pos, idx in out.groupby("pos").groups.items():
        fam = out.loc[idx]
        finite = fam["p"].notna().to_numpy()
        pvals = fam["p"].to_numpy()
        if finite.sum() == 0:
            continue
        holm = multipletests(pvals[finite], alpha=0.05, method="holm")
        fdr = multipletests(pvals[finite], alpha=0.05, method="fdr_bh")
        out.loc[fam.index[finite], "holm_p"] = holm[1]
        out.loc[fam.index[finite], "sig_holm_05"] = holm[0]
        out.loc[fam.index[finite], "fdr_p"] = fdr[1]
        out.loc[fam.index[finite], "sig_fdr_05"] = fdr[0]
    out.to_csv(OUT / "ngs_spearman.csv", index=False)
    log(f"  wrote ngs_spearman.csv ({len(out)} tests)")
    return out


def style_fig() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.labelcolor": "#222222",
            "text.color": "#222222",
            "xtick.color": "#222222",
            "ytick.color": "#222222",
            "axes.grid": True,
            "grid.color": "#DDDDDD",
            "grid.linewidth": 0.6,
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "figure.titlesize": 15,
            "font.family": "DejaVu Sans",
        }
    )


def _fmt_rho(row, key="rho", lo="rho_lo", hi="rho_hi", p="p") -> str:
    if not np.isfinite(row[key]):
        return "n too small"
    ci = ""
    if np.isfinite(row[lo]) and np.isfinite(row[hi]):
        ci = f"  [{row[lo]:+.2f}, {row[hi]:+.2f}]"
    ptxt = f"  p={row[p]:.3f}" if np.isfinite(row[p]) else ""
    return f"ρ={row[key]:+.2f}{ci}{ptxt}  n={int(row['n'])}"


def fig17(career: pd.DataFrame, validation: pd.DataFrame, spearman: pd.DataFrame) -> Path:
    style_fig()
    sample = career[(career.targets >= MIN_TARGETS) & career.nfl_position.isin(["WR", "TE"])].copy()
    colors = {"WR": "#1F4E79", "TE": "#C47B17"}

    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.6))
    fig.suptitle(
        "Next Gen Stats as a check on our tracking and Combine story",
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.935,
        "Rookie WR / TE, 2023–2025 regular season  ·  NGS is supporting evidence, not a replacement for Kaggle tracking",
        ha="center",
        fontsize=10,
        color="#444444",
    )

    def scatter(ax, xcol, ycol, xlabel, ylabel, title, val_x, val_y):
        for pos, sub in sample.groupby("nfl_position"):
            ax.scatter(
                sub[xcol],
                sub[ycol],
                s=36,
                alpha=0.85,
                color=colors[pos],
                edgecolor="white",
                linewidth=0.5,
                label=f"{pos} (n={sub[xcol].notna().mul(sub[ycol].notna()).sum()})",
            )
        # Pooled validation row
        row = validation[(validation.group == "WR+TE") & (validation.x == val_x) & (validation.y == val_y)]
        wr = validation[(validation.group == "WR") & (validation.x == val_x) & (validation.y == val_y)]
        te = validation[(validation.group == "TE") & (validation.x == val_x) & (validation.y == val_y)]
        bits = []
        if len(wr):
            bits.append("WR " + _fmt_rho(wr.iloc[0]))
        if len(te):
            bits.append("TE " + _fmt_rho(te.iloc[0]))
        if len(row):
            bits.append("pooled " + _fmt_rho(row.iloc[0]))
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        if bits:
            ax.text(
                0.98,
                0.02,
                "\n".join(bits),
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=7.5,
                color="#333333",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#CCCCCC", alpha=0.9),
            )
        # y=x guide when units match (yards)
        xs = sample[xcol].dropna()
        ys = sample[ycol].dropna()
        if len(xs) and len(ys):
            lo = min(xs.min(), ys.min())
            hi = max(xs.max(), ys.max())
            ax.plot([lo, hi], [lo, hi], color="#888888", lw=0.8, ls="--", zorder=0)

    scatter(
        axes[0, 0],
        "sep_tgt_mean",
        "avg_separation",
        "Our tracking: mean separation at throw, targets (yds)",
        "NGS average separation (yds)",
        "A. Does our tracking separation match NGS?",
        "sep_tgt_mean",
        "avg_separation",
    )
    scatter(
        axes[0, 1],
        "cushion_mean",
        "avg_cushion",
        "Our tracking: mean pre-snap cushion (yds)",
        "NGS average cushion (yds)",
        "B. Does our tracking cushion match NGS?",
        "cushion_mean",
        "avg_cushion",
    )

    def forest(ax, yname, title, pos="WR"):
        fam = spearman[(spearman.pos == pos) & (spearman.y == yname) & spearman.rho.notna()].copy()
        # Lead with 20-yard, then official tests, then our composites.
        order = [x for x, _ in COMBINE_X]
        fam["_ord"] = fam.x.map({k: i for i, k in enumerate(order)})
        fam = fam.sort_values("_ord", ascending=False)
        if fam.empty:
            ax.set_axis_off()
            ax.set_title(title)
            ax.text(0.5, 0.5, "No tests with enough n", ha="center")
            return
        yloc = np.arange(len(fam))
        ax.axvline(0, color="#888888", lw=0.8)
        for i, r in enumerate(fam.itertuples()):
            lo = r.rho_lo if np.isfinite(r.rho_lo) else r.rho
            hi = r.rho_hi if np.isfinite(r.rho_hi) else r.rho
            color = "#1F4E79"
            if bool(r.sig_fdr_05):
                color = "#8B1E1E"
            ax.plot([lo, hi], [i, i], color=color, lw=1.6)
            ax.scatter([r.rho], [i], color=color, s=22, zorder=3)
        ax.set_yticks(yloc)
        labels = []
        for r in fam.itertuples():
            star = " ★" if bool(r.sig_fdr_05) else ""
            labels.append(f"{r.x_label}  n={int(r.n)}{star}")
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Spearman ρ  (95% bootstrap CI)")
        ax.set_title(title, fontweight="bold")
        ax.set_xlim(-1.05, 1.05)

    forest(
        axes[1, 0],
        "avg_cushion",
        "C. WR traits vs NGS cushion",
        "WR",
    )
    forest(
        axes[1, 1],
        "avg_intended_air_yards",
        "D. WR traits vs NGS intended air yards",
        "WR",
    )

    footnote = (
        f"Career pool = each rookie's regular-season NGS rows from draft year through year 3, inside 2023–2025. "
        f"Week-0 season totals used when published; otherwise target-weighted weekly rows (NGS weekly floor is typically ≥5 targets). "
        f"Analysis floor: ≥{MIN_TARGETS} observed NGS targets. "
        "Primary Spearman is unadjusted; year-residualized is a sensitivity in the tables. "
        "BH-FDR is within-position across all Combine/Sunday × NGS pairs. ★ = FDR < 0.05. "
        "No Combine/Sunday vs NGS pair survives BH-FDR. Unadjusted hints in C and D (20-yard/40 vs cushion; Sunday Re-Burst vs air yards) are exploratory. TE forests omitted because the qualified TE sample is small (n=11; see tables). "
        "NGS separation is a published Next Gen average; our metric is official charting of separation at throw, so the two are close cousins, not identical."
    )
    fig.text(0.04, 0.015, footnote, ha="left", va="bottom", fontsize=7.2, color="#444444", wrap=True)
    fig.tight_layout(rect=(0.0, 0.10, 1.0, 0.92))
    path = FIGS / "fig17_ngs_receiving.png"
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def main() -> int:
    t0 = time.time()
    download_if_missing()
    update_attribution()
    kaggle = pd.read_csv(DATA / "players.csv")
    # Drop draft slot immediately so it cannot leak into joins.
    drop_picks = [c for c in kaggle.columns if re.search(r"draft_(round|pick|overall)|(^pick$)", c)]
    kaggle = kaggle.drop(columns=drop_picks, errors="ignore")

    log("Inventorying NGS / nflverse columns …")
    inventory()

    log("Joining nflverse gsis_id to the 510 Kaggle rookies …")
    idmap, rates = build_id_map(kaggle)
    show_rates = rates[rates.group_type.isin(["pos_group", "all"]) | rates.group.isin(["WR", "TE"])]
    print(show_rates.to_string(index=False))

    log("Building 2023-2025 NGS receiving seasons and career pools …")
    seasons = season_receiving()
    wrte = idmap[idmap.nfl_position.isin(["WR", "TE"]) & idmap.has_gsis_id].copy()
    linked = wrte.merge(seasons, left_on="gsis_id", right_on="player_gsis_id", how="inner")
    linked = linked[linked.season.between(linked.draft_year, linked.draft_year + 2)].copy()
    # Player-season table (no draft slot).
    season_keep = [
        "nfl_id",
        "display_name",
        "draft_year",
        "nfl_position",
        "pos_group",
        "gsis_id",
        "season",
        "teams",
        "source",
        "n_weeks",
        "targets",
        "receptions",
        "yards",
        "rec_touchdowns",
        "catch_percentage",
        *RATE_COLS,
    ]
    player_seasons = linked[[c for c in season_keep if c in linked.columns]].copy()
    player_seasons.to_csv(OUT / "ngs_player_seasons.csv", index=False)

    career_stats = pool_career(linked)
    career = attach_traits(career_stats, idmap)
    # Keep WR/TE only (RB is excluded from headline work; NGS receiving is WR/TE).
    career = career[career.nfl_position.isin(["WR", "TE"])].copy()
    career.to_csv(OUT / "ngs_career.csv", index=False)
    log(f"  wrote ngs_career.csv ({len(career)} WR/TE with any window NGS row)")

    cov = coverage_table(idmap, career)
    print(cov.to_string(index=False))

    log("Validation: tracking separation / cushion vs NGS …")
    validation = run_validation(career)
    with pd.option_context("display.width", 180, "display.float_format", lambda v: f"{v:0.3f}"):
        print(validation.to_string(index=False))

    log("Within-position Spearman, Combine / Sunday vs NGS …")
    sp = run_spearman(career)
    show = sp[sp.rho.notna()].copy()
    show["abs_rho"] = show.rho.abs()
    focus = show.sort_values(["pos", "y", "p"])
    # Print the stronger unadjusted tests and all FDR hits.
    hits = show[(show.sig_fdr_05) | ((show.p < 0.05) & (show.n >= 12))]
    print("\nTests with p<0.05 at n≥12, or FDR-significant:")
    cols = [
        "group",
        "x_label",
        "y_label",
        "n",
        "rho",
        "rho_lo",
        "rho_hi",
        "p",
        "fdr_p",
        "sig_fdr_05",
        "rho_year",
        "p_year",
        "small_n",
    ]
    with pd.option_context("display.width", 200, "display.float_format", lambda v: f"{v:0.3f}"):
        if len(hits):
            print(hits[cols].sort_values(["group", "p"]).to_string(index=False))
        else:
            print("  none")
        print("\nLead tests (20-yard, Burst, Sunday Brakes/Re-Burst) vs separation and YACOE:")
        lead = show[
            show.x.isin(["c_t20_derived", "burst_0_100", "sunday_brakes", "sunday_reburst", "ten_yd_split", "forty"])
            & show.y.isin(["avg_separation", "avg_yac_above_expectation"])
        ]
        print(lead[cols].sort_values(["pos", "y", "p"]).to_string(index=False))

    log("Drawing fig17 …")
    fig17(career, validation, sp)
    log(f"Done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
