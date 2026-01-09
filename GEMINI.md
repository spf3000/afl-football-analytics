# AFL Football Analytics - AI Context

## Project Overview
This is a data engineering and analytics project focused on Australian Football League (AFL) match data. It utilizes a **Medallion Architecture** (Bronze -> Silver -> Gold) implemented on **Databricks** using **dbt** for transformations and **Python** for raw data parsing and analysis.

The project emphasizes Functional Programming principles in data engineering: idempotency, immutability, and function composition.

## Tech Stack
- **Language**: Python (>=3.12), SQL (dbt)
- **Dependency Management**: `uv`
- **Transformation**: `dbt` (dbt-databricks adapter)
- **Platform**: Databricks (Unity Catalog, Volumes, SQL Warehouses)
- **Data Format**: Delta Lake

## Architecture & Data Flow
1.  **Raw Ingestion**: Text files (`.txt`) are uploaded to Databricks Volumes.
2.  **Parsing**: `scripts/stg_match_results.py` parses these messy text files into a raw Delta table (`raw.match_results_parsed`).
3.  **Bronze Layer**: `dbt` models (`models/bronze/`) clean, type, and test the raw data.
4.  **Silver Layer**: `dbt` models (`models/silver/`) create dimension and fact tables (In Progress).
5.  **Gold Layer**: Advanced analytics like Elo ratings and predictions (Planned).

## Directory Structure
- `afl_analytics/`: The root of the dbt project.
    - `dbt_project.yml`: Main dbt configuration.
    - `models/`: SQL transformation logic.
        - `bronze/`: Staging models (e.g., `stg_match_results.sql`).
        - `silver/`: Intermediate models (e.g., `dim_teams.sql`).
    - `scripts/`: Python scripts for Databricks execution.
- `scripts/`: Local/Utility Python scripts (e.g., parsers).
- `notebooks/`: Jupyter notebooks for data analysis (e.g., `winner.ipynb`).
- `pyproject.toml`: Python project configuration and dependencies.
- `.venv/`: Virtual environment.

### Key Commands & Workflows

### Setup & Dependencies
```bash
uv sync                 # Install dependencies
source .venv/bin/activate
```

### dbt Operations (run from `afl_analytics/` directory)
**Note**: Requires `DATABRICKS_TOKEN` environment variable and properly configured `~/.dbt/profiles.yml`.

**Critical Workflow:**
1.  **Raw Data Updates**: If the raw data schema changes (e.g., adding `match_datetime`) or new files are added, you **must** run `scripts/stg_match_results.py` in Databricks first to update `raw.match_results_parsed`.
2.  **Seed Updates**: If you modify files in `seeds/` (e.g., `seed_teams.csv`), run `uv run dbt seed` to update the tables in Databricks.
3.  **Run Models**: Once dependencies are met, run dbt models.

```bash
cd afl_analytics
uv run dbt deps         # Install dbt packages
uv run dbt debug        # Test connection
uv run dbt seed         # Upload seeds (static data) to Databricks
uv run dbt run          # Run all models
uv run dbt run --select stg_match_results # Run specific model
uv run dbt test         # Run data quality tests
uv run dbt docs generate # Generate documentation
```

### Python Parser

## Conventions
- **Naming**: Snake_case for files and columns.
- **Testing**: All dbt models should have associated tests (schema tests like `not_null`, `unique`).
- **Idempotency**: All scripts and models must be safe to re-run multiple times.
- **Documentation**: Update `_models.yml` and `_sources.yml` when modifying tables.

## Current State
- **Bronze Layer**: Complete & Tested (`stg_match_results` with 2016-2025 data).
- **Silver Layer**: In Progress
  - `dim_teams` - complete (from seed_teams.csv)
  - `dim_venues` - complete (from seed_venues.csv with 26 venues)
  - `fct_matches` - next step
- **Gold Layer**: Planned (crowd analytics, Elo ratings, predictions).
