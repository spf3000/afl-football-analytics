import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("afl_attendance_2024.csv")
df.head()
print(df.shape)
print(df.info())
print(df.describe())

venue_summary = df.groupby("venue")["attendance"].agg(
    games="count",
    total="sum",
    average="mean"
)

venue_summary

sorted_venues = venue_summary.sort_values("average", ascending=False)
sorted_venues

sorted_venues["average"].plot(kind="barh", figsize=(10,6), title="Average Attendance by Venue")
plt.xlabel("Average Attendance")
plt.ylabel("Venue")
plt.tight_layout()
plt.show()

home_team_summary = df.groupby("home_team")["attendance"].agg(
    games = "count",
    total="sum",
    average="mean"
).sort_values("average", ascending=False)

home_team_summary["average"].plot(kind="barh", figsize=(10,6), title="Average Attendance by Home Team")
plt.xlabel("Average Attendance")
plt.ylabel("Home Team")
plt.tight_layout()
plt.show()