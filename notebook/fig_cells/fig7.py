order = ["WR", "DL", "DB", "TE"]; names = {"WR": "Receivers", "DL": "Defensive line (all linemen)", "DB": "Defensive backs (CB + S)", "TE": "Tight ends (too few players)"}
cd_ = card[card.subgroup == "All"].copy(); cd_["o"] = cd_.group.map(order.index); cd_ = cd_.sort_values(["o"], kind="stable")
fig, ax = plt.subplots(figsize=(8.6, 9.6)); y = 0; yt, yl = [], []
for grp in order:
    d_ = cd_[cd_.group == grp]
    ax.text(-.78, y, names[grp], fontsize=10, fontweight="bold", va="center", transform=ax.get_yaxis_transform(), clip_on=False, ha="left"); y -= 1
    for _, r in d_.iterrows():
        col = VCOL[r.verdict]
        ax.axhline(y, color="#eeeeee", lw=.6, zorder=0)
        draw_ci(ax, y, r.ci_lo, r.ci_hi, r.n, col, 2.6); ax.scatter(r.rho_size, y, s=56, color=col, zorder=3); ax.scatter(r.rho_raw, y, s=36, facecolor="white", edgecolor=col, marker="D", zorder=3)
        yt.append(y); yl.append(f"{r.test_label.replace(' (tracking)', '')} → {r.outcome_label.replace(' (Sunday Speed)', '').replace(' (PFR)', '')}\n{tag(r.n, r.fdr_q)} · MDE ±{r.mde80:.2f}")
        y -= 1
    y -= .5
ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=8); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-.9, .9); ax.set_ylim(y + .3, .8)
ax.set_xlabel("size-controlled rank correlation; + = better athlete, better result\nfilled dot = estimate, 95% interval; hollow = before size control")
fig.subplots_adjust(left=.43, right=.97, top=.90, bottom=.09)
fig.suptitle("Scorecard: one test per result, picked for the smallest p (so optimistic)", x=.01, y=.985, ha="left", va="top", fontweight="bold", fontsize=10.5)
fig.legend([ml.Line2D([], [], marker="o", color=VCOL[k], lw=0) for k in ["TRANSLATES", "LEANS", "SIZE, NOT SPEED", ND, "TOO FEW TO TELL"]], ["TRANSLATES", "LEANS", "SIZE, NOT SPEED", "NOT DETECTED (low power)", "TOO FEW TO TELL"], loc="upper left", bbox_to_anchor=(.01, .955), ncol=3, fontsize=8.5, frameon=False)
fig.savefig(SAVE / "fig7_scorecard.png"); plt.show()
