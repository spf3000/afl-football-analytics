# Quick Reference: Before & After dbt

## Your Current Workflow

```python
# notebook: crowd-analysis.ipynb

import pandas as pd

# Step 1: Load raw data
raw_df = pd.read_csv("../data/match_results.csv")
crowd_df = pd.read_csv("../data/crowd_data.csv")

# Step 2: Clean data
raw_df['date'] = pd.to_datetime(raw_df['date'])
raw_df['margin'] = raw_df['home_score'] - raw_df['away_score']
crowd_df['attendance'] = crowd_df['attendance'].fillna(0)

# Step 3: Join data
merged = raw_df.merge(crowd_df, on='match_id')

# Step 4: Analysis
avg_crowd = merged.groupby('team')['attendance'].mean()
print(avg_crowd)
```

## New Workflow with dbt

### dbt does the data prep (Bronze layer)

```sql
-- models/bronze/stg_match_results.sql
-- Runs on schedule, creates bronze.stg_match_results table

SELECT
    CAST(match_id AS STRING) as match_id,
    CAST(match_date AS DATE) as match_date,
    CAST(home_score AS INT) as home_score,
    CAST(away_score AS INT) as away_score,
    home_score - away_score as margin  -- Pre-calculated
FROM {{ source('raw', 'match_results_raw') }}
```

```sql
-- models/bronze/stg_crowd_data.sql
-- Creates bronze.stg_crowd_data table

SELECT
    CAST(match_id AS STRING) as match_id,
    COALESCE(CAST(attendance AS INT), 0) as attendance  -- Pre-cleaned
FROM {{ source('raw', 'crowd_data_raw') }}
```

### Your notebook just does analysis

```python
# notebook: crowd-analysis.py
# Much simpler!

# Step 1: Read clean data (that's it!)
matches = spark.table("bronze.stg_match_results")
crowds = spark.table("bronze.stg_crowd_data")

# Step 2: Join (or let dbt do this too in Silver layer)
merged = matches.join(crowds, on='match_id')

# Step 3: Analysis (the fun part!)
avg_crowd = merged.groupBy('team').agg({'attendance': 'avg'})
avg_crowd.show()
```

### Even better: dbt also does the join (Silver layer)

```sql
-- models/silver/fct_matches.sql
-- Creates silver.fct_matches with everything joined

SELECT
    m.match_id,
    m.match_date,
    m.home_team,
    m.away_team,
    m.home_score,
    m.away_score,
    m.margin,
    c.attendance
FROM {{ ref('stg_match_results') }} m
LEFT JOIN {{ ref('stg_crowd_data') }} c ON m.match_id = c.match_id
```

### Now your notebook is JUST analysis

```python
# notebook: crowd-analysis.py
# Super clean!

# Get fully prepared data
matches = spark.table("silver.fct_matches")

# Pure analysis
avg_crowd = matches.groupBy('team').agg({'attendance': 'avg'})
avg_crowd.show()

# Experiment with different metrics
matches.filter("season == 2024").groupBy('venue').agg({'attendance': 'max'}).show()
```

## The Magic

**Before:**
- 50 lines of data prep
- 10 lines of analysis
- Data prep repeated in every notebook

**After:**
- 0 lines of data prep (dbt does it)
- 10 lines of analysis
- Data prep runs once, used everywhere

## Migration Strategy

**Week 1: Just Bronze**
```python
# Keep everything in notebook
matches = spark.table("bronze.stg_match_results")  # Only change!

# Still do your own cleaning/joining/analysis
matches['margin'] = matches['home_score'] - matches['away_score']
# ... rest of analysis
```

**Week 2: Add Silver**
```python
# dbt now handles cleaning/joining
matches = spark.table("silver.fct_matches")  # Pre-joined and clean!

# Just analysis
avg_crowd = matches.groupby('team')['attendance'].mean()
```

**Week 3: Add Gold**
```python
# dbt pre-computes aggregations
crowd_stats = spark.table("gold.agg_crowd_by_team")  # Already aggregated!

# Just visualization
import matplotlib.pyplot as plt
plt.bar(crowd_stats['team'], crowd_stats['avg_home_crowd'])
```

## File Locations

```
Before:
your_project/
├── data/
│   ├── match_results.csv           ← Raw files
│   └── crowd_data.csv
├── crowd-analysis/
│   └── analysis.ipynb              ← Everything in one notebook
└── match-winner/
    └── prediction.ipynb

After:
your_project/
├── afl_analytics/                  ← dbt project (NEW!)
│   ├── models/
│   │   ├── bronze/                 ← Raw ingestion
│   │   ├── silver/                 ← Cleaned & joined
│   │   └── gold/                   ← Analytics-ready
│   └── dbt_project.yml
│
├── notebooks/                      ← Your notebooks (cleaner!)
│   ├── crowd_analysis.py           ← Just reads from dbt tables
│   └── match_prediction.py
│
└── scripts/
    └── load_raw_data.py            ← Automation
```

## Commands You'll Use

```bash
# Morning routine: Update all tables
dbt run

# Made changes to one model?
dbt run --select stg_match_results

# Test everything
dbt test

# See what's in your warehouse
dbt docs generate
dbt docs serve
```

## Your notebooks become

```python
# Top of every notebook (standard pattern)
matches = spark.table("silver.fct_matches")
crowd_stats = spark.table("gold.agg_crowd_by_team")
elo_ratings = spark.table("gold.elo_ratings")

# Then just your analysis!
```

## The Power: Composition

```
bronze.stg_match_results  ←  Used by 5 different models
        ↓
silver.fct_matches  ←  Used by 10 different notebooks
        ↓
gold.elo_ratings  ←  Used by predictions
gold.agg_crowd_by_team  ←  Used by visualizations
gold.brownlow_predictor  ←  Used by season analysis

Your notebook reads whatever it needs!
```

---

**Remember:** You don't migrate everything at once. Start with Bronze, keep notebooks the same, gradually move transformations to dbt as you get comfortable.
