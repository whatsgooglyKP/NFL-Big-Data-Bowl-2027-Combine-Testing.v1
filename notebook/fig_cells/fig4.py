def players_needed(rho, alpha, k=4):
    return int(np.ceil(1.06 * ((norm.ppf(1 - alpha / 2) + norm.ppf(.8)) / np.arctanh(rho)) ** 2 + k + 3))
LEADS = [("WR", "All", "vertical", "break_y", "Receivers: vertical jump → break separation"),
         ("WR", "All", "burst_0_100", "break_y", "Receivers: Burst Score † → break separation"),
         ("DL", "All", "forty", "pressure_rate", "Linemen: 40-yard dash → pressure rate"),
         ("DL", "All", "ten_yd_split", "speed_1s_mph", "Linemen: 10-yard split → get-off speed"),
         ("DL", "All", "burst_0_100", "tfl_rate", "Linemen: Burst Score † → tackles for loss")]
fig, ax = plt.subplots(figsize=(8.6, 4.6)); col = VCOL["LEANS"]
for i, (grp, sub, t, oc, lab) in enumerate(LEADS[::-1]):
    r = full[(full.group == grp) & (full.subgroup == sub) & (full.test == t) & (full.outcome == oc)].iloc[0]
    ax.fill_betweenx([i - .34, i + .34], -r.mde80, r.mde80, color="#d9d9d9", alpha=.7, zorder=0)
    draw_ci(ax, i, r.ci_lo, r.ci_hi, r.n, col, 2.8); ax.scatter(r.rho_size, i, s=60, color=col, zorder=3)
    ax.text(1.01, i, f"{tag(r.n, r.fdr_q)}\nheld-out {r.classes_helped}\n~{players_needed(r.rho_size, r.alpha_bh)} players to confirm", va="center", fontsize=8, color="#333", transform=ax.get_yaxis_transform())
ax.set_yticks(range(len(LEADS))); ax.set_yticklabels([x[4] for x in LEADS[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.55, .8)
ax.set_xlabel("size-controlled rank correlation; + = better athlete, better result\ndot = estimate, line = 95% interval, gray band = smallest link this n reliably sees")
finish(fig, "fig4_leads.png", "Five leads: consistent in held-out classes, not yet past the correction",
       "Leads are the best-looking of many tests, so true links are probably smaller. 'Players to confirm' assumes today's estimate is true (optimistic). † Burst Score recipe tuned using game results.", rect_lr=(0, .79))
