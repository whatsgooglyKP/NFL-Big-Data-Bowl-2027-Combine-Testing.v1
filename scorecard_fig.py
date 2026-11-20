"""fig22: coach scorecard, one panel per group (WR, TE, DB, DL). Reads out/scorecard.csv only."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from dl_recheck import OUT

c = pd.read_csv(OUT / "scorecard.csv")
COL = {"TRANSLATES": "#1a9850", "LEANS": "#f1a340", "SIZE, NOT SPEED": "#d95f02", "NOT DETECTED (low power)": "#7f7f7f", "TOO FEW TO TELL": "#bdbdbd"}
SHORT_T = {"forty": "40", "ten_yd_split": "10-yd", "vertical": "Vertical", "broad_jump": "Broad jump", "three_cone": "3-cone", "short_shuttle": "Shuttle",
           "c_top_mph": "Top speed (tracked)", "burst_0_100": "Burst Score", "c_decel": "DB-drill braking", "c_accel": "DB-drill re-burst"}
SHORT_O = {"sunday_speed_mph": "deep-route game speed", "sep_all_mean": "separation (all routes)", "break_y": "separation (break routes)",
           "pressure_rate": "pressure rate", "sack_rate": "sack rate", "tfl_rate": "tackles for loss", "run_stop_rate": "run stops",
           "speed_1s_mph": "get-off speed", "tackle_rate": "tackle rate", "close_rate_mph": "closing speed", "pfr_yds_tgt": "yards allowed / target",
           "pfr_mtkl_pct": "missed tackles"}
TITLE = {"WR": "WIDE RECEIVERS", "TE": "TIGHT ENDS", "DB": "DEFENSIVE BACKS (CB+S)", "DL": "DEFENSIVE LINE (all, with Edge / Interior)"}
fig, axs = plt.subplots(2, 2, figsize=(20, 11)); axs = axs.ravel()
for ax, g in zip(axs, ["WR", "TE", "DB", "DL"]):
    d = c[c.group == g]; main = d[~d.breakout.astype(bool)].reset_index(drop=True)
    y = 0; ticks, labs = [], []
    ax.axvspan(0, 1, color="#e8f3e8", alpha=0.45, zorder=0)
    for _, r in main.iterrows():
        rows = [("All", r)]
        if g == "DL":
            for sg in ("Edge", "Interior"):
                b = d[d.breakout.astype(bool) & (d.subgroup == sg) & (d.test == r.test) & (d.outcome == r.outcome)]
                if len(b):
                    rows.append((sg, b.iloc[0]))
        top = y
        for k, (sg, x) in enumerate(rows):
            col = COL[x.verdict]; yy = y - 0.28 * k if g == "DL" else y
            mk = {"All": "o", "Edge": "^", "Interior": "s"}[sg]
            ax.plot([x.ci_lo, x.ci_hi], [yy, yy], color=col, lw=2.4 if sg == "All" else 1.6, solid_capstyle="round", alpha=1 if sg == "All" else 0.85, zorder=2)
            ax.plot(x.rho_size, yy, mk, color=col, ms=9 if sg == "All" else 6.5, mec="white", zorder=4)
            ax.plot(x.rho_raw, yy, "D", mfc="none", mec="#444", ms=5.5 if sg == "All" else 4, mew=1, zorder=3, alpha=0.9 if sg == "All" else 0.6)
            if sg == "All":
                ax.text(1.02, yy + 0.03, x.verdict, color=col if x.verdict != "TOO FEW TO TELL" else "#8a8a8a", ha="left", va="bottom", fontsize=8.2, fontweight="bold",
                        transform=ax.get_yaxis_transform())
                ax.text(1.02, yy - 0.04, f"n {int(x.n)}  q {("<0.01" if x.fdr_q < 0.01 else format(x.fdr_q, ".2f"))}  held-out {x.classes_helped}  MDE ±{x.mde80:.2f}", ha="left", va="top", fontsize=6.8, color="#444",
                        transform=ax.get_yaxis_transform())
        ticks.append(y - (0.28 if g == "DL" else 0)); labs.append(f"{SHORT_T[r.test]} → {SHORT_O[r.outcome]}")
        y -= 1.45 if g == "DL" else 1.0
    ax.axvline(0, color="#555", lw=0.9)
    ax.set_yticks(ticks); ax.set_yticklabels(labs, fontsize=9)
    ax.set_xlim(-0.9, 0.9); ax.set_ylim(y + 0.45, 0.85)
    ax.set_xlabel("← worse athlete does better      |      better athlete does better →     (rank ρ)", fontsize=8)
    ax.set_title(TITLE[g], loc="left", fontsize=11.5, fontweight="bold"); ax.grid(axis="x", alpha=0.25)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
leg = [Line2D([0], [0], marker="o", color="w", mfc=COL[k], ms=10, label=k) for k in COL] + \
      [Line2D([0], [0], marker="D", color="w", mfc="none", mec="#444", ms=7, label="year-controlled ρ (before size control)"),
       Line2D([0], [0], marker="^", color="w", mfc="#777", ms=8, label="DL Edge"), Line2D([0], [0], marker="s", color="w", mfc="#777", ms=8, label="DL Interior")]
fig.legend(handles=leg, loc="lower center", ncol=8, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.025))
fig.suptitle("What the Combine tells you about regular-season games, position by position", fontsize=15, fontweight="bold", x=0.01, ha="left")
fig.text(0.01, 0.945, "Filled dot = size-controlled ρ with 95% CI (draft year, weight, height held fixed). Hollow diamond = year-controlled ρ before size control: the gap is size (and role). Green band = better athlete goes with better result.",
         fontsize=9, color="#333")
fig.text(0.01, 0.006, "One row per outcome: the test with the smallest permutation p (n ≥ 25). q = BH false-discovery rate over the full family. 'MDE' = smallest |ρ| detectable with 80% power at this n (alpha 0.05): a gray row means not detected, not no effect. 'held-out' = draft classes where adding the test beat a size-only model on unseen data. "
         "Draft slot never used. Source: out/scorecard.csv.", fontsize=7.3, color="#444", wrap=True)
fig.subplots_adjust(left=0.16, right=0.845, wspace=1.45, hspace=0.22, top=0.905, bottom=0.115)
fig.savefig(OUT / "figs" / "fig22_scorecard.png", dpi=150); print("wrote fig22")
