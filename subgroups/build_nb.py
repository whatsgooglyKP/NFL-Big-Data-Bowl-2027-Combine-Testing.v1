"""Builds bdb2027_subgroups_prelim.ipynb from subgroups_lib.py + subgroups_figs.py + the text in notebook_text.md."""
import nbformat as nbf, re
from pathlib import Path
H = Path(__file__).parent
lib = (H / "subgroups_lib.py").read_text()
figs = (H / "subgroups_figs.py").read_text()
txt = (H / "notebook_text.md").read_text()
sec = dict(re.findall(r"<!-- (\w+) -->\n(.*?)(?=\n<!-- |\Z)", txt, flags=re.S))
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md(sec["intro"]),
    code("# ---- methods library (same engines as the main entry; raw competition files only) ----\n" + lib),
    code("# ---- figure helpers ----\n" + figs),
    code('''from pathlib import Path
from IPython.display import display
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)
OUTDIR = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path("out_sub")
FIGDIR = OUTDIR / "figs"; FIGDIR.mkdir(parents=True, exist_ok=True)
P = build()          # per-player table: kept in memory only, never written to disk'''),
    md(sec["who"]),
    code('''ns = sample_sizes(P)
display(ns.round(2))
fig_power(ns, FIGDIR / "sub_fig1_sample_power.png")'''),
    code('''t0 = time.time()
cells = run_cells(P)
ints = run_interactions(P)
print(f"all tests: {time.time() - t0:.0f}s | {len(cells)} subgroup cells, {len(ints)} interaction tests")
# aggregate results only: no player IDs, names or per-player rows
keep_c = ["group", "sub", "test_label", "outcome_label", "tracking", "n", "rho_year", "rho", "lo", "hi", "p", "q",
          "ho_dr2", "ho_pos", "ho_folds", "ho_p", "held_out_ok", "mde80", "verdict"]
keep_i = ["group", "sub_a", "sub_b", "test_label", "outcome_label", "tracking", "n_a", "n_b", "rho_a", "rho_b", "diff",
          "diff_lo", "diff_hi", "p_int", "q_int", "mde_diff", "verdict"]
assert "nfl_id" not in cells.columns and "nfl_id" not in ints.columns
cells[keep_c].to_csv(OUTDIR / "subgroup_cells.csv", index=False)
ints[keep_i].to_csv(OUTDIR / "subgroup_interactions.csv", index=False)
ns.to_csv(OUTDIR / "subgroup_sample_sizes.csv", index=False)
print("verdicts, subgroup cells:"); print(cells[~cells["sub"].str.contains("pooled")].verdict.value_counts().to_string())
print("verdicts, interaction tests:"); print(ints.verdict.value_counts().to_string())'''),
    md(sec["leads"]),
    code('''s = cells[~cells["sub"].str.contains("pooled") & (cells.n >= 25)].sort_values("p")
show = s.head(15)[["sub", "test_label", "outcome_label", "n", "rho_year", "rho", "lo", "hi", "p", "q", "held_out_ok", "ho_pos", "mde80", "verdict"]]
display(show.round(3).reset_index(drop=True))'''),
    md(sec["fig_db"]),
    code('fig_forest(cells, ints, "DB", FIGDIR / "sub_fig2_forest_s_vs_cb.png")'),
    md(sec["fig_dl"]),
    code('fig_forest(cells, ints, "DL", FIGDIR / "sub_fig3_forest_edge_vs_idl.png")'),
    md(sec["diff"]),
    code('''fig_diff(ints, FIGDIR / "sub_fig4_interactions.png")
d = ints[(ints[["n_a", "n_b"]].min(axis=1) >= 25)].sort_values("p_int").head(10)
display(d[["sub_a", "sub_b", "test_label", "outcome_label", "n_a", "n_b", "rho_a", "rho_b", "diff", "diff_lo", "diff_hi", "p_int", "q_int", "mde_diff", "verdict"]].round(3).reset_index(drop=True))'''),
    code('''# pooling check: is the pooled (role held fixed) link weaker than BOTH subgroups?
pv = cells[cells.n >= 25].pivot_table(index=["group", "test_label", "outcome_label"], columns="sub", values="rho")
rows = []
for grp, (a, b, _) in PAIRS.items():
    g = pv.loc[grp][[a, b, f"{grp} pooled"]].dropna()
    g = g[(np.sign(g[a]) == np.sign(g[b])) & (g[[a, b]].abs().min(axis=1) >= 0.30) & (g[f"{grp} pooled"].abs() < g[[a, b]].abs().min(axis=1))]
    rows.append(g.assign(group=grp))
display(pd.concat(rows).round(2))'''),
    md(sec["findings"]),
    md(sec["methods"]),
]
nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
               "language_info": {"name": "python"}}
out = H / "kernel" / "bdb2027_subgroups_prelim.ipynb"; out.parent.mkdir(exist_ok=True)
nbf.write(nb, out); print("wrote", out)
