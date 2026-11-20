#!/usr/bin/env python3
"""Step 1b: in-game movement-style features and the pre-declared outcomes, per player (cache only).

Game style (movement + deployment, from game tracking and player_play; never used to build Combine archetypes):
  WR/TE : cut profile on all routes (peak braking, re-accel, speed lost, time through the cut), deep-route game speed,
          defender cushion, slot share, deep-route share (GO/POST/CORNER/WHEEL), short-route share (HITCH/SLANT/FLAT/SCREEN)
  DB    : cut profile in coverage, closing speed at arrival, peak closing speed in last 0.5 s, coverage game speed,
          cushion, man-coverage share, slot-CB share, high-safety share
  DL    : speed 1 s after snap, NGS get-off time, penetration at 2 s (pass, run), edge alignment share
Outcomes (the repo's existing scorecard definitions, METRICS §6-§9; shrunk rates where the repo shrinks):
  WR: sunday_speed_mph, sep_all_mean, break_y ; TE: sep_all_mean ; DB: tackle_rate, tfl_rate, close_rate_mph,
  pfr_yds_tgt, pfr_mtkl_pct, sunday_speed_mph ; DL: pressure_rate, sack_rate, tfl_rate, run_stop_rate, speed_1s_mph
Reads only repo-derived player tables in ../out (no draft slot columns) plus player_play for deployment shares.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from common import DATA, CACHE, REPO, players, assert_no_draft

O = REPO / "out"
OUTCOMES = {"WR": ["sunday_speed_mph", "sep_all_mean", "break_y"], "TE": ["sep_all_mean"],
            "DB": ["tackle_rate", "tfl_rate", "close_rate_mph", "pfr_yds_tgt", "pfr_mtkl_pct", "sunday_speed_mph"],
            "DL": ["pressure_rate", "sack_rate", "tfl_rate", "run_stop_rate", "speed_1s_mph"]}
STYLE = {"WR": ["game_wr_peak_decel_mag", "game_wr_peak_accel", "game_wr_speed_lost", "game_wr_time_through",
                "g_deep_speed", "cushion_mean", "slot_share", "deep_route_share", "short_route_share"],
         "DB": ["game_db_peak_decel_mag", "game_db_peak_accel", "game_db_speed_lost", "game_db_time_through",
                "close_speed_at_arrival", "close_max_s_0p5", "g_cov_speed", "cushion_mean", "man_share", "slot_share", "high_safety_share"],
         "DL": ["g_speed_1s", "g_get_off", "pen_pass_2s", "pen_run_2s", "edge_share"]}
STYLE["TE"] = [c for c in STYLE["WR"] if c != "g_deep_speed"]   # deep-route game speed is WR-only


def usage() -> pd.DataFrame:
    g = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pd.read_csv(DATA / "player_play.csv", usecols=["game_id", "nfl_id", "lined_up_position", "route_ran", "coverage_assignment",
                                                        "play_nullified_by_penalty", "pass_result"])
    pp = pp.merge(g, on="game_id")
    pp = pp[(pp.season_type == "REG") & (pp.play_nullified_by_penalty.astype(str) == "N")]
    r = pp[pp.route_ran.notna()].groupby("nfl_id").agg(
        n_routes=("route_ran", "size"),
        slot_share_r=("lined_up_position", lambda v: (v == "SLOT_WR").mean()),
        deep_route_share=("route_ran", lambda v: v.isin(["GO", "POST", "CORNER", "WHEEL"]).mean()),
        short_route_share=("route_ran", lambda v: v.isin(["HITCH", "SLANT", "FLAT", "SCREEN"]).mean()))
    cov = pp[pp.pass_result.notna() & pp.coverage_assignment.notna() & pp.lined_up_position.isin(["CB", "SLOT_CB", "HIGH_SAFETY", "BOX_SAFETY", "MLB", "OLB"])]
    c = cov.groupby("nfl_id").agg(n_cov=("coverage_assignment", "size"),
                                  man_share=("coverage_assignment", lambda v: v.str.contains("MAN").mean()),
                                  slot_share_d=("lined_up_position", lambda v: (v == "SLOT_CB").mean()),
                                  high_safety_share=("lined_up_position", lambda v: (v == "HIGH_SAFETY").mean()))
    dl = pp[pp.lined_up_position.isin(["EDGE", "INTERIOR_LINE"])].groupby("nfl_id").agg(
        n_dl=("lined_up_position", "size"), edge_share=("lined_up_position", lambda v: (v == "EDGE").mean()))
    u = r.join(c, how="outer").join(dl, how="outer").reset_index()
    for col, nmin in [("slot_share_r", ("n_routes", 30)), ("deep_route_share", ("n_routes", 30)), ("short_route_share", ("n_routes", 30)),
                      ("man_share", ("n_cov", 30)), ("slot_share_d", ("n_cov", 30)), ("high_safety_share", ("n_cov", 30)), ("edge_share", ("n_dl", 20))]:
        u.loc[u[nmin[0]].fillna(0) < nmin[1], col] = np.nan
    return u


def main() -> None:
    pl = players()
    u = usage()
    rc = pd.read_csv(O / "route_cod_game_player.csv")
    wt = pd.read_csv(O / "wr_te_robust_players.csv", usecols=["nfl_id", "sep_all_mean", "sunday_speed_mph"])
    rl = pd.read_csv(O / "wr_route_lead_players.csv", usecols=["nfl_id", "break_y"])
    db = pd.read_csv(O / "db_robust_players.csv", usecols=["nfl_id", "tackle_rate", "tfl_rate", "close_rate_mph", "pfr_yds_tgt", "pfr_mtkl_pct", "sunday_speed_mph"])
    dl = pd.read_csv(O / "dl_robust_players.csv", usecols=["nfl_id", "pressure_rate", "sack_rate", "tfl_rate", "run_stop_rate", "speed_1s_mph",
                                                           "player_get_off", "pen_pass_2s", "pen_run_2s"])
    for d in (rc, wt, rl, db, dl):
        assert_no_draft(d)
    rows = []
    for grp in ["WR", "TE"]:
        d = pl[pl.group == grp].merge(rc.drop(columns=["display_name", "draft_year", "nfl_position", "pos_group", "sep_all_mean"]), on="nfl_id", how="left")
        d = d.merge(wt, on="nfl_id", how="left").merge(rl, on="nfl_id", how="left").merge(u, on="nfl_id", how="left")
        d["g_deep_speed"] = d.sunday_speed_mph; d["slot_share"] = d.slot_share_r
        rows.append(d)
    d = pl[pl.group == "DB"].merge(rc.drop(columns=["display_name", "draft_year", "nfl_position", "pos_group"]), on="nfl_id", how="left")
    d = d.merge(db, on="nfl_id", how="left").merge(u, on="nfl_id", how="left")
    d["g_cov_speed"] = d.sunday_speed_mph; d["slot_share"] = d.slot_share_d
    rows.append(d)
    d = pl[pl.group == "DL"].merge(dl, on="nfl_id", how="left").merge(u, on="nfl_id", how="left")
    d["g_speed_1s"] = d.speed_1s_mph; d["g_get_off"] = d.player_get_off
    rows.append(d)
    keep = ["nfl_id", "group", "role", "draft_year"] + sorted({c for v in STYLE.values() for c in v} | {c for v in OUTCOMES.values() for c in v})
    g = pd.concat(rows, ignore_index=True)[keep]
    assert_no_draft(g)
    g.to_parquet(CACHE / "game_features.parquet", index=False)
    for grp in ["WR", "TE", "DB", "DL"]:
        s = g[g.group == grp]
        print(grp, "style n (all present):", s[STYLE[grp]].notna().all(axis=1).sum(), "| outcome n:", s[OUTCOMES[grp]].notna().sum().to_dict())


if __name__ == "__main__":
    main()
