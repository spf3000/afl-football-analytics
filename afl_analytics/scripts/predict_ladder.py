"""
AFL 2026 Ladder Prediction via Monte Carlo Simulation.

Uses latest Elo ratings from the gold.elo_ratings model and the 2026 fixture
to simulate the season 10,000 times. Outputs predicted ladder rankings.

Run from repo root:
    cd afl_analytics && uv run python scripts/predict_ladder.py
"""
import os
import csv
import numpy as np
from databricks import sql as dbsql

NUM_SIMULATIONS = 10_000
HOME_ADVANTAGE = 45.0
SEED = 42

def get_connection():
    """Connect to Databricks SQL warehouse using dbt profile settings."""
    import yaml

    with open(os.path.expanduser("~/.dbt/profiles.yml")) as f:
        profiles = yaml.safe_load(f)

    dev = profiles["afl_analytics"]["outputs"]["dev"]
    return dbsql.connect(
        server_hostname=dev["host"],
        http_path=dev["http_path"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def fetch_latest_elo(conn):
    """Get each team's most recent Elo rating."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team_id, team_name, post_match_elo
        FROM afl_analytics_dev.default_gold.elo_ratings
        WHERE (team_id, team_match_number) IN (
            SELECT team_id, MAX(team_match_number)
            FROM afl_analytics_dev.default_gold.elo_ratings
            GROUP BY team_id
        )
        ORDER BY post_match_elo DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    return {row[0]: {"name": row[1], "elo": float(row[2])} for row in rows}


def load_fixture():
    """Load the 2026 fixture from the seed CSV."""
    matches = []
    with open("seeds/seed_fixture_2026.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append(row)
    return matches


def expected_win_prob(home_elo, away_elo):
    """Home team's expected win probability."""
    return 1.0 / (1.0 + 10.0 ** (-(home_elo - away_elo + HOME_ADVANTAGE) / 400.0))


def simulate_season(fixture, team_elos, rng):
    """Simulate one full season, return wins per team."""
    wins = {team_id: 0.0 for team_id in team_elos}

    for match in fixture:
        home_id = match["home_team_id"]
        away_id = match["away_team_id"]

        home_elo = team_elos[home_id]
        away_elo = team_elos[away_id]

        p_home = expected_win_prob(home_elo, away_elo)

        if rng.random() < p_home:
            wins[home_id] += 1.0
        else:
            wins[away_id] += 1.0

    return wins


def plot_heatmap(ladder, team_data, position_counts):
    """Generate a heatmap showing probability of each team finishing in each position."""
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import seaborn as sns

    n_teams = len(ladder)
    team_names = [team_data[tid]["name"] for tid in ladder]

    # Build probability matrix (teams x positions), as percentages
    prob_matrix = np.zeros((n_teams, n_teams))
    for i, team_id in enumerate(ladder):
        prob_matrix[i] = position_counts[team_id] / position_counts[team_id].sum() * 100

    fig, ax = plt.subplots(figsize=(14, 9))

    # Custom colourmap: white (0%) -> dark teal (high%)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "afl", ["#ffffff", "#d4edda", "#28a745", "#155724"], N=256
    )

    sns.heatmap(
        prob_matrix,
        ax=ax,
        cmap=cmap,
        vmin=0,
        vmax=prob_matrix.max(),
        annot=True,
        fmt=".0f",
        annot_kws={"size": 7.5},
        linewidths=0.5,
        linecolor="#e0e0e0",
        cbar_kws={"label": "Probability (%)", "shrink": 0.8},
        xticklabels=[str(i) for i in range(1, n_teams + 1)],
        yticklabels=team_names,
    )

    # Hide annotations where probability is 0
    for text in ax.texts:
        if text.get_text() == "0":
            text.set_text("")

    ax.set_xlabel("Predicted Ladder Position", fontsize=12, labelpad=10)
    ax.set_ylabel("")
    ax.set_title(
        "2026 AFL Ladder Prediction  —  Monte Carlo Simulation (10,000 seasons)",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.tick_params(axis="y", rotation=0)
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")

    plt.tight_layout()
    output_path = "scripts/predicted_ladder_2026.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\n  Heatmap saved to {output_path}")


def main():
    print("Connecting to Databricks...")
    conn = get_connection()

    print("Fetching latest Elo ratings...")
    team_data = fetch_latest_elo(conn)
    conn.close()

    print("\nCurrent Elo Ratings (end of 2025 season + regression):")
    print("-" * 45)
    for team_id, data in sorted(team_data.items(), key=lambda x: -x[1]["elo"]):
        print(f"  {data['name']:<22} {data['elo']:>7.1f}")

    print(f"\nLoading 2026 fixture ({len(load_fixture())} matches)...")
    fixture = load_fixture()

    # Extract just the elo values for simulation
    team_elos = {tid: data["elo"] for tid, data in team_data.items()}

    print(f"Running {NUM_SIMULATIONS:,} simulations...")
    rng = np.random.default_rng(SEED)

    # Accumulate wins across simulations
    total_wins = {team_id: 0.0 for team_id in team_elos}
    # Track finishing position counts for each team
    position_counts = {team_id: np.zeros(18) for team_id in team_elos}

    for i in range(NUM_SIMULATIONS):
        wins = simulate_season(fixture, team_elos, rng)
        for team_id, w in wins.items():
            total_wins[team_id] += w

        # Rank teams by wins (random tiebreak)
        ranked = sorted(wins.keys(), key=lambda t: (-wins[t], rng.random()))
        for pos, team_id in enumerate(ranked):
            position_counts[team_id][pos] += 1

    # Compute average wins
    avg_wins = {tid: total_wins[tid] / NUM_SIMULATIONS for tid in team_elos}

    # Sort by average wins descending
    ladder = sorted(avg_wins.keys(), key=lambda t: -avg_wins[t])

    print("\n" + "=" * 72)
    print("  2026 AFL PREDICTED LADDER")
    print("=" * 72)
    print(f"  {'#':<4} {'Team':<22} {'Avg Wins':>9} {'Top 4':>7} {'Top 10':>7} {'Wooden':>7}")
    print("-" * 72)

    for pos, team_id in enumerate(ladder):
        name = team_data[team_id]["name"]
        aw = avg_wins[team_id]
        top4_pct = sum(position_counts[team_id][:4]) / NUM_SIMULATIONS * 100
        top10_pct = sum(position_counts[team_id][:10]) / NUM_SIMULATIONS * 100
        spoon_pct = position_counts[team_id][17] / NUM_SIMULATIONS * 100

        print(f"  {pos+1:<4} {name:<22} {aw:>8.1f}  {top4_pct:>6.1f}% {top10_pct:>6.1f}% {spoon_pct:>6.1f}%")

    print("=" * 72)
    print(f"  Based on {NUM_SIMULATIONS:,} simulations using end-of-2025 Elo ratings")
    print(f"  Home advantage: {HOME_ADVANTAGE} Elo points")

    # Generate heatmap
    plot_heatmap(ladder, team_data, position_counts)

    # Write CSV output
    output_path = "scripts/predicted_ladder_2026.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["predicted_rank", "team_id", "team_name", "avg_wins", "top_4_pct", "top_10_pct", "wooden_spoon_pct"])
        for pos, team_id in enumerate(ladder):
            name = team_data[team_id]["name"]
            top4 = round(sum(position_counts[team_id][:4]) / NUM_SIMULATIONS * 100, 1)
            top10 = round(sum(position_counts[team_id][:10]) / NUM_SIMULATIONS * 100, 1)
            spoon = round(position_counts[team_id][17] / NUM_SIMULATIONS * 100, 1)
            writer.writerow([pos + 1, team_id, name, round(avg_wins[team_id], 1), top4, top10, spoon])

    print(f"\n  Results saved to {output_path}")


if __name__ == "__main__":
    main()
