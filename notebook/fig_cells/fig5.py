db = card[card.group == "DB"]
fig, ax = plt.subplots(figsize=(8.6, 5.0))
labs = []
for i, (_, r) in enumerate(db.iloc[::-1].iterrows()):
    col = VCOL[r.verdict]
    ax.fill_betweenx([i - .34, i + .34], -r.mde80, r.mde80, color="#d9d9d9", alpha=.7, zorder=0)
    draw_ci(ax, i, r.ci_lo, r.ci_hi, r.n, col, 2.8); ax.scatter(r.rho_size, i, s=56, color=col, zorder=3)
    ax.text(1.01, i, tag(r.n, r.fdr_q) + ("\nruns the wrong way" if (r.rho_size < 0 and r.verdict == "LEANS") else ""), va="center", fontsize=8, color="#333", transform=ax.get_yaxis_transform())
    labs.append(f"{r.test_label.replace(' (tracking)', '')} → {r.outcome_label.replace(' (Sunday Speed)', '')}")
ax.set_yticks(range(len(db))); ax.set_yticklabels(labs, fontsize=8.5)
ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.7, .8)
ax.set_xlabel("size-controlled rank correlation; + = better athlete, better result\ndot = estimate, line = 95% interval, gray band = smallest link this n reliably sees")
finish(fig, "fig5_db_power.png", "Defensive backs: wide intervals, most inside what this n can see",
       "One test per result, the one with the smallest p, so these intervals flatter the Combine. Not detected is not ruled out.", rect_lr=(0, .85),
       legend=([ml.Line2D([], [], marker="o", color=VCOL[k], lw=0) for k in ["LEANS", ND]], ["lead (interval excludes 0, q not cleared)", "NOT DETECTED (low power)"], 2))
