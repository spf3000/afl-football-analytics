# Project Organization & Migration Guide

## Question 1: Where Does dbt Go?

**Recommended structure: Parent folder with both projects**

```
afl-football-analytics/           ← Parent folder (your repo)
├── afl_analytics/                ← dbt project (NEW!)
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   └── README.md
│
├── notebooks/                    ← Your existing notebooks
│   ├── crowd_analysis.ipynb      ← Keep as-is for now
│   └── match_winner.ipynb        ← Can be broken, that's fine!
│
├── data/                         ← Your existing data folder
│   ├── match_results.csv         ← Keep this!
│   └── crowd_data.csv
│
├── scripts/                      ← Helper scripts
│   └── load_raw_data.py
│
└── README.md                     ← Overall project README
```

**Why this structure?**
- dbt is a separate concern (data pipeline)
- Notebooks are a separate concern (analysis/ML)
- Both use the same Databricks workspace
- All in one Git repo for easy management

## Question 2: Do I Need to Fix Broken Notebooks?

**NO! Leave them broken. Here's why:**

### Your Current Situation
```python
# notebook: crowd_analysis.ipynb
# Some cells work, some are broken mid-refactor

# Cell 1: Load data
raw_df = pd.read_csv("../data/match_results.csv")  # Works

# Cell 2: Clean data (BROKEN from refactor)
raw_df['something'] = some_function_that_doesnt_exist()  # ❌ Broken

# Cell 3: Analysis
avg_crowd = raw_df.groupby('team')['attendance'].mean()  # Can't run because Cell 2 broke
```

### What You Should Do

**Step 1: Ignore broken notebooks entirely**
- Don't fix them
- Don't even open them
- Focus 100% on getting dbt working

**Step 2: Get dbt Bronze layer working**
```bash
# Just get match_results into Bronze
dbt run --select stg_match_results
```

**Step 3: Create a NEW notebook to test**
```python
# notebooks/test_bronze.py
# Fresh start!

matches = spark.table("bronze.stg_match_results")
matches.show(5)
matches.count()

# Does it work? Great! Now you have clean data.
```

**Step 4: Eventually rewrite notebooks from scratch**
```python
# notebooks/crowd_analysis_v2.py
# Clean slate, reading from dbt tables

matches = spark.table("silver.fct_matches")  # When you build Silver
# Write fresh analysis code with clean data
```

### The Migration Path

```
Week 1:
✅ Build dbt Bronze layer
✅ Test with new simple notebook
❌ Don't touch old broken notebooks

Week 2:
✅ Build dbt Silver layer
✅ Create fresh analysis notebooks
❌ Still ignore old notebooks

Week 3:
✅ Build dbt Gold layer
✅ Migrate key analyses to new notebooks
📦 Archive old broken notebooks

Week 4:
✅ Working entirely from dbt + new notebooks
🗑️  Delete old broken notebooks (or keep for reference)
```

## Practical Steps for You

### 1. Set Up Project Structure

```bash
# Create parent folder
mkdir afl-football-analytics
cd afl-football-analytics

# Copy your existing work
cp -r ~/path/to/current/notebooks ./notebooks
cp -r ~/path/to/current/data ./data

# Add dbt project (from the starter I gave you)
# Extract afl_analytics_starter here, rename to afl_analytics
mv afl_analytics_starter afl_analytics

# Your structure now:
# afl-football-analytics/
#   ├── afl_analytics/     (dbt project)
#   ├── notebooks/         (your existing stuff)
#   └── data/              (your CSVs)
```

### 2. Initialize Git (if not already)

```bash
cd afl-football-analytics

git init
echo "target/" >> .gitignore
echo "dbt_packages/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "~/.dbt/profiles.yml" >> .gitignore  # Contains secrets!

git add .
git commit -m "Initial project structure with dbt"
```

### 3. Focus on dbt First

```bash
cd afl_analytics

# Set up Databricks connection
cp profiles.yml.example ~/.dbt/profiles.yml
# Edit profiles.yml with your details

# Test connection
dbt debug

# Upload your CSV to Databricks (see README Step 4)
# Then run Bronze model
dbt run --select stg_match_results
```

### 4. Test Bronze Works

Create a new simple notebook:
```python
# notebooks/test_dbt_bronze.py
# Fresh notebook just to verify dbt works

from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

# Read from Bronze
matches = spark.table("bronze.stg_match_results")

# Verify it works
print(f"Row count: {matches.count()}")
matches.show(5)
matches.printSchema()

# If this works, you're golden! 
# dbt is working, data is accessible
```

### 5. Don't Touch Old Notebooks Yet

```python
# notebooks/crowd_analysis.ipynb
# ← Leave this broken/half-refactored
# ← Don't even open it
# ← You'll rewrite it later with clean dbt data
```

## When to Fix/Rewrite Notebooks?

**After you have dbt Silver layer working:**

```bash
# Once you've built:
# - bronze.stg_match_results
# - bronze.stg_crowd_data  
# - silver.fct_matches (joined and clean)

# THEN create fresh notebooks:
cd ../notebooks

# New crowd analysis
# crowd_analysis_v2.py
matches = spark.table("silver.fct_matches")
# Fresh analysis code here

# New match prediction
# match_winner_v2.py  
features = spark.table("gold.ml_features")  # When Gold is ready
# Fresh ML code here
```

## What About My Data Files?

**Keep them!**

```
data/
├── match_results.csv      ← Keep for backup
├── crowd_data.csv         ← Keep for backup
└── ladder_stats.csv       ← Keep for backup

But don't READ from them in new code!
Instead, load once to Databricks raw schema,
then dbt processes from there.
```

**Loading data workflow:**
```bash
# One-time: Upload CSV to Databricks
# (See scripts/load_raw_data.py)

# From then on: dbt reads from Databricks tables
# Your CSV files are just backups
```

## Summary

### Do This
✅ Create parent folder structure
✅ Add dbt project as subfolder
✅ Keep existing notebooks folder
✅ Focus on getting dbt Bronze working
✅ Test with NEW simple notebook
✅ Leave broken notebooks alone

### Don't Do This
❌ Try to fix broken notebooks
❌ Mix dbt and notebook code
❌ Delete your CSV files
❌ Worry about migrating everything at once
❌ Try to use dbt FROM notebooks

### Timeline

**This week:**
- Set up folder structure
- Get dbt Bronze working
- Test with simple notebook
- Broken notebooks stay broken

**Next week:**
- Build Silver layer in dbt
- Start writing fresh notebooks
- Read from Silver tables
- Old notebooks still ignored

**Week 3+:**
- Build Gold layer
- Rewrite key analyses
- Archive/delete old notebooks
- Fully on new stack

## The Mental Model

```
Old world:
notebooks/ ← Everything here (data loading, cleaning, analysis)
  ├── All mixed together
  └── Hard to reuse, test, or maintain

New world:
afl_analytics/ ← Data pipeline (repeatable, tested)
  └── Creates clean tables

notebooks/ ← Just analysis (clean, focused)
  └── Reads from dbt tables
```

**You're moving from "notebook does everything" to "dbt does data, notebook does analysis"**

That's why broken notebooks don't matter - you're building a new better system!
