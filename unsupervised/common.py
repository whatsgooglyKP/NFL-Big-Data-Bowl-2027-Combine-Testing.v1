"""Shared paths, group definitions and helpers for the unsupervised track (11/2026).

Hard rules enforced here: no draft slot / pick / round column is ever read (assert_no_draft);
RB is excluded; groups are WR, TE, DB (CB+S), DL (Edge/Interior breakout).
"""
from __future__ import annotations
import os
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = Path(os.environ.get("BDB_DATA", "/workspace/bdb2027/data"))   # raw Kaggle CSVs (read only, never committed)
CACHE, OUT, FIGS = HERE / "cache", HERE / "out", HERE / "figs"
for p in (CACHE, OUT, FIGS):
    p.mkdir(exist_ok=True)
SEED = 2027
GROUPS = ["WR", "TE", "DB", "DL"]
POS2GROUP = {"WR": "WR", "TE": "TE", "CB": "DB", "SS": "DB", "FS": "DB", "DB": "DB",
             "DE": "DL", "OLB": "DL", "DT": "DL", "NT": "DL"}
POS2ROLE = {"CB": "CB", "DB": "CB", "SS": "S", "FS": "S", "DE": "Edge", "OLB": "Edge", "DT": "Interior", "NT": "Interior"}


def assert_no_draft(df: pd.DataFrame) -> None:
    bad = [c for c in df.columns if any(k in c.lower() for k in ("draft_round", "pick", "overall", "draft_slot", "round"))]
    assert not bad, f"draft slot columns present: {bad}"


def players() -> pd.DataFrame:
    pl = pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "draft_year", "nfl_position"])
    pl["group"] = pl.nfl_position.map(POS2GROUP)
    pl["role"] = pl.nfl_position.map(POS2ROLE).fillna(pl.nfl_position)
    pl = pl[pl.group.notna()].copy()
    assert_no_draft(pl)
    return pl


def bh(p) -> np.ndarray:
    p = np.asarray(p, float); q = np.full_like(p, np.nan); m = np.isfinite(p)
    if m.sum():
        from statsmodels.stats.multitest import multipletests
        q[m] = multipletests(p[m], method="fdr_bh")[1]
    return q
