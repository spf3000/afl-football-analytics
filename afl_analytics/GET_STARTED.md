# AFL Analytics dbt Starter - Getting Started

You now have a minimal dbt project ready to go! 🎉

## What You Got

```
afl_analytics_starter/
├── README.md                    ← Full instructions (START HERE!)
├── QUICK_REFERENCE.md           ← Before/after examples
├── dbt_project.yml              ← Main config
├── profiles.yml.example         ← Connection template
│
├── models/bronze/
│   ├── _sources.yml             ← Where raw data lives
│   ├── _models.yml              ← Documentation & tests
│   └── stg_match_results.sql    ← Your first Bronze model!
│
└── scripts/
    └── load_raw_data.py         ← Helper to upload CSV
```

## Quick Start (3 Steps!)

### 1. Install dbt
```bash
pip install dbt-databricks
```

### 2. Set up Databricks connection
```bash
# Copy example profile
mkdir -p ~/.dbt
cp profiles.yml.example ~/.dbt/profiles.yml

# Edit with your Databricks details
nano ~/.dbt/profiles.yml

# Set your token
export DATABRICKS_TOKEN='your-token-here'
```

### 3. Run it!
```bash
# Load your CSV to Databricks first (see README Step 4)
# Then:

cd afl_analytics_starter
dbt debug  # Test connection
dbt run    # Create Bronze table!
```

## What Happens

**dbt takes your CSV:**
```
data/match_results.csv
```

**And creates a Bronze table:**
```sql
bronze.stg_match_results
```

**Your notebook reads from Bronze:**
```python
# Instead of: pd.read_csv("data/match_results.csv")
matches = spark.table("bronze.stg_match_results")

# Data is now:
# ✅ Properly typed (dates are dates, ints are ints)
# ✅ Tested (no nulls, valid scores)
# ✅ Documented
# ✅ Versioned in Git
```

## Full Details

Read **README.md** for:
- Complete setup instructions
- How to load your CSV
- Troubleshooting
- Next steps

Read **QUICK_REFERENCE.md** for:
- Before/after workflow examples
- Migration strategy
- Common patterns

## Your Journey

```
Today:     Bronze layer (match_results only)
           └─ Your notebooks read from Bronze

Week 2:    Add crowd_data and ladder_stats to Bronze
           └─ Start building Silver layer (joins, cleaning)

Week 3:    Build Silver layer (fct_matches)
           └─ Notebooks get simpler!

Week 4+:   Build Gold layer (Elo, aggregations)
           └─ Advanced analytics!

3 months:  Pass Databricks certification
           └─ Become the specialist!
```

## Need Help?

1. **Check README.md** - Step-by-step instructions
2. **Check QUICK_REFERENCE.md** - See examples
3. **Ask me!** - I'm here to help

## Remember

- Start small (just Bronze!)
- Keep notebooks working as-is
- Gradually migrate transformations
- FP principles: pure, idempotent, composable

Ready? Open README.md and let's go! 🚀
