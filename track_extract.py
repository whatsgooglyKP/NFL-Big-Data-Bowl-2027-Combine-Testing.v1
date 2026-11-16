"""One pass over Kaggle game tracking for DB and DL rookies.

Writes two gitignored caches (derived Kaggle tracking, never committed):
  out/cache/dl_snap_frames.parquet   - DL frames from snap to snap+2.05 s (every play)
  out/cache/tackle_window_frames.parquet - DB+DL frames from tackle-1.05 s to the tackle event
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent
DATA, CACHE = ROOT / "data", ROOT / "out" / "cache"
DB_POS = {"CB", "SS", "FS", "DB"}
DL_POS = {"DE", "DT", "NT", "OLB"}
SNAP_EVENTS = {"ball_snap", "snap_direct"}


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    pl = pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "nfl_position"])
    db_ids = set(pl.loc[pl.nfl_position.isin(DB_POS), "nfl_id"])
    dl_ids = set(pl.loc[pl.nfl_position.isin(DL_POS), "nfl_id"])
    ids = db_ids | dl_ids
    snaps, tack = [], []
    for yr in (2023, 2024, 2025):
        parts = []
        for ch in pd.read_csv(DATA / f"game_tracking_{yr}.csv",
                              usecols=["game_id", "play_id", "nfl_id", "time", "x", "y", "s", "event"],
                              dtype={"x": "float32", "y": "float32", "s": "float32"}, chunksize=2_000_000):
            parts.append(ch[ch.nfl_id.isin(ids)])
        f = pd.concat(parts, ignore_index=True)
        f["time"] = pd.to_datetime(f["time"], format="ISO8601")
        key = ["game_id", "play_id", "nfl_id"]
        ev = f[f.event.notna()]
        st = ev[ev.event.isin(SNAP_EVENTS)].groupby(key)["time"].min().rename("snap_time")
        tt = ev[ev.event == "tackle"].groupby(key)["time"].min().rename("tackle_time")
        f = f.join(st, on=key).join(tt, on=key)
        f["t_snap"] = (f.time - f.snap_time).dt.total_seconds().astype("float32")
        f["t_tackle"] = (f.time - f.tackle_time).dt.total_seconds().astype("float32")
        cols = key + ["x", "y", "s", "event"]
        m = f.nfl_id.isin(dl_ids) & f.t_snap.between(-0.05, 2.05)
        snaps.append(f.loc[m, cols + ["t_snap"]])
        m2 = f.t_tackle.between(-1.05, 0.001)
        tack.append(f.loc[m2, cols + ["t_tackle", "t_snap"]])
        print(yr, len(f), int(m.sum()), int(m2.sum()), flush=True)
        del f, parts
    pd.concat(snaps, ignore_index=True).to_parquet(CACHE / "dl_snap_frames.parquet")
    pd.concat(tack, ignore_index=True).to_parquet(CACHE / "tackle_window_frames.parquet")


if __name__ == "__main__":
    main()
