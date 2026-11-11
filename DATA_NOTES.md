# BDB 2027 — Data Notes
Source of truth: Kaggle Data tab (https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data), read 2026-10-25, plus profiling (`profile.py` → `out/profile.txt`).

> "high-frequency optical tracking, standardized physical testing results, and multi-season NFL game performance metrics for **510 rookie prospects** drafted or signed between 2023 and 2025."
> Game tracking: "10 Hz … in-game optical tracking frames for **all rookie cohort prospects**" — i.e. ONLY the 510 cohort players are tracked, not all 22 on the field.

## Inventory (9 CSVs, 2.31 GB, CC BY-NC 4.0)
| File | Size | Rows | Grain |
|---|---|---|---|
| players.csv | 47 KB | 510 | player |
| combine_results.csv | 41 KB | 510 | player (draft_year) |
| combine_tracking.csv | 84 MB | 463,189 (431,094 PLAYER + 32,095 BALL) | 10 Hz frame × drill attempt (6,310 attempts) |
| player_career_successes.csv | 14 KB | 510 | player |
| games.csv | 43 KB | 1,002 games | game (2023–25, REG+POST) |
| player_play.csv | 147 MB | 316,338 | player × play (cohort only) |
| game_tracking_2023/2024/2025.csv | 335 / 718 / 1,023 MB | 22.65 M frames total | 10 Hz frame × player × play |

## Join keys
- `nfl_id` → every table. `game_id` → games ↔ player_play ↔ game_tracking. `(game_id, play_id, nfl_id)` → player_play ↔ game_tracking (314,944 play-player tracks).
- combine_tracking: `event_id` = one drill attempt; `(nfl_id, drill_type, drill_name, attempt)`.
- Time ordering: sort by `time` (ISO string) within event/play; there is no frame_id.

## Columns (abridged from the Data tab)
- **players**: nfl_id, display_name, draft_year, nfl_position, birth_date, college_name, college_conference, draft_round/pick_within_round/overall_pick (null = UDFA).
- **combine_results**: combine_position (only DB/OL/DL/WR/TE!), height (in), weight, hand_size, arm_length, wing_span, ten_yd_split, forty, vertical, broad_jump, three_cone, short_shuttle, bench_reps, ngs_athleticism_score, ngs_college_production_score, ngs_final_score.
- **combine_tracking**: draft_year, event_id, nfl_id, entity_type (PLAYER/BALL), time, drill_type, drill_name, attempt, x, y, s (yd/s), a (yd/s², **unsigned magnitude**), dis, dir. **No `o` (orientation).**
- **player_career_successes** (= the "success" outcome): career_offensive_snaps, career_defensive_snaps, career_special_teams_snaps (REG+POST), career_games_active, career_games_started, ap_all_pro_1st_team, ap_all_pro_2nd_team, pro_bowl_original_ballot. All-Pro/Pro Bowl ≈ 1–3% of players → useless as outcomes; use starts/active, snaps/game.
- **player_play**: context (quarter, down, yards_to_go, yardline, game_clock, scores, play_direction, WP/EPA), scheme (offense_formation, receiver_alignment, team_coverage_man_zone, team_coverage_type), results (pass_result, pass_length, yards_gained, penalties), receiver (target, rec_yards, rush_yards, yards_after_catch, expected_yards_after_catch, route_ran, separation_at_pass_forward, cushion, in_motion_at_ball_snap), OL (dropback_duration, pressure_allowed, sack_allowed, time_to_pressure_allowed, peak_pressure_probability_allowed…), DL/defense (blitzing, player_get_off, sack, tackle, assist, tackle_for_loss, time_to_pressure, time_to_qb_hurry, coverage_assignment, coverage_assignment_at_snap, quick_pressure, unblocked_pressure). `lined_up_position` values: G, T, EDGE, CB, INTERIOR_LINE, WR, HIGH_SAFETY, SLOT_WR, C, SLOT_CB, TE, OLB, MLB, RB(320), BOX_SAFETY, FB.
- **game_tracking_YYYY**: game_id, play_id, nfl_id, time, x, y, s, a (unsigned), dis, o, dir, event (ball_snap, pass_forward, pass_arrived, tackle, first_contact, handoff, out_of_bounds…).

## Combine drills (unique players)
FORTY_YARD_DASH 418 · THREE_CONE 160 · SHORT_SHUTTLE 170 · SKILL_DRILLS_WR (~100 each: GO_ROUTE_RIGHT, SLANT_ROUTE_LEFT, CURL, COMEBACK, DAGGER, POST_CORNER L/R, SLOT_SAIL, SLOT_STRIKE, SPEED_OUT, RED_ZONE_FADE, OVER_SHOULDER_ADJUST, GAUNTLET, CIRCUS) · SKILL_DRILLS_DB (~120 each: BACK_PEDAL_AND_90_DEGREE_BREAK_TO_BALL, BACK_PEDAL_AND_TRANSITION_45, BOX_DRILL, W_DRILL, GAUNTLET, TERYL_AUSTIN_DRILL_1/2, LINE[_DRILL]) · DL, OL, TE, LB skill drills. Duplicated naming (LINE vs LINE_DRILL, PASS_PRO-MIRROR vs PASS_PRO_MIRROR, SPEED_OUT vs SPEED_OUT_ROUTE) → normalize. No 10-yd split inside tracking — derive from x over time.

## Coverage by position (players / with 40-yd tracking / 3-cone tracking / shuttle tracking / ≥50 tracked game plays / 40 + game / median plays)
| pos | n | 40 | 3C | SS | game | both | med plays |
|---|---|---|---|---|---|---|---|
| WR | 106 | 93 | 24 | 29 | 85 | **76** | 268 |
| CB | 60 | 51 | 13 | 16 | 56 | **47** | 538 |
| FS | 25 | 21 | 3 | 4 | 24 | 20 | 242 |
| SS | 28 | 24 | 7 | 7 | 27 | 23 | 632 |
| S (FS+SS) | 53 | 45 | 10 | 11 | 51 | **43** | — |
| **RB** | **1** | 1 | 0 | 0 | 1 | **1** | 84 |
Other: T 50, G 51, DT 47, TE 42, DE 36, OLB 30, C 20, DB 5, NT 5. **RBs are effectively absent (1 player; no RB combine group) → the RB vs S matchup is impossible.** 3-cone/shuttle tracking is thin for DBs (≤16 per position).

## Speed sanity check (40-yd tracking max s vs game, players with ≥50 tracked plays; yd/s, ×2.045 = mph)
| pos | n | Combine max | game max | game p95 (per-play max) | r(max) | r(p95) | ρ(max) | game max / combine |
|---|---|---|---|---|---|---|---|---|
| WR | 76 | 11.13 | 10.14 | 9.02 | 0.22 | 0.53 | 0.45 | 0.91 |
| CB | 47 | 11.13 | 10.20 | 8.42 | 0.05 | 0.24 | 0.17 | 0.92 |
| FS | 20 | 10.92 | 9.82 | 8.27 | 0.31 | −0.12 | 0.35 | 0.90 |
| SS | 23 | 11.00 | 9.98 | 8.19 | 0.12 | 0.46 | 0.02 | 0.91 |
| TE | 28 | 10.53 | 9.07 | 8.04 | 0.48 | 0.52 | 0.62 | 0.86 |
Season max is noisy (one glitch/opportunity frame); a percentile over role-filtered plays is far better (see STRATEGY.md: WR deep-route p90 ρ=0.64).

## Gotchas
- `a` is unsigned in both sources → compute signed accel as Δs/Δt (×10) after sorting by time; clip |Δs/Δt|>12 as glitches.
- Only cohort players are tracked: no opponent/ball-carrier tracks in game data → no pursuit angles or tracking-derived separation; use `separation_at_pass_forward`, `cushion`, `tackle`, `coverage_assignment` from player_play.
- `player_play` booleans/flags are mixed types (TRUE/FALSE strings, NA) → coerce.
- Outcomes are rookies' first 1–3 seasons; 2025 draftees have one season only → normalize per game / per opportunity, include draft_year.
