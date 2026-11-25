# v2 analysis library (branch v2-review, 11/2026). Recomputes every v2 statistic LIVE from the nine competition CSVs.
# No precomputed result tables are read. Aggregate output only: no player names or IDs are printed or saved.
# Draft slot / pick / round is never a variable here. Seed 2027.
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

SEED = 2027
MPH = 2.0455                      # yards/second -> mph
DEEP = ["GO", "POST", "CORNER", "WHEEL"]
BREAK = ["OUT", "IN", "HITCH", "SLANT"]
TIMES = {"forty", "ten_yd_split", "three_cone", "short_shuttle"}     # lower = better: sign flipped so + = better athlete

def find_comp(cands=("data", "../data", "../../data")):
    for p in map(Path, cands):
        if (p / "combine_tracking.csv").exists():
            return p
    hits = list(Path("/kaggle/input").rglob("combine_tracking.csv")) if Path("/kaggle/input").exists() else []
    if hits:
        return hits[0].parent
    raise RuntimeError("Competition data are not attached (combine_tracking.csv not found). "
                       "GATE: FAIL. Attach the nfl-big-data-bowl-2027 competition data and rerun.")

# ------------------------------------------------------------------ statistics
def _design(df, cols):
    """Intercept + class dummies + ranks of any numeric controls; categorical controls as dummies."""
    parts = [np.ones((len(df), 1))]
    for c in cols:
        v = df[c]
        if c in ("draft_year", "role"):
            parts.append(pd.get_dummies(v.astype(str), drop_first=True).to_numpy(float))
        else:
            parts.append(stats.rankdata(v)[:, None])
    return np.hstack(parts)

def _res(v, Z):
    r = stats.rankdata(v)
    return r - Z @ np.linalg.lstsq(Z, r, rcond=None)[0]

def rank_partial(df, x, y, ctrl=("draft_year", "combine_weight", "combine_height")):
    d = df[[x, y, *ctrl]].dropna()
    Z = _design(d, ctrl)
    rx, ry = _res(d[x], Z), _res(d[y], Z)
    return float(np.corrcoef(rx, ry)[0, 1]), len(d), rx, ry, d

def perm_p(df, x, y, ctrl=("draft_year", "combine_weight", "combine_height"), P=10000, seed=SEED):
    """Freedman-Lane: shuffle the outcome's residuals (reduced model = controls only)."""
    r, n, rx, ry, d = rank_partial(df, x, y, ctrl)
    rng = np.random.default_rng(seed)
    rxs = (rx - rx.mean()) / rx.std(); ryc = ry - ry.mean()
    sims = np.array([abs(np.dot(rxs, rng.permutation(ryc))) for _ in range(P)]) / (len(rx) * ryc.std())
    return float((1 + (sims >= abs(r) - 1e-12).sum()) / (P + 1))

def boot_ci(df, x, y, ctrl=("draft_year", "combine_weight", "combine_height"), B=2000, seed=SEED, stat=None):
    d = df.reset_index(drop=True) if stat else df[[x, y, *ctrl]].dropna().reset_index(drop=True)
    rng = np.random.default_rng(seed); out = []
    f = stat or (lambda dd: rank_partial(dd, x, y, ctrl)[0])
    for _ in range(B):
        dd = d.iloc[rng.integers(0, len(d), len(d))]
        try:
            out.append(f(dd))
        except Exception:
            pass
    out = np.array(out); out = out[np.isfinite(out)]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))

def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1); q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n); out[o] = np.minimum(q, 1); return out

def mde(n, k=3, alpha=0.05, power=0.8):
    """Smallest |rho| seen `power` of the time (Fisher z, 1.06 Spearman factor, k controls)."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return float(np.tanh(z * np.sqrt(1.06 / max(n - k - 3, 1))))

def zscore(r, n, k):
    return np.arctanh(np.clip(np.abs(r), 0, 0.999999)) * np.sqrt(max(n - k - 3, 1) / 1.06)

# ------------------------------------------------------------------ data
def load(COMP):
    pl = pd.read_csv(COMP / "players.csv", usecols=["nfl_id", "nfl_position", "draft_year", "draft_round"])
    pl["undrafted"] = pl.draft_round.isna()           # descriptive only; never a model variable
    pl = pl.drop(columns="draft_round")
    cr = pd.read_csv(COMP / "combine_results.csv").drop_duplicates("nfl_id").drop(columns="draft_year")
    for t in TIMES:
        cr[t] = -cr[t]
    games = pd.read_csv(COMP / "games.csv", usecols=["game_id", "season", "season_type"])
    reg = games[games.season_type == "REG"]
    pp = pd.read_csv(COMP / "player_play.csv", usecols=[
        "game_id", "play_id", "nfl_id", "lined_up_position", "pass_result", "play_nullified_by_penalty", "target",
        "rec_yards", "route_ran", "separation_at_pass_forward", "pressure_allowed", "time_to_pressure", "sack",
        "tackle_for_loss", "tackle", "assist"])
    pp = pp[(pp.play_nullified_by_penalty == "N") & pp.game_id.isin(reg.game_id)].merge(reg[["game_id", "season"]], on="game_id")
    ct = pd.read_csv(COMP / "combine_tracking.csv", usecols=["nfl_id", "entity_type", "time", "drill_type", "drill_name", "attempt", "s"])
    ct = ct[ct.entity_type == "PLAYER"]
    return pl, cr, pp, ct

def combine_tracking_features(ct):
    f = pd.DataFrame(index=pd.Index(ct.nfl_id.unique(), name="nfl_id"))
    f["c_top_mph"] = ct[ct.drill_type == "FORTY_YARD_DASH"].groupby("nfl_id").s.max() * MPH
    ol = ct[ct.drill_type == "SKILL_DRILLS_OL"].copy()
    ol["drill"] = ol.drill_name.str.replace("PASS_PRO-MIRROR_DRILL", "PASS_PRO_MIRROR_DRILL")
    ol = ol.sort_values(["nfl_id", "drill", "attempt", "time"])
    ol["ds"] = ol.groupby(["nfl_id", "drill", "attempt"]).s.diff()
    att = ol.groupby(["nfl_id", "drill", "attempt"]).agg(peak_s=("s", "max"), acc=("ds", "max"), dec=("ds", "min"))
    att["acc"] *= 10; att["dec"] *= -10        # largest 0.1-s speed gain / loss, yd/s^2 (10 Hz)
    per = att.groupby(["nfl_id", "drill"]).mean().unstack("drill")   # averaged over attempts
    short = {"FIVE_YARD_WAVE_DRILL_SLIDE_AND_SHUFFLE": "slide", "OL_PULL_DRILL_DEEP_SHORT_PULL_LEFT": "pull_short",
             "OL_PULL_DRILL_FOLD_BLOCK_RIGHT": "fold", "OL_PULL_DRILL_LONG_PULL_RIGHT": "pull_long",
             "PASS_PRO_MIRROR_DRILL": "mirror", "PASS_RUSH_DROP": "rush_drop", "SCREEN_DRILL": "screen"}
    per.columns = [f"ol_{short[d]}_{m}" for m, d in per.columns]
    return f.join(per)

def wr_play_speeds(COMP, ids, chunksize=2_000_000):
    """Per-play max speed (yd/s) from game tracking, for the given players."""
    parts = []
    for yr in (2023, 2024, 2025):
        for ch in pd.read_csv(COMP / f"game_tracking_{yr}.csv", usecols=["game_id", "play_id", "nfl_id", "s"],
                              dtype={"s": "float32"}, chunksize=chunksize):
            ch = ch[ch.nfl_id.isin(ids)]
            if len(ch):
                parts.append(ch.groupby(["game_id", "play_id", "nfl_id"], sort=False).s.max().reset_index())
    return pd.concat(parts).groupby(["game_id", "play_id", "nfl_id"], as_index=False).s.max()

# ------------------------------------------------------------------ receivers
def wr_table(pl, cr, pp, feat, plays):
    wr = pl[pl.nfl_position == "WR"].set_index("nfl_id")
    deep = pp[pp.nfl_id.isin(wr.index) & pp.route_ran.isin(DEEP)]
    dp = plays.merge(deep[["game_id", "play_id", "nfl_id", "season"]], on=["game_id", "play_id", "nfl_id"])
    dp = dp.sort_values(["nfl_id", "game_id", "play_id"])
    cnt = dp.groupby("nfl_id").size()
    T = wr.join(cr.set_index("nfl_id")).join(feat)
    T["deep_routes"] = cnt
    T["sunday_speed_mph"] = (dp.groupby("nfl_id").s.quantile(0.9) * MPH).where(cnt >= 20)
    dp = dp.join(T.draft_year, on="nfl_id")
    rk = dp[dp.season == dp.draft_year]; rc = rk.groupby("nfl_id").size()
    T["sunday_rookie"] = (rk.groupby("nfl_id").s.quantile(0.9) * MPH).where(rc >= 20)
    for k in (20, 30):
        h = dp.groupby("nfl_id").head(k); hc = h.groupby("nfl_id").size()
        T[f"sunday_first{k}"] = (h.groupby("nfl_id").s.quantile(0.9) * MPH).where(hc >= k)
    routes = pp[pp.nfl_id.isin(wr.index) & pp.route_ran.notna()].copy()
    routes["rec_yards"] = routes.rec_yards.fillna(0)
    g = routes.groupby("nfl_id")
    T["yards_per_route"] = g.rec_yards.sum() / g.size()
    dr = routes[routes.route_ran.isin(DEEP)].groupby("nfl_id")
    T["deep_yds_per_deep_route"] = dr.rec_yards.sum() / dr.size()
    T["deep_target_share"] = dr.target.mean()                      # targets per deep route
    T["sep_all_mean"] = g.separation_at_pass_forward.mean()
    T["break_y"] = routes[routes.route_ran.isin(BREAK)].groupby("nfl_id").separation_at_pass_forward.mean()
    return T

def funnel(T):
    a = len(T); b = T.c_top_mph.notna().sum(); c = (T.deep_routes >= 20).sum()
    S = T.dropna(subset=["c_top_mph", "sunday_speed_mph", "combine_weight", "combine_height"])
    return dict(listed=a, tracked_40=int(b), deep20=int(c), both=len(S),
                undrafted_in_sample=int(S.undrafted.sum()), undrafted_listed=int(T.undrafted.sum())), S

# ------------------------------------------------------------------ DL / OL / DB samples
def dl_table(pl, cr, pp, feat):
    dl = pl[pl.nfl_position.isin(["DE", "OLB", "DT", "NT"])].set_index("nfl_id")
    dl["role"] = np.where(dl.nfl_position.isin(["DE", "OLB"]), "Edge", "Interior")
    s = pp[pp.nfl_id.isin(dl.index) & pp.lined_up_position.isin(["EDGE", "INTERIOR_LINE"])]
    rush = s[s.pass_result.notna()]; g = rush.groupby("nfl_id")
    T = dl.join(cr.set_index("nfl_id")).join(feat)
    T["rush_snaps"] = g.size()
    T["pressure_rate"] = g.time_to_pressure.apply(lambda v: v.notna().mean())
    T["sack_rate"] = g.sack.apply(lambda v: v.fillna(0).sum()) / g.size()
    T["tfl_rate"] = s.groupby("nfl_id").tackle_for_loss.apply(lambda v: (v == 1).mean() if v.dtype != object else v.isin([True, "True", 1]).mean())
    return T[T.rush_snaps >= 20]

def ol_table(pl, cr, pp, feat):
    ol = pl[pl.nfl_position.isin(["T", "G", "C"])].set_index("nfl_id")
    ol["role"] = np.where(ol.nfl_position == "T", "Tackle", "Interior")
    s = pp[pp.nfl_id.isin(ol.index) & pp.pressure_allowed.notna()]
    g = s.groupby("nfl_id")
    T = ol.join(cr.set_index("nfl_id")).join(feat)
    T["pb_snaps"] = g.size()
    T["pressure_allowed_rate"] = g.pressure_allowed.apply(lambda v: v.astype(str).eq("True").mean())
    T["pressure_allowed_rate"] = -T["pressure_allowed_rate"]       # + = better (fewer pressures)
    return T[T.pb_snaps >= 100]

def db_table(pl, cr, pp, feat):
    db = pl[pl.nfl_position.isin(["CB", "SS", "FS", "DB"])].set_index("nfl_id")
    db["role"] = np.where(db.nfl_position.isin(["CB", "DB"]), "CB", "S")
    s = pp[pp.nfl_id.isin(db.index) & pp.lined_up_position.isin(["CB", "SLOT_CB", "HIGH_SAFETY", "BOX_SAFETY"])].copy()
    tb = lambda v: v.astype(str).isin(["True", "1", "1.0"])
    s["tk"] = tb(s.tackle) | tb(s.assist); s["tf"] = tb(s.tackle_for_loss)
    g = s.groupby("nfl_id")
    T = db.join(cr.set_index("nfl_id")).join(feat)
    T["def_snaps"] = g.size(); T["tackle_rate"] = g.tk.mean(); T["tfl_rate"] = g.tf.mean()
    return T[T.def_snaps >= 50]

# ------------------------------------------------------------------ families and best-of-N (Westfall-Young max-|z|)
def family(T, tests, outcomes, ctrl, min_n=25, P=10000):
    rows = []
    for t in tests:
        for o in outcomes:
            d = T[[t, o, *ctrl]].dropna()
            if len(d) < min_n:
                continue
            r, n, *_ = rank_partial(d, t, o, ctrl)
            rows.append(dict(test=t, outcome=o, n=n, rho=r, p=perm_p(d, t, o, ctrl, P=P)))
    F = pd.DataFrame(rows); F["q"] = bh(F.p); F["k"] = _design(T.dropna(subset=list(ctrl)), ctrl).shape[1] - 1
    F["z"] = [zscore(r, n, k) for r, n, k in zip(F.rho, F.n, F.k)]
    return F

def best_of_n(T, F, ctrl, S=2000, seed=SEED):
    """Shuffle the whole outcome block within draft class (players keep their tests and controls), recompute every
    cell; p_maxT = share of shuffles whose best |z| beats the cell's observed |z|. Also the k-th best luck bands."""
    rng = np.random.default_rng(seed)
    outs = sorted(F.outcome.unique()); tests = sorted(F.test.unique())
    base = T.dropna(subset=list(ctrl)).copy()
    idx_by_class = [np.where(base.draft_year.values == y)[0] for y in sorted(base.draft_year.unique())]
    O = base[outs].to_numpy()
    maxz, kth = [], []
    cells = list(zip(F.test, F.outcome))
    for _ in range(S):
        perm = np.arange(len(base))
        for ix in idx_by_class:
            perm[ix] = rng.permutation(ix)
        B = base.copy(); B[outs] = O[perm]
        zs = []
        for t, o in cells:
            d = B[[t, o, *ctrl]].dropna()
            r, n, *_ = rank_partial(d, t, o, ctrl)
            zs.append(zscore(r, n, F.k.iloc[0]))
        zs = np.sort(np.array(zs))[::-1]; maxz.append(zs[0]); kth.append(zs)
    maxz = np.array(maxz)
    F = F.copy(); F["p_best_of_n"] = [(1 + (maxz >= z - 1e-12).sum()) / (S + 1) for z in F.z]
    return F, np.array(kth)

# ------------------------------------------------------------------ Table 2: nested leave-one-class-out R^2 gain
def _nscore(v, cls):
    out = pd.Series(np.nan, index=v.index)
    for c in cls.unique():
        m = (cls == c) & v.notna(); r = stats.rankdata(v[m]); out[m] = stats.norm.ppf((r - 0.5) / m.sum())
    return out

def loco_gain(T, tests, y, size=("combine_weight", "combine_height"), extra=(), min_cov=0.8, detail=False):
    """Nested leave-one-class-out. Inside the two training classes, pick the Combine test with the largest POSITIVE
    size-adjusted rank partial (direction pre-declared: + = better athlete does better), among tests measured for at
    least `min_cov` of the outcome sample (so a held-out fold is never cut to a handful of players). Score it on the third
    class. Gain = R^2(size + test) - R^2(size only) on pooled held-out predictions; within-class normal scores.
    (11/25/2026 fix: the 11/23 version picked by |rho|, so it could pick a test running the 'wrong' way, and allowed
    sparsely measured drills, which cut one OL fold to 13 players.)"""
    d = T[[*tests, y, "draft_year", *size, *extra]].copy()
    d = d[d[y].notna()].dropna(subset=list(size))
    tests = [t for t in tests if d[t].notna().mean() >= min_cov]
    for c in [*tests, y, *size]:
        d[c] = _nscore(d[c], d.draft_year).where(d[c].notna())
    if "role" in extra:
        d["role"] = d["role"].isin(["Tackle", "Edge", "CB"]).astype(float)
    cols0 = [*size, *extra]
    Xm = lambda df, cols: np.column_stack([np.ones(len(df))] + [df[c].to_numpy(float) for c in cols])
    preds0, preds1, ys, folds = [], [], [], []
    for hold in sorted(d.draft_year.unique()):
        tr, te = d[d.draft_year != hold], d[d.draft_year == hold]
        sc = {t: rank_partial(tr, t, y, ("draft_year", *size, *extra))[0] for t in tests}
        best = max(sc, key=sc.get)
        trb, teb = tr.dropna(subset=[best]), te.dropna(subset=[best])
        b0 = np.linalg.lstsq(Xm(trb, cols0), trb[y].to_numpy(float), rcond=None)[0]
        b1 = np.linalg.lstsq(Xm(trb, cols0 + [best]), trb[y].to_numpy(float), rcond=None)[0]
        p0, p1, yy = Xm(teb, cols0) @ b0, Xm(teb, cols0 + [best]) @ b1, teb[y].to_numpy(float)
        preds0.append(p0); preds1.append(p1); ys.append(yy)
        if detail:
            sst = ((yy - yy.mean()) ** 2).sum()
            folds.append(dict(held_out=int(hold), test=best, train_rho=float(sc[best]), n_train=len(trb), n_test=len(teb),
                              test_rho=float(rank_partial(teb, best, y, tuple(cols0))[0]), fold_gain=float((((yy - p0) ** 2).sum() - ((yy - p1) ** 2).sum()) / sst)))
    p0, p1, yy = map(np.concatenate, (preds0, preds1, ys))
    sst = ((yy - yy.mean()) ** 2).sum()
    g = float((((yy - p0) ** 2).sum() - ((yy - p1) ** 2).sum()) / sst)
    return (g, len(yy), folds) if detail else (g, len(yy))

def loco_null(T, tests, y, S=300, seed=SEED, **kw):
    rng = np.random.default_rng(seed); obs, n = loco_gain(T, tests, y, **kw); sims = []
    for _ in range(S):
        P = T.copy()
        for c in P.draft_year.dropna().unique():
            m = (P.draft_year == c).to_numpy(); P.loc[m, y] = rng.permutation(P.loc[m, y].to_numpy())
        sims.append(loco_gain(P, tests, y, **kw)[0])
    sims = np.array(sims)
    return obs, n, float(np.percentile(sims, 95)), float((1 + (sims >= obs).sum()) / (S + 1))
