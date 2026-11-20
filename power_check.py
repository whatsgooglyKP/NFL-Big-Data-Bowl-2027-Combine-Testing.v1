#!/usr/bin/env python3
"""Simulation check of the Fisher-z minimum detectable effect in scorecard.py (11/2026).
Generates normal data with a known partial Spearman rho between x and y given k independent control columns, ranks everything,
residualises on the controls, and tests the partial rank correlation with a t test (df n-k-2). Reports the simulated power at the
analytic MDE (target 0.80) and at a true rho of 0.30, at alpha 0.05 and at the BH cutoffs used (about 0.0018 for DL/DB, 0.0015 for WR).
Writes out/power_simulation.csv. Usage: python3 power_check.py"""
import numpy as np, pandas as pd
from scipy import stats
import scorecard as SC

rng = np.random.default_rng(2027)
REPS = 6000


def sim_power(n, k, rho_s, alpha_list):
    r = 2 * np.sin(np.pi * rho_s / 6)            # normal-scale correlation that gives Spearman rho_s
    hits = np.zeros(len(alpha_list))
    for _ in range(REPS):
        z = rng.standard_normal((n, k)); x = rng.standard_normal(n)
        y = r * x + np.sqrt(1 - r * r) * rng.standard_normal(n)
        R = stats.rankdata(np.column_stack([x, y, z]), axis=0)
        A = np.column_stack([np.ones(n), R[:, 2:]])
        rx = R[:, 0] - A @ np.linalg.lstsq(A, R[:, 0], rcond=None)[0]; ry = R[:, 1] - A @ np.linalg.lstsq(A, R[:, 1], rcond=None)[0]
        pr = np.corrcoef(rx, ry)[0, 1]; df = n - k - 2
        p = 2 * stats.t.sf(abs(pr) * np.sqrt(df / (1 - pr * pr)), df)
        hits += np.array([p < a for a in alpha_list])
    return hits / REPS


rows = []
for n in (21, 33, 38, 60, 64):
    k = 4
    for a_lab, a in (("alpha 0.05", 0.05), ("BH cutoff 0.0018", 0.0018)):
        m = float(SC.mde(n, k, alpha=a)); p_at_mde = sim_power(n, k, m, [a])[0]; p03 = sim_power(n, k, 0.30, [a])[0]
        rows.append(dict(n=n, k=k, alpha=a, analytic_mde80=round(m, 3), simulated_power_at_mde=round(float(p_at_mde), 3),
                         analytic_power_rho03=round(float(SC.power_at(0.30, n, k, alpha=a)), 3), simulated_power_rho03=round(float(p03), 3)))
d = pd.DataFrame(rows); d.to_csv(SC.OUT / "power_simulation.csv", index=False); print(d.to_string())
