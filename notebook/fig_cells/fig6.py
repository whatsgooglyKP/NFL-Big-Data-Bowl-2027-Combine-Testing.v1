rows = [("DL", "player_get_off", "Linemen: get-off time"), ("DL", "speed_1s_mph", "Linemen: speed 1 s after snap"), ("DL", "pen_pass_2s", "Linemen: pass-rush depth at 2 s"),
        ("DL", "pressure_rate", "Linemen: pressure rate"), ("DL", "sack_rate", "Linemen: sack rate"),
        ("WR", "sunday_speed_mph", "Receivers: deep-route game speed"), ("WR", "ssoe_mph", "Receivers: game speed vs own 40"), ("WR", "sep_all_mean", "Receivers: separation, all routes")]
fig, ax = plt.subplots(figsize=(8.6, 4.9))
for i, (grp, outc, lab) in enumerate(rows[::-1]):
    r = wt[(wt.group == grp) & (wt.outcome == outc)].iloc[0]; clear = r.fdr_q < .05
    col = VCOL["TRANSLATES"] if clear else VCOL[ND]
    draw_ci(ax, i, r.ci_lo, r.ci_hi, r.n, col, 2.6); ax.scatter(r.rho_height_ctrl, i, s=54, color=col, zorder=3)
    ax.scatter(r.rho_raw, i, s=40, facecolor="white", edgecolor=col, marker="D", zorder=3)
    ax.text(1.01, i, tag(r.n, r.fdr_q), va="center", fontsize=8, color="#333", transform=ax.get_yaxis_transform())
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[2] for r in rows[::-1]]); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-1, 1)
ax.set_xlabel("rank correlation of weight with the result (negative: heavier does worse)\nfilled dot = height and draft year fixed (linemen: role too), 95% interval; hollow diamond = draft year only")
finish(fig, "fig6_weight.png", "Weight: large where it matters, absent where it does not", "",
       rect_lr=(0, .86), legend=([ml.Line2D([], [], marker="o", color=VCOL[k], lw=0) for k in ["TRANSLATES", ND]], ["clears q < 0.05", "does not clear q < 0.05"], 2))
