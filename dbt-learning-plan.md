# dbt Learning Plan (6 weeks + restart)

Goal: build dbt depth plus Airflow/Cosmos experience using the AFL project (dbt + Databricks Free), then sit the dbt certification.

Time budget: ~4–6 hours per week.

Structure stays as-is: bronze/silver/gold already maps onto dbt's staging → marts convention (`stg_*` in bronze, dims/facts in silver, analytics in gold). No layer refactor.

Already done (don't redo): sources declared in `models/bronze/_sources.yml` (both raw tables); freshness configured on `squiggle_games`; generic tests (`unique`, `not_null`, `relationships`, `accepted_values`, `dbt_utils.accepted_range`) across all models; dbt-utils installed.

---

## Week 0 — Restart (project untouched since 26 Jun 2026)

- [x] `uv run dbt debug` — confirm the PAT and warehouse still work (PAT had expired; renewed)
- [x] `uv run dbt parse --no-partial-parse --show-all-deprecations` — fixed 17× `MissingArgumentsPropertyInGenericTestDeprecation` (generic-test args now under `arguments:`). Partial parsing hides deprecations, hence the flags
- [x] Load the 2026 season — fetched with `--years 2016 ... 2026` (the script does `CREATE OR REPLACE`, so `--years 2026` alone would wipe 2016–2025), then `uv run dbt build`: PASS=101 WARN=3. `DEFAULT_YEARS` in the script still stops at 2025
- [ ] **Next up → [elo-plan.md](elo-plan.md):** fix Elo scaling and home advantage, measured by a new `elo_evaluation` gold model (Brier / log loss / tip accuracy per season). Currently 448 rows outside 1000–2000
  - [ ] 1. Baseline `elo_evaluation` model and record the numbers
  - [ ] 2. Margin-as-outcome instead of the MOV multiplier (fixes draws too)
  - [ ] 3. Home advantage from travel + venue familiarity (not a flat 45)
  - [ ] 4. Tune locally (`scripts/tune_elo.py`), bake the parameters into the dbt model
  - [ ] 5. Tighten Elo tests (1200–1800, error) + zero-sum singular test
  - [ ] 6. Backtest the 2026 ladder prediction against the actual ladder

**Done when:** `dbt build` is green with no Elo range warnings, and 2026 is in `stg_squiggle_games` (done).

## Week 1 — Sources & freshness

- [x] Run `uv run dbt source freshness` and understand the result — ERROR STALE before the 2026 load (last load 26 Jun, `error_after` 30 days); should pass after the reload (re-run to confirm), but only because the script just ran. See `target/sources.json`
- [ ] Notice that `_ingested_at` is the same for every row (full rebuild), so freshness measures "when did I last run the script", not "how recent is the newest game". Decide which you actually want
- [ ] Design freshness for a seasonal sport: in-season vs off-season thresholds; try `loaded_at_query` or a `filter`, or accept off-season warnings deliberately
- [ ] `match_results_parsed` is a frozen legacy source: set `freshness: null` explicitly (or use `scraped_at`) and document why
- [ ] Fix the stale description (names `parse_all_match_results.py`, should be `stg_match_results.py`)
- [ ] Add seed descriptions (`seeds/_seeds.yml`) so every node has one

**Done when:** freshness passes (or warns when expected), every model/source/seed has a description, and `dbt docs generate` shows a clean lineage graph.

## Week 2 — Testing & contracts

- [ ] Rename `tests:` → `data_tests:` everywhere and move `severity:` under `config:` (current syntax; dbt 1.10 doesn't warn on either yet)
- [ ] Singular tests (`tests/`):
  - `home_score = home_goals * 6 + home_behinds` (and away) on `stg_squiggle_games`
  - Elo is zero-sum: `SUM(elo_change)` per `match_id` ≈ 0
  - `home_team_id != away_team_id` in `fct_matches`
  - no team plays twice in the same `season` + `round_number`
  - attendance coverage: Squiggle games in seasons the `.txt` path covers should get a crowd (catches silent join misses in `fct_matches.txt_attendance`)
- [ ] Try dbt-expectations for one or two distribution-style checks
- [ ] Model contract on `fct_matches` (consumed by Elo and `predict_ladder.py`)
- [ ] Unit test (dbt ≥ 1.8) on a SQL model: venue alias lookup or the attendance date join in `fct_matches.sql`. Note: unit tests don't support Python models, so Elo stays covered by singular tests (or pytest)
- [ ] Tidy `crowd_analysis.sql`: use `fct_matches.is_final` / `round_number` instead of re-parsing the round string

## Week 3 — Incrementals & snapshots

- [ ] Change the fetch script to stop doing `CREATE OR REPLACE` — `MERGE` on `game_id` into `raw.squiggle_games` (or append + dedupe), with per-row `_ingested_at`
- [ ] Make `stg_squiggle_games` incremental (`merge`, `unique_key='game_id'`)
- [ ] Try `insert_overwrite` partitioned by `season` on Databricks and compare
- [ ] Snapshot something that changes: Squiggle `/standings` (ladder position by round) or venue sponsor names in `seed_venues`
- [ ] Revisit Week 1 freshness now that `_ingested_at` means something per row

**Done when:** you can explain when each strategy breaks (late-arriving data, score corrections, full refreshes).

## Week 4 — Jinja, macros, multi-target

- [ ] Macros for repeated logic (e.g. win/draw/loss result, margin, team-name → `team_id` mapping)
- [ ] Add a DuckDB target alongside Databricks. SQL models should port; `elo_ratings.py` returns via `session.createDataFrame` (Spark) — isolate that difference
- [ ] Handle adapter differences with `adapter.dispatch` (e.g. `REGEXP_EXTRACT`, `TRY_CAST`, timestamp functions)
- [ ] Tooling: sqlfluff, pre-commit, dbt-project-evaluator

## Week 5 — Airflow + Cosmos (work-relevant)

- [ ] Run Airflow locally via the Astro CLI
- [ ] Point Cosmos at the project using the Databricks profile
- [ ] Compare load modes: manifest vs `dbt ls`
- [ ] Observe how tests render as tasks (and how the Python model runs on serverless)
- [ ] Select by tag to create separate DAGs (e.g. ingestion + bronze `daily` in season vs gold `weekly`)
- [ ] Break things on purpose: failed test, stale source (freshness), renamed model

## Week 6 — CI & certification prep

- [ ] Add a separate "prod" target/schema — there's currently only `afl_analytics_dev` with the `default` schema, so `--defer` has nothing to defer to
- [ ] GitHub Actions slim CI: `dbt build --select state:modified+ --defer` against the prod manifest
- [ ] Work through the certification study guide; list topics not yet touched
- [ ] Book the exam

---

## Notes

- Keep GitHub Actions as the project's real scheduler for clone-and-run simplicity. Airflow is the learning layer.
- The end state mirrors the team's setup (dbt + Airflow/Cosmos): useful for work and as a portfolio piece.
- After this plan: ML match predictions on top of the fixed Elo (see `FABLE_feedback.md`), then player data → Brownlow.
- Ongoing: dbt Community Slack, Coalesce talks on Cosmos/Airflow, dbt best-practice guides.
