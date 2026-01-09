# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AFL Football Analytics is a data engineering project for Australian Football League match analysis using a Medallion Architecture (Bronze → Silver → Gold) on Databricks with dbt for transformations.

## Key Commands

All dbt commands must be run from `afl_analytics/` directory with `uv run` prefix:

```bash
# Setup
uv sync                              # Install dependencies
cd afl_analytics

# dbt operations
uv run dbt deps                      # Install dbt packages (first time)
uv run dbt debug                     # Test Databricks connection
uv run dbt seed                      # Upload seeds (e.g., seed_teams.csv, seed_venues.csv)
uv run dbt run                       # Run all models
uv run dbt run --select bronze       # Run all bronze layer models
uv run dbt run --select silver       # Run all silver layer models
uv run dbt run --select stg_match_results  # Run specific model
uv run dbt test                      # Run all data quality tests
uv run dbt test --select bronze      # Test bronze layer only
uv run dbt test --select silver      # Test silver layer only
uv run dbt docs generate && uv run dbt docs serve  # Generate and view docs
```

## Architecture

### Data Flow
1. **Raw .txt files** → Uploaded to Databricks Volume (`/Volumes/afl_analytics_dev/raw/afl_raw_files/`)
2. **Python parser** (`afl_analytics/scripts/stg_match_results.py`) → Run in Databricks to create `raw.match_results_parsed`
3. **Bronze layer** (dbt) → `bronze.stg_match_results` - typed and tested
4. **Silver layer** (dbt) → Dimension/fact tables (e.g., `dim_teams`)
5. **Gold layer** (dbt) → Analytics models (planned: Elo ratings, predictions)

### Critical Workflow
If the raw data schema changes or new years are added:
1. Edit `afl_analytics/scripts/stg_match_results.py` (e.g., add year to `YEARS` list)
2. Run the parser script **in Databricks** to update `raw.match_results_parsed`
3. Then run `uv run dbt run` locally

### Project Structure
```
afl_analytics/                  # dbt project root
├── dbt_project.yml            # dbt config (profile: afl_analytics)
├── models/
│   ├── bronze/                # Raw → typed (stg_match_results.sql)
│   │   ├── _sources.yml       # Source definitions (raw.match_results_parsed)
│   │   └── _models.yml        # Column docs and tests
│   └── silver/                # Dimension tables (dim_teams.sql)
├── seeds/                     # Static reference data (seed_teams.csv)
└── scripts/                   # Python scripts to run in Databricks
```

### Databricks Configuration
- Catalog: `afl_analytics_dev`
- Schemas: `raw`, `bronze`, `silver`, `gold`
- Connection: Requires `DATABRICKS_TOKEN` env var and `~/.dbt/profiles.yml`

## Conventions

- **Naming**: Snake_case for files, tables, and columns
- **Testing**: All models have associated schema tests in `_models.yml`
- **Documentation**: Update `_models.yml` and `_sources.yml` when modifying tables
- **Idempotency**: All scripts and models must be safe to re-run

## Current State

- **Bronze**: Complete (`stg_match_results` with 2016-2025 data)
- **Silver**: In progress
  - `dim_teams` - complete (from seed_teams.csv)
  - `dim_venues` - complete (from seed_venues.csv with 26 venues)
  - `fct_matches` - next step (join matches with teams/venues)
- **Gold**: Planned (crowd analytics, Elo ratings, predictions, Brownlow predictor)

## Next Steps

1. **fct_matches** - Silver layer fact table joining `stg_match_results` with `dim_teams` and `dim_venues`
2. **Crowd analytics** - Gold layer aggregations on attendance data
3. **Elo ratings** - Gold layer match predictions
