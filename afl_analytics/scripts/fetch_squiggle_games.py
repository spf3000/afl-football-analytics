"""
Fetch AFL match results from the Squiggle API and load them into
`afl_analytics_dev.raw.squiggle_games` on Databricks.

This replaces the manual .txt copy-paste ingestion for match RESULTS.
Note: the Squiggle `games` endpoint does NOT return crowd/attendance,
so the existing .txt-based `raw.match_results_parsed` is still the source
for crowd_analysis until an attendance source is wired in.

Squiggle API: https://api.squiggle.com.au/?q=games;year=YYYY
Usage rules honoured here: descriptive User-Agent with contact email,
on-disk response caching, and a polite delay between requests.

Run from the dbt project root:
    cd afl_analytics && uv run python scripts/fetch_squiggle_games.py
    cd afl_analytics && uv run python scripts/fetch_squiggle_games.py --years 2024 2025
    cd afl_analytics && uv run python scripts/fetch_squiggle_games.py --dry-run   # fetch + parse only, no DB write
    cd afl_analytics && uv run python scripts/fetch_squiggle_games.py --no-cache  # force re-fetch
"""
import argparse
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

API_BASE = "https://api.squiggle.com.au/"
CONTACT_EMAIL = "alandevlin7@gmail.com"
USER_AGENT = f"afl-football-analytics ({CONTACT_EMAIL})"
TARGET_TABLE = "afl_analytics_dev.raw.squiggle_games"
DEFAULT_YEARS = list(range(2016, 2026))  # 2016-2025 (matches existing dataset)
CACHE_DIR = "data/squiggle_cache"
REQUEST_DELAY_SECONDS = 1.0  # be kind to the API
INSERT_BATCH_SIZE = 400

# Explicit raw schema. Faithful to Squiggle fields, renamed to snake_case.
# Order here is the canonical column order used for inserts.
COLUMNS = [
    ("game_id", "BIGINT"),
    ("season", "INT"),
    ("round", "INT"),
    ("round_name", "STRING"),
    ("match_datetime", "STRING"),  # 'YYYY-MM-DD HH:MM:SS' local; bronze casts to TIMESTAMP
    ("tz", "STRING"),
    ("unixtime", "BIGINT"),
    ("home_team", "STRING"),
    ("home_team_squiggle_id", "INT"),
    ("away_team", "STRING"),
    ("away_team_squiggle_id", "INT"),
    ("home_score", "INT"),
    ("home_goals", "INT"),
    ("home_behinds", "INT"),
    ("away_score", "INT"),
    ("away_goals", "INT"),
    ("away_behinds", "INT"),
    ("venue", "STRING"),
    ("complete", "INT"),
    ("winner", "STRING"),
    ("winner_squiggle_id", "INT"),
    ("is_final", "INT"),
    ("is_grand_final", "INT"),
    ("time_str", "STRING"),
    ("updated", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
]


def fetch_year(year, use_cache=True):
    """Fetch all games for a season, with on-disk JSON caching."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"games_{year}.json")

    if use_cache and os.path.exists(cache_path):
        with open(cache_path) as f:
            games = json.load(f)
        print(f"  {year}: {len(games)} games (cached)")
        return games

    url = f"{API_BASE}?q=games;year={year}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    games = payload.get("games", [])

    with open(cache_path, "w") as f:
        json.dump(games, f)
    print(f"  {year}: {len(games)} games (fetched)")
    time.sleep(REQUEST_DELAY_SECONDS)
    return games


def normalise_game(g, ingested_at):
    """Map a raw Squiggle game dict to a row tuple in COLUMNS order."""
    return (
        g.get("id"),
        g.get("year"),
        g.get("round"),
        g.get("roundname"),
        g.get("date"),
        g.get("tz"),
        g.get("unixtime"),
        g.get("hteam"),
        g.get("hteamid"),
        g.get("ateam"),
        g.get("ateamid"),
        g.get("hscore"),
        g.get("hgoals"),
        g.get("hbehinds"),
        g.get("ascore"),
        g.get("agoals"),
        g.get("abehinds"),
        g.get("venue"),
        g.get("complete"),
        g.get("winner"),
        g.get("winnerteamid"),
        g.get("is_final"),
        g.get("is_grand_final"),
        g.get("timestr"),
        g.get("updated"),
        ingested_at,
    )


def sql_literal(value):
    """Render a Python value as a safe Spark SQL literal."""
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def build_create_table_sql():
    cols = ",\n    ".join(f"{name} {dtype}" for name, dtype in COLUMNS)
    return f"CREATE OR REPLACE TABLE {TARGET_TABLE} (\n    {cols}\n) USING DELTA"


def build_insert_batches(rows):
    """Yield multi-row INSERT statements for batches of rows."""
    col_names = ", ".join(name for name, _ in COLUMNS)
    for start in range(0, len(rows), INSERT_BATCH_SIZE):
        batch = rows[start : start + INSERT_BATCH_SIZE]
        values = ",\n    ".join(
            "(" + ", ".join(sql_literal(v) for v in row) + ")" for row in batch
        )
        yield f"INSERT INTO {TARGET_TABLE} ({col_names}) VALUES\n    {values}"


def get_connection():
    """Connect to the Databricks SQL warehouse using the dbt profile."""
    import yaml
    from databricks import sql as dbsql

    with open(os.path.expanduser("~/.dbt/profiles.yml")) as f:
        profiles = yaml.safe_load(f)
    dev = profiles["afl_analytics"]["outputs"]["dev"]
    return dbsql.connect(
        server_hostname=dev["host"],
        http_path=dev["http_path"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def write_to_databricks(rows):
    """Create-or-replace the raw table and load all rows."""
    print(f"\nConnecting to Databricks to write {TARGET_TABLE}...")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS afl_analytics_dev.raw")
        cursor.execute(build_create_table_sql())
        n_batches = 0
        for stmt in build_insert_batches(rows):
            cursor.execute(stmt)
            n_batches += 1
        print(f"  Loaded {len(rows)} rows in {n_batches} batch(es).")
        cursor.execute(
            f"SELECT season, COUNT(*) FROM {TARGET_TABLE} GROUP BY season ORDER BY season"
        )
        print("  Rows by season:")
        for season, count in cursor.fetchall():
            print(f"    {season}: {count}")
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years", type=int, nargs="+", default=DEFAULT_YEARS,
        help="Seasons to fetch (default 2016-2025)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and parse only; do not write to Databricks",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Force re-fetch, ignore cached JSON",
    )
    args = parser.parse_args()

    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    print(f"Fetching Squiggle games for {len(args.years)} season(s)...")
    rows = []
    for year in args.years:
        for g in fetch_year(year, use_cache=not args.no_cache):
            rows.append(normalise_game(g, ingested_at))

    print(f"\nParsed {len(rows)} total games across {len(args.years)} season(s).")
    complete_idx = [name for name, _ in COLUMNS].index("complete")
    complete = sum(1 for r in rows if r[complete_idx] == 100)
    print(f"  {complete} completed (complete=100), {len(rows) - complete} other.")

    if args.dry_run:
        print("\n--dry-run: skipping Databricks write.")
        if rows:
            print("Sample CREATE TABLE:\n" + build_create_table_sql())
            first_batch = next(build_insert_batches(rows[:2]))
            print("\nSample INSERT (first 2 rows):\n" + first_batch)
        return

    if not rows:
        print("No rows to write; aborting.")
        return
    write_to_databricks(rows)
    print("\nDone. Next: run the bronze model with `uv run dbt run --select stg_squiggle_games`.")


if __name__ == "__main__":
    main()
