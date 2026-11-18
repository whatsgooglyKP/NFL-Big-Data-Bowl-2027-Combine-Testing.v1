"""Markdown tables for RESULTS_LOG.md from out/dl_robust_tests.csv and out/pos_robust_tests.csv."""
import numpy as np, pandas as pd
from dl_recheck import OUT, TEST_LABEL
from pos_robust import DB_TESTS

def f(v, d=2, sign=True):
    return "—" if not np.isfinite(v) else (f"{v:+.{d}f}" if sign else f"{v:.{d}f}")

def pv(p):
    return "—" if not np.isfinite(p) else (f"{p:.3f}" if p >= 0.001 else "<0.001")

def row(r, label):
    ci = f"{f(r.lo)} to {f(r.hi)}"
    un = f(r.rho_size_unshrunk) if np.isfinite(r.rho_size_unshrunk) else "n/a"
    wt = f(r.rho_size_wtd) if np.isfinite(r.rho_size_wtd) else "n/a"
    oos = f"{f(r.loso_dr2, 3)} (p {pv(r.loso_p)}, {int(r.loso_pos_folds)}/{int(r.loso_folds)})" if np.isfinite(r.loso_dr2) else "—"
    ver = {"SURVIVES": "**survives**", "LEAN": "lean", "small n": "small n", "size variable": "size"}.get(r.verdict, "")
    return (f"| {label} | {int(r.n)} | {f(r.rho_raw)} | {f(r.rho_yr)} | **{f(r.rho_size)}** | {ci} | {un} | {wt} | {pv(r.p_perm)} | {r.fdr:.2f} | {oos} | {ver} |")

HEAD = ("| Combine test | n | raw ρ | year+role ρ | size-controlled ρ | 95% CI | unshrunk ρ | snap-wtd ρ | perm p | FDR q | out-of-sample ΔR² (perm p, classes +) | verdict |\n"
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|")

def table(t, group, outcome, tests):
    s = t[(t.group == group) & (t.outcome == outcome)].set_index("test")
    lines = [HEAD]
    for tc in tests:
        if tc in s.index and np.isfinite(s.loc[tc, "rho_size"]):
            lines.append(row(s.loc[tc], TEST_LABEL.get(tc, tc)))
    return "\n".join(lines)

if __name__ == "__main__":
    d = pd.read_csv(OUT / "dl_robust_tests.csv"); p = pd.read_csv(OUT / "pos_robust_tests.csv")
    from dl_recheck import TESTS
    dl_tests = [c for c, *_ in TESTS]
    out = []
    for oc, ttl in [("pressure_rate", "DL · pressure rate (shrunk)"), ("sack_rate", "DL · sack rate (shrunk)"), ("tfl_rate", "DL · TFL per snap (shrunk)"), ("run_stop_rate", "DL · run stops per run snap (shrunk)")]:
        out += [f"#### {ttl}", table(d, "DL", oc, dl_tests), ""]
    for oc, ttl in [("speed_1s_mph", "DL · 1-sec burst speed (tracking)"), ("player_get_off", "DL · NFL/NGS get-off time")]:
        out += [f"#### {ttl}", table(d, "DL", oc, dl_tests), ""]
    for g, oc, ttl in [("WR", "sep_all_mean", "WR · separation, all routes"), ("WR", "sep_brk_mean", "WR · separation, break routes"), ("WR", "sunday_speed_mph", "WR · Sunday Speed"), ("WR", "ssoe_mph", "WR · SSOE"),
                       ("TE", "sep_all_mean", "TE · separation, all routes"), ("DB", "tackle_rate", "DB · tackle rate (shrunk)"), ("DB", "close_rate_mph", "DB · closing rate"), ("DB", "pfr_yds_tgt", "DB · PFR yards/target")]:
        out += [f"#### {ttl}", table(p, g, oc, [c for c, *_ in DB_TESTS]), ""]
    (OUT / "robust_tables.md").write_text("\n".join(out))
    print("\n".join(out))
