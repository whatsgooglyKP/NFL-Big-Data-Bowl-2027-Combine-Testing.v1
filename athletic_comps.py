#!/usr/bin/env python3
"""K-nearest-neighbor athletic comps for 2023–2025 rookies.

Historical Combine data is the public nflverse / Pro-Football-Reference
release (seasons 2000–2022), not Kaggle data. Career labels (weighted
Approximate Value, Pro Bowls, All-Pros) come from the nflverse draft_picks
release. See external/ATTRIBUTION.md.

The 10-yard split is not in the nflverse Combine file, so the distance
uses official 40, vertical, broad jump, 3-cone, short shuttle, height,
and weight. Distance is a nan-aware RMS of within-position z-scores on
the tests two players both ran; a pair needs at least three shared tests (so a player who only ran the 40, but was measured for height and weight, still gets comps).

RB is not modeled anywhere in this repo (n = 1). Sione Vaki still gets
historical comps, clearly labeled as an anecdote.

Usage:
    /workspace/bdb2027/.venv/bin/python /workspace/bdb2027/athletic_comps.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import warnings
from scipy import stats
warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path("/workspace/bdb2027")
DATA = ROOT / "data"
OUT = ROOT / "out"
EXT = ROOT / "external"

K = 5
MIN_SHARED = 3
HIST_YEARS = (2000, 2022)
# Career-runway window for percentile labels: drafted 2000–2018 so they
# had at least several NFL seasons by the 2026 draft_picks snapshot.
RUNWAY_YEARS = (2000, 2018)
EARLY_CAREER_FROM = 2019

# Features available on both our Combine file and nflverse/PFR.
# 10-yard split is intentionally absent — it is not in the public file.
FEATS = ["forty", "vertical", "broad_jump", "cone", "shuttle", "height_in", "weight"]
FEAT_LABELS = {
    "forty": "Official 40",
    "vertical": "Vertical",
    "broad_jump": "Broad jump",
    "cone": "3-cone",
    "shuttle": "Short shuttle",
    "height_in": "Height",
    "weight": "Weight",
}

POS_GROUPS = ["WR", "TE", "CB", "S", "Edge", "Interior", "RB"]
# RB is anecdote-only.
MODELED_GROUPS = ["WR", "TE", "CB", "S", "Edge", "Interior"]

# Combine-file (PFR) position → our group.
COMBINE_POS_MAP = {
    "WR": "WR",
    "TE": "TE",
    "CB": "CB", "CB/WR": "CB",
    "S": "S", "SAF": "S", "FS": "S", "SS": "S",
    "DE": "Edge", "EDGE": "Edge", "OLB": "Edge",
    "DT": "Interior", "NT": "Interior",
    "RB": "RB",
    # Ambiguous groups are left unmapped (LB, DL, DB, ILB) so they
    # do not leak into Edge/Interior/S/CB distances.
}


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_ht(x) -> float:
    """PFR height like '6-4' or '5-10' → inches."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float)):
        return float(x) if np.isfinite(x) else np.nan
    s = str(x).strip()
    if not s or s in {"nan", "None"}:
        return np.nan
    if "-" in s:
        parts = s.split("-")
        try:
            return float(parts[0]) * 12.0 + float(parts[1])
        except ValueError:
            return np.nan
    try:
        v = float(s)
        # already inches if > 20, feet if small
        return v * 12.0 if v < 10 else v
    except ValueError:
        return np.nan


def year_residual(y: pd.Series, year: pd.Series) -> np.ndarray:
    """Residual after a linear draft-year fit. No draft slot / pick / round (Kevin's rule, 11/2026)."""
    d = pd.DataFrame({"y": y, "year": year}).dropna()
    resid = pd.Series(np.nan, index=y.index, dtype=float)
    if len(d) < 8 or d["year"].nunique() < 2:
        return resid.to_numpy()
    X = np.column_stack([np.ones(len(d)), (d["year"] - d["year"].min()).astype(float)])
    coef, *_ = np.linalg.lstsq(X, d["y"].to_numpy(dtype=float), rcond=None)
    resid.loc[d.index] = d["y"].to_numpy(dtype=float) - X @ coef
    return resid.to_numpy()


def load_historical() -> pd.DataFrame:
    comb = pd.read_csv(EXT / "combine.csv")
    picks = pd.read_csv(EXT / "draft_picks.csv")
    comb["pos_group"] = comb["pos"].map(COMBINE_POS_MAP)
    comb["height_in"] = comb["ht"].map(parse_ht)
    comb["weight"] = pd.to_numeric(comb["wt"], errors="coerce")
    for c in ["forty", "vertical", "broad_jump", "cone", "shuttle"]:
        comb[c] = pd.to_numeric(comb[c], errors="coerce")
    comb["hist_year"] = pd.to_numeric(comb["season"], errors="coerce")
    comb["hist_name"] = comb["player_name"]
    comb["hist_school"] = comb["school"]
    comb["hist_pos"] = comb["pos"]

    # Career outcomes via PFR id. w_av is filled; car_av is empty in this snapshot.
    keep_p = picks.rename(columns={
        "pfr_player_id": "pfr_id",
        "pfr_player_name": "pfr_name",
        "season": "draft_season",
    })[[
        "pfr_id", "pfr_name", "draft_season", "team",
        "hof", "allpro", "probowls", "seasons_started", "w_av", "games",
        "to", "position", "college",
    ]].copy()
    keep_p = keep_p[keep_p["pfr_id"].notna()].drop_duplicates("pfr_id")
    H = comb.merge(keep_p, on="pfr_id", how="left")
    H["career_w_av"] = pd.to_numeric(H["w_av"], errors="coerce")
    H["career_allpro"] = pd.to_numeric(H["allpro"], errors="coerce").fillna(0)
    H["career_probowls"] = pd.to_numeric(H["probowls"], errors="coerce").fillna(0)
    H["career_games"] = pd.to_numeric(H["games"], errors="coerce")
    H["career_started"] = pd.to_numeric(H["seasons_started"], errors="coerce")
    H["career_to"] = pd.to_numeric(H["to"], errors="coerce")
    H["has_career_row"] = H["w_av"].notna() | H["games"].notna()
    H["is_hof"] = H["hof"].isin([True, "TRUE", "True", "true"])
    return H


def career_thresholds(H: pd.DataFrame) -> pd.DataFrame:
    """Position-group w_av median and 90th percentile on 2000–2018 draftees."""
    rows = []
    runway = H[H["hist_year"].between(*RUNWAY_YEARS) & H["career_w_av"].notna() & H["pos_group"].notna()]
    for g, sub in runway.groupby("pos_group"):
        rows.append({
            "pos_group": g,
            "n_runway": int(len(sub)),
            "wav_p50": float(sub["career_w_av"].median()),
            "wav_p90": float(sub["career_w_av"].quantile(0.90)),
            "wav_p75": float(sub["career_w_av"].quantile(0.75)),
        })
    T = pd.DataFrame(rows)
    log("Career w_av thresholds (2000–2018 draftees with a Combine and a w_av):")
    log(T.to_string(index=False))
    return T


def label_career(row: pd.Series, thresh: pd.DataFrame) -> tuple[str, str]:
    """Return (label, flag). flag is 'early_career', 'no_record', or ''."""
    g = row.get("pos_group")
    t = thresh[thresh["pos_group"] == g]
    p50 = float(t["wav_p50"].iloc[0]) if len(t) else 8.0
    p90 = float(t["wav_p90"].iloc[0]) if len(t) else 50.0
    year = row.get("hist_year")
    early = pd.notna(year) and year >= EARLY_CAREER_FROM
    wav = row.get("career_w_av")
    ap = row.get("career_allpro") or 0
    pb = row.get("career_probowls") or 0
    started = row.get("career_started") or 0
    hof = bool(row.get("is_hof"))
    has = bool(row.get("has_career_row"))

    if hof or ap >= 1 or pb >= 3 or (pd.notna(wav) and wav >= p90):
        lab = "star"
    elif pd.notna(wav) and (wav >= p50 or pb >= 1 or started >= 3):
        lab = "solid"
    elif has:
        lab = "journeyman"
    else:
        lab = "no_record"

    flag = ""
    if lab == "no_record":
        flag = "no_record"
    elif early:
        flag = "early_career"
    return lab, flag


def load_rookies() -> pd.DataFrame:
    """Every 2023–2025 rookie in WR, TE, CB, S, Edge, Interior, and the one RB."""
    players = pd.read_csv(DATA / "players.csv")
    comb = pd.read_csv(DATA / "combine_results.csv")
    M = players.merge(comb, on=["nfl_id", "draft_year"], how="left")

    def group(row):
        p = row["nfl_position"]
        if p == "WR":
            return "WR"
        if p == "TE":
            return "TE"
        if p == "CB":
            return "CB"
        if p in {"FS", "SS"}:
            return "S"
        if p in {"DE", "OLB"}:
            return "Edge"
        if p in {"DT", "NT"}:
            return "Interior"
        if p == "RB":
            return "RB"
        return None

    M["pos_group"] = M.apply(group, axis=1)
    M = M[M["pos_group"].isin(POS_GROUPS)].copy()
    M["forty"] = pd.to_numeric(M["forty"], errors="coerce")
    M["vertical"] = pd.to_numeric(M["vertical"], errors="coerce")
    M["broad_jump"] = pd.to_numeric(M["broad_jump"], errors="coerce")
    M["cone"] = pd.to_numeric(M["three_cone"], errors="coerce")
    M["shuttle"] = pd.to_numeric(M["short_shuttle"], errors="coerce")
    M["height_in"] = pd.to_numeric(M["combine_height"], errors="coerce")
    M["weight"] = pd.to_numeric(M["combine_weight"], errors="coerce")
    M["ten_yd_split"] = pd.to_numeric(M["ten_yd_split"], errors="coerce")
    M["rookie_name"] = M["display_name"]
    M["rookie_year"] = M["draft_year"]
    M["anecdote_only"] = M["pos_group"].eq("RB")

    # Gameplay outcomes, where we have them.
    gs_path = OUT / "multi_test_players.csv"
    if gs_path.exists():
        gs = pd.read_csv(gs_path)
        keep = ["nfl_id", "yards_per_route", "tackle_rate", "n_routes", "n_def_snaps",
                "success", "complete_case", "median_outcome"]
        keep = [c for c in keep if c in gs.columns]
        M = M.merge(gs[keep], on="nfl_id", how="left")
    dl_path = OUT / "dl_burst_players.csv"
    if dl_path.exists():
        dl = pd.read_csv(dl_path)
        dkeep = ["nfl_id", "pressure_rate", "sack_rate", "n_rush_plays", "subtype"]
        dkeep = [c for c in dkeep if c in dl.columns]
        M = M.merge(dl[dkeep], on="nfl_id", how="left")

    # A single continuous gameplay outcome per group, for the KNN check.
    def outcome(row):
        g = row["pos_group"]
        if g in {"WR", "TE"}:
            n = row.get("n_routes")
            y = row.get("yards_per_route")
            if pd.notna(n) and n >= 20 and pd.notna(y):
                return y, "yards_per_route"
        if g in {"CB", "S"}:
            n = row.get("n_def_snaps")
            y = row.get("tackle_rate")
            if pd.notna(n) and n >= 50 and pd.notna(y):
                return y, "tackle_rate"
        if g in {"Edge", "Interior"}:
            n = row.get("n_rush_plays")
            y = row.get("pressure_rate")
            if pd.notna(n) and n >= 20 and pd.notna(y):
                return y, "pressure_rate"
        return np.nan, ""

    out = M.apply(outcome, axis=1, result_type="expand")
    M["gameplay"] = out[0]
    M["gameplay_metric"] = out[1]
    return M


def zscore_tables(H: pd.DataFrame) -> dict:
    """Mean and SD of each feature within position, on 2000–2022 historical players."""
    hist = H[H["hist_year"].between(*HIST_YEARS) & H["pos_group"].notna()]
    tables = {}
    for g, sub in hist.groupby("pos_group"):
        stats_ = {}
        for f in FEATS:
            s = sub[f].dropna()
            mu = float(s.mean()) if len(s) >= 10 else np.nan
            sd = float(s.std(ddof=1)) if len(s) >= 10 else np.nan
            if pd.notna(sd) and sd < 1e-8:
                sd = np.nan
            stats_[f] = (mu, sd, int(len(s)))
        tables[g] = stats_
        pretty = ", ".join(
            f"{f} n={n} μ={mu:.2f} σ={sd:.2f}" if pd.notna(sd) else f"{f} n={n}"
            for f, (mu, sd, n) in stats_.items()
        )
        log(f"  z-score {g} (n={len(sub)}): {pretty}")
    return tables


def apply_z(df: pd.DataFrame, tables: dict, group_col: str = "pos_group") -> pd.DataFrame:
    out = df.copy()
    for f in FEATS:
        z = np.full(len(out), np.nan)
        for g, st in tables.items():
            mu, sd, _n = st[f]
            if not np.isfinite(sd):
                continue
            mask = out[group_col] == g
            z[mask.to_numpy()] = (out.loc[mask, f] - mu) / sd
        out[f"z_{f}"] = z
    return out


def pairwise_knn(rookies: pd.DataFrame, hist: pd.DataFrame, thresh: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each rookie, the K nearest historical players at the same position."""
    zcols = [f"z_{f}" for f in FEATS]
    long_rows = []
    sum_rows = []
    for g in POS_GROUPS:
        R = rookies[rookies["pos_group"] == g].reset_index(drop=True)
        H = hist[(hist["pos_group"] == g) & hist["hist_year"].between(*HIST_YEARS)].reset_index(drop=True)
        if len(R) == 0 or len(H) == 0:
            log(f"  {g}: no rookies or no historical pool")
            continue
        ZR = R[zcols].to_numpy(dtype=float)
        ZH = H[zcols].to_numpy(dtype=float)
        log(f"  {g}: {len(R)} rookies vs {len(H)} historical")
        for i in range(len(R)):
            zr = ZR[i]
            # shared-test mask for every historical player
            both = np.isfinite(zr)[None, :] & np.isfinite(ZH)
            n_shared = both.sum(axis=1)
            # RMS of z-diffs on shared tests
            diff = np.where(both, zr[None, :] - ZH, np.nan)
            with np.errstate(invalid="ignore"):
                dist = np.sqrt(np.nanmean(diff ** 2, axis=1))
            # Prefer neighbors with 4+ shared tests. If a rookie only ran a
            # few drills (e.g. 40 + height + weight), fall back to 3 so they
            # still get a (flagged) thin comparison. Players who have 4+ of
            # their own tests are not matched to a 3-test neighbor when 4-test
            # neighbors exist — otherwise missing jumps make a pair look closer.
            pref = (n_shared >= max(MIN_SHARED + 1, 4)) & np.isfinite(dist)
            # MIN_SHARED is 3; preferred threshold is 4.
            pref = (n_shared >= 4) & np.isfinite(dist)
            fallback = (n_shared >= MIN_SHARED) & np.isfinite(dist) & ~pref
            order4 = np.argsort(np.where(pref, dist, np.inf))
            comps = [int(j) for j in order4 if pref[j]][:K]
            if len(comps) < K:
                order3 = np.argsort(np.where(fallback, dist, np.inf))
                for j in order3:
                    if not fallback[j]:
                        break
                    comps.append(int(j))
                    if len(comps) >= K:
                        break
            r = R.iloc[i]
            if not comps:
                sum_rows.append({
                    "nfl_id": r["nfl_id"],
                    "display_name": r["rookie_name"],
                    "pos_group": g,
                    "nfl_position": r["nfl_position"],
                    "draft_year": r["rookie_year"],
                    "anecdote_only": bool(r["anecdote_only"]),
                    "n_comps": 0,
                    "headline": "too few Combine tests for a historical comp",
                    "comp_names": "",
                    "note": f"Fewer than {MIN_SHARED} shared Combine tests (40, jumps, agility, height, weight) with any historical player at the position.",
                })
                continue
            labels, flags, wavs, dists = [], [], [], []
            for rank, j in enumerate(comps, start=1):
                h = H.iloc[j]
                long_rows.append({
                    "nfl_id": r["nfl_id"],
                    "display_name": r["rookie_name"],
                    "pos_group": g,
                    "nfl_position": r["nfl_position"],
                    "draft_year": int(r["rookie_year"]),
                    "anecdote_only": bool(r["anecdote_only"]),
                    "rookie_forty": r["forty"],
                    "rookie_vertical": r["vertical"],
                    "rookie_broad": r["broad_jump"],
                    "rookie_cone": r["cone"],
                    "rookie_shuttle": r["shuttle"],
                    "rookie_height": r["height_in"],
                    "rookie_weight": r["weight"],
                    "rookie_ten_yd": r.get("ten_yd_split", np.nan),
                    "gameplay": r.get("gameplay", np.nan),
                    "gameplay_metric": r.get("gameplay_metric", ""),
                    "comp_rank": rank,
                    "comp_name": h["hist_name"],
                    "comp_year": int(h["hist_year"]) if pd.notna(h["hist_year"]) else np.nan,
                    "comp_pos": h["hist_pos"],
                    "comp_school": h["hist_school"],
                    "comp_forty": h["forty"],
                    "comp_vertical": h["vertical"],
                    "comp_broad": h["broad_jump"],
                    "comp_cone": h["cone"],
                    "comp_shuttle": h["shuttle"],
                    "comp_height": h["height_in"],
                    "comp_weight": h["weight"],
                    "distance": float(dist[j]),
                    "n_shared": int(n_shared[j]),
                    "thin_comparison": bool(n_shared[j] < 4),
                    "comp_w_av": h["career_w_av"],
                    "comp_allpro": h["career_allpro"],
                    "comp_probowls": h["career_probowls"],
                    "comp_games": h["career_games"],
                    "comp_started": h["career_started"],
                    "comp_to": h["career_to"],
                    "comp_hof": bool(h["is_hof"]),
                    "comp_label": h["career_label"],
                    "comp_flag": h["career_flag"],
                })
                labels.append(h["career_label"])
                flags.append(h["career_flag"])
                wavs.append(h["career_w_av"])
                dists.append(float(dist[j]))
            wavs_a = np.asarray(wavs, dtype=float)
            n_star = sum(x == "star" for x in labels)
            n_solid = sum(x == "solid" for x in labels)
            n_jour = sum(x == "journeyman" for x in labels)
            n_none = sum(x == "no_record" for x in labels)
            n_early = sum(x == "early_career" for x in flags)
            trow = thresh[thresh["pos_group"] == g]
            p50 = float(trow["wav_p50"].iloc[0]) if len(trow) else np.nan
            p90 = float(trow["wav_p90"].iloc[0]) if len(trow) else np.nan
            mean_wav = float(np.nanmean(wavs_a)) if np.isfinite(wavs_a).any() else np.nan
            headline = headline_phrase(n_star, n_solid, n_jour, n_none, n_early, len(comps),
                                       mean_wav=mean_wav, p50=p50, p90=p90)
            sum_rows.append({
                "nfl_id": r["nfl_id"],
                "display_name": r["rookie_name"],
                "pos_group": g,
                "nfl_position": r["nfl_position"],
                "draft_year": int(r["rookie_year"]),
                "anecdote_only": bool(r["anecdote_only"]),
                "n_comps": len(comps),
                "mean_distance": float(np.mean(dists)),
                "knn_mean_w_av": float(np.nanmean(wavs_a)) if np.isfinite(wavs_a).any() else np.nan,
                "knn_median_w_av": float(np.nanmedian(wavs_a)) if np.isfinite(wavs_a).any() else np.nan,
                "knn_n_with_av": int(np.isfinite(wavs_a).sum()),
                "n_star": n_star,
                "n_solid": n_solid,
                "n_journeyman": n_jour,
                "n_no_record": n_none,
                "n_early_career": n_early,
                "star_frac": n_star / max(len(comps) - n_none, 1),
                "headline": headline,
                "comp_names": "; ".join(
                    f"{H.iloc[j]['hist_name']} ({int(H.iloc[j]['hist_year'])}, {H.iloc[j]['career_label']})"
                    for j in comps
                ),
                "gameplay": r.get("gameplay", np.nan),
                "gameplay_metric": r.get("gameplay_metric", ""),
                "n_shared_typical": int(np.median([n_shared[j] for j in comps])),
                "n_thin_comps": int(sum(n_shared[j] < 4 for j in comps)),
            })
    return pd.DataFrame(long_rows), pd.DataFrame(sum_rows)


def headline_phrase(n_star, n_solid, n_jour, n_none, n_early, n,
                    mean_wav=None, p50=None, p90=None) -> str:
    labeled = n - n_none
    if labeled <= 0:
        return "no career records among comps"
    # Prefer mean career AV, when we have it, so a group with two solid
    # starters and three lower-AV players is not automatically "journeyman."
    if n_star >= 2:
        base = "tests like a star"
    elif mean_wav is not None and p90 is not None and np.isfinite(mean_wav) and mean_wav >= p90:
        base = "tests like a star"
    elif mean_wav is not None and p50 is not None and np.isfinite(mean_wav) and mean_wav >= p50:
        base = "tests like a solid starter"
    elif n_jour >= 3 and n_star == 0 and (
        mean_wav is None or not np.isfinite(mean_wav) or p50 is None or mean_wav < p50
    ):
        base = "tests like a journeyman"
    else:
        base = "mixed comps"
    extra = []
    if n_early:
        extra.append(f"{n_early} early-career (AV still accumulating)")
    if n_none:
        extra.append(f"{n_none} with no career record")
    if extra:
        return base + " — " + "; ".join(extra)
    return base


def knn_vs_gameplay(summary: pd.DataFrame) -> pd.DataFrame:
    """Does a KNN prediction from comps' careers line up with our rookies' gameplay?"""
    rows = []
    # Modeled groups only; RB is excluded from this test.
    S = summary[(~summary["anecdote_only"]) & summary["gameplay"].notna() & summary["knn_mean_w_av"].notna()].copy()
    groups = [(g, S[S["pos_group"] == g]) for g in MODELED_GROUPS]
    # Do not pool WR/TE yards, CB/S tackle rate, and DL pressure — different outcomes.
    for name, d in groups:
        d = d.dropna(subset=["gameplay", "knn_mean_w_av", "draft_year"]).copy()
        if len(d) < 8:
            rows.append({"pos_group": name, "n": int(len(d)), "note": "too few for a correlation"})
            continue
        rho, p = stats.spearmanr(d["knn_mean_w_av"], d["gameplay"])
        # year-controlled residuals
        ry = year_residual(d["gameplay"], d["draft_year"])
        rx = year_residual(d["knn_mean_w_av"], d["draft_year"])
        ok = np.isfinite(rx) & np.isfinite(ry)
        if ok.sum() >= 8 and np.unique(rx[ok]).size >= 2 and np.unique(ry[ok]).size >= 2:
            pr, pp = stats.spearmanr(rx[ok], ry[ok])
        else:
            pr, pp = np.nan, np.nan
        # also star_frac vs gameplay
        d2 = d.dropna(subset=["star_frac"])
        if len(d2) >= 8 and d2["star_frac"].nunique() >= 2:
            rs, ps = stats.spearmanr(d2["star_frac"], d2["gameplay"])
        else:
            rs, ps = np.nan, np.nan
        rows.append({
            "pos_group": name,
            "n": int(len(d)),
            "gameplay_metric": ",".join(sorted(d["gameplay_metric"].dropna().unique())),
            "rho_wav": float(rho),
            "p_wav": float(p),
            "partial_year_rho": float(pr) if np.isfinite(pr) else np.nan,
            "partial_year_p": float(pp) if np.isfinite(pp) else np.nan,
            "rho_star_frac": float(rs) if np.isfinite(rs) else np.nan,
            "p_star_frac": float(ps) if np.isfinite(ps) else np.nan,
            "mean_knn_wav": float(d["knn_mean_w_av"].mean()),
        })
        log(f"  {name} n={len(d)}: raw ρ(knn w_av, gameplay)={rho:.3f} p={p:.3f}; "
            f"year partial ρ={pr if np.isfinite(pr) else float('nan'):.3f} "
            f"p={pp if np.isfinite(pp) else float('nan'):.3f}")
    out = pd.DataFrame(rows)
    if "partial_year_p" in out.columns and out["partial_year_p"].notna().sum() >= 2:
        from statsmodels.stats.multitest import multipletests
        ok = out["partial_year_p"].notna()
        _rej, p_adj, _, _ = multipletests(out.loc[ok, "partial_year_p"], alpha=0.05, method="holm")
        out.loc[ok, "holm_p"] = p_adj
        out.loc[ok, "sig_holm_05"] = _rej
        out.loc[~ok, "holm_p"] = np.nan
        out.loc[~ok, "sig_holm_05"] = False
    return out


HIGHLIGHTS = [
    "Chop Robinson",
    "Cedric Johnson",
    "Luther Burden",
    "Brian Thomas",
    "Sione Vaki",
    "Jared Verse",
    "Will Anderson",
    "Ladd McConkey",
    "Brian Branch",
]


def print_highlights(summary: pd.DataFrame, long: pd.DataFrame) -> None:
    log("\n==== Headline athletic comps ====")
    # Always print requested names; then a couple of extra gems if present.
    names = list(HIGHLIGHTS)
    for name in names:
        s = summary[summary["display_name"] == name]
        if s.empty:
            # fuzzy
            s = summary[summary["display_name"].str.contains(name.split()[-1], case=False, na=False)
                        & summary["display_name"].str.contains(name.split()[0], case=False, na=False)]
        if s.empty:
            log(f"  {name}: not in the rookie file")
            continue
        r = s.iloc[0]
        tag = " [ANECDOTE — RB excluded from models]" if r["anecdote_only"] else ""
        log(f"  {r['display_name']} ({r['pos_group']}, {int(r['draft_year'])}){tag}")
        log(f"    {r['headline']}")
        log(f"    comps: {r['comp_names']}")
        if pd.notna(r.get("knn_mean_w_av")):
            log(f"    mean comp w_av={r['knn_mean_w_av']:.1f}, "
                f"mean distance={r['mean_distance']:.2f}")


def main() -> int:
    log("Loading public nflverse Combine (2000–2026) and draft_picks (career AV)...")
    H = load_historical()
    log(f"  historical raw {len(H)}; 2000–2022 with a position group: "
        f"{int(H['hist_year'].between(*HIST_YEARS).sum() & H['pos_group'].notna().sum())}")
    thresh = career_thresholds(H)
    labels, flags = [], []
    for _, row in H.iterrows():
        lab, fl = label_career(row, thresh)
        labels.append(lab)
        flags.append(fl)
    H["career_label"] = labels
    H["career_flag"] = flags

    log("\nLoading 2023–2025 rookies (Kaggle Combine tests + our gameplay outcomes)...")
    R = load_rookies()
    log(f"  rookies in scope: {len(R)}")
    log(R["pos_group"].value_counts().to_string())
    log(f"  with a gameplay outcome: {int(R['gameplay'].notna().sum())}")

    log("\nZ-scoring tests within position on the 2000–2022 historical pool...")
    tables = zscore_tables(H)
    H = apply_z(H, tables)
    R = apply_z(R, tables)

    log(f"\nFinding {K} nearest historical comps (min {MIN_SHARED} shared tests, RMS z-distance)...")
    hist_pool = H[H["hist_year"].between(*HIST_YEARS) & H["pos_group"].notna()].copy()
    long, summary = pairwise_knn(R, hist_pool, thresh)
    OUT.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT / "athletic_comps.csv", index=False)
    summary.to_csv(OUT / "athletic_comps_summary.csv", index=False)
    log(f"Wrote {OUT / 'athletic_comps.csv'} ({len(long)} rows) and summary ({len(summary)} rookies)")

    log("\n==== KNN career prediction vs our gameplay success (RB excluded) ====")
    corr = knn_vs_gameplay(summary)
    corr.to_csv(OUT / "athletic_comps_correlation.csv", index=False)
    log(corr.to_string(index=False))

    print_highlights(summary, long)

    # Coverage note
    log("\n==== Notes ====")
    log("The nflverse Combine release (PFR) has no 10-yard split. Distances use "
        "40, vertical, broad, 3-cone, shuttle, height, and weight.")
    log("RB (Sione Vaki) is an anecdote only — excluded from every model and from "
        "the KNN-vs-gameplay correlation.")
    log("Career labels: star = 1+ AP first-team All-Pro, 3+ Pro Bowls, Hall of Fame, "
        "or w_av at/above the 2000–2018 position 90th percentile; solid = w_av at/above "
        "the position median, 1+ Pro Bowl, or 3+ seasons started; journeyman = a career "
        "record below that; no_record = not in the draft_picks file (often undrafted). "
        "Players drafted 2019–2022 are flagged early-career: their AV is still accumulating.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
