"""fig21: WR break-route lead re-test (forest plots, size-controlled). Reads out/wr_route_lead_{cells,contrasts}.csv."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dl_recheck import OUT

c = pd.read_csv(OUT / "wr_route_lead_cells.csv"); k = pd.read_csv(OUT / "wr_route_lead_contrasts.csv")
COL = {"break": "#0072B2", "vertical": "#D55E00", "man_all": "#CC3311", "zone_all": "#0077BB",
       "screen": "#009E73", "crosser": "#AA3377", "man_break": "#CC3311", "zone_break": "#0077BB"}
NAME = {"three_cone": "3-cone", "short_shuttle": "Short shuttle", "ten_yd_split": "Official 10-yard", "vertical": "Vertical jump",
        "burst_0_100": "Burst Score", "combine_weight": "Weight"}


def forest(ax, rows, title, ylabels_extra=None):
    y = 0; ticks, labs = [], []
    for grp in rows:
        for test, split, lab in grp:
            r = c[(c.test == test) & (c.split == split) & (c.group != "sens" if split.endswith("break") is False else True)]
            r = r.iloc[0]
            col = COL[split]
            ax.plot([r.lo, r.hi], [y, y], color=col, lw=2.2, solid_capstyle="round")
            ax.plot(r.rho_size, y, "o", color=col, ms=7, mec="white", zorder=3)
            ticks.append(y); labs.append(f"{NAME[test]} → {lab}\nn={int(r.n)}  q={r.fdr:.2f}")
            y -= 1
        y -= 0.6
    ax.axvline(0, color="#666", lw=0.8)
    ax.set_yticks(ticks); ax.set_yticklabels(labs, fontsize=8)
    ax.set_xlim(-0.85, 0.85); ax.set_xlabel("size-controlled rank partial ρ (95% bootstrap CI); + = better test, more separation", fontsize=8)
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold"); ax.grid(axis="x", alpha=0.25)


fig, axs = plt.subplots(2, 2, figsize=(14, 10.5)); a, b, d, e = axs.ravel()
forest(a, [[(t, "break", "break routes"), (t, "vertical", "vertical routes")] for t in ["three_cone", "short_shuttle", "vertical", "burst_0_100"]],
       "A. Route family (H1, H2): blue = break, orange = vertical")
forest(b, [[(t, "man_all", "vs man"), (t, "zone_all", "vs zone")] for t in ["three_cone", "short_shuttle", "ten_yd_split"]],
       "B. Coverage (H3): red = man, blue = zone")
# C: contrasts
rows = [("H1", "three_cone", "3-cone: break − vertical"), ("H1", "short_shuttle", "Shuttle: break − vertical"),
        ("H3", "three_cone", "3-cone: man − zone"), ("H3", "short_shuttle", "Shuttle: man − zone"), ("H3", "ten_yd_split", "10-yard: man − zone"),
        ("H2-ctx", "vertical", "Vert. jump: break − vertical (context)"), ("H2-ctx", "burst_0_100", "Burst: break − vertical (context)"),
        ("S1", "combine_weight", None)]
y = 0; ticks, labs = [], []
for hyp, test, lab in rows:
    sub = k[(k.hyp == hyp) & (k.test == test)]
    for _, r in sub.iterrows():
        l = lab or f"Weight: {r.contrast}"
        col = "#222222" if hyp in ("H1", "H3") else "#888888"
        d.plot([r.lo, r.hi], [y, y], color=col, lw=2.2); d.plot(r["diff"], y, "s", color=col, ms=7, mec="white", zorder=3)
        v = r.verdict if isinstance(r.verdict, str) else ""
        q = f"  q={r.q_bh5:.2f}" if np.isfinite(r.q_bh5) else ""
        ticks.append(y); labs.append(f"{l}\nn={int(r.n)}  swap p={r.p_swap:.3f}{q}  {v}")
        y -= 1
    y -= 0.3
d.axvline(0, color="#666", lw=0.8); d.set_yticks(ticks); d.set_yticklabels(labs, fontsize=8); d.set_xlim(-1.1, 1.1)
d.set_xlabel("difference in partial ρ, paired bootstrap 95% CI (predicted: > 0 for H1, H3)", fontsize=8)
d.set_title("C. Formal contrasts (what H1 and H3 actually claim); grey = context", loc="left", fontsize=10, fontweight="bold"); d.grid(axis="x", alpha=0.25)
# D: weight cost
y = 0; ticks, labs = [], []
for s, lab in [("screen", "screens"), ("crosser", "crossers"), ("break", "break routes"), ("vertical", "vertical routes")]:
    r = c[(c.test == "combine_weight") & (c.split == s)].iloc[0]
    e.plot([r.lo, r.hi], [y, y], color=COL[s], lw=2.2); e.plot(r.rho_size, y, "o", color=COL[s], ms=7, mec="white", zorder=3)
    ticks.append(y); labs.append(f"Weight → {lab}\nn={int(r.n)}  p={r.p_perm:.3f}  q={r.fdr:.2f}"); y -= 1
e.axvline(0, color="#666", lw=0.8); e.set_yticks(ticks); e.set_yticklabels(labs, fontsize=8); e.set_xlim(-0.85, 0.85)
e.set_xlabel("rank partial ρ controlling draft year and height (95% bootstrap CI)", fontsize=8)
e.set_title("D. Secondary S1: does weight cost separation?", loc="left", fontsize=10, fontweight="bold"); e.grid(axis="x", alpha=0.25)
fig.suptitle("WR break-route lead re-test: route-family and man/zone effects of Combine tests (separation vs route/coverage average, EB-shrunk)",
             fontsize=12, fontweight="bold", x=0.01, ha="left")
fig.text(0.01, 0.005, "Controls: draft year, weight, height (minus the test). Draft slot never used. Same 2023–25 sample as the original lead, so a re-test not a replication. "
         "3-cone/shuttle exist for only ~21–30 WRs. q = BH-FDR across the 14 primary cells (A–B), 4 cells (D).", fontsize=7.5, ha="left", wrap=True)
fig.tight_layout(rect=(0, 0.02, 1, 0.96))
fig.savefig(OUT / "figs" / "fig21_wr_route_lead.png", dpi=150); print("wrote fig21")
