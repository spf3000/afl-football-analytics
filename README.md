# AFL Football Analytics - Data Pipeline

A modern data engineering project for AFL match analysis, built with dbt, Databricks, and functional programming principles.

## 🎯 Project Goals

- **Learning**: Master Databricks and dbt while building a real data pipeline
- **Certification**: Pass Databricks Data Engineer Associate certification (3-4 months)
- **Long-term**: Become a Databricks specialist with deep technical knowledge
- **Analytics**: Build advanced AFL analytics (Elo ratings, predictions, Brownlow predictor)
- **FP Principles**: Apply functional programming patterns (idempotency, composition, purity)

## 📁 Project Structure

```
afl-football-analytics/
├── afl_analytics/              # dbt project (data pipeline)
│   ├── dbt_project.yml         # Main dbt config
│   ├── models/
│   │   ├── bronze/             # Raw → typed tables
│   │   ├── silver/             # Cleaned & core entities (in development)
│   │   └── gold/               # Analytics & aggregations (future)
│   ├── scripts/                 # Run on databricks
│   └── data/                   # data - not committed
    └ seeds/                    #


│
├── scripts/                    # Python preprocessing scripts
│   └── stg_match_results.py  # Parse .txt files → raw table
│
├── notebooks/                  # Analysis notebooks
│   ├── crowd_analysis.ipynb    # (your existing work)
│   └── match_winner.ipynb
│
├── data/                       # Local data (for reference)
│   └── (your CSV files)
│
├── README.md                   # This file
└── COMMANDS_REFERENCE.md       # Quick command reference
```

## 🏗️ Architecture

### Medallion Architecture (Bronze → Silver → Gold)

```
Raw .txt Files (Volume)
    ↓
Python Parser (scripts/stg_match_results.py)
    ↓
raw.match_results_parsed (Raw table)
    ↓
dbt Bronze Model (models/bronze/stg_match_results.sql)
    ↓
bronze.stg_match_results (Typed, tested, documented)
    ↓
Silver Models:
  - dim_teams (team dimension from seed)
  - dim_venues (venue dimension from seed)
  - fct_matches (fact table with FK joins)
    ↓
Gold Models:
  - crowd_analysis (match-level attendance analytics)
  - [Future: Elo ratings, predictions]
```

### Functional Programming Principles

**Idempotency:**

- Python parser: Same .txt files → same parsed table (can rerun safely)
- dbt models: Same input → same output (can rerun safely)
- No side effects, no hidden state

**Composition:**

- Bronze models compose into Silver models
- Silver models compose into Gold models
- Small, single-purpose transformations

**Purity:**

- Each dbt model is a pure function: `output = f(inputs)`
- Deterministic transformations
- Easy to test and reason about

**Immutability:**

- Bronze layer stays raw
- Transformations create new tables, never UPDATE in place
- Version history preserved

## 🚀 Current Pipeline Status

### ✅ Completed

**Bronze Layer:**

- [x] Raw .txt files uploaded to Databricks Volume
- [x] Python parser handles messy text format
- [x] `raw.match_results_parsed` table created (2016-2025)
- [x] dbt Bronze model creates `bronze.stg_match_results`
- [x] Data quality tests passing
- [x] Documentation generated

**Silver Layer:**

- [x] `dim_teams` - Team dimension (18 AFL teams with metadata)
- [x] `dim_venues` - Venue dimension (26 venues with capacity, aliases)
- [x] `fct_matches` - Fact table with team/venue foreign keys
- [x] Venue name matching via aliases (handles sponsored names)
- [x] Team name matching (handles "GWS" → "Greater Western Sydney")

**Gold Layer:**

- [x] `crowd_analysis` - Match-level attendance analytics with:
  - Venue utilization % (attendance/capacity)
  - Finals flag and round ordering
  - Team season averages (overall and venue-specific)
  - Benchmark averages for deviation calculations

**Data Available:**

- Match results (2016-2025): ~2000+ matches
- Teams, venues, scores, crowds (NULL for 2020 COVID year)
- Calculated fields: margin, result, utilization_pct, benchmark averages

### 🔨 In Progress / Next Steps

**Gold Layer (Next):**

- [ ] Elo rating system
- [ ] Match prediction model
- [ ] Brownlow predictor (requires player data)

**Other:**

- [ ] Migrate existing notebooks to use Gold tables
- [ ] Add player statistics data source

## 🔧 Tech Stack

- **Data Platform**: Databricks (Unity Catalog, Volumes, SQL Warehouses)
- **Transformation**: dbt (SQL-based transformations)
- **Language**: Python (preprocessing), SQL (transformations)
- **Package Management**: uv (Python), dbt (SQL packages)
- **Version Control**: Git + GitHub
- **Storage Format**: Delta Lake (ACID transactions, time travel)
- **Testing**: dbt tests (data quality), dbt_utils package

## 📊 Data Sources

### Match Results (.txt files)

- **Source**: Copy/paste from AFL websites
- **Format**: Tab-delimited text files (messy!)
- **Years**: 2020-2024 (one file per year)
- **Location**: `/Volumes/afl_analytics_dev/raw/afl_raw_files/`
- **Parser**: `scripts/stg_match_results.py`
- **Challenges**:
  - Empty crowd column for 2020 (COVID)
  - Multiple lines per match
  - Inconsistent spacing
  - BYE rows to filter

### Future Data Sources

- Crowd analysis data
- Player statistics (if available)

## 🏃 Quick Start

### Prerequisites

- Databricks workspace access
- Python 3.11+
- uv package manager
- Git

### Initial Setup

1. **Clone Repository:**

   ```bash
   git clone <your-repo-url>
   cd afl-football-analytics
   ```

2. **Install Dependencies:**

   ```bash
   uv sync
   ```

3. **Configure Databricks Connection:**

   ```bash
   cp afl_analytics/profiles.yml.example ~/.dbt/profiles.yml
   # Edit ~/.dbt/profiles.yml with your Databricks credentials
   export DATABRICKS_TOKEN='your-token-here'
   ```

4. **Create Databricks Resources:**

   ```sql
   -- In Databricks SQL Editor
   CREATE CATALOG IF NOT EXISTS afl_analytics_dev;
   CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.raw;
   CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.bronze;
   CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.silver;
   CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.gold;
   CREATE VOLUME IF NOT EXISTS afl_analytics_dev.raw.afl_raw_files;
   ```

5. **Upload Raw Data:**
   - Navigate to Catalog → `afl_analytics_dev` → `raw` → `Volumes` → `afl_raw_files`
   - Upload your .txt files: `real_afl_attendance_YYYY.txt`

6. **Run Parser Script:**

   ```bash
   # In Databricks notebook or Repos
   # Open: scripts/stg_match_results.py
   # Click "Run All"
   ```

7. **Run dbt:**

   ```bash
   cd afl_analytics
   uv run dbt deps    # Install packages (first time only)
   uv run dbt run     # Create Bronze tables
   uv run dbt test    # Run data quality tests
   ```

### Daily Workflow

```bash
# When you get new data (e.g., 2025 season) or schema changes

# 1. Upload new .txt file to Volume (via Databricks UI) if applicable

# 2. Update and Run parser script in Databricks
# Edit scripts/stg_match_results.py if adding new years.
# IMPORTANT: Run this in Databricks to update raw.match_results_parsed
# especially if you've modified the parsing logic (e.g., adding match_datetime).

# 3. Run dbt locally
cd afl_analytics
uv run dbt seed                 # Update seeds (teams, venues)
uv run dbt run                  # Run all models
uv run dbt run --select bronze  # Run bronze layer only
uv run dbt run --select silver  # Run silver layer only
uv run dbt run --select gold    # Run gold layer only
uv run dbt test                 # Verify data quality

# 4. Use in notebooks!
```

## 📚 Documentation

### Generate dbt Docs

```bash
cd afl_analytics
uv run dbt docs generate
uv run dbt docs serve  # Opens browser at http://localhost:8080
```

**What you'll see:**

- Data lineage diagram (visual flow of transformations)
- Column-level documentation
- Test results
- SQL code for each model
- Source → Model → Usage relationships

### Key Documentation Files

- `README.md` (this file) - Project overview
- `COMMANDS_REFERENCE.md` - Quick command reference
- `afl_analytics/models/bronze/_models.yml` - Column documentation
- `docs/football-databricks-learning-roadmap.md` - Learning timeline
- `docs/football-dbt-project-structure.md` - Detailed architecture

## 🧪 Testing

### Run All Tests

```bash
cd afl_analytics
uv run dbt test
```

### Run Tests for Specific Model

```bash
uv run dbt test --select stg_match_results
```

### What Tests Check

- **not_null**: Critical columns have no NULLs
- **accepted_range**: Scores between 0-300
- **accepted_values**: Result is home_win/away_win/draw
- Custom tests in `tests/` directory

## 🔍 Exploration & Analysis

### Using Gold Data in Notebooks

```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

# Read from Gold layer (recommended for analysis)
crowd = spark.table("afl_analytics_dev.gold.crowd_analysis")

# Spot attendance anomalies (games well above team's venue average)
crowd.filter("attendance - home_team_venue_season_avg > 10000").show()

# Compare team's drawing power at a specific venue
crowd.filter("venue_id = 'MCG'") \
    .groupBy("home_team_id", "season") \
    .agg({"attendance": "avg"}) \
    .orderBy("avg(attendance)", ascending=False).show()

# Venue utilization trends
crowd.groupBy("venue_id", "season") \
    .agg({"utilization_pct": "avg"}) \
    .orderBy("season").show()
```

### Using Silver/Bronze Data

```python
# Silver layer - for custom joins
matches = spark.table("afl_analytics_dev.silver.fct_matches")
teams = spark.table("afl_analytics_dev.silver.dim_teams")
venues = spark.table("afl_analytics_dev.silver.dim_venues")

# Bronze layer - raw typed data
raw_matches = spark.table("afl_analytics_dev.bronze.stg_match_results")
```

### Query in Databricks SQL

```sql
-- Average scores by season
SELECT 
    season,
    AVG(home_score) as avg_home_score,
    AVG(away_score) as avg_away_score,
    AVG(margin) as avg_margin
FROM afl_analytics_dev.bronze.stg_match_results
GROUP BY season
ORDER BY season;

-- Biggest wins by margin
SELECT season, round, home_team, away_team, margin
FROM afl_analytics_dev.bronze.stg_match_results
ORDER BY ABS(margin) DESC
LIMIT 10;
```

## 📖 Learning Resources

### Databricks Certification Prep

- Databricks Academy (free courses)
- Practice exam (before attempting)
- Focus areas: Delta Lake, Spark SQL, performance tuning
- Timeline: 3-4 months to Associate certification

### FP + Data Engineering

- Medallion architecture = function composition
- dbt models = pure functions
- Delta Lake = immutable event log
- Idempotent transformations = safe reruns

### Reference Documentation

- `/docs/` folder contains detailed guides
- dbt docs: `dbt docs serve`
- Databricks docs: <https://docs.databricks.com>

## 🐛 Troubleshooting

### Common Issues

**"dbt command not found"**

```bash
# Use uv run prefix
uv run dbt --version

# Or activate environment first
uv sync
source .venv/bin/activate
dbt --version
```

**"Source 'match_results_parsed' not found"**

```bash
# Make sure parser script ran successfully
# Check in Databricks SQL:
SHOW TABLES IN afl_analytics_dev.raw;
SELECT COUNT(*) FROM afl_analytics_dev.raw.match_results_parsed;
```

**"Column not found" or "UNRESOLVED_COLUMN" errors in dbt**

- This usually means the Python parser hasn't been run on Databricks since a schema change (e.g., adding `match_datetime`).
- Run the `scripts/stg_match_results.py` script in Databricks to refresh the raw table.
- Check `_sources.yml` matches actual table schema: `DESCRIBE afl_analytics_dev.raw.match_results_parsed`

**Tests failing**

```bash
# See which tests failed
uv run dbt test --select stg_match_results

# Check the data
SELECT * FROM afl_analytics_dev.bronze.stg_match_results
WHERE home_score IS NULL;  -- Find the problem rows
```

## 🎯 Project Milestones

### Completed ✅

- [x] Project structure set up
- [x] Git repository initialized
- [x] Databricks connection configured
- [x] Raw data uploaded to Volume (2016-2025)
- [x] Python parser working
- [x] Bronze layer complete (`stg_match_results`)
- [x] Silver layer complete (`dim_teams`, `dim_venues`, `fct_matches`)
- [x] Gold layer started (`crowd_analysis`)
- [x] dbt tests passing
- [x] Documentation generated
- [x] Match datetime parsing implemented
- [x] Venue alias matching (sponsored names)
- [x] Team name matching (GWS edge case)

### Next Steps 🔨

- [ ] Migrate notebooks to use Gold tables
- [ ] Build Elo rating system in Gold layer
- [ ] Start Databricks certification study

### Future 📅

- [ ] Match prediction model
- [ ] Brownlow predictor (requires player data)
- [ ] Pass Databricks Data Engineer Associate certification

## 🤝 Contributing / Development

### Making Changes

1. **Edit locally in Git repo**
2. **Commit changes**

   ```bash
   git add .
   git commit -m "Add feature X"
   git push
   ```

3. **Sync in Databricks Repos**
   - Go to Repos → Your repo
   - Click Git → Pull
4. **Test changes**

   ```bash
   uv run dbt run
   uv run dbt test
   ```

### Code Style

- SQL: Lowercase keywords, clear indentation
- Python: Follow PEP 8, use type hints
- dbt: One model per file, clear naming
- Tests: Add tests for all new models
- Documentation: Update _models.yml for new columns

## 📞 Contact / Questions

- **Project Owner**: Alan (that's you!)
- **Repository**: <https://github.com:spf3000/afl-football-analytics.git>
- **Databricks Workspace**: <https://dbc-1a2d7fa9-029a.cloud.databricks.com/browse/folders/2908617711815098?o=157478337743706>

## 📝 Notes

- 2020 season has NULL crowds (COVID)
- Parser script handles messy .txt format
- dbt runs can be scheduled in Databricks Jobs (future)
- Delta Lake provides time travel: `SELECT * FROM table VERSION AS OF 1`
- All transformations are idempotent - safe to rerun anytime

---

**Last Updated**: January 2026
**Status**: Bronze/Silver complete, Gold layer (crowd_analysis) complete
**Learning Focus**: Databricks certification prep + FP principles
