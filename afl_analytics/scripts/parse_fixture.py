"""Parse the 2026 AFL fixture text file into a seed CSV."""
import csv
import re

TEAM_ID_MAP = {
    "Adelaide Crows": "ADE",
    "Brisbane Lions": "BRI",
    "Carlton": "CAR",
    "Collingwood": "COL",
    "Essendon": "ESS",
    "Fremantle": "FRE",
    "Geelong Cats": "GEE",
    "GWS Giants": "GWS",
    "Gold Coast Suns": "GCS",
    "Hawthorn": "HAW",
    "Melbourne": "MEL",
    "North Melbourne": "NM",
    "Port Adelaide": "PA",
    "Richmond": "RIC",
    "St Kilda": "STK",
    "Sydney Swans": "SYD",
    "Western Bulldogs": "WB",
    "West Coast Eagles": "WCE",
}

input_path = "data/fixture_2026.txt"
output_path = "afl_analytics/seeds/seed_fixture_2026.csv"

matches = []
current_round = None

with open(input_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # Detect round headers
        if re.match(r"^(Opening Round|Round \d+)", line):
            current_round = re.match(r"^(Opening Round|Round \d+)", line).group(1)
            continue

        # Skip header/date lines
        if line.startswith("Fixture") or re.match(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", line):
            continue

        # Parse match lines: "Home vs. Away\tVenue\t..."
        if " vs. " in line:
            parts = line.split("\t")
            teams_str = parts[0].strip()
            venue = parts[1].strip() if len(parts) > 1 else ""

            home_name, away_name = teams_str.split(" vs. ")
            home_name = home_name.strip()
            away_name = away_name.strip()

            home_id = TEAM_ID_MAP.get(home_name)
            away_id = TEAM_ID_MAP.get(away_name)

            if not home_id:
                print(f"WARNING: Unknown team '{home_name}'")
            if not away_id:
                print(f"WARNING: Unknown team '{away_name}'")

            matches.append({
                "round": current_round,
                "home_team_id": home_id,
                "home_team_name": home_name,
                "away_team_id": away_id,
                "away_team_name": away_name,
                "venue": venue,
            })

with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["round", "home_team_id", "home_team_name", "away_team_id", "away_team_name", "venue"])
    writer.writeheader()
    writer.writerows(matches)

print(f"Wrote {len(matches)} matches to {output_path}")
