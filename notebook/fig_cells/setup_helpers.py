# shared style: one verdict palette (Okabe-Ito, colour-blind safe) used by every figure; readable at Kaggle width (about 8.5 in wide, 9 pt+)
VCOL = {"TRANSLATES": "#009E73", "LEANS": "#E69F00", "SIZE, NOT SPEED": "#CC79A7", ND: "#7f7f7f", "TOO FEW TO TELL": "#bdbdbd"}
plt.rcParams.update({"font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5, "xtick.labelsize": 9, "ytick.labelsize": 9, "figure.dpi": 110, "savefig.dpi": 150})

def draw_ci(ax, y, lo, hi, n, col, lw=2.4, alpha=1.0):
    """95% interval; hidden below 15 players (the bootstrap is unreliable there) and flagged on the plot."""
    if n < 15 or not np.isfinite(lo) or not np.isfinite(hi):
        ax.text(0.02, y, "interval not shown (n<15)", fontsize=7.5, color=col, va="center"); return
    ax.plot([lo, hi], [y, y], color=col, lw=lw, alpha=alpha, solid_capstyle="round")

def tag(n, q, extra=""):
    return f"n {int(n)} · q {qtxt(q)}" + (f" · {extra}" if extra else "")

import textwrap
def finish(fig, name, title, foot="", legend=None, rect_lr=(0.0, 1.0), top_pad=0.0):
    """Left-aligned takeaway title, optional legend row under it, wrapped footnote at the bottom, then save. Keeps text inside the canvas."""
    W, H = fig.get_size_inches(); line = 0.135 / H
    lines = textwrap.wrap(foot, int(W * 14.5)) if foot else []
    if lines: fig.text(.01, .006, "\n".join(lines), fontsize=7.5, color="#444", va="bottom")
    fig.suptitle(title, x=.01, y=1 - .06 / H, ha="left", va="top", fontweight="bold", fontsize=10.5)
    top = 1 - (.40 if legend else .30) / H - top_pad
    if legend: fig.legend(legend[0], legend[1], loc="upper left", bbox_to_anchor=(0.01, 1 - .30 / H), ncol=legend[2] if len(legend) > 2 else 3, fontsize=8.5, frameon=False, handletextpad=.4, columnspacing=1.2)
    fig.tight_layout(rect=(rect_lr[0], .006 + line * len(lines) + .01, rect_lr[1], top)); fig.savefig(SAVE / name); plt.show()
