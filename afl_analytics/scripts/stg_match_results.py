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
    Handles empty crowd column (COVID 2020)
    """

    rows = []
    current_round = None
    pending_match = None

    # Handle file path (you said /dbfs not needed)
    dbfs_path = (
        file_path  # Or file_path.replace('/Volumes/', '/dbfs/Volumes/') if needed
    )

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

            # Split by tabs (your data is tab-delimited)
            tokens = line.split("\t")

            # Clean up empty strings from double tabs
            tokens = [
                t.strip() for t in tokens if t.strip() or t == ""
            ]  # Keep empty strings to maintain position

            # Match line should have at least 5 tokens (Date, Home v Away, Venue, Crowd, Result)
            # But crowd might be empty, so we need flexible parsing

            # Strategy: Look for the pattern "XX-YY" to find the result column
            result_idx = None
            for i, token in enumerate(tokens):
                if re.match(r"^\d+-\d+$", token):  # Matches "105-81"
                    result_idx = i
                    break

            if result_idx is not None and result_idx >= 3:
                # Flush previous pending match (if any)
                if pending_match:
                    rows.append(pending_match)
                    pending_match = None

                # Parse based on position of result column
                date_str = tokens[0] if len(tokens) > 0 else None
                home_away = tokens[1] if len(tokens) > 1 else None
                venue = tokens[2] if len(tokens) > 2 else None

                # Crowd is between venue and result
                crowd_str = (
                    tokens[result_idx - 1]
                    if result_idx > 3
                    else tokens[3]
                    if len(tokens) > 3
                    else None
                )

                result = tokens[result_idx]

                # Everything after result is stats
                stats_tokens = (
                    tokens[result_idx + 1 :] if result_idx + 1 < len(tokens) else []
                )

                # Skip if we don't have the basics
                if not home_away or " v " not in home_away:
                    continue

                # Split "Richmond v Carlton"
                home_team, away_team = home_away.split(" v ", 1)

                # Parse crowd to int (handle empty/missing)
                crowd_val = None
                if crowd_str and crowd_str.strip():
                    try:
                        crowd_val = int(crowd_str.strip().replace(",", ""))
                    except:
                        pass

                # Parse date
                date_val = parse_date(date_str, current_season)

                # Parse result (e.g., "105-81" → home_score=105, away_score=81)
                home_score = None
                away_score = None
                if result and "-" in result:
                    score_parts = result.split("-")
                    if len(score_parts) == 2:
                        try:
                            home_score = int(score_parts[0].strip())
                            away_score = int(score_parts[1].strip())
                        except:
                            pass

                pending_match = {
                    "season": current_season,
                    "round": current_round,
                    "date": date_val,
                    "home_team": home_team.strip(),
                    "away_team": away_team.strip(),
                    "venue": venue.strip() if venue else None,
                    "crowd": crowd_val,
                    "home_score": home_score,
                    "away_score": away_score,
                    "result_raw": result,
                    "stats": stats_tokens,  # First stat from same line
                }

            else:
                # Not a match header — must be a stat line (Goals on next line)
                # e.g., "J. Martin 4"
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
