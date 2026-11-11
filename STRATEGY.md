# BDB 2027 Strategy — "Sunday Speed": Which Combine Speed Is Real?
Owner: Kevin · Deadline **Wed Jan 6 2027, 6:59 PM EST** · Built from real data (`profile.py`, `explore.py`, outputs in `out/`). Data dictionary: `DATA_NOTES.md` (based on the Kaggle Data tab).

## 0. What the data forced us to change
- **No running backs.** 1 RB in 510 players; Combine groups are only DB/OL/DL/WR/TE. RB vs S is dead.
- **Only the 510 rookies are tracked in games.** No opponents/ball carriers → no tracking-based pursuit angles or separation. Use `separation_at_pass_forward`, `coverage_assignment`, `route_ran` from `player_play.csv` for context.
- Viable skill-position samples (40-yd tracking + ≥100 game plays): **WR 68, CB 46, S 38 (FS 17 + SS 21)**. 3-cone/shuttle tracking is too thin for DBs (≤17).
- New framing: **WR vs DB (CB & S)** — the passing-game matchup, one side offense, one side defense.

## 1. Evidence (quick, honest tests; Spearman ρ, "partial" = after controlling for log draft pick; ~45 tests run, so expect ~2 false positives at p<.05; Bonferroni cutoff ≈ .001)
| # | Test | Pos | n | ρ | partial ρ | Verdict |
|---|---|---|---|---|---|---|
| A1 | Combine 40 top speed → game deep-route (GO/POST/CORNER/WHEEL) p90 speed | WR | 68 | **+0.64** (p=6e-9) | **+0.62** | **Strong, survives correction** |
| A1 | Combine top → coverage (MAN/DEEP) p90 speed | CB | 33 | +0.06 | +0.05 | Null |
| A1 | same | S | 27 | +0.19 | +0.15 | Weak/null |
| F5 | Combine top → start rate (games started/active) | CB | 43 | −0.06 | **−0.43** (p=.004) | Intriguing "speed tax"; does NOT survive Bonferroni |
| F5 | same | WR / S | 67 / 36 | +0.08 / +0.28 | −0.03 / −0.03 | Null |
| A2/F2 | Speed realization (game/combine) or speed-over-expected → start rate | WR | 67 | −0.24 | −0.26 (p=.03) | Weak, *opposite* sign; realization ≠ value |
| F6–F8 | WR speed-over-expected → deep separation / YAC-over-expected / target rate | WR | 68 | +0.09 / +0.07 / −0.05 | ~same | Null |
| B1–B5 | Braking (Δs/Δt) in agility or WR skill drills → game braking or separation on breaking routes | WR | 29–75 | −0.25…+0.06 | — | Null |
| C1 | 40-yd burst (time to 90% top speed) → deep separation | WR | 68 | +0.01 | +0.03 | Null |
| D1/D2 | Drill consistency (CV) or top speed → 4th-quarter speed retention (Q4/Q1 p90) | WR/CB/S | 31–63 | −0.19…+0.12 | — | Null (retention ~0.97–0.99 everywhere) |
| E1 | Skill-drill braking → tackle rate | CB/S | 46–54 | ±0.15 | — | Null |
| Stability | Odd vs even games, p90 game speed | WR 72 / DB 67 | | r=**0.80** / 0.57 | | WR metric is a stable trait |

Position "translation slopes" (game p90 speed per 1 yd/s of Combine top speed): **WR 0.65, S 0.33, CB 0.10.** CB median 4th-qtr retention 0.98, WR 0.99.

**Read:** the Combine 40 is *real* for receivers (it shows up on Sunday deep routes, beyond what draft slot already knew) and *mostly irrelevant* to how fast corners actually play in coverage — yet teams still pay for it at CB. That contrast is the story. Do not claim Speed Realization predicts careers; it didn't.

## 2. Recommended concept
**"Sunday Speed: which Combine speed is real?"** One named metric, **Sunday Speed (mph)** = the speed a player actually reaches on the plays where his job demands top speed, plus **Speed Translation Rate** = how much of each Combine mph shows up on Sunday, by position. Actual-vs-expected layer: **Sunday Speed Over Expected (SSOE)** = actual Sunday Speed − Sunday Speed predicted from his Combine tracking. Coach line: *"For receivers, every 1 mph at the Combine is worth ~0.65 mph on go routes. For corners it's worth ~0.1 mph — so stop paying for the 40 at corner and look at the DB drills instead."*

**Pitch paragraph.** Every spring a 4.3 forty moves a prospect up the board, but nobody checks whether that speed ever shows up on Sundays. Using 10 Hz Combine tracking and three seasons of in-game tracking for 510 rookies, we measure Sunday Speed — how fast a player really runs on the plays where his job demands it (go routes for receivers, deep and man coverage for DBs). For receivers, Combine speed is real: it predicts Sunday deep speed (ρ=0.64, n=68) even after accounting for draft slot, and the trait is stable week to week (split-half r=0.80). For corners it barely transfers (translation 0.10 vs 0.65), yet faster corners drafted at the same slot start *less* often. Sunday Speed gives scouts a position-specific exchange rate for the 40 and a draft-day flag — "WR speed: trust it; CB speed: verify it in the DB drills" — plus SSOE as a development target for coaches.

**Why it can win (vs past winners):** one catchy named metric in mph; actual-vs-expected (SSOE); position-specific contrast with a surprise (CB null + speed tax); explicit Combine-tracking → regular-season link (pass/fail gate); stability check built in; actionable for drafting (exchange rate) and development (SSOE). Null results are allowed and here they *are* the insight.

**Next test that could upgrade it (Phase 2):** do DB *skill-drill* tracking features (BACK_PEDAL_AND_TRANSITION_45, W_DRILL, BOX_DRILL: peak speed, Δs/Δt braking, transition time) predict CB/S coverage Sunday Speed better than the 40? Similarly, does the WR GO_ROUTE_RIGHT drill top speed beat the 40? If yes → "the right drill for each position" is the headline figure. If no → keep the honest null.

## 3. Metric definitions
Units: data are yd/s; report mph = yd/s × 2.0455.
- **Combine Top Speed** `c_top_i` = max over FORTY_YARD_DASH attempts of max `s` (PLAYER rows).
- **Signed acceleration** = Δs/Δt = diff(s)×10 after sorting by `time` within `event_id` (Combine) or `(game_id, play_id, nfl_id)` (game); drop |value|>12 yd/s². (`a` is unsigned.)
- **Top-speed opportunity plays** (from `player_play`):
  - WR: `route_ran` ∈ {GO, POST, CORNER, WHEEL}, `play_nullified_by_penalty`=='N'.
  - CB/S: `coverage_assignment` contains MAN or DEEP (DEEP_THIRD_*, DEEP_HALF_*, QUARTERS_* optional sensitivity), pass plays.
- **Play max speed** `v_ip` = max `s` for player i on play p (consider restricting to frames between `ball_snap` and `pass_arrived`/`tackle`/`out_of_bounds`).
- **Sunday Speed** `SS_i` = 90th percentile of `v_ip` over i's opportunity plays (require ≥20 WR, ≥30 DB plays). Alt robust: mean of top-10 plays.
- **Speed Translation Rate** (position k) = slope β_k from `SS_i = α_k + β_k·c_top_i` (Bayesian or bootstrap CI). Observed: WR 0.65, S 0.33, CB 0.10.
- **Speed Realization %** = SS_i / c_top_i (keep as coach-facing descriptor; median WR 81.5%).
- **SSOE_i** = SS_i − (α_k + β_k·c_top_i + γ·weight + δ·draft_year), in mph.
- **Outcomes**: start_rate = career_games_started / career_games_active; snaps_per_game = (off+def snaps)/games_active; WR separation_at_pass_forward on deep routes; YAC − expected_yards_after_catch.

## 4. Pipeline (real files/columns)
1. `players.csv` + `combine_results.csv` on `nfl_id`; filter `nfl_position` ∈ {WR, CB, FS, SS}; pick = `draft_overall_pick` fillna(260).
2. `combine_tracking.csv`: keep `entity_type=='PLAYER'`; per `event_id` → max s, time to 90% max, signed peak accel/brake, 10/20-yd split derived from x vs time (40 only), drill-specific features for SKILL_DRILLS_DB/WR. Normalize drill_name dups.
3. `game_tracking_{2023,2024,2025}.csv`: read in 5M-row chunks, `usecols=[game_id, play_id, nfl_id, time, s, event]`, filter nfl_id, sort, per play-player aggregate → parquet (already produced: `out/game_dbwr_play.parquet`, `out/game_play_player.parquet`).
4. Join `player_play.csv` on (game_id, play_id, nfl_id) for route_ran, coverage_assignment, separation, quarter, penalties; join `games.csv` for season/week/season_type (use REG for the "regular-season" claim).
5. Player table → `out/explore_player.parquet` columns: c_top, c_t90, c_brake_*, g_deep_p90, g_cov_p90, realization, real_resid (SSOE), start_rate, snap_share, sep_deep, yac_oe…

## 5. Modeling & validation
- Hierarchical linear model: SS ~ position-varying slope on c_top (+ weight, draft_year), PyMC or statsmodels MixedLM; report β_k with 95% CI. Bootstrap players (2,000) as a check.
- Incremental value: does c_top predict SS beyond ngs_athleticism_score and draft pick? (partial ρ, ΔR²).
- Stability: split-half by odd/even game (WR r=0.80, DB 0.57) and season-to-season for 2023–24 draftees.
- Robustness: p90 vs top-10 mean vs max; opportunity definitions; minimum plays thresholds; REG-only.
- Speed-tax check (CB): start_rate ~ c_top + log(pick) + draft_year; permutation p; report as "suggestive" given multiple testing. Holm-correct the full test family.
- Phase-2 drill comparison: leave-one-out CV R² of SS from each drill's features; pick best drill per position.

## 6. Figures (8)
1. **Hero animation**: one WR go route and one CB deep coverage play, speedometer overlay (mph) vs his Combine 40 trace — "Combine speed vs Sunday speed".
2. Combine top speed vs Sunday Speed scatter, faceted WR / CB / S, regression lines with slopes labeled (the exchange rate).
3. "Exchange rate" bar chart: mph on Sunday per Combine mph, by position, with CIs.
4. Speed-curve overlay: Combine 40 speed profile vs median deep-route speed profile from snap, by position.
5. Stability: split-half scatter (WR vs DB).
6. CB speed tax: start rate by draft-round bucket × faster/slower than median 40 speed.
7. Phase-2: which Combine drill best predicts Sunday Speed per position (bars of CV R²).
8. SSOE leaderboard table (top/bottom 5 per position, mph, with draft pick) — the scouting card.

## 7. Writeup outline (≤2,000 words)
Intro & hook (180) · Data & definitions (300) · WR: speed is real (300) · DBs: speed isn't the trait (300) · Speed tax & draft implications (250) · Which drill to trust (250) · SSOE for development (200) · Limitations (nulls, sample, rookies only, untracked opponents) (150) · Conclusion/actions (70).

## 8. Week-by-week plan
- Oct 26–Nov 1: re-run `profile.py`/`explore.py`, freeze opportunity definitions, REG-only filter.
- Nov 2–8: DB & WR skill-drill feature extraction; Phase-2 drill comparison.
- Nov 9–15: hierarchical model, bootstrap CIs, Holm correction, stability.
- Nov 16–22: speed-tax analysis + robustness; decide final headline.
- Nov 23–29: figures 2–6, 8 (static).
- Nov 30–Dec 6: hero animation (fig 1) + speed curves (fig 4).
- Dec 7–13: draft writeup v1 (Kaggle notebook, markdown).
- Dec 14–20: score draft vs rubric; get a football person to read it.
- Dec 21–27: polish visuals (accessibility, colorblind palette, alt text).
- Dec 28–Jan 3: final edits, word/figure count, make notebook public.
- Jan 4–6: submit early (by Jan 5), buffer.

## 9. Risks
Small n (CB 33–46, S 27–38): use CIs, avoid overclaiming. Multiple testing: speed tax is suggestive only. Opportunity bias (fast WRs run more go routes) — condition on route. Season max/p90 sensitive to tracking glitches — clip. Rookie-contract outcomes are short and coach-driven. Data is only rookies → small team context.

## 10. Claude prompts (paste one per phase; attach DATA_NOTES.md)
**Schema block (include in every prompt):**
```
Files in ./data: players.csv(nfl_id,display_name,draft_year,nfl_position,birth_date,college_name,college_conference,draft_round,draft_pick_within_round,draft_overall_pick);
combine_results.csv(draft_year,nfl_id,combine_position,combine_height,combine_weight,hand_size,arm_length,wing_span,ten_yd_split,forty,vertical,broad_jump,three_cone,short_shuttle,bench_reps,ngs_athleticism_score,ngs_college_production_score,ngs_final_score);
combine_tracking.csv(draft_year,event_id,nfl_id,entity_type[PLAYER|BALL],time ISO,drill_type,drill_name,attempt,x,y,s yd/s,a unsigned yd/s2,dis,dir) 10Hz;
player_career_successes.csv(nfl_id,career_offensive_snaps,career_defensive_snaps,career_special_teams_snaps,career_games_active,career_games_started,ap_all_pro_1st_team,ap_all_pro_2nd_team,pro_bowl_original_ballot);
games.csv(game_id,game_key,season,season_type[REG|POST],week,home_team_abbr,visitor_team_abbr);
player_play.csv(game_id,play_id,team_abbr,nfl_id,lined_up_position,quarter,down,...,play_nullified_by_penalty,pass_result,pass_length,yards_gained,team_coverage_man_zone,team_coverage_type,target,rec_yards,yards_after_catch,expected_yards_after_catch,route_ran[GO,HITCH,CROSS,IN,OUT,POST,CORNER,SLANT,FLAT,SCREEN,WHEEL,ANGLE],separation_at_pass_forward,cushion,tackle,assist,coverage_assignment[MAN,DEEP_THIRD_*,DEEP_HALF_*,QUARTERS_*,CURL_FLAT_*,FLAT_*...]);
game_tracking_2023/2024/2025.csv(game_id,play_id,nfl_id,time ISO,x,y,s,a unsigned,dis,o,dir,event[ball_snap,pass_forward,pass_arrived,tackle,first_contact,out_of_bounds,...]) 10Hz, ONLY the 510 cohort players, ~22.6M rows/2.1GB total — read in chunks.
No frame_id: sort by time. Signed accel = diff(s)*10, clip |x|>12. mph = yd/s*2.0455. Positions: WR(106), CB(60), FS(25), SS(28); RB essentially absent.
```
**P1 Data pipeline:** "Using the schema above, write a Kaggle-notebook-ready Python module `pipeline.py` that (a) builds per-attempt Combine features (max s, time to 90% max, signed peak accel and brake, derived 10/20-yd splits from x vs time for FORTY_YARD_DASH), (b) streams the three game_tracking files in 5M-row chunks keeping only WR/CB/FS/SS nfl_ids, restricts frames to between ball_snap and the first of pass_arrived/tackle/out_of_bounds/touchdown, and aggregates per (game_id,play_id,nfl_id) max speed and signed peak brake, (c) joins player_play and games (REG only, play_nullified_by_penalty=='N'), and saves parquet. Include asserts on row counts and a memory-safe design."
**P2 Sunday Speed metric:** "Given pipeline outputs, compute Sunday Speed (p90 play max speed over opportunity plays: WR route_ran in GO/POST/CORNER/WHEEL with ≥20 plays; CB/S coverage_assignment containing MAN or DEEP with ≥30 plays), Speed Realization %, and per-position translation slopes with 2,000-player bootstrap CIs. Expect WR slope ≈0.65, S ≈0.33, CB ≈0.10 (yd/s per yd/s). Report in mph."
**P3 Modeling & validation:** "Fit a hierarchical model SS ~ (1 + c_top | position) + weight + draft_year; compute SSOE residuals; test incremental value over ngs_athleticism_score and log(draft pick); split-half (odd/even game_id) and season-to-season stability; Holm-correct a family of tests; permutation test for the CB 'speed tax' (start_rate ~ c_top + log pick)."
**P4 Drill comparison:** "For CB/S use SKILL_DRILLS_DB (BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION, BACK_PEDAL_AND_90_DEGREE_BREAK_TO_BALL, W_DRILL, BOX_DRILL; normalize LINE/LINE_DRILL) and for WR SKILL_DRILLS_WR (GO_ROUTE_RIGHT etc.) to build drill features (peak speed, brake, transition time = time from peak brake to 80% re-accel). Compare leave-one-out CV R² for predicting Sunday Speed vs the 40 alone. Report honestly including nulls."
**P5 Figures:** "Make figures 1–8 from STRATEGY.md §6 in matplotlib/plotly with a colorblind-safe palette, mph units, coach-readable titles that state the takeaway, and an animated play (matplotlib FuncAnimation → gif) with a live mph speedometer vs the player's Combine 40 trace. Note: only the cohort player is tracked, so animate that player alone over a field drawing."
**P6 Writeup:** "Draft a ≤2,000-word Kaggle writeup following STRATEGY.md §7 word budgets; scouting-report tone; every claim cites a number with n and CI; explicitly state the Combine-tracking → regular-season link; include limitations and nulls; ≤8 figures."
