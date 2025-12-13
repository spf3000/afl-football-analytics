import csv
import re
import pandas as pd
from datetime import datetime

INPUT_FILE = "data/real_afl_attendance_2024.txt"
OUTPUT_FILE = "data/parsed_real_afl_attendance_2024.csv"
current_season = 2024

def parse_input_file(path):
    rows = []
    current_round = None
    pending_match = None  # temp storage for the match row
    
    with open(path, "r") as f:
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

            # Detect a match line (must begin with a day or digit time)
            # e.g. "Thu 7 Mar 7:30pm Sydney v Melbourne SCG 40012 86-64"
            tokens = re.split(r"\s{2,}|\t+", line.strip())
            # tokens: [Date, Home v Away, Venue, Crowd, Result, maybe stats?]
           
           
            from dateutil import parser as dateparser

            def parse_date(date_str, current_season):
                if not date_str or date_str.strip() == "":
                    return None
                try:
                    dt = dateparser.parse(date_str, fuzzy=True)
                    return dt.replace(year=current_season).date()
                except:
                    return None

            if len(tokens) >= 5:
                # Flush previous pending match (if any)
                if pending_match:
                    rows.append(pending_match)
                    pending_match = None

                date_str = parse_date(tokens[0], current_season)
                home_away = tokens[1]
                venue = tokens[2]
                crowd = tokens[3]
                result = tokens[4]

                # Split "Sydney v Melbourne"
                if " v " in home_away:
                    home_team, away_team = home_away.split(" v ", 1)
                else:
                    # If malformed, skip
                    continue

                # Parse crowd to int (optional)
                try:
                    crowd_val = int(crowd)
                except:
                    crowd_val = None

                # Parse date (convert e.g. "Thu 7 Mar 7:30pm" → datetime)
                try:
                    date_val = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                except:
                    date_val = None

                pending_match = {
                    "season": 2024,  # You can parameterise this
                    "round": current_round,
                    "date": date_val,
                    "home_team": home_team,
                    "away_team": away_team,
                    "venue": venue,
                    "crowd": crowd_val,
                    "result": result,
                    "stats": []  # hold stat lines like "J. Viney 30"
                }

            else:
                # Not a match header — must be a stat line
                # e.g. "J. Viney 30" or "C. Oliver 30"
                if pending_match:
                    pending_match["stats"].append(line)

        # Flush last pending match
        if pending_match:
            rows.append(pending_match)

    # Convert to flat rows
    parsed_rows = []
    for r in rows:
        parsed_rows.append({
            "season": r["season"],
            "round": r["round"],
            "date": r["date"],
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "venue": r["venue"],
            "crowd": r["crowd"],
            "result": r["result"],
            "disposals/goals": "; ".join(r["stats"]) # stats combined for now
        })

    return parsed_rows


if __name__ == "__main__":
    parsed = parse_input_file(INPUT_FILE)
    df = pd.DataFrame(parsed)
    df["scraped_at"] = pd.Timestamp.now()
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(df)} matches to {OUTPUT_FILE}")
