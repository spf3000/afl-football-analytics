# AFL Analytics - Quick Start Guide

## 🎯 Current Status
- **Bronze layer**: ✅ Working (2020-2024 match data)
- **Silver layer**: 🔨 Next step
- **Gold layer**: 📅 Future

## 🚀 Running the Pipeline

### Step 1: Run Python Parser (in Databricks)
```python
# Open: afl_analytics/scripts/stg_match_results.py
# Click "Run All" or press Cmd/Ctrl + Shift + Enter
```

### Step 2: Run dbt (locally)
```bash
cd afl_analytics
uv run dbt run --select stg_match_results
uv run dbt test --select stg_match_results
```

### Step 3: Query Your Data
```sql
-- In Databricks SQL Editor
SELECT * FROM afl_analytics_dev.bronze.stg_match_results LIMIT 10;
```

## 📁 Project Structure
```
afl_analytics/
├── scripts/
│   └── stg_match_results.py    # Parser script (run in Databricks)
├── models/bronze/
│   └── stg_match_results.sql   # dbt model
└── dbt_project.yml
```

## ⚠️ Common Issues

### "Column 'date_time' not found"
The Python parser creates a column named `date`, not `date_time`. This has been fixed.

### "Source table not found"
Run the Python parser first - it creates the source table `raw.match_results_parsed`.

### Adding New Year Data
1. Upload `real_afl_attendance_2025.txt` to Databricks Volume
2. Edit `stg_match_results.py`: Add 2025 to `YEARS` list
3. Re-run the parser and dbt

## 🔍 Useful Queries
```sql
-- Matches by season
SELECT season, COUNT(*) as matches
FROM afl_analytics_dev.bronze.stg_match_results
GROUP BY season;

-- Biggest wins
SELECT season, round, home_team, away_team, margin
FROM afl_analytics_dev.bronze.stg_match_results
ORDER BY ABS(margin) DESC
LIMIT 10;
```

## 📚 Next Steps
1. Build Silver layer (dim_teams, dim_venues, fct_matches)
2. Migrate notebooks to use Bronze tables
3. Build Gold layer (Elo ratings, predictions)

---
**Last Updated**: December 2024