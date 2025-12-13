with open("afl_attendance_2024.csv", "r") as f:
    lines = f.readlines()
    data_set = []

for line in lines[1:]:
    fields = [field.strip() for field in line.split(',')]
    data_set.append({"year":fields[0],
                     "round":fields[1],
                     "home_team":fields[2],
                     "away_team":fields[3],
                     "venue":fields[4],
                     "attendance":int(fields[5])})
venue_stats = {}

for game in data_set:
    venue = game["venue"]
    attendance = game["attendance"]

    if venue not in venue_stats:
        venue_stats[venue] = {
            "games": 0,
            "total_attendance": 0
        }

    venue_stats[venue]["games"] += 1
    venue_stats[venue]["total_attendance"] += attendance

for venue in venue_stats:
    total = venue_stats[venue]["total_attendance"]
    games = venue_stats[venue]["games"]
    venue_stats[venue]["average_attendance"] = total / games

for venue, stats in venue_stats.items():
    print(f"{venue:<20} | {stats['games']:<5} | {stats['total_attendance']:<10} | {int(stats['average_attendance']):<10}")
