"""Figure 20: forest plot, each Combine test vs the primary outcome per position group.

Two estimates per test: year-controlled Spearman on the same outcome as the size-controlled fit (grey, open; corrected 11/2026, was a plain pooled Spearman, then an as-reported-rate version that mixed outcomes) and the size-controlled rank partial
correlation (colour; controls = draft year, role, weight, height). 95% bootstrap CIs.
Orientation: timed drills are sign-flipped so RIGHT of zero always means "better athlete goes
with the higher outcome". No draft slot is used anywhere.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scorecard import _frames, year_raw
from dl_recheck import OUT, FIGS, FIG19_ROW_LABELS, SPEED_AGILITY, POWER_SIZE, FLIP_TESTS

LABELS = {**FIG19_ROW_LABELS, "combine_weight": "Weight ‡", "combine_height": "Height ‡",
          "c_decel": "Combine Brakes (DB drill)", "c_accel": "Combine Re-Burst (DB drill)"}
ORDER = SPEED_AGILITY + POWER_SIZE + ["c_decel", "c_accel"]
PANELS = [  # (group, outcome, title, colour)
    ("DL", "pressure_rate", "DL  ·  pressure rate (shrunk)", "#c0392b"),
    ("DL", "tfl_rate", "DL  ·  TFL rate (shrunk)", "#e67e22"),
    ("WR", "sep_all_mean", "WR  ·  route separation (all routes)", "#1f77b4"),
    ("WR", "sep_brk_mean", "WR  ·  route separation (break routes)", "#0b4f8a"),
    ("TE", "sep_all_mean", "TE  ·  route separation (all routes)", "#8e44ad"),
    ("DB", "tackle_rate", "DB (CB + S)  ·  tackle rate (shrunk)", "#2e8b57"),
]


def forest(path=None):
    t = pd.concat([pd.read_csv(OUT / "dl_robust_tests.csv"), pd.read_csv(OUT / "pos_robust_tests.csv")], ignore_index=True)
    fig, axes = plt.subplots(2, 3, figsize=(25, 15.5), sharex=True)
    for ax, (g, oc, title, col) in zip(axes.ravel(), PANELS):
        p = t[(t.group == g) & (t.outcome == oc)].set_index("test").copy()
        fr = _frames()[("DL", "All") if g == "DL" else (g, "All")]
        for r_ in p.index:  # hollow marker = year-controlled Spearman on the same outcome (METRICS §9 corrections)
            p.loc[r_, ["rho_raw", "raw_lo", "raw_hi"]] = year_raw(fr, r_, oc)[:3]
        rows = [r for r in ORDER if r in p.index and np.isfinite(p.loc[r, "rho_size"])]
        ys = np.arange(len(rows))[::-1]
        for y, r in zip(ys, rows):
            q = p.loc[r]; f = -1.0 if r in FLIP_TESTS else 1.0
            for off, (rho, lo, hi, c, mk, fill) in {
                0.17: (q.rho_raw, q.raw_lo, q.raw_hi, "#8a8a8a", "D", "white"),
                -0.17: (q.rho_size, q.lo, q.hi, col, "o", col)}.items():
                a, b = sorted([lo * f, hi * f])
                ax.plot([a, b], [y + off] * 2, color=c, lw=2.2 if off < 0 else 1.4, solid_capstyle="butt", alpha=.95)
                ax.plot(rho * f, y + off, mk, color=c, mfc=fill, mec=c, ms=7.5 if off < 0 else 5.5, zorder=3)
        ax.set_yticks(ys); ax.set_yticklabels([f"{LABELS[r]}   n={int(p.loc[r, 'n'])}" + {"SURVIVES": "  ★", "LEAN": "  ◆", "small n": "  (small n)"}.get(p.loc[r, "verdict"], "") for r in rows], fontsize=8.8)
        ax.axvline(0, color="#222", lw=1)
        ax.set_xlim(-1.0, 1.0); ax.grid(axis="x", alpha=.3); ax.set_ylim(-0.8, len(rows) - 0.2)
        ax.set_title(title, fontsize=11.5, fontweight="bold", loc="left")
        ax.set_xlabel("Spearman ρ  (→ better athlete goes with higher outcome)", fontsize=8.8)
        ax.tick_params(axis="x", labelbottom=True)
    h = [plt.Line2D([], [], color="#8a8a8a", marker="D", mfc="white", lw=1.4, label="Year-controlled Spearman ρ (before size control)"),
         plt.Line2D([], [], color="#333", marker="o", lw=2.2, label="Size-controlled ρ (year, role, weight, height)")]
    fig.legend(handles=h, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 0.955), frameon=False, fontsize=10)
    fig.suptitle("Which Combine tests still matter once body size is held fixed?", fontsize=15, fontweight="bold", y=0.985)
    fig.text(0.5, 0.012,
             "Bars = 95% player-level bootstrap CI (2,000 resamples).  Timed drills sign-flipped (faster = right).  ‡ weight / height are controlled for the other size measure only.\n"
             "★ passes every check (FDR<0.05 within its group, CI excludes 0, unshrunk sign, leave-one-class-out).  ◆ nominal only (permutation p<0.05 + CI + out-of-sample) — FDR not cleared.   small-n rows (n<25 or <5 players per fitted parameter) are shown but not scored.\n"
             "Rates are shrunk toward the role mean (beta-binomial) in both marker types.  FDR families differ in size by group (DL 273 cells, WR 68, DB 152), so stars are not comparable across groups.  Draft slot / pick / round never used.  2023–2025 rookie classes, REG snaps.",
             ha="center", fontsize=8.2)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    path = path or FIGS / "fig20_forest_size_controlled.png"
    fig.savefig(path, dpi=150); plt.close(fig)
    return path


if __name__ == "__main__":
    print(forest())
