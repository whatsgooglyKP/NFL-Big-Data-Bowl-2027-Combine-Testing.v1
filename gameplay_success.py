#!/usr/bin/env python3
"""On-field gameplay success checks for WR, CB, and S.

Playing time (snaps, start rate) is context, not the success definition.
This script measures outcomes that actually exist in player_play.csv — it
does not invent targets allowed, completions allowed, PBUs, or interceptions
attributed to a defender, because those fields are not in the file.

Wide receivers (official Sunday Speed sample, ≥20 deep routes):
  yards per route, deep yards per deep route, deep target share, catch rate,
  deep-route separation, YAC over expected.

Cornerbacks and safeties:
  tackle involvement rate and tackle-for-loss rate on regular-season snaps
  that stood. There is no target-allowed or completion-allowed field, and
  play-level pass_result is not attributed to the covered defender.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/gameplay_success.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

N_BOOT = 2000
BOOT_SEED = 2027
DEEP_ROUTES = frozenset({"GO", "POST", "CORNER", "WHEEL"})
MIN_TARGETS = 8
POS_ORDER = ["WR", "CB", "S"]
POS_COLOR = {"WR": "#0072B2", "CB": "#D55E00", "S": "#009E73"}


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def coerce_bool(s: pd.Series) -> pd.Series:
    return s.map({
        True: True, False: False, "TRUE": True, "FALSE": False,
        "True": True, "False": False, 1: True, 0: False, 1.0: True, 0.0: False,
    })


def _residualize(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    keep = [0]
    for j in range(1, A.shape[1]):
        cand = A[:, keep + [j]]
        if np.linalg.matrix_rank(cand) > len(keep):
            keep.append(j)
    A = A[:, keep]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def year_controls(d: pd.DataFrame) -> pd.DataFrame:
    """Draft-year dummies only. No draft slot / pick / round (Kevin's rule, 11/2026)."""
    return pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True).astype(float)


def spearman_controlled(x: pd.Series, y: pd.Series, df: pd.DataFrame) -> dict:
    d = pd.DataFrame({"x": x, "y": y, "draft_year": df["draft_year"]}).dropna()
    out = {
        "n": int(len(d)), "rho": np.nan, "p": np.nan,
        "partial_year_rho": np.nan, "partial_year_p": np.nan,
    }
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    controls = year_controls(d)
    X = controls.to_numpy(dtype=float)
    if np.unique(X, axis=0).shape[0] >= 2:
        rx = _residualize(d["x"].to_numpy(dtype=float), X)
        ry = _residualize(d["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size >= 2 and np.unique(ry).size >= 2:
            pr, pp = stats.spearmanr(rx, ry)
            out["partial_year_rho"], out["partial_year_p"] = float(pr), float(pp)
    return out


def bootstrap_year_ci(x: pd.Series, y: pd.Series, df: pd.DataFrame,
                           n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple[float, float, int]:
    base = pd.DataFrame({
        "x": x, "y": y, "draft_year": df["draft_year"],
    }).dropna().reset_index(drop=True)
    if len(base) < 8:
        return np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    rhos: list[float] = []
    for _ in range(n_boot):
        b = base.iloc[rng.integers(0, len(base), size=len(base))].reset_index(drop=True)
        if b["x"].nunique() < 2 or b["y"].nunique() < 2:
            continue
        controls = year_controls(b)
        X = controls.to_numpy(dtype=float)
        if np.unique(X, axis=0).shape[0] < 2:
            continue
        rx = _residualize(b["x"].to_numpy(dtype=float), X)
        ry = _residualize(b["y"].to_numpy(dtype=float), X)
        if np.unique(rx).size < 2 or np.unique(ry).size < 2:
            continue
        rho, _p = stats.spearmanr(rx, ry)
        if np.isfinite(rho):
            rhos.append(float(rho))
    if len(rhos) < max(50, n_boot // 20):
        return np.nan, np.nan, len(rhos)
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return float(lo), float(hi), len(rhos)


def _style() -> None:
    plt.rcParams.update({
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
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "figure.titlesize": 15,
        "font.family": "DejaVu Sans",
    })


def load_official_players() -> pd.DataFrame:
    path = OUT / "sunday_speed_players.parquet"
    M = pd.read_parquet(path) if path.exists() else pd.read_csv(OUT / "sunday_speed_players.csv")
    M = M.drop(columns=[c for c in M.columns if "pick" in c.lower() or c in ("draft_round",)], errors="ignore")
    log(f"Loaded {len(M)} skill players; official SSOE sample = {int(M['ssoe_mph'].notna().sum())}")
    return M


def build_wr_outcomes() -> pd.DataFrame:
    log("Building WR gameplay outcomes from player_play...")
    usecols = [
        "game_id", "play_id", "nfl_id", "play_nullified_by_penalty",
        "route_ran", "target", "rec_yards", "yards_after_catch",
        "expected_yards_after_catch", "separation_at_pass_forward",
        "pass_result",
    ]
    wr_ids = set(pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "nfl_position"])
                 .query("nfl_position == 'WR'")["nfl_id"])
    parts = []
    for ch in pd.read_csv(DATA / "player_play.csv", usecols=usecols, chunksize=100_000):
        parts.append(ch[ch["nfl_id"].isin(wr_ids)])
    pp = pd.concat(parts, ignore_index=True)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp[(pp["season_type"] == "REG") & (pp["play_nullified_by_penalty"] == "N")].copy()
    pp["target"] = coerce_bool(pp["target"]).fillna(False).astype(bool)
    pp["is_route"] = pp["route_ran"].notna()
    pp["is_deep"] = pp["route_ran"].isin(DEEP_ROUTES)
    pp["rec_yds"] = pd.to_numeric(pp["rec_yards"], errors="coerce")
    pp["caught"] = pp["rec_yds"].notna()
    pp["yac"] = pd.to_numeric(pp["yards_after_catch"], errors="coerce")
    pp["eyac"] = pd.to_numeric(pp["expected_yards_after_catch"], errors="coerce")
    pp["yac_oe"] = pp["yac"] - pp["eyac"]
    pp["sep"] = pd.to_numeric(pp["separation_at_pass_forward"], errors="coerce")

    def agg(g: pd.DataFrame) -> pd.Series:
        routes = g[g["is_route"]]
        deep = g[g["is_deep"]]
        n_routes = int(len(routes))
        n_deep = int(len(deep))
        n_tgt = int(routes["target"].sum())
        n_deep_tgt = int(deep["target"].sum())
        n_rec = int(routes["caught"].sum())
        rec_yds = float(routes["rec_yds"].fillna(0).sum())
        deep_yds = float(deep["rec_yds"].fillna(0).sum())
        return pd.Series({
            "n_routes": n_routes,
            "n_deep_routes": n_deep,
            "n_targets": n_tgt,
            "n_deep_targets": n_deep_tgt,
            "n_receptions": n_rec,
            "rec_yards": rec_yds,
            "deep_rec_yards": deep_yds,
            "yards_per_route": rec_yds / n_routes if n_routes else np.nan,
            "deep_yards_per_deep_route": deep_yds / n_deep if n_deep else np.nan,
            "target_rate": n_tgt / n_routes if n_routes else np.nan,
            "deep_target_rate": n_deep_tgt / n_deep if n_deep else np.nan,
            "deep_target_share": n_deep_tgt / n_tgt if n_tgt >= MIN_TARGETS else np.nan,
            "catch_rate": n_rec / n_tgt if n_tgt >= MIN_TARGETS else np.nan,
            "sep_deep": float(deep["sep"].mean()) if deep["sep"].notna().sum() >= 8 else np.nan,
            "yac_oe": float(g.loc[g["caught"], "yac_oe"].mean()) if g.loc[g["caught"], "yac_oe"].notna().sum() >= 5 else np.nan,
        })

    out = pp.groupby("nfl_id", sort=False).apply(agg, include_groups=False).reset_index()
    log(f"  WR outcomes for {len(out)} players; "
        f"{int((out.n_routes >= 20).sum())} with ≥20 routes, "
        f"{int((out.n_targets >= MIN_TARGETS).sum())} with ≥{MIN_TARGETS} targets")
    return out


def build_db_outcomes() -> pd.DataFrame:
    """Tackle and TFL rates for CB / FS / SS. No allowed-target fields exist."""
    log("Building CB/S gameplay outcomes from player_play...")
    usecols = [
        "game_id", "play_id", "nfl_id", "play_nullified_by_penalty",
        "pass_result", "coverage_assignment",
        "tackle", "assist", "tackle_for_loss", "caused_forced_fumble",
    ]
    pos = pd.read_csv(DATA / "players.csv", usecols=["nfl_id", "nfl_position"])
    db_ids = set(pos[pos["nfl_position"].isin(["CB", "FS", "SS"])]["nfl_id"])
    parts = []
    for ch in pd.read_csv(DATA / "player_play.csv", usecols=usecols, chunksize=100_000):
        parts.append(ch[ch["nfl_id"].isin(db_ids)])
    pp = pd.concat(parts, ignore_index=True)
    games = pd.read_csv(DATA / "games.csv", usecols=["game_id", "season_type"])
    pp = pp.merge(games, on="game_id", how="left")
    pp = pp[(pp["season_type"] == "REG") & (pp["play_nullified_by_penalty"] == "N")].copy()
    pp["solo"] = pd.to_numeric(pp["tackle"], errors="coerce").fillna(0) >= 1
    pp["ast"] = pd.to_numeric(pp["assist"], errors="coerce").fillna(0) >= 1
    pp["involved"] = pp["solo"] | pp["ast"]
    pp["tfl"] = coerce_bool(pp["tackle_for_loss"]).fillna(False).astype(bool)
    pp["ff"] = pd.to_numeric(pp["caused_forced_fumble"], errors="coerce").fillna(0) >= 1
    cov = pp["coverage_assignment"].notna() & (pp["coverage_assignment"] != "NO_ASSIGNMENT")
    man_deep = pp["coverage_assignment"].fillna("").str.contains("MAN|DEEP", regex=True)
    pp["is_cov"] = cov
    pp["is_man_deep"] = man_deep
    # Pass plays only for a coverage-context rate; all snaps for a box-score rate.
    pp["is_pass"] = pp["pass_result"].notna()

    def agg(g: pd.DataFrame) -> pd.Series:
        n = int(len(g))
        n_pass = int(g["is_pass"].sum())
        n_cov = int(g["is_cov"].sum())
        n_md = int(g["is_man_deep"].sum())
        return pd.Series({
            "n_def_snaps": n,
            "n_pass_snaps": n_pass,
            "n_cov_snaps": n_cov,
            "n_man_deep": n_md,
            "n_tackles": int(g["involved"].sum()),
            "n_solo": int(g["solo"].sum()),
            "n_tfl": int(g["tfl"].sum()),
            "n_ff": int(g["ff"].sum()),
            "tackle_rate": float(g["involved"].mean()) if n else np.nan,
            "solo_tackle_rate": float(g["solo"].mean()) if n else np.nan,
            "tfl_rate": float(g["tfl"].mean()) if n else np.nan,
            "tackle_rate_pass": float(g.loc[g["is_pass"], "involved"].mean()) if n_pass else np.nan,
            "tfl_rate_pass": float(g.loc[g["is_pass"], "tfl"].mean()) if n_pass else np.nan,
        })

    out = pp.groupby("nfl_id", sort=False).apply(agg, include_groups=False).reset_index()
    log(f"  DB outcomes for {len(out)} players; "
        f"median snaps={out.n_def_snaps.median():.0f}, "
        f"median tackles={out.n_tackles.median():.0f}")
    return out


def _test_row(family, pos, sample, feature, flabel, outcome, olabel, frame, feat_s, out_s) -> dict:
    res = spearman_controlled(feat_s, out_s, frame)
    lo, hi, n_boot = bootstrap_year_ci(feat_s, out_s, frame)
    res["partial_ci_low"] = lo
    res["partial_ci_high"] = hi
    res["n_boot"] = n_boot
    log(
        f"  {pos:2s}  {flabel:28s} vs {olabel:32s}  [{sample}]  n={res['n']:3d}  "
        f"ρ={res['rho']:+.2f} (p={fmt_p(res['p'])})  "
        f"year ρ={res['partial_year_rho']:+.2f} "
        f"(p={fmt_p(res['partial_year_p'])}, CI {lo:+.2f}–{hi:+.2f})"
    )
    return {
        "family": family, "pos_group": pos, "sample": sample,
        "feature": feature, "feature_label": flabel,
        "outcome": outcome, "outcome_label": olabel, **res,
    }


def holm_on(df: pd.DataFrame, pcol: str) -> pd.DataFrame:
    pvals = df[pcol].to_numpy(dtype=float)
    finite = np.isfinite(pvals)
    holm_p = np.full(len(pvals), np.nan)
    sig = np.zeros(len(pvals), dtype=bool)
    if finite.sum() >= 1:
        reject, p_adj, _, _ = multipletests(pvals[finite], method="holm")
        holm_p[finite] = p_adj
        sig[finite] = reject
    df = df.copy()
    df["holm_p"] = holm_p
    df["sig_holm_05"] = sig
    return df


def run_wr_tests(M: pd.DataFrame) -> pd.DataFrame:
    official = M[(M["pos_group"] == "WR") & M["ssoe_mph"].notna()].copy()
    log(f"\n==== WR production family (official Sunday Speed sample, n={len(official)}) ====")
    log("Pre-declared: Sunday Speed and SSOE vs yards/route, deep yards/deep route, deep target share.")
    log("Holm is on those 6 year partial p-values.")

    # Official family
    family_spec = [
        ("sunday_speed_mph", "Sunday Speed (mph)", "yards_per_route", "Yards per route"),
        ("sunday_speed_mph", "Sunday Speed (mph)", "deep_yards_per_deep_route", "Deep yards per deep route"),
        ("sunday_speed_mph", "Sunday Speed (mph)", "deep_target_share", "Deep target share"),
        ("ssoe_mph", "Sunday Speed Over Expected", "yards_per_route", "Yards per route"),
        ("ssoe_mph", "Sunday Speed Over Expected", "deep_yards_per_deep_route", "Deep yards per deep route"),
        ("ssoe_mph", "Sunday Speed Over Expected", "deep_target_share", "Deep target share"),
    ]
    fam = []
    for feat, flabel, out, olabel in family_spec:
        fam.append(_test_row(
            "wr_production_primary", "WR", "official_sunday_speed",
            feat, flabel, out, olabel, official, official[feat], official[out],
        ))
    F = holm_on(pd.DataFrame(fam), "partial_year_p")
    log("  Holm-adjusted p (6-test WR production family, year partial p):")
    for _, r in F.iterrows():
        star = " *" if bool(r["sig_holm_05"]) else ""
        log(
            f"    {r['feature_label']:28s} vs {r['outcome_label']:32s}  "
            f"ρ={r['partial_year_rho']:+.2f}  "
            f"p={fmt_p(r['partial_year_p'])} → Holm p={fmt_p(r['holm_p'])}{star}"
        )

    # Combine → production (competition link) and secondary outcomes, not in the family.
    log("\n==== WR production companions (Combine top speed; catch rate, separation, YAC-OE) ====")
    extra = []
    companions = [
        ("c_top_mph", "Combine top speed (mph)", "yards_per_route", "Yards per route"),
        ("c_top_mph", "Combine top speed (mph)", "deep_yards_per_deep_route", "Deep yards per deep route"),
        ("c_top_mph", "Combine top speed (mph)", "deep_target_share", "Deep target share"),
        ("c_top_mph", "Combine top speed (mph)", "catch_rate", "Catch rate"),
        ("c_top_mph", "Combine top speed (mph)", "sep_deep", "Deep-route separation (yd)"),
        ("sunday_speed_mph", "Sunday Speed (mph)", "catch_rate", "Catch rate"),
        ("sunday_speed_mph", "Sunday Speed (mph)", "sep_deep", "Deep-route separation (yd)"),
        ("sunday_speed_mph", "Sunday Speed (mph)", "yac_oe", "YAC over expected"),
        ("sunday_speed_mph", "Sunday Speed (mph)", "target_rate", "Target rate"),
        ("ssoe_mph", "Sunday Speed Over Expected", "catch_rate", "Catch rate"),
        ("ssoe_mph", "Sunday Speed Over Expected", "sep_deep", "Deep-route separation (yd)"),
        ("ssoe_mph", "Sunday Speed Over Expected", "yac_oe", "YAC over expected"),
        ("ssoe_mph", "Sunday Speed Over Expected", "target_rate", "Target rate"),
    ]
    for feat, flabel, out, olabel in companions:
        row = _test_row(
            "wr_production_companion", "WR", "official_sunday_speed",
            feat, flabel, out, olabel, official, official[feat], official[out],
        )
        row["holm_p"] = np.nan
        row["sig_holm_05"] = False
        extra.append(row)
    return pd.concat([F, pd.DataFrame(extra)], ignore_index=True, sort=False)


def run_db_tests(M: pd.DataFrame) -> pd.DataFrame:
    log("\n==== Fields that do not exist for CB/S (will not be invented) ====")
    log("  No targets-allowed, completions-allowed, PBU, or interception field")
    log("  is attached to a defender. play_result / pass_result is play-level and")
    log("  is not attributed to the covered defender. target is only ever True")
    log("  for offensive skill players. Tests below use tackle and TFL rates,")
    log("  which do exist.")

    # Broader sample: anyone at the position with a 40 and enough snaps.
    # Official SS sample is a sensitivity.
    rows = []
    log("\n==== CB/S gameplay family: Combine speed vs tackle / TFL rate ====")
    log("Pre-declared: 4 tests (CB and S × tackle involvement rate and TFL rate),")
    log("broader sample (40-yard tracking + start rate available, ≥50 defensive snaps).")
    log("Holm on year partial p. WR is reported as a control, not in the family.")

    fam = []
    mask_broad = M["c_top"].notna() & (M["n_def_snaps"] >= 50)
    for pos in ("CB", "S"):
        d = M[(M["pos_group"] == pos) & mask_broad].copy()
        for out, olabel in (
            ("tackle_rate", "Tackle involvement rate"),
            ("tfl_rate", "Tackle-for-loss rate"),
        ):
            fam.append(_test_row(
                "db_gameplay_primary", pos, "all_with_40_and_50_snaps",
                "c_top_mph", "Combine top speed (mph)",
                out, olabel, d, d["c_top_mph"], d[out],
            ))
    F = holm_on(pd.DataFrame(fam), "partial_year_p")
    log("  Holm-adjusted p (4-test CB/S gameplay family, year partial p):")
    for _, r in F.iterrows():
        star = " *" if bool(r["sig_holm_05"]) else ""
        log(
            f"    {r['pos_group']:2s}  {r['outcome_label']:32s}  "
            f"ρ={r['partial_year_rho']:+.2f}  "
            f"p={fmt_p(r['partial_year_p'])} → Holm p={fmt_p(r['holm_p'])}{star}"
        )
    rows.append(F)

    log("\n==== CB speed tax, re-tested on gameplay (and official-sample sensitivities) ====")
    extra = []
    for sample_name, mask in (
        ("all_with_40_and_50_snaps", mask_broad),
        ("official_sunday_speed_sample", M["ssoe_mph"].notna()),
    ):
        for pos in POS_ORDER:
            d = M[(M["pos_group"] == pos) & mask].copy()
            outcomes = (
                [("tackle_rate", "Tackle involvement rate"),
                 ("tfl_rate", "Tackle-for-loss rate")]
                if pos in ("CB", "S")
                else []
            )
            # Also restate start-rate tax as a playing-time companion on the same samples.
            outcomes.append(("start_rate", "Start rate (playing time, context)"))
            for out, olabel in outcomes:
                if out not in d.columns:
                    continue
                # Skip CB/S broader-sample tackle/TFL already in the primary family.
                if (
                    sample_name == "all_with_40_and_50_snaps"
                    and pos in ("CB", "S")
                    and out in ("tackle_rate", "tfl_rate")
                ):
                    continue
                row = _test_row(
                    "db_gameplay_companion", pos, sample_name,
                    "c_top_mph", "Combine top speed (mph)",
                    out, olabel, d, d["c_top_mph"], d[out],
                )
                row["holm_p"] = np.nan
                row["sig_holm_05"] = False
                extra.append(row)
            if pos in ("CB", "S") and "sunday_speed_mph" in d.columns:
                d2 = d.dropna(subset=["sunday_speed_mph"])
                for out, olabel in (
                    ("tackle_rate", "Tackle involvement rate"),
                    ("tfl_rate", "Tackle-for-loss rate"),
                ):
                    row = _test_row(
                        "db_gameplay_companion", pos, sample_name,
                        "sunday_speed_mph", "Sunday Speed (mph)",
                        out, olabel, d2, d2["sunday_speed_mph"], d2[out],
                    )
                    row["holm_p"] = np.nan
                    row["sig_holm_05"] = False
                    extra.append(row)
    rows.append(pd.DataFrame(extra))
    return pd.concat(rows, ignore_index=True, sort=False)


def make_figure(wr_tests: pd.DataFrame, db_tests: pd.DataFrame) -> Path:
    """Coach-readable: do Sunday Speed / the CB 40 predict gameplay outcomes?"""
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.4))

    wr = wr_tests[wr_tests["family"] == "wr_production_primary"].copy().reset_index(drop=True)
    wr_labels = [
        "Sunday Speed vs yards/route",
        "Sunday Speed vs deep yards/route",
        "Sunday Speed vs deep target share",
        "SSOE vs yards/route",
        "SSOE vs deep yards/route",
        "SSOE vs deep target share",
    ]
    ax = axes[0]
    ys = np.arange(len(wr))[::-1]
    colors = ["#0072B2" if bool(s) else "#7A7A7A" for s in wr["sig_holm_05"].fillna(False)]
    rhos = wr["partial_year_rho"].fillna(0).to_numpy()
    ax.barh(ys, rhos, color=colors, height=0.66, zorder=3, edgecolor="white")
    ax.axvline(0, color="#888888", lw=0.8)
    for y, r in zip(ys, wr.itertuples()):
        val = r.partial_year_rho if np.isfinite(r.partial_year_rho) else 0.0
        star = " ★" if bool(getattr(r, "sig_holm_05", False)) else ""
        ax.text(
            val + (0.02 if val >= 0 else -0.02), y,
            f"{val:+.2f}{star}  n={int(r.n)}",
            ha="left" if val >= 0 else "right", va="center", fontsize=8,
        )
    ax.set_yticks(ys, wr_labels, fontsize=8.5)
    ax.set_xlabel("Correlation after draft year")
    ax.set_xlim(-0.55, 0.75)
    wr_any = bool(wr["sig_holm_05"].fillna(False).any())
    ax.set_title(
        "Receivers: Sunday Speed vs production"
        if wr_any else
        "Receivers: Sunday Speed does not predict production",
        loc="left", fontweight="bold", color=POS_COLOR["WR"], fontsize=11,
    )

    db = db_tests[db_tests["family"] == "db_gameplay_primary"].copy().reset_index(drop=True)
    db_labels = [
        f"{r.pos_group}: {('tackle rate' if r.outcome == 'tackle_rate' else 'TFL rate')}"
        for r in db.itertuples()
    ]
    ax = axes[1]
    ys = np.arange(len(db))[::-1]
    colors = [
        "#D55E00" if (p == "CB" and bool(s)) else "#009E73" if (p == "S" and bool(s)) else "#7A7A7A"
        for p, s in zip(db["pos_group"], db["sig_holm_05"].fillna(False))
    ]
    rhos = db["partial_year_rho"].fillna(0).to_numpy()
    ax.barh(ys, rhos, color=colors, height=0.66, zorder=3, edgecolor="white")
    ax.axvline(0, color="#888888", lw=0.8)
    for y, r in zip(ys, db.itertuples()):
        val = r.partial_year_rho if np.isfinite(r.partial_year_rho) else 0.0
        star = " ★" if bool(getattr(r, "sig_holm_05", False)) else ""
        ax.text(
            val + (0.02 if val >= 0 else -0.02), y,
            f"{val:+.2f}{star}  n={int(r.n)}",
            ha="left" if val >= 0 else "right", va="center", fontsize=8,
        )
    ax.set_yticks(ys, db_labels, fontsize=8.5)
    ax.set_xlabel("Correlation after draft year")
    ax.set_xlim(-0.55, 0.75)
    db_any = bool(db["sig_holm_05"].fillna(False).any())
    ax.set_title(
        "DBs: Combine speed vs tackles / TFLs"
        if db_any else
        "DBs: the 40 does not predict tackles or TFLs",
        loc="left", fontweight="bold", color=POS_COLOR["CB"], fontsize=11,
    )

    title = (
        "Gameplay outcomes that actually exist — and what they do (or do not) follow"
        if (wr_any or db_any) else
        "Sunday Speed and the CB 40 do not predict the gameplay outcomes we can actually measure"
    )
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=12.5, y=0.98)
    import textwrap
    caption = (
        "Left: official WR Sunday Speed sample (n=62). Yards per route = receiving yards / routes (regular season, plays that stood). "
        "Deep routes are go, post, corner, and wheel. Deep target share needs at least 8 targets. "
        "Right: Combine speed vs tackle involvement (solo or assist) and tackle-for-loss rate, regular-season snaps that stood, at least 50 snaps. "
        "There is no targets-allowed, completions-allowed, PBU, or interception field for a defender; those tests were not invented. "
        "★ would mark a Holm-surviving result in the pre-declared family. Grey bars did not. Playing time is context, not the success definition. "
        "Defensive-line pressure and sack results are in Figures 5 and 6 (headline: all DL, with Edge vs Interior breakouts)."
    )
    fig.text(0.01, 0.01, textwrap.fill(caption, width=165), fontsize=8, color="#555555", ha="left", va="bottom")
    fig.subplots_adjust(left=0.28, right=0.98, top=0.86, bottom=0.20, wspace=0.55)
    path = FIGS / "fig7_gameplay_success.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    M = load_official_players()
    wr_out = build_wr_outcomes()
    db_out = build_db_outcomes()
    M = M.merge(wr_out, on="nfl_id", how="left", suffixes=("_old", ""))
    M = M.merge(db_out, on="nfl_id", how="left")
    # Prefer newly built sep_deep / yac_oe over the earlier exploratory columns.
    for c in ("sep_deep", "yac_oe"):
        if f"{c}_old" in M.columns and c not in M.columns:
            M[c] = M[f"{c}_old"]
        elif f"{c}_old" in M.columns and c in M.columns:
            M[c] = M[c].combine_first(M[f"{c}_old"])

    wr_tests = run_wr_tests(M)
    db_tests = run_db_tests(M)
    tests = pd.concat([wr_tests, db_tests], ignore_index=True, sort=False)
    tests_path = OUT / "gameplay_success_tests.csv"
    tests.to_csv(tests_path, index=False)
    log(f"\n  wrote {tests_path}")

    keep = [
        "nfl_id", "display_name", "nfl_position", "pos_group", "draft_year",
        "c_top_mph", "sunday_speed_mph", "ssoe_mph",
        "n_routes", "n_deep_routes", "n_targets", "n_deep_targets", "n_receptions",
        "rec_yards", "deep_rec_yards", "yards_per_route", "deep_yards_per_deep_route",
        "target_rate", "deep_target_rate", "deep_target_share", "catch_rate",
        "sep_deep", "yac_oe",
        "n_def_snaps", "n_pass_snaps", "n_tackles", "n_solo", "n_tfl",
        "tackle_rate", "solo_tackle_rate", "tfl_rate", "tackle_rate_pass", "tfl_rate_pass",
        "start_rate", "career_defensive_snaps", "career_games_active",
    ]
    keep = [c for c in keep if c in M.columns]
    players_path = OUT / "gameplay_success_players.csv"
    official_or_db = M["ssoe_mph"].notna() | M["n_def_snaps"].notna() | M["n_routes"].notna()
    M.loc[official_or_db, keep].to_csv(players_path, index=False)
    log(f"  wrote {players_path}")

    make_figure(wr_tests, db_tests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
