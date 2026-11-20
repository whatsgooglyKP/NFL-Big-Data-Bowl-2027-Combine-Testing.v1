tests = [("ten_yd_split", "10-yard split"), ("forty", "40-yard dash"), ("c_top_mph", "Top speed (tracked)"), ("burst_0_100", "Burst Score †"), ("vertical", "Vertical jump"), ("broad_jump", "Broad jump")]
outs = [("speed_1s_mph", "Get-off speed (1 s)"), ("pressure_rate", "Pressure rate"), ("sack_rate", "Sack rate"), ("tfl_rate", "Tackles for loss")]
fig, axes = plt.subplots(2, 2, figsize=(8.6, 7.4), sharex=True)
used = []
for ax, (oc, ol) in zip(axes.ravel(), outs):
    for i, (t, tl_) in enumerate(tests[::-1]):
        r = g25[(g25.group == "DL") & (g25.subgroup == "All") & (g25.test == t) & (g25.outcome == oc)]
        if r.empty: continue
        r = r.iloc[0]; col = VCOL[r.verdict]; used.append(r)
        ax.annotate("", xy=(r.rho_size, i), xytext=(r.rho_raw, i), arrowprops=dict(arrowstyle="->", color=col, lw=1.2, alpha=.6))
        draw_ci(ax, i, r.ci_lo, r.ci_hi, r.n, col, 2.6, .55)
        ax.scatter(r.rho_raw, i, s=40, facecolor="white", edgecolor=col, marker="D", zorder=3); ax.scatter(r.rho_size, i, s=50, color=col, zorder=4)
    ax.set_yticks(range(len(tests))); ax.set_yticklabels([t[1] for t in tests[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.45, .95); ax.set_title(ol, fontweight="bold", loc="left")
for ax in axes[1]: ax.set_xlabel("rank correlation (+ = better athlete)")
U = pd.DataFrame(used); QMIN, NMIN, NMAX = U.fdr_q.min(), int(U.n.min()), int(U.n.max())
finish(fig, "fig3_dl_size.png", "Defensive line: most of the raw link shrinks once body size and role are held fixed",
       f"n {NMIN} to {NMAX} per cell; none clears q < 0.05 (lowest q {QMIN:.2f}). Raw links carry no interval. 3-cone and shuttle (under 36 linemen) omitted. † Burst Score recipe tuned using game results.",
       legend=([ml.Line2D([], [], marker="D", color="w", markerfacecolor="w", markeredgecolor="#333", lw=0), ml.Line2D([], [], marker="o", color="#333", lw=0), ml.Line2D([], [], marker="o", color=VCOL["SIZE, NOT SPEED"], lw=0), ml.Line2D([], [], marker="o", color=VCOL["LEANS"], lw=0)],
               ["raw link (year fixed)", "adjusted, 95% interval", "mostly size", "lead (q not cleared)"], 4))
