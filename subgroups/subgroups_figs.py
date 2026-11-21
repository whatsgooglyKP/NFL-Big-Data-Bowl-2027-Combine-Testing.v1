import textwrap
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
COL = {"S": "#0072B2", "CB": "#E69F00", "EDGE": "#D55E00", "IDL": "#009E73", "pooled": "#444444"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": .25, "figure.dpi": 110, "savefig.dpi": 150})
TL = {c: l for c, l, _ in TESTS}


def fig_power(ns, path):
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    order = ["S", "CB", "EDGE", "IDL"]; d = ns.set_index("subgroup").loc[order]
    b = ax.bar(order, d.n_core, color=[COL[o] for o in order])
    for r, (o, row) in zip(b, d.iterrows()):
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + .8, f"n {int(row.n_core)}\nneeds |ρ| ≥ {row.mde80_core:.2f}",
                ha="center", va="bottom", fontsize=8.5)
    ax.axhline(25, color="#999", ls="--", lw=1); ax.text(-0.45, 25.6, "25 = smallest group we grade", fontsize=7.5, ha="left", color="#666")
    ax.set_ylim(0, max(d.n_core) * 1.45); ax.set_ylabel("players with size, tracked 40\nand a main game result")
    ax.set_title("Who is in each subgroup, and the smallest link each can detect (80% power)")
    fig.tight_layout(); fig.savefig(path); plt.show()


def fig_forest(cells, ints, grp, path):
    a, b, outs = PAIRS[grp]
    c = cells[cells.group == grp]; it = ints[ints.group == grp].set_index(["test", "outcome"])
    fig, axes = plt.subplots(1, len(outs), figsize=(2.55 * len(outs) + 1.6, 6.4), sharey=True)
    ys = np.arange(len(TESTS))[::-1]
    for ax, (oc, ol, *_ ) in zip(axes, outs):
        for j, (tc, tl, _) in enumerate(TESTS):
            y0 = ys[j]
            for sub, off in ((a, .18), (b, -.18)):
                r = c[(c["sub"] == sub) & (c.test == tc) & (c.outcome == oc)]
                if not len(r) or not np.isfinite(r.rho.iloc[0]):
                    continue
                r = r.iloc[0]; small = r.n < 25
                ax.plot([r.lo, r.hi], [y0 + off] * 2, color=COL[sub], lw=1.4, alpha=.35 if small else .9)
                ax.plot(r.rho, y0 + off, "o", ms=5, mfc="white" if small else COL[sub], mec=COL[sub])
            p = c[(c["sub"] == f"{grp} pooled") & (c.test == tc) & (c.outcome == oc)]
            if len(p) and np.isfinite(p.rho.iloc[0]):
                ax.plot(p.rho.iloc[0], y0, "D", ms=4, mfc="none", mec=COL["pooled"])
            if (tc, oc) in it.index and it.loc[(tc, oc), "p_int"] < 0.05 and it.loc[(tc, oc), "verdict"] != "TOO FEW TO TELL":
                ax.text(1.02, y0, "Δ", color="#CC0000", fontsize=9, fontweight="bold", va="center", transform=ax.get_yaxis_transform())
        ax.axvline(0, color="#333", lw=.8); ax.set_xlim(-1, 1); ax.set_title("\n".join(textwrap.wrap(ol, 26)), fontsize=8.5)
        ax.set_xlabel("ρ, size held fixed")
    axes[0].set_yticks(ys); axes[0].set_yticklabels([tl for _, tl, _ in TESTS])
    h = [Line2D([], [], marker="o", color=COL[a], label=a), Line2D([], [], marker="o", color=COL[b], label=b),
         Line2D([], [], marker="D", ls="", mfc="none", mec=COL["pooled"], label=f"{grp} pooled (role held fixed)"),
         Line2D([], [], marker="o", ls="", mfc="white", mec="#888", label="hollow = under 25 players"),
         Line2D([], [], marker="$Δ$", ls="", color="#CC0000", label="slopes differ, p < 0.05 (lead only)")]
    fig.legend(handles=h, loc="lower center", ncol=5, fontsize=8, frameon=False)
    name = {"DB": "Safeties vs corners", "DL": "Edge rushers vs interior linemen"}[grp]
    fig.suptitle(f"{name}: does the same Combine number mean the same thing on Sunday?\n"
                 "Right of zero = the better athlete does better. Bars = 95% bootstrap interval.", fontsize=10)
    fig.tight_layout(rect=(0, .05, .97, 1)); fig.savefig(path); plt.show()


def fig_diff(ints, path, top=12):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    for ax, grp in zip(axes, ["DB", "DL"]):
        a, b, _ = PAIRS[grp]
        d = ints[(ints.group == grp) & ints["diff"].notna() & (ints[["n_a", "n_b"]].min(axis=1) >= 25)].sort_values("p_int").head(top)[::-1]
        y = np.arange(len(d))
        m = d.mde_diff.median()
        ax.axvspan(-m, m, color="#eeeeee", zorder=0)
        col = np.where(d.verdict == "REAL DIFFERENCE", "#009E73", np.where(d.verdict.str.startswith("LEAD"), "#E69F00", "#7f7f7f"))
        ax.hlines(y, d.diff_lo, d.diff_hi, color=col, lw=1.6); ax.scatter(d["diff"], y, c=col, zorder=3, s=22)
        ax.set_yticks(y); ax.set_yticklabels([f"{TL[t]} → {o.split(' (')[0]}" for t, o in zip(d.test, d.outcome_label)], fontsize=7.5)
        ax.axvline(0, color="#333", lw=.8); ax.set_xlabel(f"ρ({a}) − ρ({b}), size held fixed")
        ax.set_title(f"{a} vs {b}: {top} biggest gaps\n(grey = too small to detect, MDE ≈ {m:.2f})", fontsize=9.5)
    fig.legend(handles=[Patch(color="#E69F00", label="LEAD (p < 0.05, q ≥ 0.05)"), Patch(color="#7f7f7f", label="NOT DETECTED (low power)")],
               loc="lower center", ncol=2, frameon=False, fontsize=8)
    fig.suptitle("Do the subgroups really differ? Interaction tests (Freedman–Lane, 10,000 permutations)", fontsize=10)
    fig.tight_layout(rect=(0, .05, 1, .96)); fig.savefig(path); plt.show()
