#!/usr/bin/env python3
"""Step 6: figures (aggregate views only; no player names). Writes figs/u_fig*.png."""
from __future__ import annotations
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from common import CACHE, OUT, FIGS, GROUPS, SEED
import pipe as P

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
ARCH_NAME = {("WR", "ALL"): {0: "Lean burner", 1: "Big-bodied"}, ("TE", "ALL"): {0: "Slower in-line build", 1: "Explosive move build"},
             ("DB", "ALL"): {0: "Explosive, lighter", 1: "Bigger, less explosive"}, ("DL", "ALL"): {0: "Lean explosive (edge build)", 1: "Heavy anchor (interior build)"},
             ("WR", "SIZEADJ"): {0: "Fast for his size", 1: "Slow for his size"}, ("TE", "SIZEADJ"): {0: "Slow for his size", 1: "Fast for his size"},
             ("DB", "SIZEADJ"): {0: "Fast for his size", 1: "Slow for his size"}, ("DL", "SIZEADJ"): {0: "Slow for his size", 1: "Fast for his size"}}
PC_NAME = {"WR": {1: "Size (bigger, slower)", 2: "Tracked launch (mostly 10 Hz noise)", 3: "Long speed + jumps"},
           "TE": {1: "Speed + jumps", 2: "Bulk + hands vs launch", 3: "Tracked launch"},
           "DB": {1: "Speed + jumps (lighter)", 2: "Tracked launch + bulk", 3: "Length (height, arms)"},
           "DL": {1: "All-round athleticism (lighter, faster, jumps)", 2: "Tracked launch", 3: "Length (arms, height)"}}
OUTS = {"sunday_speed_mph": "Game speed (mph)", "sep_all_mean": "Separation, all routes", "break_y": "Separation, break routes",
        "tackle_rate": "Tackle rate", "tfl_rate": "TFL rate", "close_rate_mph": "Closing speed", "pfr_yds_tgt": "Yds/target allowed (lower better)",
        "pfr_mtkl_pct": "Missed-tackle % (lower better)", "pressure_rate": "Pressure rate", "sack_rate": "Sack rate", "run_stop_rate": "Run-stop rate",
        "speed_1s_mph": "Get-off speed at 1 s"}
UNITS = {"sunday_speed_mph": "mph", "sep_all_mean": "yards", "break_y": "yards vs expected (shrunk)", "pressure_rate": "pressures per pass rush",
         "sack_rate": "sacks per pass rush", "pfr_yds_tgt": "yards per target", "close_rate_mph": "mph", "tfl_rate": "TFL per snap",
         "tackle_rate": "tackles per snap", "pfr_mtkl_pct": "missed-tackle %", "run_stop_rate": "run stops per run snap", "speed_1s_mph": "mph"}
C2 = ["#1f77b4", "#e66100", "#5e3c99"]   # blue / orange / purple: colourblind-safe


def fig_biplot(cf, arch):
    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    for ax, g in zip(axs.flat, GROUPS):
        df = cf[cf.group == g].reset_index(drop=True)
        ids, X, f = P.prepare(df, g, "ALL")
        pca = PCA().fit(X); S = pca.transform(X); ev = pca.explained_variance_ratio_
        lab = arch[(arch.group == g) & (arch.fset == "ALL")].set_index("nfl_id").arch.loc[ids].to_numpy()
        for a in np.unique(lab):
            ax.scatter(S[lab == a, 0], S[lab == a, 1], s=18, alpha=.6, color=C2[a], label=f"{ARCH_NAME[(g, 'ALL')][a]} (n={int((lab == a).sum())})")
        L = pca.components_[:2].T; sc = np.abs(S[:, :2]).max() * 0.85 / np.abs(L).max()
        top = np.argsort(-(L ** 2).sum(1))[:8]
        for i in top:
            ax.arrow(0, 0, L[i, 0] * sc, L[i, 1] * sc, color="k", alpha=.6, head_width=.08, length_includes_head=True)
            ax.text(L[i, 0] * sc * 1.08, L[i, 1] * sc * 1.08, P.LABEL[f[i]], fontsize=8)
        ax.axhline(0, c="0.85", lw=.8); ax.axvline(0, c="0.85", lw=.8)
        ax.set_xlabel(f"PC1 {PC_NAME[g][1]} ({ev[0]:.0%})"); ax.set_ylabel(f"PC2 {PC_NAME[g][2]} ({ev[1]:.0%})", fontsize=9)
        ax.set_title(f"{g}: n={len(X)}", loc="left", fontweight="bold"); ax.legend(fontsize=8, loc="lower right", frameon=False)
    fig.suptitle("Combine profiles by position: PCA biplot (standardised within group, Combine data only)\nArrows = the 8 heaviest loadings; colour = the only stable split (k = 2)", x=.01, ha="left")
    fig.tight_layout(); fig.savefig(FIGS / "u_fig1_pca_biplot.png", bbox_inches="tight"); plt.close(fig)


def fig_types():
    s = pd.read_csv(OUT / "cluster_selection.csv"); nl = pd.read_csv(OUT / "cluster_null.csv")
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    ax = axs[0]
    km = s[(s.method == "kmeans") & (s.fset == "ALL")]
    for i, g in enumerate(GROUPS):
        d = km[km.group == g]; ax.plot(d.k, d.boot_ari_median, ["o-", "s--", "^-", "D-."][i], color=["#1f77b4", "#e66100", "#5e3c99", "#222222"][i], label=g)
    ax.axhline(.6, ls="--", c="k", lw=1); ax.text(6.05, .6, "stable\n(ARI 0.6)", fontsize=8, va="center")
    ax.set_xlabel("number of archetypes (k-means k)"); ax.set_ylabel("bootstrap stability (median ARI)"); ax.set_ylim(0, 1)
    ax.set_title("Only 2-way splits are stable", loc="left", fontweight="bold"); ax.legend(frameon=False)
    ax = axs[1]
    d = nl[(nl.fset == "ALL")]
    x = np.arange(len(GROUPS)); w = .25
    for j, k in enumerate((2, 3, 4)):
        e = d[d.k == k].set_index("group").loc[GROUPS]
        ax.bar(x + (j - 1) * w, e.sil_obs, w, color=C2[j], alpha=.8, label=f"k={k} real data")
        ax.errorbar(x + (j - 1) * w, e.sil_null_median, yerr=[np.zeros(4), e.sil_null_95 - e.sil_null_median], fmt="_", c="k", capsize=3)
        for xi, (_, r) in zip(x, e.iterrows()):
            if r.p_one_blob < 0.05:
                ax.text(xi + (j - 1) * w, r.sil_obs + .01, "*", ha="center", fontsize=14)
    ax.set_xticks(x, GROUPS); ax.set_xlabel("Position group"); ax.set_ylabel("silhouette (higher = more distinct types)")
    ax.set_title("Real data vs one continuous blob (black = blob median to 95th pct)", loc="left", fontweight="bold", fontsize=10)
    ax.legend(frameon=False, fontsize=8); ax.text(0, -.24, "* = more distinct than a single blob (p < 0.05).\nOnly DL k = 2 (edge build vs interior build) and an unstable WR k = 3 qualify.",
                                                   transform=ax.transAxes, fontsize=8)
    fig.tight_layout(rect=(0, .08, 1, 1)); fig.savefig(FIGS / "u_fig2_types_or_continuum.png", bbox_inches="tight"); plt.close(fig)


def fig_centroids():
    c = pd.read_csv(OUT / "archetype_centroids.csv"); c = c[c.fset == "ALL"]
    fig, axs = plt.subplots(1, 4, figsize=(16, 5.5), sharey=False)
    for ax, g in zip(axs, GROUPS):
        d = c[c.group == g].pivot_table(index="label", columns="arch", values="z")
        d = d.loc[d.abs().max(axis=1).sort_values().index]
        y = np.arange(len(d))
        for a in d.columns:
            n = int(c[(c.group == g) & (c.arch == a)].n_arch.iloc[0])
            ax.barh(y + (a - .5) * .4, d[a], .4, color=C2[a], label=f"{ARCH_NAME[(g, 'ALL')][a]} (n={n})")
        ax.set_yticks(y, d.index, fontsize=8); ax.axvline(0, c="k", lw=.8); ax.set_xlabel("archetype average (SD from position mean)")
        ax.set_title(g, loc="left", fontweight="bold"); ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    fig.suptitle("What the two Combine archetypes look like (centroids; times flipped so right = more athletic)", x=.01, ha="left")
    fig.tight_layout(); fig.savefig(FIGS / "u_fig3_archetype_centroids.png", bbox_inches="tight"); plt.close(fig)


def fig_arch_outcome():
    a = pd.read_csv(OUT / "familyA.csv"); s = pd.read_csv(OUT / "archetype_outcome_summary.csv")
    a = a[(a.tag == "pre-registered")]
    rows = [(g, fs, o) for g, fs, o in a[["group", "fset", "outcome"]].itertuples(index=False)]
    sel = [("WR", "ALL", "sunday_speed_mph"), ("WR", "ALL", "sep_all_mean"), ("WR", "SIZEADJ", "sunday_speed_mph"), ("WR", "SIZEADJ", "break_y"),
           ("DL", "ALL", "pressure_rate"), ("DL", "SIZEADJ", "pressure_rate"), ("DL", "SIZEADJ", "sack_rate"), ("DB", "ALL", "pfr_yds_tgt"),
           ("DB", "SIZEADJ", "close_rate_mph"), ("TE", "SIZEADJ", "sep_all_mean")]
    fig, axs = plt.subplots(2, 5, figsize=(17, 7.5))
    for ax, (g, fs, o) in zip(axs.flat, sel):
        r = a[(a.group == g) & (a.fset == fs) & (a.outcome == o)].iloc[0]
        d = s[(s.group == g) & (s.fset == fs) & (s.outcome == o) & (s.tag == "pre-registered")]
        for _, e in d.iterrows():
            ax.errorbar(e.arch, e["median"], yerr=[[e["median"] - e.boot_lo], [e.boot_hi - e["median"]]], fmt="o", ms=8, color=C2[int(e.arch)], capsize=5)
            ax.text(e.arch, e.boot_hi, f" n={e.n}", fontsize=8, va="bottom", ha="center")
        ax.set_xticks(d.arch, [ARCH_NAME[(g, fs)][int(k)].replace(" (", "\n(") for k in d.arch], fontsize=7.5); ax.set_xlim(-.6, 1.6)
        ax.set_ylabel(f"median {UNITS[o]} (95% CI)", fontsize=8.5)
        ax.set_title(f"{g} {'size-adj.' if fs == 'SIZEADJ' else 'all'}: {OUTS[o]}", loc="left", fontsize=9, fontweight="bold")
        held = "yes" if (r.loso_p < .05 and r.loso_classes_pos >= 2 and r.loso_rho > 0) else "no"
        ax.text(.02, -.32, f"beyond size p={r.p_size:.3f} (q={r.q_size:.2f})\nheld-out class rho={r.loso_rho:+.2f}, passes: {held}", transform=ax.transAxes, fontsize=7.5)
    fig.suptitle("Archetype medians with 95% bootstrap CIs (as-reported outcome). Selected pre-registered rows; full table in out/familyA.csv", x=.01, ha="left")
    fig.tight_layout(); fig.savefig(FIGS / "u_fig4_archetype_vs_outcome.png", bbox_inches="tight"); plt.close(fig)


def fig_crosstab():
    ct = pd.read_csv(OUT / "crosstab_counts.csv"); t = pd.read_csv(OUT / "crosstab_tests.csv"); gc = pd.read_csv(OUT / "game_style_centroids.csv")
    SN = {"WR": {0: "Vertical outside\n(deep routes, big cushion,\nhard cuts)", 1: "Pressed outside\n(tight cushion,\nsoft cuts)", 2: "Slot / short\n(short routes,\nlower deep speed)"},
          "TE": {0: "Flexed to slot", 1: "In-line, short\nroutes", 2: "1-player\noutlier"},
          "DB": {0: "Deep / zone\n(high safety,\nbig cushion)", 1: "Man / press\n(tight, faster)"},
          "DL": {0: "Edge rusher\n(fast first second)", 1: "Interior\n(slower first second)"}}
    style_name = lambda g, k: SN[g][k]
    fig, axs = plt.subplots(2, 2, figsize=(13, 9.5), gridspec_kw=dict(wspace=.55, hspace=.75))
    for ax, g in zip(axs.flat, GROUPS):
        m = ct[ct.group == g].pivot_table(index="combine_arch", columns="game_style", values="count", fill_value=0)
        sh = m.div(m.sum(axis=1), axis=0)
        im = ax.imshow(sh, cmap="Blues", vmin=0, vmax=1)
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, f"{int(m.iloc[i, j])}\n({sh.iloc[i, j]:.0%})", ha="center", va="center", fontsize=9, color="k" if sh.iloc[i, j] < .6 else "w")
        ax.set_xlabel("In-game style (game movement + deployment cluster)", fontsize=9)
        ax.set_ylabel("Combine archetype", fontsize=9)
        ax.set_yticks(range(m.shape[0]), [ARCH_NAME[(g, "ALL")][k].replace(" (", "\n(") for k in m.index], fontsize=8.5)
        ax.set_xticks(range(m.shape[1]), [style_name(g, k) for k in m.columns], fontsize=8.5)
        r = t[t.group == g].iloc[0]
        ax.set_title(f"{g} (n={r.n}): ARI {r.ari:.2f}, q={r.q_ari:.3f}{'' if r.style_stable else ' (styles unstable)'}", loc="left", fontsize=9, fontweight="bold")
    cb = fig.colorbar(im, ax=list(axs.flat), fraction=.025, pad=.03)
    cb.set_label("Share of the archetype's players\nin each game style (row %)", fontsize=9); cb.ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    fig.suptitle("Combine archetype (rows) vs in-game movement/deployment style (columns)\nCell = number of players (row %); shading = row %", x=.01, ha="left")
    fig.savefig(FIGS / "u_fig5_combine_vs_game_style.png", bbox_inches="tight"); plt.close(fig)


def fig_forest():
    b = pd.read_csv(OUT / "familyB.csv"); b = b[b.group != "TE"].copy()
    b["name"] = [f"{g} PC{p} {PC_NAME[g][p]} -> {OUTS[o]}" for g, p, o in b[["group", "pc", "outcome"]].itertuples(index=False)]
    b = b.sort_values("rho_size")
    fig, ax = plt.subplots(figsize=(10, 13))
    y = np.arange(len(b))
    held = (b.loso_p < .05) & (b.loso_classes_pos >= 2) & (b.loso_rho > 0)
    col = np.where(b.q_size < .05, "#1f4e9c", np.where(b.p_size < .05, "#e66100", "0.6"))
    ax.hlines(y, b.lo, b.hi, color=col); ax.scatter(b.rho_size, y, c=col, s=np.where(held, 60, 20), zorder=3, edgecolor=np.where(held, "k", "none"))
    ax.axvline(0, c="k", lw=.8); ax.set_yticks(y, b.name, fontsize=7)
    ax.set_xlabel("rank partial correlation, draft year + weight + height (+ role) held fixed; 95% bootstrap CI")
    ax.set_title("Latent Combine axes vs game outcomes (Family B)\ndark blue = q < 0.05, orange = p < 0.05 only, grey = not detected\nbig black-edged dot = training-class fit also ranks the held-out class (either sign)", loc="left", fontsize=9)
    fig.tight_layout(); fig.savefig(FIGS / "u_fig6_latent_axes_forest.png", bbox_inches="tight"); plt.close(fig)


def fig_quality():
    r = pd.read_csv(OUT / "drill_reliability.csv"); ph = pd.read_csv(OUT / "posthoc.csv")
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.4), gridspec_kw=dict(wspace=.9, width_ratios=[1, 1.1]))
    ax = axs[0]
    piv = r.pivot_table(index="feature", columns="group", values="alpha_k")[GROUPS]
    names = {"drill_top": "peak speed", "drill_acc": "peak accel", "drill_dec": "braking", "drill_keep": "speed kept in cuts", "drill_turn": "turn rate", "drill_dur": "duration"}
    im = ax.imshow(piv.clip(-.2, 1), cmap="viridis", vmin=-.2, vmax=1)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.iloc[i, j]
            ax.text(j, i, f"{v:.2f}" + (" *" if v >= .6 else ""), ha="center", va="center", fontsize=9, color="k" if v > .45 else "w",
                    fontweight="bold" if v >= .6 else "normal")
    ax.set_xticks(range(4), GROUPS); ax.set_yticks(range(len(piv)), [names[i] for i in piv.index])
    ax.set_xlabel("Position group"); ax.set_ylabel("Skill-drill movement trait (tracking)")
    cb = fig.colorbar(im, ax=ax, fraction=.06, pad=.05, ticks=[-.2, 0, .2, .4, .6, .8, 1.0])
    cb.ax.set_yticklabels(["-0.2", "0.0", "0.2", "0.4", "0.6 trustworthy", "0.8", "1.0"], fontsize=8.5)
    cb.set_label("Reliability (Cronbach's alpha): how consistently\na trait repeats across drills", fontsize=9)
    cb.ax.axhline(.6, color="#e66100", lw=3)
    ax.set_title("Skill-drill tracking: does the trait repeat across drills?\n(* = alpha 0.6 or more, used; below = drill noise, not used)", loc="left", fontsize=9, fontweight="bold")
    ax = axs[1]
    d = ph[ph.check.str.startswith("3 ") & ph.check.str.contains("f40_s1 vs ten_fast")]
    d2 = ph[ph.check.str.startswith("3 ") & ph.check.str.contains("f40_acc vs ten_fast")]
    x = np.arange(4)
    ax.bar(x - .2, d.rho, .4, label="tracked speed 1 s into the 40", color=C2[0]); ax.bar(x + .2, d2.rho, .4, label="tracked peak accel in the 40", color=C2[1])
    ax.set_xticks(x, GROUPS); ax.axhline(0, c="k", lw=.8); ax.set_ylim(-.1, 1); ax.set_xlabel("Position group")
    ax.set_ylabel("Spearman ρ with official 10-yd split\n(faster split = higher; 1 = perfect agreement)")
    ax.set_title("Tracked 'launch' barely agrees with the official 10-yd split\n(10 Hz frames are too coarse for the first step, except heavier DL)", loc="left", fontsize=9, fontweight="bold")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(FIGS / "u_fig7_tracking_reliability.png", bbox_inches="tight"); plt.close(fig)


def fig_tsne(cf, arch):
    fig, axs = plt.subplots(1, 4, figsize=(16, 4))
    for ax, g in zip(axs, GROUPS):
        df = cf[cf.group == g].reset_index(drop=True); ids, X, _ = P.prepare(df, g, "ALL")
        E = TSNE(2, perplexity=min(15, len(X) // 4), random_state=SEED, init="pca").fit_transform(X)
        lab = arch[(arch.group == g) & (arch.fset == "ALL")].set_index("nfl_id").arch.loc[ids].to_numpy()
        for a in np.unique(lab):
            ax.scatter(E[lab == a, 0], E[lab == a, 1], s=12, color=C2[a], alpha=.7, label=ARCH_NAME[(g, "ALL")][a])
        ax.set_xticks([]); ax.set_yticks([]); ax.set_title(g, loc="left", fontweight="bold"); ax.legend(fontsize=7, frameon=False)
    fig.suptitle("t-SNE picture only (not used for any test): one cloud per position, with DL the exception", x=.01, ha="left")
    fig.tight_layout(); fig.savefig(FIGS / "u_fig8_tsne_picture.png", bbox_inches="tight"); plt.close(fig)


def main():
    cf = pd.read_parquet(CACHE / "combine_features.parquet"); arch = pd.read_parquet(CACHE / "archetypes.parquet")
    fig_biplot(cf, arch); fig_types(); fig_centroids(); fig_arch_outcome(); fig_crosstab(); fig_forest(); fig_quality(); fig_tsne(cf, arch)


if __name__ == "__main__":
    main()
