#!/usr/bin/env python3
"""Pre-registered re-examination of two suggestive CB findings.

Finding A: CB "speed tax" (Combine 40 top speed vs start rate beyond draft slot).
Finding B: CB gauntlet drill peak speed vs official Sunday Speed.

Written to the plan in CB_DEEP_DIVE.md §0. Does not modify ssoe.py, dl_burst.py,
METRICS.md, or RESULTS_LOG.md.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/cb_deep_dive.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
FIGS = OUT / "figs"

MPH = 2.0455
UDFA_PICK = 260
N_BOOT = 10_000
N_PERM = 10_000
SEED = 2027
MIN_N = 8

CB_COLOR = "#D55E00"
S_COLOR = "#009E73"
GRAY = "#4C4C4C"
LIGHT = "#888888"

# Round-bucket colors (Okabe-Ito)
DRAFT_COLORS = {
    "Rounds 1–2": "#0072B2",
    "Rounds 3–4": "#E69F00",
    "Rounds 5–7": "#009E73",
    "Undrafted": "#999999",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "NA"
    if p < 1e-4:
        return f"{p:.1e}"
    return f"{p:.3f}"


def draft_bucket(row: pd.Series) -> str:
    if pd.isna(row.get("draft_overall_pick")):
        return "Undrafted"
    rnd = row.get("draft_round")
    if pd.notna(rnd):
        if rnd <= 2:
            return "Rounds 1–2"
        if rnd <= 4:
            return "Rounds 3–4"
        return "Rounds 5–7"
    pick = row.get("pick", UDFA_PICK)
    if pick <= 64:
        return "Rounds 1–2"
    if pick <= 144:
        return "Rounds 3–4"
    if pick < UDFA_PICK:
        return "Rounds 5–7"
    return "Undrafted"


def design_matrix(df: pd.DataFrame, controls: list[str]) -> np.ndarray | None:
    """Intercept plus requested controls. 'log_pick' and 'year' are special."""
    cols = [np.ones(len(df))]
    if "log_pick" in controls:
        cols.append(np.log(df["pick"].astype(float).to_numpy()))
    if "year" in controls:
        year = df["draft_year"].astype(int).to_numpy()
        cols.append((year == 2024).astype(float))
        cols.append((year == 2025).astype(float))
    Z = np.column_stack(cols)
    # Need some variation beyond the intercept.
    if Z.shape[1] > 1 and np.linalg.matrix_rank(Z) < Z.shape[1]:
        # Drop perfectly collinear year dummies if a year is missing.
        keep = [0]
        for j in range(1, Z.shape[1]):
            trial = np.column_stack([Z[:, keep], Z[:, j]])
            if np.linalg.matrix_rank(trial) == trial.shape[1]:
                keep.append(j)
        Z = Z[:, keep]
        if Z.shape[1] == 1:
            return None
    return Z


def residualize(y: np.ndarray, Z: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return y - Z @ beta


def spearman_pair(x: np.ndarray, y: np.ndarray, Z: np.ndarray | None = None) -> tuple[float, float]:
    if Z is not None:
        if Z.shape[0] != len(x) or np.linalg.matrix_rank(Z) < Z.shape[1]:
            return np.nan, np.nan
        x = residualize(x, Z)
        y = residualize(y, Z)
    if len(x) < MIN_N or np.unique(x).size < 2 or np.unique(y).size < 2:
        return np.nan, np.nan
    rho, p = stats.spearmanr(x, y)
    return float(rho), float(p)


def n_covariates(controls: list[str], Z: np.ndarray | None) -> int:
    if Z is None:
        return 0
    return max(0, Z.shape[1] - 1)


def bootstrap_ci(
    x: np.ndarray,
    y: np.ndarray,
    Z: np.ndarray | None,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = len(x)
    rhos = np.empty(n_boot, dtype=float)
    k = 0
    attempts = 0
    # Draw until we have n_boot finite rhos, but cap attempts.
    max_attempts = n_boot * 3
    while k < n_boot and attempts < max_attempts:
        attempts += 1
        idx = rng.integers(0, n, n)
        xx, yy = x[idx], y[idx]
        ZZ = Z[idx] if Z is not None else None
        rho, _ = spearman_pair(xx, yy, ZZ)
        if np.isfinite(rho):
            rhos[k] = rho
            k += 1
    rhos = rhos[:k]
    if k < 100:
        return np.nan, np.nan, rhos
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return float(lo), float(hi), rhos


def permutation_p(
    x: np.ndarray,
    y: np.ndarray,
    Z: np.ndarray | None,
    observed: float,
    n_perm: int = N_PERM,
    seed: int = SEED,
) -> float:
    if not np.isfinite(observed):
        return np.nan
    rng = np.random.default_rng(seed)
    if Z is not None:
        rx = residualize(x, Z)
        ry = residualize(y, Z)
    else:
        rx, ry = x.copy(), y.copy()
    count = 0
    for _ in range(n_perm):
        pr = rng.permutation(rx)
        r, _ = stats.spearmanr(pr, ry)
        if np.isfinite(r) and abs(r) >= abs(observed) - 1e-15:
            count += 1
    return (count + 1) / (n_perm + 1)


def bayes_shrink(rho: float, n: int, k_cov: int = 0, prior_sd: float = 0.5) -> tuple[float, float, float]:
    df = n - 3 - k_cov
    if not np.isfinite(rho) or df <= 0 or abs(rho) >= 1:
        return np.nan, np.nan, np.nan
    z = np.arctanh(np.clip(rho, -0.999999, 0.999999))
    like_var = 1.0 / df
    prior_var = prior_sd ** 2
    post_var = 1.0 / (1.0 / prior_var + 1.0 / like_var)
    post_mean = post_var * (z / like_var)
    half = 1.96 * np.sqrt(post_var)
    return float(np.tanh(post_mean)), float(np.tanh(post_mean - half)), float(np.tanh(post_mean + half))


def influence_table(
    df: pd.DataFrame,
    xcol: str,
    ycol: str,
    controls: list[str],
    full_rho: float,
    full_p: float,
) -> pd.DataFrame:
    rows = []
    n = len(df)
    for i in range(n):
        d = df.drop(df.index[i])
        Z = design_matrix(d, controls) if controls else None
        rho, p = spearman_pair(d[xcol].to_numpy(float), d[ycol].to_numpy(float), Z)
        rows.append(
            {
                "nfl_id": df.iloc[i]["nfl_id"],
                "display_name": df.iloc[i]["display_name"],
                "pos_group": df.iloc[i]["pos_group"],
                "draft_year": int(df.iloc[i]["draft_year"]),
                "pick": float(df.iloc[i]["pick"]),
                "x": float(df.iloc[i][xcol]),
                "y": float(df.iloc[i][ycol]),
                "rho_loo": rho,
                "p_loo": p,
                "delta_rho": (full_rho - rho) if np.isfinite(rho) else np.nan,
                "crosses_05": bool(np.isfinite(p) and np.isfinite(full_p) and ((full_p < 0.05) != (p < 0.05))),
                "big_shift": bool(np.isfinite(rho) and abs(full_rho - rho) > 0.08),
            }
        )
    out = pd.DataFrame(rows)
    out["abs_delta"] = out["delta_rho"].abs()
    return out.sort_values("abs_delta", ascending=False)


def drop_top3_rho(df: pd.DataFrame, xcol: str, ycol: str, controls: list[str], infl: pd.DataFrame) -> dict:
    top = infl.head(3)["nfl_id"].tolist()
    d = df[~df["nfl_id"].isin(top)].copy()
    Z = design_matrix(d, controls) if controls else None
    rho, p = spearman_pair(d[xcol].to_numpy(float), d[ycol].to_numpy(float), Z)
    return {"n": len(d), "rho": rho, "p": p, "dropped": ", ".join(infl.head(3)["display_name"].tolist())}


def run_test(
    name: str,
    finding: str,
    family: str,
    df: pd.DataFrame,
    xcol: str,
    ycol: str,
    controls: list[str],
    description: str,
    seed: int = SEED,
) -> tuple[dict, pd.DataFrame | None]:
    d = df.dropna(subset=[xcol, ycol, "pick", "draft_year"]).copy()
    n = len(d)
    row = {
        "test": name,
        "finding": finding,
        "family": family,
        "description": description,
        "n": n,
        "x": xcol,
        "y": ycol,
        "controls": "+".join(controls) if controls else "none",
        "rho": np.nan,
        "p_analytic": np.nan,
        "ci_lo": np.nan,
        "ci_hi": np.nan,
        "p_perm": np.nan,
        "shrink_rho": np.nan,
        "shrink_lo": np.nan,
        "shrink_hi": np.nan,
        "loo_min": np.nan,
        "loo_max": np.nan,
        "n_flagged": 0,
        "drop3_n": np.nan,
        "drop3_rho": np.nan,
        "drop3_p": np.nan,
        "drop3_names": "",
        "ci_excludes_0": False,
    }
    infl = None
    if n < MIN_N:
        log(f"  {name}: n={n} too small")
        return row, infl

    Z = design_matrix(d, controls) if controls else None
    x = d[xcol].to_numpy(float)
    y = d[ycol].to_numpy(float)
    rho, p = spearman_pair(x, y, Z)
    k_cov = n_covariates(controls, Z)
    lo, hi, _ = bootstrap_ci(x, y, Z, seed=seed)
    p_perm = permutation_p(x, y, Z, rho, seed=seed + 1)
    sh, sh_lo, sh_hi = bayes_shrink(rho, n, k_cov=k_cov)

    infl = influence_table(d, xcol, ycol, controls, rho, p)
    infl.insert(0, "test", name)
    drop3 = drop_top3_rho(d, xcol, ycol, controls, infl)

    row.update(
        {
            "n": n,
            "rho": rho,
            "p_analytic": p,
            "ci_lo": lo,
            "ci_hi": hi,
            "p_perm": p_perm,
            "shrink_rho": sh,
            "shrink_lo": sh_lo,
            "shrink_hi": sh_hi,
            "loo_min": float(infl["rho_loo"].min()) if infl["rho_loo"].notna().any() else np.nan,
            "loo_max": float(infl["rho_loo"].max()) if infl["rho_loo"].notna().any() else np.nan,
            "n_flagged": int((infl["crosses_05"] | infl["big_shift"]).sum()),
            "drop3_n": drop3["n"],
            "drop3_rho": drop3["rho"],
            "drop3_p": drop3["p"],
            "drop3_names": drop3["dropped"],
            "ci_excludes_0": bool(np.isfinite(lo) and np.isfinite(hi) and ((hi < 0) or (lo > 0))),
        }
    )
    log(
        f"  {name}: n={n}  ρ={rho:+.3f}  p={fmt_p(p)}  "
        f"CI [{lo:+.3f}, {hi:+.3f}]  perm p={fmt_p(p_perm)}  "
        f"shrink={sh:+.3f}  LOO [{row['loo_min']:+.3f}, {row['loo_max']:+.3f}]  "
        f"drop3 ρ={drop3['rho']:+.3f} (n={drop3['n']})"
    )
    return row, infl


# ---------------------------------------------------------------------------
# Gauntlet mechanism features
# ---------------------------------------------------------------------------
def _attempt_mechanism(g: pd.DataFrame) -> dict:
    g = g.sort_values("time").copy()
    s = g["s"].to_numpy(dtype=float)
    n = len(g)
    out = {
        "peak_s": np.nan,
        "sustain_s": np.nan,
        "retention": np.nan,
        "reaccel_ratio": np.nan,
        "n_frames": n,
    }
    if n < 8 or not np.isfinite(s).any():
        return out
    i_peak = int(np.nanargmax(s))
    peak = float(s[i_peak])
    out["peak_s"] = peak
    if peak <= 0:
        return out
    cruise = s[s >= 0.8 * peak]
    if cruise.size:
        out["sustain_s"] = float(np.nanmean(cruise))
    after = s[i_peak + 1 :]
    if after.size and np.isfinite(after).any():
        i_val_rel = int(np.nanargmin(after))
        valley = float(after[i_val_rel])
        out["retention"] = valley / peak
        later = after[i_val_rel + 1 :]
        if later.size and np.isfinite(later).any():
            out["reaccel_ratio"] = float(np.nanmax(later)) / peak
    return out


def build_gauntlet_mechanism(ids: list[int]) -> pd.DataFrame:
    log("Loading combine_tracking.csv for DB gauntlet mechanism features...")
    usecols = ["event_id", "nfl_id", "entity_type", "time", "drill_name", "s"]
    chunks = []
    id_set = set(ids)
    for chunk in pd.read_csv(DATA / "combine_tracking.csv", usecols=usecols, chunksize=200_000):
        m = (
            (chunk["entity_type"] == "PLAYER")
            & (chunk["drill_name"] == "GAUNTLET_DRILL")
            & (chunk["nfl_id"].isin(id_set))
        )
        if m.any():
            chunks.append(chunk.loc[m, ["event_id", "nfl_id", "time", "s"]])
    if not chunks:
        log("  no gauntlet frames found")
        return pd.DataFrame(columns=["nfl_id", "gnt_sustain_s", "gnt_retention", "gnt_reaccel_ratio"])
    raw = pd.concat(chunks, ignore_index=True)
    log(f"  {len(raw):,} gauntlet frames, {raw['nfl_id'].nunique()} players")
    feats = (
        raw.groupby("event_id", sort=False)
        .apply(_attempt_mechanism, include_groups=False)
        .apply(pd.Series)
        .reset_index()
    )
    # event_id -> nfl_id (one player per attempt)
    ev = raw.groupby("event_id", sort=False)["nfl_id"].first().reset_index()
    feats = feats.merge(ev, on="event_id", how="left")
    # Use the attempt with the highest peak speed, matching db_gauntlet_max_s.
    feats = feats.sort_values(["nfl_id", "peak_s"], ascending=[True, False])
    best = feats.groupby("nfl_id", sort=False).first().reset_index()
    best = best.rename(
        columns={
            "sustain_s": "gnt_sustain_s",
            "retention": "gnt_retention",
            "reaccel_ratio": "gnt_reaccel_ratio",
        }
    )
    return best.set_index("nfl_id")[["gnt_sustain_s", "gnt_retention", "gnt_reaccel_ratio"]]


# ---------------------------------------------------------------------------
# Samples
# ---------------------------------------------------------------------------
def add_outcomes(M: pd.DataFrame) -> pd.DataFrame:
    M = M.copy()
    games = M["career_games_active"].replace(0, np.nan)
    M["def_snaps_per_game"] = M["career_defensive_snaps"] / games
    # Career defensive snaps residualized on draft-year dummies, among players
    # who have a snaps value (everyone does) — computed later within-sample so
    # the residual is not mixed with WRs. Store the raw snaps column only here.
    M["def_snaps"] = M["career_defensive_snaps"].astype(float)
    M["draft_bucket"] = M.apply(draft_bucket, axis=1)
    return M


def year_adjusted_snaps(df: pd.DataFrame) -> pd.Series:
    """Residual career defensive snaps after draft-year dummies (within this sample)."""
    d = df.copy()
    Z = design_matrix(d, ["year"])
    y = d["def_snaps"].to_numpy(float)
    if Z is None:
        # No year variation: return mean-centered snaps.
        return pd.Series(y - np.nanmean(y), index=d.index)
    return pd.Series(residualize(y, Z), index=d.index)


def subset_cb_a(M: pd.DataFrame, rule: str) -> pd.DataFrame:
    base = M[M["pos_group"] == "CB"].copy()
    if rule == "A1":
        return base[base["c_top"].notna() & base["start_rate"].notna() & (base["n_plays"] >= 100)]
    if rule == "no_floor":
        return base[base["c_top"].notna() & base["start_rate"].notna()]
    if rule == "plays_50":
        return base[base["c_top"].notna() & base["start_rate"].notna() & (base["n_plays"] >= 50)]
    if rule == "plays_200":
        return base[base["c_top"].notna() & base["start_rate"].notna() & (base["n_plays"] >= 200)]
    if rule == "official_ss":
        return base[base["c_top"].notna() & base["start_rate"].notna() & base["sunday_speed"].notna()]
    if rule == "games_8":
        return base[
            base["c_top"].notna()
            & base["start_rate"].notna()
            & (base["n_plays"] >= 100)
            & (base["career_games_active"] >= 8)
        ]
    if rule == "games_16":
        return base[
            base["c_top"].notna()
            & base["start_rate"].notna()
            & (base["n_plays"] >= 100)
            & (base["career_games_active"] >= 16)
        ]
    raise ValueError(rule)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def style_ax(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)


def figure_speed_tax(a1: pd.DataFrame, a1_row: dict, infl: pd.DataFrame, tests: pd.DataFrame) -> Path:
    """Two-panel coach figure: raw scatter (colored by draft capital) + beyond-the-pick residuals."""
    d = a1.copy()
    Z = design_matrix(d, ["log_pick"])
    d["c_top_resid_mph"] = residualize(d["c_top"].to_numpy(float), Z) * MPH
    d["start_resid"] = residualize(d["start_rate"].to_numpy(float), Z)

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.2))

    # Left: raw
    ax = axes[0]
    style_ax(ax)
    for bucket, color in DRAFT_COLORS.items():
        sub = d[d["draft_bucket"] == bucket]
        if sub.empty:
            continue
        ax.scatter(
            sub["c_top_mph"],
            sub["start_rate"],
            c=color,
            s=42,
            alpha=0.85,
            edgecolors="white",
            linewidths=0.4,
            zorder=3,
            label=bucket,
        )
    ax.set_xlabel("Combine 40-yard top speed (mph)")
    ax.set_ylabel("Start rate (games started ÷ games active)")
    ax.set_title("Raw picture: no obvious tax", loc="left", fontweight="bold", fontsize=12)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    raw_rho = float(stats.spearmanr(d["c_top"], d["start_rate"]).statistic)
    ax.text(
        0.04,
        0.04,
        f"Raw ρ = {raw_rho:+.2f}   n = {len(d)}\nFaster corners are also drafted earlier,\nwhich masks anything within a slot.",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=8,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#DDDDDD", alpha=0.92),
    )

    # Right: residual
    ax = axes[1]
    style_ax(ax)
    ax.axhline(0, color=LIGHT, lw=0.8, zorder=1)
    ax.axvline(0, color=LIGHT, lw=0.8, zorder=1)
    ax.scatter(
        d["c_top_resid_mph"],
        d["start_resid"],
        c=CB_COLOR,
        s=42,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.4,
        zorder=3,
    )
    # Trend line on residuals
    if d["c_top_resid_mph"].nunique() >= 2:
        coef = np.polyfit(d["c_top_resid_mph"], d["start_resid"], 1)
        xs = np.linspace(d["c_top_resid_mph"].min(), d["c_top_resid_mph"].max(), 40)
        ax.plot(xs, np.poly1d(coef)(xs), color=CB_COLOR, lw=1.8, zorder=4)
    # Label the three most influential and a couple of extremes.
    # Use a last name only when it uniquely identifies a player in this sample.
    def short_name(full: str, counts: dict) -> str:
        last = full.split()[-1]
        if counts.get(last, 0) > 1:
            first = full.split()[0]
            return f"{first[0]}. {last}"
        return last

    last_counts = d["display_name"].map(lambda s: s.split()[-1]).value_counts().to_dict()
    label_ids = set(infl.head(3)["nfl_id"].tolist())
    extra = pd.concat(
        [
            d.nlargest(1, "c_top_resid_mph"),
            d.nsmallest(1, "c_top_resid_mph"),
            d.nlargest(1, "start_resid"),
        ]
    )
    for _, r in d.iterrows():
        if r["nfl_id"] in label_ids or r["nfl_id"] in set(extra["nfl_id"]):
            ax.annotate(
                short_name(r["display_name"], last_counts),
                (r["c_top_resid_mph"], r["start_resid"]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=7,
                color="#222222",
            )
    rho = a1_row["rho"]
    lo, hi = a1_row["ci_lo"], a1_row["ci_hi"]
    pperm = a1_row["p_perm"]
    ci_txt = f"95% bootstrap CI {lo:+.2f} to {hi:+.2f}"
    ax.set_xlabel("Combine speed after taking out draft slot (mph)")
    ax.set_ylabel("Start rate after taking out draft slot")
    ax.set_title("Same draft slot: faster corners started less", loc="left", fontweight="bold", fontsize=12)
    ax.text(
        0.04,
        0.04,
        f"Beyond-slot ρ = {rho:+.2f}   n = {int(a1_row['n'])}\n{ci_txt}\nPermutation p = {fmt_p(pperm)}",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=8,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#DDDDDD", alpha=0.92),
    )

    # Overall title depends on whether the CI excludes 0 and influence is mild.
    drop3 = a1_row["drop3_rho"]
    fragile = (not a1_row["ci_excludes_0"]) or (np.isfinite(drop3) and np.sign(drop3) != np.sign(rho)) or (
        np.isfinite(drop3) and abs(drop3) < 0.15
    )
    if a1_row["ci_excludes_0"] and not fragile:
        title = "After you account for draft slot, faster corners have started less often"
    elif a1_row["ci_excludes_0"] or (np.isfinite(pperm) and pperm <= 0.05):
        title = "A corner 'speed tax' still shows up — but check how fragile it is"
    else:
        title = "The corner 'speed tax' is not solid enough to trust"
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=14, y=1.03)
    fig.text(
        0.01,
        -0.04,
        "Left: every CB with a tracked 40 and at least 100 game plays (the original sample). "
        "Right: both axes are residuals after accounting for log draft slot (undrafted = pick 260). "
        "Start rate is playing time, not sacks or grades. Labeled names include the three most influential players.",
        fontsize=8,
        color="#555555",
        ha="left",
    )
    fig.tight_layout()
    path = FIGS / "cb_speed_tax.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


def figure_gauntlet(b1: pd.DataFrame, b1_row: dict, infl: pd.DataFrame, tests: pd.DataFrame) -> Path:
    """Scatter of gauntlet peak vs Sunday Speed, plus mechanism / replication bars with CIs."""
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.2), gridspec_kw={"width_ratios": [1.05, 1.15]})

    ax = axes[0]
    style_ax(ax)
    d = b1.copy()
    d["gauntlet_mph"] = d["db_gauntlet_max_s"] * MPH
    ax.scatter(
        d["gauntlet_mph"],
        d["sunday_speed_mph"],
        c=CB_COLOR,
        s=42,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.4,
        zorder=3,
    )
    if d["gauntlet_mph"].nunique() >= 2:
        coef = np.polyfit(d["gauntlet_mph"], d["sunday_speed_mph"], 1)
        xs = np.linspace(d["gauntlet_mph"].min(), d["gauntlet_mph"].max(), 40)
        ax.plot(xs, np.poly1d(coef)(xs), color=CB_COLOR, lw=1.8, zorder=4)
    def short_name(full: str, counts: dict) -> str:
        last = full.split()[-1]
        if counts.get(last, 0) > 1:
            first = full.split()[0]
            return f"{first[0]}. {last}"
        return last

    last_counts = d["display_name"].map(lambda s: s.split()[-1]).value_counts().to_dict()
    label_ids = set(infl.head(3)["nfl_id"].tolist())
    extremes = pd.concat(
        [d.nlargest(1, "gauntlet_mph"), d.nsmallest(1, "gauntlet_mph"), d.nlargest(1, "sunday_speed_mph")]
    )
    seen = set()
    for _, r in d.iterrows():
        if r["nfl_id"] in label_ids or r["nfl_id"] in set(extremes["nfl_id"]):
            lab = short_name(r["display_name"], last_counts)
            if lab in seen:
                lab = r["display_name"]
            seen.add(lab)
            ax.annotate(
                lab,
                (r["gauntlet_mph"], r["sunday_speed_mph"]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=7,
                color="#222222",
            )
    rho, lo, hi, pperm = b1_row["rho"], b1_row["ci_lo"], b1_row["ci_hi"], b1_row["p_perm"]
    ax.set_xlabel("Gauntlet drill peak speed (mph)")
    ax.set_ylabel("Sunday Speed (mph)")
    ax.set_title("Gauntlet peak vs. coverage speed", loc="left", fontweight="bold", fontsize=12)
    ax.text(
        0.04,
        0.04,
        f"ρ = {rho:+.2f}   n = {int(b1_row['n'])}\n95% bootstrap CI {lo:+.2f} to {hi:+.2f}\n"
        f"Permutation p = {fmt_p(pperm)}",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=8,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#DDDDDD", alpha=0.92),
    )

    # Right: pre-registered checks as a forest plot
    ax = axes[1]
    style_ax(ax)
    # Order: primary, controls, increment, mechanism, S replication
    wanted = [
        ("B1_primary", "CB gauntlet peak (primary)"),
        ("B2_pick", "CB, after draft slot"),
        ("B2_pick_year", "CB, after slot + year"),
        ("B2_incremental_40", "CB, after the 40"),
        ("B3_sustain", "CB sustained speed"),
        ("B3_retention", "CB speed through the turn"),
        ("B3_brake", "CB braking into the turn"),
        ("B3_reaccel", "CB re-accel after the turn"),
        ("B3_trans", "CB transition time"),
        ("B4_primary", "Safeties, gauntlet peak"),
    ]
    tmap = tests.set_index("test")
    labels, rhos, los, his, colors, ns = [], [], [], [], [], []
    for key, lab in wanted:
        if key not in tmap.index:
            continue
        r = tmap.loc[key]
        if not np.isfinite(r["rho"]):
            continue
        labels.append(lab)
        rhos.append(float(r["rho"]))
        los.append(float(r["ci_lo"]) if np.isfinite(r["ci_lo"]) else float(r["rho"]))
        his.append(float(r["ci_hi"]) if np.isfinite(r["ci_hi"]) else float(r["rho"]))
        ns.append(int(r["n"]))
        colors.append(CB_COLOR if key.startswith("B1") or key.startswith("B2") or key.startswith("B3") else S_COLOR)
        if key.startswith("B3"):
            colors[-1] = "#7A7A7A"

    y = np.arange(len(labels))[::-1]
    ax.axvline(0, color=LIGHT, lw=0.8, zorder=1)
    for yi, rho_i, lo_i, hi_i, c, n_i, lab in zip(y, rhos, los, his, colors, ns, labels):
        ax.plot([lo_i, hi_i], [yi, yi], color=c, lw=1.6, zorder=3)
        ax.scatter([rho_i], [yi], color=c, s=36, zorder=4, edgecolors="white", linewidths=0.4)
        ax.text(max(hi_i, rho_i) + 0.03, yi, f"{rho_i:+.2f}  n={n_i}", va="center", fontsize=7.5, color="#333333")
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_xlabel("Spearman ρ with Sunday Speed  (95% bootstrap CI)")
    ax.set_xlim(min(los) - 0.15, max(his) + 0.38)
    ax.set_title("Does the signal survive the checks?", loc="left", fontweight="bold", fontsize=12)

    if b1_row["ci_excludes_0"] and abs(b1_row.get("drop3_rho", np.nan) if np.isfinite(b1_row.get("drop3_rho", np.nan)) else 0) >= 0.2:
        title = "The gauntlet has a real lead — now see whether it is more than peak speed"
    elif np.isfinite(pperm) and pperm <= 0.05:
        title = "The gauntlet lead is still only suggestive"
    else:
        title = "The gauntlet lead does not hold up as a Combine test we can trust"
    # Refine after we know increment/mechanism — keep honest either way.
    inc = tmap.loc["B2_incremental_40"] if "B2_incremental_40" in tmap.index else None
    if inc is not None and not bool(inc["ci_excludes_0"]):
        if not b1_row["ci_excludes_0"]:
            title = "The CB gauntlet looks useful until you check the uncertainty"
        else:
            title = "Gauntlet peak speed tracks coverage speed a little — not clearly beyond the 40"

    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=14, y=1.03)
    fig.text(
        0.01,
        -0.04,
        "Sunday Speed is the 90th-percentile play top speed on regular-season man or deep coverage plays that stood. "
        "Gray bars are pre-registered change-of-direction features from the same gauntlet attempt. "
        "Error bars are 95% bootstrap confidence intervals (10,000 player resamples).",
        fontsize=8,
        color="#555555",
        ha="left",
    )
    fig.tight_layout()
    path = FIGS / "cb_gauntlet.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log(f"  wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    FIGS.mkdir(parents=True, exist_ok=True)
    log("Loading out/sunday_speed_players.parquet")
    M = pd.read_parquet(OUT / "sunday_speed_players.parquet")
    M = add_outcomes(M)

    db_ids = M.loc[M["pos_group"].isin(["CB", "S"]), "nfl_id"].tolist()
    mech = build_gauntlet_mechanism(db_ids)
    M = M.merge(mech.reset_index(), on="nfl_id", how="left")

    # Year-adjusted snaps must be computed within each analysis sample; we'll
    # add the column inside those subsets.

    tests = []
    infl_all = []

    log("\n=== Finding A — CB speed tax ===")
    A1 = subset_cb_a(M, "A1")
    log(f"  A1 sample n={len(A1)}")
    row, infl = run_test(
        "A1_primary",
        "A",
        "primary",
        A1,
        "c_top",
        "start_rate",
        ["log_pick"],
        "CB, original F5 sample (≥100 plays): c_top vs start rate, control log pick",
        seed=SEED,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    # A2.1 year control, same sample
    row, infl = run_test(
        "A2_pick_year",
        "A",
        "robustness",
        A1,
        "c_top",
        "start_rate",
        ["log_pick", "year"],
        "CB, same sample: c_top vs start rate, control log pick + draft year",
        seed=SEED + 10,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    # A2.2 alternative outcomes
    A1_spg = A1.dropna(subset=["def_snaps_per_game"]).copy()
    row, infl = run_test(
        "A2_snaps_per_game",
        "A",
        "robustness",
        A1_spg,
        "c_top",
        "def_snaps_per_game",
        ["log_pick", "year"],
        "CB, same sample: c_top vs defensive snaps/game, control log pick + year",
        seed=SEED + 20,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    A1_adj = A1.copy()
    A1_adj["def_snaps_year_adj"] = year_adjusted_snaps(A1_adj)
    row, infl = run_test(
        "A2_snaps_year_adj",
        "A",
        "robustness",
        A1_adj,
        "c_top",
        "def_snaps_year_adj",
        ["log_pick"],
        "CB, same sample: c_top vs career def snaps residualized on draft year, then log pick",
        seed=SEED + 30,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    # A2.3 sample cuts (start rate, log pick only)
    cuts = [
        ("A2_no_floor", "no_floor", "CB, no play-count floor: c_top vs start rate, log pick"),
        ("A2_plays_50", "plays_50", "CB, ≥50 tracked plays: c_top vs start rate, log pick"),
        ("A2_plays_200", "plays_200", "CB, ≥200 tracked plays: c_top vs start rate, log pick"),
        ("A2_official_ss", "official_ss", "CB, official Sunday Speed sample: c_top vs start rate, log pick"),
        ("A2_games_8", "games_8", "CB, ≥100 plays and ≥8 games active: c_top vs start rate, log pick"),
        ("A2_games_16", "games_16", "CB, ≥100 plays and ≥16 games active: c_top vs start rate, log pick"),
    ]
    for name, rule, desc in cuts:
        d = subset_cb_a(M, rule)
        row, infl = run_test(name, "A", "robustness", d, "c_top", "start_rate", ["log_pick"], desc, seed=SEED + 40)
        tests.append(row)
        if infl is not None:
            infl_all.append(infl)

    # A3 safeties
    log("\n=== Finding A replication on safeties ===")
    S_A = M[
        (M["pos_group"] == "S")
        & M["c_top"].notna()
        & M["start_rate"].notna()
        & (M["n_plays"] >= 100)
    ].copy()
    row, infl = run_test(
        "A3_primary",
        "A",
        "replication",
        S_A,
        "c_top",
        "start_rate",
        ["log_pick"],
        "S, ≥100 plays: c_top vs start rate, control log pick",
        seed=SEED + 80,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)
    row, infl = run_test(
        "A3_pick_year",
        "A",
        "replication",
        S_A,
        "c_top",
        "start_rate",
        ["log_pick", "year"],
        "S, ≥100 plays: c_top vs start rate, control log pick + draft year",
        seed=SEED + 90,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    log("\n=== Finding B — CB gauntlet ===")
    B1 = M[(M["pos_group"] == "CB") & M["db_gauntlet_max_s"].notna() & M["sunday_speed"].notna()].copy()
    log(f"  B1 sample n={len(B1)}")
    row, infl = run_test(
        "B1_primary",
        "B",
        "primary",
        B1,
        "db_gauntlet_max_s",
        "sunday_speed",
        [],
        "CB official SS sample: gauntlet peak vs Sunday Speed",
        seed=SEED + 100,
    )
    tests.append(row)
    b1_infl = infl
    if infl is not None:
        infl_all.append(infl)

    row, infl = run_test(
        "B2_pick",
        "B",
        "robustness",
        B1,
        "db_gauntlet_max_s",
        "sunday_speed",
        ["log_pick"],
        "CB: gauntlet peak vs Sunday Speed, control log pick",
        seed=SEED + 110,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    row, infl = run_test(
        "B2_pick_year",
        "B",
        "robustness",
        B1,
        "db_gauntlet_max_s",
        "sunday_speed",
        ["log_pick", "year"],
        "CB: gauntlet peak vs Sunday Speed, control log pick + draft year",
        seed=SEED + 120,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    # Incremental over the 40: residualize both on c_top, then Spearman (no other controls).
    B_inc = B1.dropna(subset=["c_top"]).copy()
    Z40 = design_matrix(B_inc, [])  # unused
    # residualize on c_top only
    Zc = np.column_stack([np.ones(len(B_inc)), B_inc["c_top"].to_numpy(float)])
    B_inc = B_inc.copy()
    B_inc["gnt_resid_40"] = residualize(B_inc["db_gauntlet_max_s"].to_numpy(float), Zc)
    B_inc["ss_resid_40"] = residualize(B_inc["sunday_speed"].to_numpy(float), Zc)
    row, infl = run_test(
        "B2_incremental_40",
        "B",
        "robustness",
        B_inc,
        "gnt_resid_40",
        "ss_resid_40",
        [],
        "CB: gauntlet vs Sunday Speed after residualizing both on c_top",
        seed=SEED + 130,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    log("\n=== Finding B mechanism ===")
    mech_specs = [
        ("B3_sustain", "gnt_sustain_s", "CB: gauntlet sustained speed (mean at ≥80% of peak) vs Sunday Speed"),
        ("B3_retention", "gnt_retention", "CB: gauntlet speed retention through the turn vs Sunday Speed"),
        ("B3_brake", "db_gauntlet_brake", "CB: gauntlet peak braking vs Sunday Speed"),
        ("B3_reaccel", "gnt_reaccel_ratio", "CB: gauntlet re-accel ratio (post-valley max / peak) vs Sunday Speed"),
        ("B3_trans", "db_gauntlet_trans", "CB: gauntlet transition time vs Sunday Speed"),
    ]
    for name, col, desc in mech_specs:
        d = B1.dropna(subset=[col, "sunday_speed"]).copy()
        row, infl = run_test(name, "B", "mechanism", d, col, "sunday_speed", [], desc, seed=SEED + 140)
        tests.append(row)
        if infl is not None:
            infl_all.append(infl)

    log("\n=== Finding B replication on safeties ===")
    S_B = M[(M["pos_group"] == "S") & M["db_gauntlet_max_s"].notna() & M["sunday_speed"].notna()].copy()
    row, infl = run_test(
        "B4_primary",
        "B",
        "replication",
        S_B,
        "db_gauntlet_max_s",
        "sunday_speed",
        [],
        "S official SS sample: gauntlet peak vs Sunday Speed",
        seed=SEED + 180,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)
    row, infl = run_test(
        "B4_pick",
        "B",
        "replication",
        S_B,
        "db_gauntlet_max_s",
        "sunday_speed",
        ["log_pick"],
        "S: gauntlet peak vs Sunday Speed, control log pick",
        seed=SEED + 190,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)
    row, infl = run_test(
        "B4_pick_year",
        "B",
        "replication",
        S_B,
        "db_gauntlet_max_s",
        "sunday_speed",
        ["log_pick", "year"],
        "S: gauntlet peak vs Sunday Speed, control log pick + draft year",
        seed=SEED + 200,
    )
    tests.append(row)
    if infl is not None:
        infl_all.append(infl)

    T = pd.DataFrame(tests)
    T_path = OUT / "cb_deep_dive_tests.csv"
    T.to_csv(T_path, index=False)
    log(f"\nWrote {T_path}")

    I = pd.concat(infl_all, ignore_index=True) if infl_all else pd.DataFrame()
    I_path = OUT / "cb_deep_dive_influence.csv"
    I.to_csv(I_path, index=False)
    log(f"Wrote {I_path}")

    # Figures
    log("\n=== Figures ===")
    a1_row = T.set_index("test").loc["A1_primary"].to_dict()
    a1_infl = I[I["test"] == "A1_primary"].copy()
    figure_speed_tax(A1, a1_row, a1_infl, T)

    b1_row = T.set_index("test").loc["B1_primary"].to_dict()
    if b1_infl is None:
        b1_infl = I[I["test"] == "B1_primary"].copy()
    figure_gauntlet(B1, b1_row, b1_infl, T)

    # Compact JSON of primary rows for the writeup pass
    summary = T.to_dict(orient="records")
    (OUT / "cb_deep_dive_tests.json").write_text(json.dumps(summary, indent=2, default=str))
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
