"""
Parse all AFL match results from Volume .txt files
Run this in Databricks notebook to create raw.match_results_parsed table
"""

import re
import pandas as pd
from pyspark.sql import SparkSession
from dateutil import parser as dateparser

# Initialize Spark
spark = SparkSession.builder.getOrCreate()

# Configuration
VOLUME_PATH = "/Volumes/afl_analytics_dev/raw/afl_raw_files"
OUTPUT_TABLE = "afl_analytics_dev.raw.match_results_parsed"
YEARS = [2020, 2021, 2022, 2023, 2024]


def parse_date(date_str, current_season):
    """Parse date string with fuzzy matching"""
    if not date_str or date_str.strip() == "":
        return None
    try:
        dt = dateparser.parse(date_str, fuzzy=True)
        return dt.replace(year=current_season).date()
    except:
        return None


def parse_match_results_file(file_path, current_season):
    """
    Parse a single .txt file for a given season
    Your existing parsing logic, wrapped in a function
    """

    rows = []
    current_round = None
    pending_match = None

    # Read from Volume (convert to /dbfs/ path for file reading)
    dbfs_path = file_path.replace("/Volumes/", "/dbfs/Volumes/")

    print(f"  Reading: {dbfs_path}")

    with open(dbfs_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            # Detect "Round X"
            round_match = re.match(r"Round\s+(\d+)", line)
            if round_match:
                current_round = int(round_match.group(1))
                continue

            # Skip header lines
            if line.startswith("Date") or line.startswith("Home"):
                continue

            # Skip BYE rows
            if "BYE" in line:
                continue

            # Detect a match line
            # Split by multiple spaces or tabs
            tokens = re.split(r"\s{2,}|\t+", line.strip())

            if len(tokens) >= 5:
                # Flush previous pending match (if any)
                if pending_match:
                    rows.append(pending_match)
                    pending_match = None

                date_str = tokens[0]
                home_away = tokens[1]
                venue = tokens[2]
                crowd = tokens[3]
                result = tokens[4]

                # Split "Sydney v Melbourne"
                if " v " in home_away:
                    home_team, away_team = home_away.split(" v ", 1)
                else:
                    # Malformed, skip
                    continue

                # Parse crowd to int
                try:
                    crowd_val = int(crowd.replace(",", ""))
                except:
                    crowd_val = None

                # Parse date
                date_val = parse_date(date_str, current_season)

                # Parse result (e.g., "86-64" → home_score=86, away_score=64)
                home_score = None
                away_score = None
                if "-" in result:
                    score_parts = result.split("-")
                    if len(score_parts) == 2:
                        try:
                            home_score = int(score_parts[0])
                            away_score = int(score_parts[1])
                        except:
                            pass

                pending_match = {
                    "season": current_season,
                    "round": current_round,
                    "date": date_val,
                    "home_team": home_team.strip(),
                    "away_team": away_team.strip(),
                    "venue": venue.strip(),
                    "crowd": crowd_val,
                    "home_score": home_score,
                    "away_score": away_score,
                    "result_raw": result,
                    "stats": [],
                }

            else:
                # Not a match header — must be a stat line
                # e.g., "J. Viney 30" or "C. Oliver 30"
                if pending_match:
                    pending_match["stats"].append(line)

        # Flush last pending match
        if pending_match:
            rows.append(pending_match)

    # Convert to DataFrame
    parsed_rows = []
    for r in rows:
        parsed_rows.append(
            {
                "season": r["season"],
                "round": r["round"],
                "date": r["date"],
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "venue": r["venue"],
                "crowd": r["crowd"],
                "home_score": r["home_score"],
                "away_score": r["away_score"],
                "result_raw": r["result_raw"],
                "disposals_goals": "; ".join(r["stats"]) if r["stats"] else None,
            }
        )

    df = pd.DataFrame(parsed_rows)
    df["scraped_at"] = pd.Timestamp.now()

    return df


# Main execution: Parse all years
print(f"Parsing match results from {VOLUME_PATH}")
print(f"Years: {YEARS}")
print()

all_matches = []

for year in YEARS:
    input_file = f"{VOLUME_PATH}/real_afl_attendance_{year}.txt"

    print(f"Processing {year}...")

    try:
        df = parse_match_results_file(input_file, year)
        all_matches.append(df)
        print(f"  ✅ Parsed {len(df)} matches")
    except FileNotFoundError:
        print(f"  ⚠️  File not found: {input_file}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print()

if not all_matches:
    print("❌ No data parsed. Check file paths and upload .txt files to Volume.")
else:
    # Combine all years
    combined_df = pd.concat(all_matches, ignore_index=True)

    print(f"✅ Total: {len(combined_df)} matches across {len(all_matches)} years")
    print()

    # Show summary
    print("Matches by season:")
    print(combined_df.groupby("season").size())
    print()

    # Convert to Spark DataFrame
    spark_df = spark.createDataFrame(combined_df)

    # Write to Databricks table
    spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        OUTPUT_TABLE
    )

    print(f"✅ Saved to {OUTPUT_TABLE}")
    print()

    # Verify
    print("Verification:")
    spark.sql(f"""
        SELECT 
            season, 
            COUNT(*) as matches,
            MIN(date) as first_match,
            MAX(date) as last_match
        FROM {OUTPUT_TABLE} 
        GROUP BY season 
        ORDER BY season
    """).show()

    print("Sample data:")
    spark.sql(f"SELECT * FROM {OUTPUT_TABLE} LIMIT 5").show()
