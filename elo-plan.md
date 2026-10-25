# Elo fix plan

Referenced from `dbt-learning-plan.md` (Week 0). Model: `afl_analytics/models/gold/elo_ratings.py`.

## The problem

After loading 2026, `dbt build` warns on 448 `pre_match_elo` rows (and 473 `post_match_elo`) outside 1000–2000. Cause: `K_FACTOR = 40` × `margin_multiplier = log(|margin|+1) * 2.2`. A 60-point win between even teams moves ~180 points (40 × 9 × 0.5). That multiplier was designed for low-scoring sports (NFL). AFL margins are large, so ratings blow out and get more extreme every season.

Secondary issues:

- **Draws** produce zero change (`log(0+1) = 0`).
- **Home advantage** is a flat 45 for whoever Squiggle lists as home. That's wrong both ways:
  - Collingwood v Carlton at the MCG gets 45 when the real advantage is ≈ 0.
  - A Grand Final at the MCG between a Melbourne club and an interstate club *does* have a real advantage, even though "home" is a ladder technicality.

## Principle: measure before tuning

Don't tune until the warnings go away. The rating should *predict*. `expected_win_prob` is already in the table, so score it, and judge every change by whether the score improves.

## Steps

### 1. Baseline evaluation model (dbt SQL, do first)

Add a gold model `elo_evaluation.sql` (+ `_models.yml` entry). Scores the *current* Elo per season, using the home-team row of each match:

```sql
WITH home AS (
    SELECT season, expected_win_prob AS p, actual_result AS y
    FROM {{ ref('elo_ratings') }}
    WHERE is_home
)
SELECT
    season,
    COUNT(*)                                             AS games,
    ROUND(AVG(POWER(p - y, 2)), 4)                       AS brier,        -- 0.25 = coin flip; lower is better
    ROUND(AVG(-(y * LN(p) + (1 - y) * LN(1 - p))), 4)    AS log_loss,     -- 0.693 = coin flip
    ROUND(AVG(CASE WHEN y = 0.5 THEN 0.5
                   WHEN (p >= 0.5) = (y = 1) THEN 1.0
                   ELSE 0.0 END), 3)                     AS tip_accuracy
FROM home
GROUP BY season
ORDER BY season
```

- Ignore 2016 when comparing (burn-in: everyone starts at 1500).
- Record the baseline numbers here before changing anything:

| Version | Brier (2017–26) | Log loss | Tip accuracy |
|---|---|---|---|
| Baseline (K=40, MOV mult, flat HGA 45) — 2,063 games | 0.2534 | 0.7775 | 0.631 |
| Step 2: margin outcome (K=40, SCALE=30, flat HGA 45) | 0.2104 | 0.6149 | 0.679 |
| | | | |

- Benchmarks: always tipping the home team; 50/50 (Brier 0.25). Squiggle's `/tips` endpoint has per-model results for an external comparison later.

**Baseline finding:** the model picks winners (63%) but is badly overconfident. Brier is above 0.25 in 8 of 10 seasons and log loss above 0.693 in all ten, so it does worse than a coin flip on probabilities. Calibration (home rows, 2017–26, buckets = `ROUND(expected_win_prob, 1)`):
- Predicted <5% → home team won 26%. Predicted ≥95% → won 85%.
- 986 of 2,063 games sit in the 0 / 0.1 / 0.9 / 1 buckets. Ratings are spread far too wide.
- The middle buckets (0.2–0.7) are flat and out of order (50–61%), so there's little signal in close games.

Follow-up: make the calibration query a second gold model, `elo_calibration`, so every build shows it.

### 2. Fix the scaling: margin as the outcome

The standard AFL approach is to replace the 1 / 0.5 / 0 result with a smooth score of the margin, and drop the multiplier:

```python
outcome = 1 / (1 + np.exp(-margin / SCALE))   # SCALE ≈ 30 to start; margin 0 → 0.5 (fixes draws)
change  = K_FACTOR * (outcome - expected)     # K ≈ 40–60 to start
```

- Keep `actual_result` (1 / 0.5 / 0) for evaluation and its `accepted_values` test. Add a new column `outcome_score` for the smooth value.
- Parameters to tune: `K_FACTOR`, `SCALE`, `HOME_ADVANTAGE`, `REGRESSION_FRACTION`.

### 3a. Measure home ground advantage (analysis, before modelling it)

Measure HGA by team × venue first. The results decide whether travel-only (step 3) is enough or familiarity is worth modelling. It's also a standalone analysis piece.

New gold model `home_advantage` (SQL, team × venue grain, optionally × season), charts in a notebook.

- **Remove team strength.** Raw home win % mostly measures how good the team is. Two methods:
  1. **Team against itself (no Elo needed, can start now).** HGA(team, venue) = the team's average margin at that venue − their average margin in away games. Team strength cancels because it's the same team either way.
  2. **Against expectation (after step 2).** Average of (actual margin − expected margin from neutral ratings) by team × venue. More precise, but only once the ratings are trustworthy.
- **Sample size is the main limitation.** AFL margins vary by about ±40 points, so ~35 games at a ground gives an average uncertain to roughly ±7 points (40/√35).
  - Report `n_games` and a confidence interval alongside each estimate.
  - Shrink small samples towards the league average (partial pooling / empirical Bayes). A technique that carries over to the Brownlow work.
- **2020 natural experiment.** Mostly crowd-free games, many in Queensland hubs. Comparing 2020 HGA with other seasons separates the crowd effect from travel and familiarity. 2020 had 16-minute quarters (~20% smaller margins), so compare using relative margin or win probability, not raw points.
- **Quirks worth testing** (check the facts in the data, not from memory):
  - Geelong home finals at the MCG vs home games at Kardinia Park: `SELECT season, venue_id FROM fct_matches WHERE is_final AND home_team_id = 'GEE'`.
  - Hawthorn at Launceston and North Melbourne in Hobart, both "home" games interstate. If a team stops playing at a ground mid-dataset, that gives a before/after.
  - GWS in Canberra; Melbourne clubs sharing the MCG and Marvel (HGA ≈ 0 expected).
- **Done when:** `home_advantage` is built and tested (`unique` on team + venue, `not_null` on `n_games`), and there's a short write-up of the 3–5 most interesting effects with their uncertainty.

### 3. Home advantage from travel + familiarity

Replace the binary home flag with an advantage computed per team per match:

- **Travel (start here):** advantage when the opponent is interstate relative to the venue. Use `dim_venues.state` vs `dim_teams.home_state`. The Elo model needs `dbt.ref("dim_venues")` and `venue_id` from `fct_matches`.
- **Familiarity (stretch):** games played at this venue in the last N matches/seasons vs the opponent's count. This captures Kardinia Park/Gabba effects and handles Melbourne clubs at the MCG and Marvel.
- Grand Finals and shared grounds then need no special case.
- Rename/redefine `home_advantage_applied` to hold the computed value, and update its description.

### 4. Tune locally, bake into dbt

Each `dbt run` of the Python model spins up serverless compute, which is too slow for a parameter sweep.

- Write `scripts/tune_elo.py`: pull `fct_matches` (+ dims) via `databricks-sql-connector`, copying the connection pattern in `scripts/predict_ladder.py`. Run the Elo loop locally over a small grid, score with the step-1 metrics, and print the best parameters.
- Move the Elo loop into a plain function that both the script and the dbt model can call, so the two can't drift.
- Put the chosen parameters in the model. Stretch: pass them as dbt `vars` → model `config` (`dbt.config.get(...)` in Python models), which is a good dbt lesson in itself.

### 5. Tighten tests

- Change the `accepted_range` on the Elo columns to something like 1200–1800, with **error** severity. Ratings drifting out should now fail the build.
- Singular test `tests/assert_elo_zero_sum.sql`: `SUM(elo_change)` per `match_id` should be 0 (±0.05 rounding). This holds as long as both teams use the same K.
- Note: dbt unit tests don't support Python models, so use singular tests (or pytest on the extracted function from step 4).

### 6. Backtest the 2026 ladder

- Re-run `scripts/predict_ladder.py` using ratings **as at the end of 2025** with the new parameters. Compare it, and the old `predicted_ladder_2026.csv`, against the actual 2026 ladder (Squiggle `/standings?year=2026`).
- Metric: Spearman rank correlation, or mean absolute ladder-position error.

## Done when

- `dbt build` has no Elo warnings, with the tighter error-severity ranges.
- The table in step 1 shows the new version beating the baseline on Brier score and log loss.
- `elo_evaluation` exists as a gold model. It becomes the baseline the ML match-prediction model (FABLE_feedback phase 2) has to beat.
