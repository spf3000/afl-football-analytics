# Project Context Summary

**Purpose**: This document captures the key decisions, current state, and important context about the AFL Football Analytics project. Use this to quickly get back up to speed or provide context to future assistants.

**Last Updated**: December 2024

---

## 🎯 What We've Built

A modern data engineering pipeline for AFL match analysis using:
- **Databricks** (data platform)
- **dbt** (SQL transformations)
- **Python** (preprocessing messy .txt files)
- **Functional Programming principles** (idempotency, composition, purity)

**Current Status**: Bronze layer complete and working ✅

---

## 🏗️ Architecture Decisions

### Why This Approach?

**Hybrid Python + dbt (Not Pure SQL)**
- **Decision**: Keep Python script for parsing .txt files, use dbt for clean transformations
- **Reason**: .txt files are genuinely messy (tabs, empty fields, COVID gaps). Python better suited for this.
- **Result**: Python creates `raw.match_results_parsed`, dbt reads it and creates `bronze.stg_match_results`
- **FP Principle**: Both steps are idempotent and composable

**Databricks Volumes (Not Tables) for Raw Files**
- **Decision**: Store raw .txt files in Volumes, not as tables
- **Reason**: More natural, files stay as files, easier to version
- **Location**: `/Volumes/afl_analytics_dev/raw/afl_raw_files/`

**Medallion Architecture**
- **Bronze**: Raw → typed (minimal transformation)
- **Silver**: Cleaned & joined (dimensions + facts) - TO DO
- **Gold**: Analytics-ready (aggregations, ML features) - TO DO

### Technology Choices

**Why uv (not pip/poetry)?**
- Modern, fast Python package manager
- User preference (already using it)
- Good dependency resolution

**Why dbt (not pure Spark)?**
- SQL-based (more maintainable)
- Built-in testing framework
- Documentation generation
- Version control friendly
- Idempotent by design

**Why Databricks (not just local Spark)?**
- Learning goal: Pass Databricks certification
- Modern data platform with Unity Catalog
- Delta Lake format (ACID, time travel)
- Industry standard

---

## 📁 File Organization

### Project Structure

```
afl-football-analytics/          # Git repo root
├── afl_analytics/               # dbt project
│   ├── models/bronze/           # Bronze layer (DONE)
│   ├── models/silver/           # Silver layer (TODO)
│   ├── models/gold/             # Gold layer (TODO)
│   ├── dbt_project.yml
│   └── packages.yml             # Contains dbt_utils
│
├── scripts/                     # Python preprocessing
│   └── parse_all_match_results.py
│
├── notebooks/                   # Analysis notebooks (not migrated yet)
│   ├── crowd_analysis.ipynb     # OLD - uses CSV
│   └── match_winner.ipynb       # OLD - uses CSV
│
├── data/                        # Local CSV files (backup/reference)
└── docs/                        # Learning materials
```

### Databricks Structure

```
afl_analytics_dev (catalog)
├── raw (schema)
│   ├── match_results_parsed     # Created by Python script
│   └── afl_raw_files (volume)   # Raw .txt files
│       ├── real_afl_attendance_2020.txt
│       ├── real_afl_attendance_2021.txt
│       └── ... (2022-2024)
│
└── bronze (schema)
    └── stg_match_results        # Created by dbt
```

---

## 🔑 Key Technical Details

### Data Format Quirks

**2020 COVID Year**
- Crowd column is EMPTY in raw .txt files
- Parser handles this: `crowd_val = None`
- Tests allow NULL crowds (expected for 2020)

**Tab-Delimited Format**
- Files use `\t` separators
- Empty crowd creates double tabs: `MCG		105-81`
- Parser splits by `\t` and finds result by regex pattern

**Multi-Line Format**
```
Thu 19 Mar 7:40pm	Richmond v Carlton	MCG		105-81	P. Cripps 31
J. Martin 4
```
- First line: match info + first stat
- Second line: goals stat
- Parser collects both into `stats` array

### Column Names

**In raw.match_results_parsed:**
- `season`, `round`, `date`
- `home_team`, `away_team`, `venue`, `crowd`
- `home_score`, `away_score`
- `result_raw` (e.g., "105-81")
- `disposals_goals` (combined stats string)
- `scraped_at` (timestamp from parser)

**In bronze.stg_match_results:**
- Same columns from raw, PLUS:
- `margin` = home_score - away_score (calculated)
- `result` = 'home_win'/'away_win'/'draw' (calculated)
- `match_date` (renamed from `date`)
- `_dbt_loaded_at`, `_source_system`, `_python_scraped_at` (metadata)

### Idempotency Patterns

**Python Parser**
- Input: .txt files (immutable in Volume)
- Output: `raw.match_results_parsed` table
- Mode: `mode="overwrite"` - full refresh each time
- Idempotent: ✅ Same files → same output

**dbt Bronze**
- Input: `raw.match_results_parsed`
- Output: `bronze.stg_match_results`
- Mode: `materialized='table'` - recreates each run
- Idempotent: ✅ Same input → same output

---

## 🧪 Testing Strategy

### dbt Tests (Automated)

**In _models.yml:**
- `not_null` on critical columns (season, home_team, scores)
- `accepted_range` on scores (0-300) - catches parsing errors
- `accepted_values` on result (home_win/away_win/draw)
- Uses `dbt_utils` package for advanced tests

**Run with:**
```bash
uv run dbt test --select stg_match_results
```

### Manual Validation

**Check counts by season:**
```sql
SELECT season, COUNT(*) FROM bronze.stg_match_results GROUP BY season;
-- Should see ~206 matches per year
```

**Check 2020 crowds:**
```sql
SELECT COUNT(*) FROM bronze.stg_match_results WHERE season = 2020 AND crowd IS NOT NULL;
-- Should be 0 or very low
```

---

## 🚀 Workflows

### Adding New Year Data (e.g., 2025)

1. **Upload .txt file** to Volume via Databricks UI
2. **Edit parser**: Add 2025 to `YEARS` list
3. **Run parser** in Databricks notebook
4. **Run dbt**: `uv run dbt run --select stg_match_results --full-refresh`
5. **Test**: `uv run dbt test --select stg_match_results`
6. **Verify**: Check row counts in SQL

### Making Changes to dbt Models

1. **Edit locally** in Git repo
2. **Commit and push** to GitHub
3. **Pull in Databricks** Repos (Git → Pull)
4. **Test locally**: `uv run dbt run --select model_name`
5. **Deploy**: Runs automatically when pulled

### Development Loop

1. Make changes locally
2. Test with `uv run dbt run` and `uv run dbt test`
3. Commit to Git
4. Push and sync to Databricks

---

## 🎓 Learning Goals

### Short-term (Next 2 Weeks)
- Build Silver layer (dim_teams, dim_venues, fct_matches)
- Migrate one notebook to use Bronze tables

### Medium-term (1-3 Months)
- Complete Gold layer (Elo, predictions, aggregations)
- Pass Databricks Data Engineer Associate cert
- Blog about FP + data engineering

### Long-term (6-12 Months)
- Become Databricks specialist
- Advanced analytics (Brownlow, game clustering)
- Professional cert, community contributions

---

## ⚠️ Important Notes

### Don't Touch These
- **Broken notebooks**: Leave them broken, will rewrite from scratch later
- **CSV files in data/**: Keep as backup, but don't use in pipeline
- **Old Python scripts**: May have been replaced, check dates

### Critical Files
- **~/.dbt/profiles.yml**: Contains Databricks credentials (NOT in Git)
- **DATABRICKS_TOKEN**: Environment variable (set in shell config)
- **packages.yml**: Contains dbt_utils (needed for tests)

### Known Issues
- `/dbfs/` path prefix not needed in current Databricks setup
- 2020 crowds are NULL (expected, not a bug)
- Parser script must be run manually when data changes (not automated yet)

---

## 🔗 Dependencies

### Python Packages (in pyproject.toml)
- `dbt-databricks` - dbt adapter for Databricks
- `pandas` - Used in parser script
- `python-dateutil` - Date parsing in parser

### dbt Packages (in packages.yml)
- `dbt-labs/dbt_utils@1.1.1` - Testing utilities

### Databricks Resources Required
- SQL Warehouse (any size)
- Unity Catalog enabled
- Volume storage for raw files
- Personal Access Token

---

## 📝 Next Session Checklist

When starting a new chat or coming back to this project:

1. **Read this file first** - get context
2. **Check README.md** - understand current architecture
3. **Check COMMANDS_REFERENCE.md** - find specific commands
4. **Run `git status`** - see what's changed
5. **Run `git log -5`** - see recent commits
6. **Check Databricks** - verify tables exist
7. **Run `uv run dbt test`** - verify data quality

### Quick Status Check

```bash
# Local check
cd afl-football-analytics
git status
git log --oneline -5

# dbt check
cd afl_analytics
uv run dbt debug  # Connection OK?
uv run dbt test   # All tests passing?

# Databricks check (in SQL Editor)
SELECT season, COUNT(*) FROM bronze.stg_match_results GROUP BY season;
-- Should see 2020-2024 with ~206 matches each
```

---

## 🤔 Design Philosophy

### Pragmatic Principles

**"Principled but pragmatic programmers"**
- Use FP principles where they help (idempotency, composition)
- Use practical solutions for messy problems (Python parser)
- Don't over-engineer for theoretical purity
- Optimize for maintainability and learning

### When to Use Python vs SQL

**Python**:
- Complex text parsing (messy .txt files)
- Multi-step stateful logic (collecting stats across lines)
- File system operations

**SQL (dbt)**:
- Clean transformations (margin = home - away)
- Joins and aggregations
- Derived columns
- Testing and documentation

### Version Control Strategy

**Everything in Git except:**
- Credentials (~/.dbt/profiles.yml)
- Generated files (target/, dbt_packages/)
- Local data files (just keep in data/ as backup)

---

## 💡 Lessons Learned

1. **Volumes > Tables for raw files** - More natural, easier to manage
2. **Python + dbt hybrid works** - Each tool for its strength
3. **Testing is crucial** - Caught the COVID crowd issue early
4. **Documentation pays off** - dbt docs are amazing
5. **Idempotency matters** - Safe reruns = less stress
6. **Start simple** - Bronze first, then Silver, then Gold

---

## 🔮 Future Enhancements

### Immediate (Next Sprint)
- [ ] Build Silver layer
- [ ] Migrate one notebook
- [ ] Add crowd data as separate source

### Soon
- [ ] Automate parser (Databricks workflow)
- [ ] Schedule dbt runs
- [ ] Add data quality monitoring
- [ ] Build Elo system in Gold

### Later
- [ ] CI/CD pipeline
- [ ] Data catalog integration
- [ ] Incremental models (not full refresh)
- [ ] Lineage tracking

---

**If you're reading this in a new chat session**: Welcome back! This document should give you everything you need to continue. Check the other docs (README.md, COMMANDS_REFERENCE.md) for detailed instructions.

**Pro tip**: Use Claude's conversation search to find previous discussions about specific topics if needed!
