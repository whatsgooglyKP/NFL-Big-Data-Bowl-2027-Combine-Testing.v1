# ---- THE GATE: Combine tracking -> regular-season game tracking, receivers, recomputed from the raw competition files ----
MPH = 2.0455  # yards/second to mph
gate = full.query("group == 'WR' and test == 'c_top_mph' and outcome == 'sunday_speed_mph'").iloc[0]
if COMP is not None:
    pl = pd.read_csv(COMP / "players.csv", usecols=["nfl_id", "nfl_position", "draft_year"])
    wr = pl[pl.nfl_position == "WR"]; ids = set(wr.nfl_id)
    # Combine side: fastest speed in any 40-yard-dash attempt, from the 10 Hz sensor
    ct = pd.read_csv(COMP / "combine_tracking.csv", usecols=["nfl_id", "entity_type", "drill_type", "s"])
    ct = ct[(ct.entity_type == "PLAYER") & (ct.drill_type == "FORTY_YARD_DASH") & ct.nfl_id.isin(ids)]
    top = (ct.groupby("nfl_id").s.max() * MPH).rename("combine_top_mph")
    # Game side: regular-season deep routes (go, post, corner, wheel) that stood; top speed on each play from game tracking
    games = pd.read_csv(COMP / "games.csv", usecols=["game_id", "season_type"])
    pp = pd.read_csv(COMP / "player_play.csv", usecols=["game_id", "play_id", "nfl_id", "route_ran", "play_nullified_by_penalty"])
    pp = pp[pp.nfl_id.isin(ids) & pp.route_ran.isin(["GO", "POST", "CORNER", "WHEEL"]) & (pp.play_nullified_by_penalty == "N")
            & pp.game_id.isin(games.game_id[games.season_type == "REG"])]
    parts = []
    for yr in (2023, 2024, 2025):
        for ch in pd.read_csv(COMP / f"game_tracking_{yr}.csv", usecols=["game_id", "play_id", "nfl_id", "s"], dtype={"s": "float32"}, chunksize=2_000_000):
            ch = ch[ch.nfl_id.isin(ids)]
            if len(ch):
                parts.append(ch.groupby(["game_id", "play_id", "nfl_id"], sort=False).s.max().reset_index())
    plays = pd.concat(parts).groupby(["game_id", "play_id", "nfl_id"], as_index=False).s.max()
    plays = plays.merge(pp[["game_id", "play_id", "nfl_id"]], on=["game_id", "play_id", "nfl_id"])
    cnt = plays.groupby("nfl_id").s.size()
    sunday = (plays.groupby("nfl_id").s.quantile(0.90) * MPH)[cnt >= 20].rename("sunday_speed_mph")   # at least 20 deep routes
    cr = pd.read_csv(COMP / "combine_results.csv", usecols=["nfl_id", "combine_weight", "combine_height"]).drop_duplicates("nfl_id").set_index("nfl_id")
    d = pd.concat([top, sunday], axis=1, join="inner").join(wr.set_index("nfl_id").draft_year).join(cr).dropna()
    x, y = d.combine_top_mph, d.sunday_speed_mph
    rho_year = stats.spearmanr(x - x.groupby(d.draft_year).transform("mean"), y - y.groupby(d.draft_year).transform("mean"))[0]
    # rank partial correlation holding draft year, weight and height fixed (same recipe as the audited fit): rank, residualise, correlate
    Z = np.column_stack([np.ones(len(d)), pd.get_dummies(d.draft_year.astype(str), drop_first=True).to_numpy(float), stats.rankdata(d.combine_weight), stats.rankdata(d.combine_height)])
    res = lambda v: stats.rankdata(v) - Z @ np.linalg.lstsq(Z, stats.rankdata(v), rcond=None)[0]
    rx, ry = res(x), res(y); rho_size = np.corrcoef(rx, ry)[0, 1]
    rng = np.random.default_rng(7); xs = np.linspace(x.min(), x.max(), 60); bands, slopes = [], []
    for _ in range(1500):
        i = rng.integers(0, len(d), len(d)); b = np.polyfit(x.to_numpy()[i], y.to_numpy()[i], 1); slopes.append(b[0]); bands.append(np.polyval(b, xs))
    lo_b, hi_b = np.percentile(bands, [2.5, 97.5], axis=0); s_lo, s_hi = np.percentile(slopes, [2.5, 97.5]); slope = np.polyfit(x, y, 1)
    print(f"Receivers with a tracked 40, size data and 20+ regular-season deep routes: n={len(d)} (audited n={int(gate.n)})")
    print(f"Spearman, draft year held fixed: {rho_year:+.2f} (audited {gate.rho_raw:+.2f}); rank partial with size held fixed: {rho_size:+.2f} (audited {gate.rho_size:+.2f}); slope {slope[0]:.2f} mph per mph (bootstrap 95% CI {s_lo:.2f} to {s_hi:.2f})")
    assert abs(len(d) - int(gate.n)) <= 1 and abs(rho_size - gate.rho_size) < 0.05, "live recomputation disagrees with the audited table"
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.4, 4.3))
    c = VCOL["TRANSLATES"]
    a.fill_between(xs, lo_b, hi_b, color=c, alpha=.18, lw=0); a.plot(xs, np.polyval(slope, xs), color=c, lw=1.8)
    a.scatter(x, y, s=20, color=c, alpha=.75, edgecolor="white", linewidth=.4)
    a.set_xlabel("Combine top speed in the 40 (mph)"); a.set_ylabel("Sunday Speed on deep routes (mph)")
    a.set_title("A. As measured", loc="left", fontweight="bold")
    a.text(.03, .97, f"n {len(d)}; Spearman {rho_year:+.2f} (year fixed)\n{slope[0]:+.2f} mph per mph\n(line and 95% band: straight-line fit)", transform=a.transAxes, va="top", fontsize=8.5)
    b.scatter(rx, ry, s=20, color=c, alpha=.75, edgecolor="white", linewidth=.4); b.axhline(0, color="k", lw=.6); b.axvline(0, color="k", lw=.6)
    bb = np.polyfit(rx, ry, 1); xx = np.linspace(rx.min(), rx.max(), 2); b.plot(xx, np.polyval(bb, xx), color=c, lw=1.8)
    b.set_xlabel("Combine top speed, rank left over\nafter year, weight, height"); b.set_ylabel("Sunday Speed, rank left over")
    b.set_title("B. With body size held fixed", loc="left", fontweight="bold")
    b.text(.03, .97, f"partial rank ρ {gate.rho_size:+.2f}\n95% CI {gate.ci_lo:+.2f} to {gate.ci_hi:+.2f}\nq {gate.fdr_q:.3f}", transform=b.transAxes, va="top", fontsize=8.5)
    fig.tight_layout(); fig.savefig(SAVE / "fig1_gate_wr.png"); plt.show()
else:
    print("Competition data not attached: showing the saved gate figure and audited numbers instead.")
    display(Image(str(FIGS / "fig1_gate_wr.png")))
ok = (gate.verdict == "TRANSLATES") and (gate.rho_raw > 0)
print(f"Audited: size-controlled rho {gate.rho_size:+.2f} (95% CI {gate.ci_lo:+.2f} to {gate.ci_hi:+.2f}), q {gate.fdr_q:.3f}, better on held-out draft classes in {gate.classes_helped}")
print("GATE (Combine tracking -> regular-season performance):", "PASS" if ok else "FAIL")
