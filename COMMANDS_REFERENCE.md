# Commands Reference - Quick Guide

Essential commands for the AFL Football Analytics project.

## 📋 Table of Contents

- [Daily Workflow](#daily-workflow)
- [dbt Commands](#dbt-commands)
- [Python Parser](#python-parser)
- [Databricks SQL](#databricks-sql)
- [Git Commands](#git-commands)
- [Troubleshooting](#troubleshooting)

---

## Daily Workflow

### Full Pipeline Run

```bash
# 1. Update data (when you have new .txt files)
# - Upload .txt file to Databricks Volume via UI
# - Update YEARS list in scripts/parse_all_match_results.py

# 2. Run parser (in Databricks notebook/Repos)
# - Open scripts/parse_all_match_results.py
# - Click "Run All"

# 3. Run dbt transformations
cd afl_analytics
uv run dbt run

# 4. Test data quality
uv run dbt test

# 5. Check results in notebooks or SQL editor
```

### Quick Bronze Update

```bash
# Just update Bronze layer
cd afl_analytics
uv run dbt run --select stg_match_results
uv run dbt test --select stg_match_results
```

---

## dbt Commands

### Basic Operations

```bash
# Navigate to dbt project
cd afl_analytics

# Install dbt packages (first time or after updating packages.yml)
uv run dbt deps

# Run all models
uv run dbt run

# Run specific model
uv run dbt run --select stg_match_results

# Run specific layer
uv run dbt run --select bronze.*
uv run dbt run --select silver.*
uv run dbt run --select gold.*

# Full refresh (rebuild from scratch)
uv run dbt run --select stg_match_results --full-refresh

# Run and test in one command
uv run dbt build
```

### Testing

```bash
# Test all models
uv run dbt test

# Test specific model
uv run dbt test --select stg_match_results

# Test specific layer
uv run dbt test --select bronze.*
```

### Documentation

```bash
# Generate documentation
uv run dbt docs generate

# Serve documentation (opens browser)
uv run dbt docs serve
# Opens http://localhost:8080

# Just compile (don't run) - see generated SQL
uv run dbt compile --select stg_match_results
# Check: target/compiled/afl_analytics/models/bronze/stg_match_results.sql
```

### Debugging

```bash
# Show debug information (test connection)
uv run dbt debug

# Dry run (show what would run)
uv run dbt run --select stg_match_results --dry-run

# Show SQL that would be executed
uv run dbt show --select stg_match_results

# List all models
uv run dbt list

# List models with specific tag
uv run dbt list --select tag:bronze
```

---

## Python Parser

### Run Parser Script

**In Databricks Repos:**
1. Navigate to `scripts/parse_all_match_results.py`
2. Click "Run All" (or Cmd/Ctrl + Shift + Enter)

**Or in Databricks Notebook:**
```python
%run ./scripts/parse_all_match_results.py
```

### Update for New Year

**Edit `scripts/parse_all_match_results.py`:**
```python
# Update this line:
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]  # Add new year
```

### Check Volume Files

```python
# List files in Volume
dbutils.fs.ls("/Volumes/afl_analytics_dev/raw/afl_raw_files/")

# Check if specific file exists
dbutils.fs.ls("/Volumes/afl_analytics_dev/raw/afl_raw_files/real_afl_attendance_2024.txt")
```

### Verify Parser Output

```sql
-- Check parsed table exists
SHOW TABLES IN afl_analytics_dev.raw;

-- Count rows
SELECT COUNT(*) FROM afl_analytics_dev.raw.match_results_parsed;

-- Check by season
SELECT season, COUNT(*) as matches
FROM afl_analytics_dev.raw.match_results_parsed
GROUP BY season
ORDER BY season;
```

---

## Databricks SQL

### Setup Commands (One-Time)

```sql
-- Create catalog and schemas
CREATE CATALOG IF NOT EXISTS afl_analytics_dev;

USE CATALOG afl_analytics_dev;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Create Volume for raw files
CREATE VOLUME IF NOT EXISTS raw.afl_raw_files;

-- Verify
SHOW SCHEMAS IN afl_analytics_dev;
SHOW VOLUMES IN raw;
```

### Check Data

```sql
-- List all tables
SHOW TABLES IN afl_analytics_dev.raw;
SHOW TABLES IN afl_analytics_dev.bronze;

-- Describe table schema
DESCRIBE afl_analytics_dev.bronze.stg_match_results;

-- Count rows
SELECT COUNT(*) FROM afl_analytics_dev.bronze.stg_match_results;

-- Sample data
SELECT * FROM afl_analytics_dev.bronze.stg_match_results LIMIT 10;

-- Check specific season
SELECT * FROM afl_analytics_dev.bronze.stg_match_results
WHERE season = 2024
LIMIT 10;
```

### Quick Analysis

```sql
-- Matches by season
SELECT season, COUNT(*) as matches
FROM afl_analytics_dev.bronze.stg_match_results
GROUP BY season
ORDER BY season;

-- Average scores by season
SELECT 
    season,
    AVG(home_score) as avg_home,
    AVG(away_score) as avg_away,
    AVG(margin) as avg_margin
FROM afl_analytics_dev.bronze.stg_match_results
GROUP BY season
ORDER BY season;

-- Biggest wins
SELECT season, round, home_team, away_team, margin
FROM afl_analytics_dev.bronze.stg_match_results
ORDER BY ABS(margin) DESC
LIMIT 10;

-- Crowd statistics (excluding 2020 COVID)
SELECT season, AVG(crowd) as avg_crowd
FROM afl_analytics_dev.bronze.stg_match_results
WHERE crowd IS NOT NULL
GROUP BY season
ORDER BY season;
```

---

## Git Commands

### Daily Git Workflow

```bash
# Check status
git status

# Add changes
git add .

# Commit with message
git commit -m "Add feature X"

# Push to GitHub
git push origin main

# Pull latest changes
git pull origin main
```

### Sync with Databricks

**After pushing to GitHub:**
1. In Databricks, go to **Repos**
2. Find your repo
3. Click **Git** → **Pull**

### Common Git Tasks

```bash
# See commit history
git log --oneline -10

# See what changed in a file
git diff afl_analytics/models/bronze/stg_match_results.sql

# Undo local changes (before commit)
git checkout -- filename

# Create a branch
git checkout -b feature-silver-layer

# Switch branches
git checkout main
```

---

## Troubleshooting

### dbt Issues

**"dbt command not found"**
```bash
# Use uv run prefix
uv run dbt --version

# Or activate environment
uv sync
source .venv/bin/activate
dbt --version
```

**"Connection failed"**
```bash
# Check connection
uv run dbt debug

# Verify environment variable
echo $DATABRICKS_TOKEN

# Re-export token
export DATABRICKS_TOKEN='your-token-here'
```

**"Source not found"**
```bash
# Make sure parser script ran
# Check in Databricks SQL:
SELECT COUNT(*) FROM afl_analytics_dev.raw.match_results_parsed;

# If empty/missing, rerun parser script
```

**"Column not found"**
```bash
# Check actual table schema
DESCRIBE afl_analytics_dev.raw.match_results_parsed;

# Compare with _sources.yml
# Update SQL to match actual columns
```

### Parser Issues

**"FileNotFoundError"**
```python
# Check files exist in Volume
dbutils.fs.ls("/Volumes/afl_analytics_dev/raw/afl_raw_files/")

# Check filename matches exactly
# Should be: real_afl_attendance_YYYY.txt
```

**"No data parsed"**
```python
# Add debug prints to parser
print(f"Line: {line}")
print(f"Tokens: {tokens}")

# Check .txt file format hasn't changed
```

### Data Quality Issues

**Tests failing**
```bash
# See which tests failed
uv run dbt test --select stg_match_results

# Find problem rows
SELECT * FROM afl_analytics_dev.bronze.stg_match_results
WHERE home_score IS NULL;

# Check raw data
SELECT * FROM afl_analytics_dev.raw.match_results_parsed
WHERE home_score IS NULL;
```

**Unexpected NULL values**
```sql
-- Check for NULLs in crowd (2020 COVID expected)
SELECT season, COUNT(*) as null_crowds
FROM afl_analytics_dev.bronze.stg_match_results
WHERE crowd IS NULL
GROUP BY season;

-- Should only be 2020
```

---

## Environment Setup

### Initial Setup

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <your-repo-url>
cd afl-football-analytics

# Install dependencies
uv sync

# Configure dbt connection
cp afl_analytics/profiles.yml.example ~/.dbt/profiles.yml
# Edit ~/.dbt/profiles.yml with your credentials

# Set Databricks token
export DATABRICKS_TOKEN='your-token-here'
# Add to ~/.bashrc or ~/.zshrc for persistence

# Install dbt packages
cd afl_analytics
uv run dbt deps
```

### Verify Setup

```bash
# Check uv
uv --version

# Check dbt connection
cd afl_analytics
uv run dbt debug
# Should show "All checks passed!"

# Check Git
git remote -v
# Should show your GitHub repo
```

---

## Quick Reference Cards

### Adding New Year Data

```
1. Upload .txt → Volume (via Databricks UI)
2. Edit parser → Add year to YEARS list
3. Run parser → Creates/updates raw table
4. Run dbt → Updates Bronze table
5. Test → Verify data quality
```

### Making Changes to Models

```
1. Edit .sql file locally
2. git add, commit, push
3. Pull in Databricks Repos
4. uv run dbt run --select model_name
5. uv run dbt test --select model_name
```

### Daily Development

```
1. git pull (get latest)
2. Make changes locally
3. uv run dbt run (test locally)
4. git commit + push
5. Pull in Databricks
6. Run in Databricks
```

---

## Keyboard Shortcuts

### Databricks Notebooks
- `Cmd/Ctrl + Enter` - Run current cell
- `Cmd/Ctrl + Shift + Enter` - Run all cells
- `Esc + A` - Insert cell above
- `Esc + B` - Insert cell below

### Terminal
- `Ctrl + R` - Search command history
- `Ctrl + C` - Cancel current command
- `Ctrl + L` - Clear screen
- `↑ / ↓` - Navigate command history

---

## Resources

- **dbt Docs**: Generated via `dbt docs serve`
- **Project README**: `../README.md`
- **Learning Roadmap**: `../docs/football-databricks-learning-roadmap.md`
- **Databricks Docs**: https://docs.databricks.com
- **dbt Docs**: https://docs.getdbt.com

---

**Last Updated**: December 2024
**Quick Tip**: Bookmark this file! Press `Cmd/Ctrl + F` to search for specific commands.
