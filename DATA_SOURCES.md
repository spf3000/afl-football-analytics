# AFL Data Sources

A reference for AFL data sources that can be used to extend this project beyond the current manual `.txt` file approach.

---

## 1. AFL Tables — afltables.com

Historical match data going back to 1897.

**What's available:**
- Match scores and results (1897–present)
- Attendance/crowd figures (1921–present)
- Player statistics and performance records
- Coaching statistics
- Umpire statistics
- Brownlow Medal historical data
- Individual team pages for all 22 current and historical clubs

**Access method:** Web scraping (no official API). The R package `fitzRoy` wraps this.

**Relevance to this project:**
- Could extend our dataset back to pre-2016 for more Elo rating history
- Player stats needed for Brownlow predictor
- Attendance data could cross-validate our current crowd figures

---

## 2. Squiggle API — api.squiggle.com.au

Free, unofficial AFL API with match data and model predictions.

**Base URL:** `https://api.squiggle.com.au/?q=<query_type>`

**Endpoints:**

| Query type  | Key parameters                        | Returns                                      |
|-------------|---------------------------------------|----------------------------------------------|
| `games`     | `year`, `round`, `game`, `team`, `complete` | Match metadata, scores, venue, timing   |
| `teams`     | `team`, `year`                        | Team details, debut/retirement dates         |
| `standings` | `year`, `round`                       | Ladder rankings, wins, losses, points        |
| `tips`      | `year`, `round`, `source`             | Predictions from multiple computer models    |
| `sources`   | `source`                              | List of available prediction models          |
| `ladder`    | `year`, `round`, `source`             | Model-projected ladder forecasts             |
| `power`     | `year`, `round`, `source`, `team`     | Relative team strength ratings               |

**Output formats:** JSON (default), XML, CSV

**Usage rules:**
- Set a descriptive User-Agent with your contact email
- Cache responses; don't fetch the same data repeatedly
- Free to use commercially (hobby project, no SLA)
- Do not hammer the endpoint — it's rate-sensitive

**Example:**
```
https://api.squiggle.com.au/?q=games;year=2025;round=1
https://api.squiggle.com.au/?q=standings;year=2025
https://api.squiggle.com.au/?q=tips;year=2025;round=1
```

**Relevance to this project:**
- `games` endpoint could replace manual `.txt` file scraping entirely — automated ingestion
- `tips` provides predictions from multiple established models (Squiggle aggregates ~10+ models) — useful benchmark against our Elo model
- `power` ratings are a ready-made alternative to our Elo ratings for comparison
- `standings` could validate our match results data

---

## 3. AFL Official API

The AFL's own data backend used by the official app and website.

**Access method:** Via `fitzRoy` R package (wraps undocumented internal API). Not publicly documented.

**What's available:**
- Fixtures and upcoming games
- Match results and scores
- Team ladders/standings
- Player statistics
- Player lineups and squad details
- Score progression (quarter-by-quarter)

**Competitions supported:** AFLM, AFLW, VFL, VFLW, WAFL, U18 Boys, U18 Girls

**Coverage:** 2019+ for AFLW; full historical for AFLM

**Relevance to this project:**
- Most authoritative source for player-level data
- Required for Brownlow predictor (needs disposal counts, votes)
- AFLW data availability (our current dataset is AFLM only)
- Quarter-by-quarter scores for more granular analysis

---

## 4. Fryzigg / AFL Player Stats API

Provides detailed player statistics.

**Access method:** Via `fitzRoy` R package. The underlying API is `https://www.afl.com.au/stats`.

**What's available:**
- Disposals, marks, goals, tackles, hitouts
- Advanced metrics (contested possessions, clearances, etc.)
- Historical player data

**Relevance to this project:**
- Primary source for Brownlow predictor
- Player-level data for team strength models beyond Elo

---

## 5. Footywire — footywire.com

**What's available:**
- Player fantasy scores (SuperCoach/DreamTeam style)
- Match statistics
- Player profiles and career stats

**Access method:** Web scraping. Wrapped by `fitzRoy`.

**Relevance to this project:**
- Alternative player stats source
- Fantasy scores as a proxy for player value/impact

---

## Using These Sources in This Project

Since this project is Python/dbt (not R), `fitzRoy` itself isn't directly usable. The practical paths are:

### Near-term: Replace manual `.txt` ingestion with Squiggle API

The current pipeline requires manually copy-pasting `.txt` files. The Squiggle `games` endpoint returns the same data in a clean JSON format.

Proposed approach:
1. Write a Python script `scripts/fetch_squiggle_games.py` that calls the Squiggle API
2. Write results to a Delta table (`raw.squiggle_games`) instead of parsing `.txt` files
3. Create a new bronze dbt model that reads from `raw.squiggle_games`

This would make the pipeline fully automated.

### Medium-term: Validate and benchmark Elo ratings

The Squiggle `tips` and `power` endpoints expose predictions from ~10 established models. Once our Elo model is built:
1. Fetch Squiggle tips for the same rounds
2. Compare our model's accuracy (tip success %, margin error) to the Squiggle ensemble
3. Use `power` ratings to cross-check our Elo rating trends

### Longer-term: Player stats for Brownlow predictor

The AFL Official API (via undocumented endpoint) or Fryzigg provides player-level stats. A Brownlow predictor needs:
- Disposals, marks, goals, tackles per player per game
- Historical Brownlow votes for training a model

Proposed approach:
1. Use a Python HTTP client to call the AFL stats API directly (reverse-engineer from fitzRoy source)
2. Or scrape AFLTables for historical player stats (more stable)
3. Land in `raw.player_stats` → bronze → silver `fct_player_game_stats` → gold `brownlow_predictions`

---

## fitzRoy Reference

While this project uses Python, `fitzRoy` is worth knowing as a reference implementation. Its source code shows exactly how to call these APIs.

- **CRAN:** https://cloud.r-project.org/web/packages/fitzRoy/index.html
- **GitHub:** https://github.com/jimmyday12/fitzRoy
- **Docs:** https://jimmyday12.github.io/fitzRoy/
- **Version:** 1.7.0, MIT license, maintained by James Day
