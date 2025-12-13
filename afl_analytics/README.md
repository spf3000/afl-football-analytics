# AFL Analytics - Minimal dbt Starter

A minimal dbt project to get you started with the Bronze layer for AFL match results.

## What This Does

This starter project:

1. Takes your raw match results CSV
2. Loads it to Databricks as a raw table
3. Creates a Bronze layer table with proper types and metadata
4. Makes it available for your Python notebooks to use

**After this, your notebooks read from Bronze instead of CSV files!**

---

## Project Structure

```
afl_analytics_starter/
├── dbt_project.yml              # Main dbt config
├── profiles.yml.example         # Databricks connection template
│
├── models/
│   └── bronze/
│       ├── _sources.yml         # Defines where raw data lives
│       ├── _models.yml          # Documentation and tests
│       └── stg_match_results.sql # The Bronze model (raw → typed table)
│
└── scripts/
    └── load_raw_data.py         # Helper to upload CSV to Databricks
```

---

## Setup Instructions

### [x] Step 1: Install dbt

```bash
# Install dbt with Databricks adapter
pip install dbt-databricks

# Verify installation
dbt --version
```

### Step 2: Configure Databricks Connection

1. Copy the example profile:

   ```bash
   mkdir -p ~/.dbt
   cp profiles.yml.example ~/.dbt/profiles.yml
   ```

2. Edit `~/.dbt/profiles.yml` with your Databricks details:
   - **host**: Your workspace URL (e.g., `dbc-abc123-xyz.cloud.databricks.com`)
   - **http_path**: Your SQL warehouse path (from SQL Warehouses → Connection Details)
   - **token**: Your personal access token

3. Set your token as environment variable:

   ```bash
   export DATABRICKS_TOKEN='your-token-here'
   ```

   Or add to your `~/.bashrc` or `~/.zshrc`:

   ```bash
   echo 'export DATABRICKS_TOKEN="your-token-here"' >> ~/.bashrc
   ```

### Step 3: Create Databricks Catalog

In Databricks SQL Editor or notebook:

```sql
-- Create catalog for your project
CREATE CATALOG IF NOT EXISTS afl_analytics_dev;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.raw;
CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.bronze;

-- Verify
SHOW SCHEMAS IN afl_analytics_dev;
```

### Step 4: Load Your Raw Data

**Option A: Using Databricks UI**

1. Upload your CSV to Databricks
2. In SQL Editor:

   ```sql
   CREATE TABLE afl_analytics_dev.raw.match_results_raw
   USING csv
   OPTIONS (path '/FileStore/tables/match_results.csv', header 'true');
   ```

**Option B: Using Python Script**

1. Upload CSV to Databricks (Data → Upload File)
2. Run in Databricks notebook:

   ```python
   %run ./scripts/load_raw_data.py
   
   load_match_results_to_databricks(
       csv_path="dbfs:/FileStore/tables/match_results.csv",
       catalog="afl_analytics_dev"
   )
   ```

**Option C: From Local File (if using dbt locally)**

```python
# In a local Python script with databricks-connect
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

df = spark.read.csv("path/to/local/match_results.csv", header=True)
df.write.mode("overwrite").saveAsTable("afl_analytics_dev.raw.match_results_raw")
```

### Step 5: Test dbt Connection

```bash
# Navigate to project directory
cd afl_analytics_starter

# Test connection
dbt debug
```

You should see:

```
Connection test: [OK connection ok]
```

### Step 6: Run Your First dbt Model

```bash
# Run the Bronze layer model
dbt run --select stg_match_results

# Check it worked
dbt test --select stg_match_results
```

You should see:

```
Completed successfully
1 table created: bronze.stg_match_results
```

---

## Verify It Worked

### In Databricks SQL Editor

```sql
-- Check the Bronze table was created
SELECT * FROM afl_analytics_dev.bronze.stg_match_results
LIMIT 10;

-- Check row count
SELECT COUNT(*) FROM afl_analytics_dev.bronze.stg_match_results;
```

### In Your Python Notebook

```python
# Read from Bronze instead of CSV!
matches_df = spark.table("afl_analytics_dev.bronze.stg_match_results")

matches_df.show(5)

# Now continue with your analysis as before
# But the data is now:
# - Properly typed
# - Documented
# - Tested
# - Versioned in Git
```

---

## What Changed in Your Workflow?

**Before:**

```python
# Your notebook
import pandas as pd
raw_df = pd.read_csv("../data/match_results.csv")
# ... cleaning and analysis
```

**After:**

```python
# Your notebook
matches_df = spark.table("bronze.stg_match_results")
# Data already typed and cleaned!
# ... just analysis
```

**Benefits:**

- ✅ Bronze table auto-updates when you run dbt
- ✅ Data is tested (no nulls, valid scores)
- ✅ Changes tracked in Git
- ✅ Documentation auto-generated
- ✅ Reusable across notebooks

---

## Common dbt Commands

```bash
# Run all models
dbt run

# Run specific model
dbt run --select stg_match_results

# Run tests
dbt test

# Run specific test
dbt test --select stg_match_results

# Generate documentation
dbt docs generate
dbt docs serve  # Opens in browser

# See what would run (dry run)
dbt run --select stg_match_results --dry-run

# Full refresh (rebuild from scratch)
dbt run --select stg_match_results --full-refresh
```

---

## Next Steps

Once this is working, you can:

1. **Add crowd data:**
   - Create `stg_crowd_data.sql` in `models/bronze/`
   - Follow same pattern as match results

2. **Add ladder stats:**
   - Create `stg_ladder_stats.sql` in `models/bronze/`
   - Update `_sources.yml` with new source

3. **Build Silver layer:**
   - Create `models/silver/` folder
   - Add `fct_matches.sql` that references Bronze
   - Start composing transformations!

4. **Migrate more notebooks:**
   - Each time you move data prep to dbt
   - Your notebooks get simpler
   - Focus more on analysis, less on data wrangling

---

## Troubleshooting

**"dbt debug fails"**

- Check `~/.dbt/profiles.yml` has correct credentials
- Verify `DATABRICKS_TOKEN` environment variable is set
- Test Databricks connection manually in SQL Editor

**"Source 'match_results_raw' not found"**

- Make sure you ran Step 4 (load raw data)
- Check table exists: `SHOW TABLES IN afl_analytics_dev.raw`
- Verify catalog name matches in profiles.yml

**"Permission denied"**

- Make sure you have CREATE TABLE permissions in Databricks
- Check you can manually create tables in SQL Editor

**"Model already exists"**

- That's fine! dbt will recreate it
- Use `dbt run --full-refresh` to force rebuild

---

## Your Columns Don't Match?

Edit `models/bronze/stg_match_results.sql` to match your CSV:

```sql
SELECT
    -- Add/remove/rename columns to match your data
    CAST(your_column_name AS STRING) as match_id,
    -- ...
FROM {{ source('raw', 'match_results_raw') }}
```

Also update `_sources.yml` and `_models.yml` to document your actual columns.

---

## Questions?

**"Do I need to learn SQL?"**
Yes, but you already know SQL from your coursework! dbt SQL is just SELECT statements.

**"Can I still use notebooks?"**
Absolutely! dbt builds the tables, notebooks consume them.

**"What if I want to experiment?"**
Keep experimenting in notebooks! Only promote stable transformations to dbt.

**"Is this FP principles?"**
Yes! Bronze model is:

- Pure: same input → same output
- Idempotent: run multiple times safely
- Immutable: creates new table, doesn't mutate source

---

## Ready to Go?

Follow steps 1-6 above, then you'll have:

- ✅ Match results in Bronze layer
- ✅ Automated data pipeline
- ✅ Foundation for Silver/Gold layers
- ✅ Cleaner notebooks

Let's get started! 🏈📊
