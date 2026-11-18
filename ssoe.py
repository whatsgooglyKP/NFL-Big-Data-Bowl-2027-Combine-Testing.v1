#!/usr/bin/env python3
"""Sunday Speed Over Expected scouting-card leaderboard.

Reads the official player table from build_dataset.py, writes a coach-facing
leaderboard, a top/bottom figure, and two supporting tests:

  1. Incremental value of Combine top speed over ngs_athleticism_score.
  2. The CB "speed tax" check: Combine speed vs start rate, draft-year controlled (no draft slot).

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/ssoe.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from statsmodels.stats.multitest import multipletests

ROOT = Path("/workspace/bdb2027")
OUT = ROOT / "out"
FIGS = OUT / "figs"

MPH = 2.0455
POS_ORDER = ["WR", "CB", "S"]
POS_COLOR = {"WR": "#0072B2", "CB": "#D55E00", "S": "#009E73"}
POS_LABEL = {"WR": "Wide receivers", "CB": "Cornerbacks", "S": "Safeties"}
N_PERM = 5000
RNG_SEED = 2027
TOP_N = 15


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def reliability(n_opp: float) -> str:
    if not np.isfinite(n_opp):
        return "Limited"
    if n_opp >= 80:
        return "High"
    if n_opp >= 40:
        return "Medium"
    return "Limited"


def spearman_partial(x: pd.Series, y: pd.Series, year: pd.Series) -> dict:
    """Spearman ρ, plus the draft-year-controlled partial (both sides demeaned within draft-year cells).

    No draft slot / pick / round is used (Kevin's rule, 11/2026).
    """
    d = pd.DataFrame({"x": x, "y": y, "year": year}).dropna()
    out = {"n": len(d), "rho": np.nan, "p": np.nan, "partial_rho": np.nan, "partial_p": np.nan}
    if len(d) < 8:
        return out
    rho, p = stats.spearmanr(d["x"], d["y"])
    out["rho"], out["p"] = float(rho), float(p)
    if d["year"].nunique() >= 2 and d["x"].nunique() >= 2 and d["y"].nunique() >= 2:
        rx = d["x"] - d.groupby("year")["x"].transform("mean")
        ry = d["y"] - d.groupby("year")["y"].transform("mean")
        pr, pp = stats.spearmanr(rx, ry)
        out["partial_rho"], out["partial_p"] = float(pr), float(pp)
        out["x_year_resid"] = rx
        out["y_resid"] = ry
        out["_df"] = d
    return out


def incremental_spearman(x: pd.Series, y: pd.Series, controls: pd.DataFrame) -> dict:
    """Spearman ρ of x vs y after residualizing both on the control columns (OLS)."""
    d = pd.concat([x.rename("x"), y.rename("y"), controls], axis=1).dropna()
    out = {"n": len(d), "rho": np.nan, "p": np.nan}
    if len(d) < 8:
        return out
    X = d[controls.columns].to_numpy(dtype=float)
    if np.unique(X, axis=0).shape[0] < 2:
        return out
    rx = d["x"] - LinearRegression().fit(X, d["x"]).predict(X)
    ry = d["y"] - LinearRegression().fit(X, d["y"]).predict(X)
    if rx.nunique() < 2 or ry.nunique() < 2:
        return out
    rho, p = stats.spearmanr(rx, ry)
    out["rho"], out["p"] = float(rho), float(p)
    return out


def perm_partial_p(x: pd.Series, y: pd.Series, year: pd.Series, n_perm: int = N_PERM, seed: int = RNG_SEED) -> float:
    """Permutation p-value for the year-controlled partial Spearman (shuffle x residuals)."""
    d = pd.DataFrame({"x": x, "y": y, "year": year}).dropna()
    if len(d) < 8:
        return np.nan
    rx = (d["x"] - d.groupby("year")["x"].transform("mean")).to_numpy()
    ry = (d["y"] - d.groupby("year")["y"].transform("mean")).to_numpy()
    obs = abs(stats.spearmanr(rx, ry).statistic)
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        shuf = rng.permutation(rx)
        hits += abs(stats.spearmanr(shuf, ry).statistic) >= obs
    return (hits + 1) / (n_perm + 1)


def select_top_bottom(sub: pd.DataFrame, n: int = TOP_N) -> tuple[pd.DataFrame, bool]:
    """Top n and bottom n by SSOE, with no player listed twice.

    If the position has fewer than 2n players, return the full roster
    sorted by SSOE (descending) and showed_all=True so the figure caption
    can say the sample is smaller than n top + n bottom.
    """
    sub_sorted = sub.sort_values(
        ["ssoe_mph", "player_name"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)
    if len(sub_sorted) <= 2 * n:
        return sub_sorted, True
    top = sub_sorted.head(n)
    bot = sub_sorted.tail(n)
    bot = bot[~bot["nfl_id"].isin(set(top["nfl_id"]))]
    return pd.concat([top, bot], ignore_index=True), False


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


def build_leaderboard(M: pd.DataFrame, slopes: dict) -> pd.DataFrame:
    d = M[M["ssoe_mph"].notna() & M["c_top_mph"].notna() & M["sunday_speed_mph"].notna()].copy()
    # Recompute expected Sunday Speed from the official position lines so the
    # scouting card is traceable to translation_slopes.json / METRICS.md.
    d["expected_sunday_speed_mph"] = np.nan
    for pos, sl in slopes.items():
        mask = d["pos_group"] == pos
        expected_yds = sl["intercept"] + sl["slope"] * d.loc[mask, "c_top"]
        d.loc[mask, "expected_sunday_speed_mph"] = expected_yds * MPH
    # Guard: official SSOE should match actual - expected within rounding.
    recon = d["sunday_speed_mph"] - d["expected_sunday_speed_mph"]
    max_err = float(np.nanmax(np.abs(recon - d["ssoe_mph"])))
    if max_err > 1e-6:
        log(f"WARNING: recomputed SSOE differs from table by up to {max_err:.3e} mph; using recomputed values.")
        d["ssoe_mph"] = recon
    else:
        log(f"  SSOE reconstruction matches official table (max abs err {max_err:.2e} mph).")

    d["n_opportunity_plays"] = np.where(d["pos_group"] == "WR", d["n_deep_reg"], d["n_cov_reg"])
    d["reliability"] = d["n_opportunity_plays"].map(reliability)
    d["rank_in_position"] = d.groupby("pos_group")["ssoe_mph"].rank(ascending=False, method="min").astype(int)

    # Draft slot and round are never used on the scouting card, even as a label.
    cols = [
        "nfl_id", "display_name", "nfl_position", "pos_group", "college_name",
        "c_top_mph", "expected_sunday_speed_mph", "sunday_speed_mph", "ssoe_mph",
        "realization", "n_opportunity_plays", "n_plays_reg", "reliability",
        "rank_in_position",
    ]
    out = d[cols].sort_values(["pos_group", "ssoe_mph"], ascending=[True, False])
    # Friendlier names for the csv a coach might open.
    out = out.rename(columns={
        "display_name": "player_name",
        "nfl_position": "position",
        "pos_group": "position_group",
        "c_top_mph": "combine_top_speed_mph",
        "sunday_speed_mph": "actual_sunday_speed_mph",
        "realization": "speed_realization",
    })
    for c in ("combine_top_speed_mph", "expected_sunday_speed_mph", "actual_sunday_speed_mph", "ssoe_mph"):
        out[c] = out[c].round(3)
    out["speed_realization"] = out["speed_realization"].round(3)
    out["n_opportunity_plays"] = out["n_opportunity_plays"].astype(int)
    out["n_plays_reg"] = out["n_plays_reg"].fillna(0).astype(int)
    return out.reset_index(drop=True)


def make_figure(board: pd.DataFrame) -> Path:
    _style()
    over_color = "#009E73"
    under_color = "#D55E00"

    panels = []
    for pos in POS_ORDER:
        sub = board[board["position_group"] == pos].copy()
        plot, showed_all = select_top_bottom(sub)
        panels.append((pos, sub, plot, showed_all))

    # One row per position keeps 15+15 names readable. Height scales with
    # how many bars each panel actually draws.
    height = sum(1.05 + 0.28 * len(plot) for _, _, plot, _ in panels) + 1.35
    fig, axes = plt.subplots(
        3, 1, figsize=(11.2, height), sharex=False,
        gridspec_kw={"height_ratios": [len(plot) for _, _, plot, _ in panels]},
    )

    caption_notes = []
    for ax, (pos, sub, plot, showed_all) in zip(axes, panels):
        labels = []
        for _, r in plot.iterrows():
            flag = "" if r["reliability"] == "High" else f"  ({r['reliability']})"
            labels.append(f"{r['player_name']}{flag}")
        colors = [over_color if v >= 0 else under_color for v in plot["ssoe_mph"]]
        y = np.arange(len(plot))
        ax.barh(y, plot["ssoe_mph"], color=colors, edgecolor="white", height=0.72, zorder=3)
        ax.axvline(0, color="#444444", lw=0.9, zorder=2)
        # Visual break: between top n and bottom n, or at the zero crossing
        # when the full roster is shown because the sample is smaller than 2n.
        if showed_all:
            n_nonneg = int((plot["ssoe_mph"] >= 0).sum())
            if 0 < n_nonneg < len(plot):
                ax.axhline(n_nonneg - 0.5, color="#AAAAAA", lw=0.8, ls="--", zorder=1)
            caption_notes.append(
                f"{POS_LABEL[pos]}: all {len(sub)} players shown "
                f"(sample is smaller than {TOP_N} top + {TOP_N} bottom, so nobody is listed twice)."
            )
        else:
            ax.axhline(TOP_N - 0.5, color="#AAAAAA", lw=0.8, ls="--", zorder=1)
        ax.set_yticks(y, labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("SSOE (mph)")
        span = max(0.4, float(plot["ssoe_mph"].abs().max()))
        for i, v in enumerate(plot["ssoe_mph"]):
            ax.text(
                v + (0.04 if v >= 0 else -0.04), i,
                f"{v:+.2f}",
                va="center", ha="left" if v >= 0 else "right",
                fontsize=7.5, fontweight="bold",
                color="#222222",
            )
        ax.set_xlim(-span - 0.35, span + 0.45)
        title = f"{POS_LABEL[pos]}  (n={len(sub)})"
        if showed_all:
            title += "  — full roster"
        else:
            title += f"  — top {TOP_N} / bottom {TOP_N}"
        ax.set_title(title, loc="left", fontweight="bold", color=POS_COLOR[pos])
        if pos == "WR":
            ax.text(
                0.01, 0.02, "Over the 40  →", color=over_color, fontsize=8,
                transform=ax.transAxes, fontweight="bold",
            )

    if any(not showed_all for _, _, _, showed_all in panels):
        shown_partial = [
            POS_LABEL[pos] for pos, _, _, showed_all in panels if not showed_all
        ]
        caption_notes.insert(
            0,
            f"{' and '.join(shown_partial)}: top {TOP_N} and bottom {TOP_N} shown."
            if len(shown_partial) <= 2
            else f"Top {TOP_N} and bottom {TOP_N} shown at each position unless noted.",
        )

    fig.suptitle(
        "Sunday Speed Over Expected: who plays faster than their Combine 40 predicted",
        x=0.01, ha="left", fontweight="bold", fontsize=14, y=1.01,
    )
    fig.text(
        0.01, -0.01,
        "SSOE (mph) = actual Sunday Speed − the speed expected from the player's Combine 40-yard top speed at his position.  "
        + "  ".join(caption_notes) + "  "
        "For receivers the 40 is a real predictor, so this is a true over/under-the-40 flag.  "
        "For corners and safeties the 40 barely predicts Sunday Speed, so SSOE is close to faster or slower than the position average.  "
        "Limited/Medium in parentheses means fewer than 80 (or 40) opportunity plays — treat those names as directional.",
        fontsize=8, color="#555555", ha="left", wrap=True,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.99))
    path = FIGS / "fig4_ssoe_leaderboard.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def ngs_incremental(M: pd.DataFrame) -> pd.DataFrame:
    rows = []
    official = M[M["ssoe_mph"].notna()].copy()
    log("\n==== Incremental test: Combine top speed vs NGS athleticism score ====")
    log("Does the 10 Hz tracked 40 still predict Sunday Speed once we know ngs_athleticism_score?")
    for pos in POS_ORDER:
        d = official[official["pos_group"] == pos]
        ngs = d["ngs_athleticism_score"]
        # Raw associations.
        raw_c = spearman_partial(d["c_top"], d["sunday_speed"], d["draft_year"])
        raw_ngs = spearman_partial(ngs, d["sunday_speed"], d["draft_year"])
        raw_cn = spearman_partial(d["c_top"], ngs, d["draft_year"])
        inc_ngs = incremental_spearman(d["c_top"], d["sunday_speed"], d[["ngs_athleticism_score"]])
        inc_both = incremental_spearman(
            d["c_top"], d["sunday_speed"],
            pd.concat([d[["ngs_athleticism_score"]],
                       pd.get_dummies(d["draft_year"], prefix="yr", drop_first=True).astype(float)], axis=1),
        )
        rows.append({
            "family": "ngs_incremental", "pos_group": pos,
            "test": "c_top vs Sunday Speed (raw)",
            "n": raw_c["n"], "rho": raw_c["rho"], "p": raw_c["p"],
            "partial_rho": raw_c["partial_rho"], "partial_p": raw_c["partial_p"],
        })
        rows.append({
            "family": "ngs_incremental", "pos_group": pos,
            "test": "ngs_athleticism_score vs Sunday Speed (raw)",
            "n": raw_ngs["n"], "rho": raw_ngs["rho"], "p": raw_ngs["p"],
            "partial_rho": raw_ngs["partial_rho"], "partial_p": raw_ngs["partial_p"],
        })
        rows.append({
            "family": "ngs_incremental", "pos_group": pos,
            "test": "c_top vs ngs_athleticism_score",
            "n": raw_cn["n"], "rho": raw_cn["rho"], "p": raw_cn["p"],
            "partial_rho": raw_cn["partial_rho"], "partial_p": raw_cn["partial_p"],
        })
        rows.append({
            "family": "ngs_incremental", "pos_group": pos,
            "test": "c_top vs Sunday Speed | ngs_athleticism_score",
            "n": inc_ngs["n"], "rho": inc_ngs["rho"], "p": inc_ngs["p"],
            "partial_rho": np.nan, "partial_p": np.nan,
        })
        rows.append({
            "family": "ngs_incremental", "pos_group": pos,
            "test": "c_top vs Sunday Speed | ngs_athleticism_score + draft year",
            "n": inc_both["n"], "rho": inc_both["rho"], "p": inc_both["p"],
            "partial_rho": np.nan, "partial_p": np.nan,
        })
        log(
            f"  {pos} n={raw_c['n']}: Combine→SS ρ={raw_c['rho']:+.2f} (p={fmt_p(raw_c['p'])}); "
            f"NGS→SS ρ={raw_ngs['rho']:+.2f} (p={fmt_p(raw_ngs['p'])}); "
            f"Combine vs NGS ρ={raw_cn['rho']:+.2f}; "
            f"Combine→SS after NGS ρ={inc_ngs['rho']:+.2f} (p={fmt_p(inc_ngs['p'])}); "
            f"after NGS+year ρ={inc_both['rho']:+.2f} (p={fmt_p(inc_both['p'])})"
        )
    return pd.DataFrame(rows)


def speed_tax(M: pd.DataFrame) -> pd.DataFrame:
    """Combine speed vs start rate, by position, controlling draft year only (no draft slot).

    Rewritten 11/2026: the original 'beyond draft slot' version is retired.
    Two samples: (a) every player at the position with a 40 and a start rate,
    (b) the official Sunday Speed sample. (a) is the pre-specified speed-tax check;
    (b) is a sensitivity restricted to players we would put on the scouting card.
    """
    rows = []
    log("\n==== CB speed tax: Combine speed vs start rate (draft year controlled) ====")
    for sample_name, mask in (
        ("all_with_40_and_starts", M["c_top"].notna() & M["start_rate"].notna()),
        ("official_sunday_speed_sample", M["ssoe_mph"].notna() & M["start_rate"].notna()),
    ):
        for pos in POS_ORDER:
            d = M[(M["pos_group"] == pos) & mask]
            res = spearman_partial(d["c_top"], d["start_rate"], d["draft_year"])
            perm_p = np.nan
            if pos == "CB" and sample_name == "all_with_40_and_starts" and res["n"] >= 8:
                perm_p = perm_partial_p(d["c_top"], d["start_rate"], d["draft_year"])
            rows.append({
                "family": "speed_tax",
                "sample": sample_name,
                "pos_group": pos,
                "test": "c_top vs start_rate (year-controlled)",
                "n": res["n"],
                "rho": res["rho"],
                "p": res["p"],
                "partial_rho": res["partial_rho"],
                "partial_p": res["partial_p"],
                "permutation_p": perm_p,
            })
            extra = ""
            if np.isfinite(perm_p):
                extra = f"; permutation p={fmt_p(perm_p)} ({N_PERM:,} shuffles)"
            log(
                f"  {pos} [{sample_name}] n={res['n']}: raw ρ={res['rho']:+.2f} (p={fmt_p(res['p'])}); "
                f"partial ρ={res['partial_rho']:+.2f} (p={fmt_p(res['partial_p'])}){extra}"
            )

    tax = pd.DataFrame(rows)
    # Holm within the pre-specified 3-position family (broader sample).
    fam = tax["sample"] == "all_with_40_and_starts"
    pvals = tax.loc[fam, "partial_p"].to_numpy(dtype=float)
    if np.isfinite(pvals).all():
        reject, p_adj, _, _ = multipletests(pvals, method="holm")
        tax.loc[fam, "holm_p"] = p_adj
        tax.loc[fam, "sig_holm_05"] = reject
        log("  Holm (3-position family, broader sample, on partial p):")
        for (_, r), hp, sig in zip(tax.loc[fam].iterrows(), p_adj, reject):
            log(f"    {r['pos_group']}: partial p={fmt_p(r['partial_p'])} → Holm p={fmt_p(hp)}  {'*' if sig else 'n.s.'}")
    log(
        "  Multiple-testing note: the CB result can survive a 3-test Holm correction "
        "for this pre-specified speed-tax family. It does not survive the original "
        "program-wide family (~45 first-pass tests; Bonferroni cutoff ≈ .001), so we "
        "still label it suggestive, not a headline finding."
    )
    return tax


def print_top(board: pd.DataFrame) -> None:
    log(f"\n==== Scouting card: top {TOP_N} and bottom {TOP_N} SSOE by position ====")
    show_cols = [
        "player_name", "college_name",
        "combine_top_speed_mph", "expected_sunday_speed_mph",
        "actual_sunday_speed_mph", "ssoe_mph",
        "n_opportunity_plays", "reliability",
    ]
    for pos in POS_ORDER:
        sub = board[board["position_group"] == pos]
        plot, showed_all = select_top_bottom(sub)
        log(f"\n{POS_LABEL[pos]} (n={len(sub)})")
        if showed_all:
            n_nonneg = int((plot["ssoe_mph"] >= 0).sum())
            log(
                f"  ALL {len(sub)} players shown (sample is smaller than "
                f"{TOP_N} top + {TOP_N} bottom; nobody is listed twice)"
            )
            if n_nonneg:
                log(f"  FASTER than the 40 predicted (n={n_nonneg})")
                log(plot[plot["ssoe_mph"] >= 0][show_cols].to_string(index=False))
            n_neg = int((plot["ssoe_mph"] < 0).sum())
            if n_neg:
                log(f"  SLOWER than the 40 predicted (n={n_neg})")
                log(plot[plot["ssoe_mph"] < 0][show_cols].to_string(index=False))
        else:
            top = plot.head(TOP_N)
            bot = plot.iloc[TOP_N:]
            log(f"  TOP {TOP_N} (faster than the 40 predicted)")
            log(top[show_cols].to_string(index=False))
            log(f"  BOTTOM {TOP_N} (slower than the 40 predicted)")
            log(bot[show_cols].to_string(index=False))


def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    players_path = OUT / "sunday_speed_players.parquet"
    if players_path.exists():
        M = pd.read_parquet(players_path)
    else:
        M = pd.read_csv(OUT / "sunday_speed_players.csv")
    with open(OUT / "translation_slopes.json") as f:
        slopes = {row["pos_group"]: row for row in json.load(f)}

    log(f"Loaded {len(M)} players; official SSOE sample = {int(M['ssoe_mph'].notna().sum())}")
    board = build_leaderboard(M, slopes)
    out_csv = OUT / "ssoe_leaderboard.csv"
    board.to_csv(out_csv, index=False)
    log(f"  wrote {out_csv} ({len(board)} rows)")
    print_top(board)
    fig_path = make_figure(board)

    ngs = ngs_incremental(M)
    tax = speed_tax(M)
    tests = pd.concat([ngs, tax], ignore_index=True, sort=False)
    tests_path = OUT / "ssoe_tests.csv"
    tests.to_csv(tests_path, index=False)
    log(f"\n  wrote {tests_path}")
    log(f"  figure: {fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
