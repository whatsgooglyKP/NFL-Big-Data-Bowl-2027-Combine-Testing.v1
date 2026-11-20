tl = [("forty", "40-yard dash"), ("c_top_mph", "Top speed (tracked)"), ("ten_yd_split", "10-yard split"), ("burst_0_100", "Burst Score †"), ("vertical", "Vertical jump"), ("broad_jump", "Broad jump"), ("short_shuttle", "Short shuttle"), ("three_cone", "3-cone")]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.6, 8.4), gridspec_kw={"height_ratios": [1.15, 1]})
for i, (t, lab) in enumerate(tl[::-1]):
    r = full[(full.group == "WR") & (full.subgroup == "All") & (full.test == t) & (full.outcome == "sunday_speed_mph")].iloc[0]; col = VCOL[r.verdict]
    draw_ci(a1, i, r.ci_lo, r.ci_hi, r.n, col, 2.4); a1.scatter(r.rho_size, i, s=52, color=col, zorder=3); a1.scatter(r.rho_raw, i, s=40, facecolor="white", edgecolor=col, marker="D", zorder=3)
    a1.text(1.01, i, tag(r.n, r.fdr_q, f"held-out {r.classes_helped}"), va="center", fontsize=8, color="#333", transform=a1.get_yaxis_transform())
a1.set_yticks(range(len(tl))); a1.set_yticklabels([x[1] for x in tl[::-1]]); a1.axvline(0, color="k", lw=.8); a1.set_xlim(-.9, .9)
a1.set_title("A. Game speed on deep routes: only straight-line speed stands out", loc="left", fontweight="bold", fontsize=9.5)
a1.set_xlabel("rank correlation; + = better athlete, faster Sunday speed\nfilled dot = size held fixed with 95% CI; hollow diamond = before size control")
p = g25.sort_values("p_perm").reset_index(drop=True); k = np.arange(1, len(p) + 1); pass_ = p.fdr_q < .05
a2.scatter(k[~pass_], p.p_perm[~pass_], s=16, color=VCOL[ND], alpha=.8, label="does not clear q < 0.05"); a2.scatter(k[pass_], p.p_perm[pass_], s=64, color=VCOL["TRANSLATES"], zorder=3, label="clears q < 0.05 (the two receiver speed rows)")
a2.plot(k, k / len(p), color="k", ls=":", lw=1.2, label="expected if no test had any real link"); a2.axhline(.05, color="#444", ls="--", lw=1, label="p = 0.05")
a2.set_yscale("log"); a2.set_ylim(5e-5, 1.3); a2.set_xlabel(f"the {len(p)} tests with at least 25 players, ranked by p-value"); a2.set_ylabel("permutation p-value (log scale)\nfloor 0.0001 = 10,000 shuffles")
a2.set_title(f"B. {int((p.p_perm < .05).sum())} tests under p = 0.05; about {len(p) * .05:.0f} expected by chance; {int(pass_.sum())} survive correction", loc="left", fontweight="bold"); a2.legend(fontsize=8, frameon=False, loc="lower right")
finish(fig, "fig2_wr_control.png", "Receivers: one speed signal clears every check, out of 164 tests", "† Burst Score recipe was tuned using game results (optimistic). q is the Benjamini-Hochberg rate within each family of tests; tests share players, so they are not independent.", rect_lr=(0, .86))
