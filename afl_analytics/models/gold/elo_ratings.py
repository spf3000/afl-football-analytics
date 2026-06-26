import pandas as pd
import numpy as np


def model(dbt, session):
    dbt.config(
        materialized="table",
        tags=["gold", "analytics"],
        schema="gold",
        # Run on Databricks serverless jobs compute: a SQL warehouse can't
        # execute PySpark Python models, and there's no interactive cluster.
        submission_method="serverless_cluster",
    )

    # --- Parameters ---
    STARTING_ELO = 1500.0
    K_FACTOR = 40
    HOME_ADVANTAGE = 45
    REGRESSION_FRACTION = 1 / 3

    # --- Load upstream models ---
    fct_matches = dbt.ref("fct_matches").toPandas()
    dim_teams = dbt.ref("dim_teams").toPandas()

    # Sort matches chronologically with match_id as tiebreaker
    fct_matches = fct_matches.sort_values(
        ["match_datetime", "match_id"]
    ).reset_index(drop=True)

    # --- Initialise ratings ---
    team_ids = dim_teams["team_id"].tolist()
    ratings = {tid: STARTING_ELO for tid in team_ids}

    # --- Helper functions ---
    def expected_win_prob(rating, opponent_rating, home_adv):
        return 1.0 / (1.0 + 10 ** (-(rating - opponent_rating + home_adv) / 400))

    def margin_multiplier(margin):
        return np.log(abs(margin) + 1) * 2.2

    # --- Process matches ---
    records = []
    team_match_counter = {tid: 0 for tid in team_ids}
    season_match_counter = {tid: 0 for tid in team_ids}
    prev_season = None

    for _, match in fct_matches.iterrows():
        season = int(match["season"])
        home_id = match["home_team_id"]
        away_id = match["away_team_id"]
        match_id = match["match_id"]
        margin = match["margin"]

        # Apply season regression when season changes
        if prev_season is not None and season != prev_season:
            for tid in ratings:
                ratings[tid] = ratings[tid] + REGRESSION_FRACTION * (
                    STARTING_ELO - ratings[tid]
                )
            season_match_counter = {tid: 0 for tid in team_ids}
        prev_season = season

        home_elo = ratings.get(home_id, STARTING_ELO)
        away_elo = ratings.get(away_id, STARTING_ELO)

        # Expected win probabilities
        home_exp = expected_win_prob(home_elo, away_elo, HOME_ADVANTAGE)
        away_exp = 1.0 - home_exp

        # Actual results
        if margin > 0:
            home_actual = 1.0
            away_actual = 0.0
        elif margin < 0:
            home_actual = 0.0
            away_actual = 1.0
        else:
            home_actual = 0.5
            away_actual = 0.5

        # Margin-adjusted elo change
        mov = margin_multiplier(margin)
        home_change = K_FACTOR * mov * (home_actual - home_exp)
        away_change = K_FACTOR * mov * (away_actual - away_exp)

        # Update counters
        team_match_counter[home_id] = team_match_counter.get(home_id, 0) + 1
        team_match_counter[away_id] = team_match_counter.get(away_id, 0) + 1
        season_match_counter[home_id] = season_match_counter.get(home_id, 0) + 1
        season_match_counter[away_id] = season_match_counter.get(away_id, 0) + 1

        # Home team record
        records.append(
            {
                "match_id": match_id,
                "team_id": home_id,
                "team_name": match["home_team_name"],
                "opponent_team_id": away_id,
                "opponent_team_name": match["away_team_name"],
                "season": season,
                "round": match["round"],
                "match_datetime": match["match_datetime"],
                "is_home": True,
                "pre_match_elo": round(home_elo, 2),
                "opponent_pre_match_elo": round(away_elo, 2),
                "home_advantage_applied": HOME_ADVANTAGE,
                "expected_win_prob": round(home_exp, 4),
                "actual_result": home_actual,
                "elo_change": round(home_change, 2),
                "post_match_elo": round(home_elo + home_change, 2),
                "team_match_number": team_match_counter[home_id],
                "season_match_number": season_match_counter[home_id],
            }
        )

        # Away team record
        records.append(
            {
                "match_id": match_id,
                "team_id": away_id,
                "team_name": match["away_team_name"],
                "opponent_team_id": home_id,
                "opponent_team_name": match["home_team_name"],
                "season": season,
                "round": match["round"],
                "match_datetime": match["match_datetime"],
                "is_home": False,
                "pre_match_elo": round(away_elo, 2),
                "opponent_pre_match_elo": round(home_elo, 2),
                "home_advantage_applied": 0,
                "expected_win_prob": round(away_exp, 4),
                "actual_result": away_actual,
                "elo_change": round(away_change, 2),
                "post_match_elo": round(away_elo + away_change, 2),
                "team_match_number": team_match_counter[away_id],
                "season_match_number": season_match_counter[away_id],
            }
        )

        # Update ratings
        ratings[home_id] = home_elo + home_change
        ratings[away_id] = away_elo + away_change

    # --- Build output DataFrame ---
    df = pd.DataFrame(records)

    # Add surrogate key
    df["elo_record_id"] = df["match_id"].astype(str) + "_" + df["team_id"].astype(str)

    # Add metadata
    df["_dbt_loaded_at"] = pd.Timestamp.now()

    # Column ordering
    df = df[
        [
            "elo_record_id",
            "match_id",
            "team_id",
            "team_name",
            "opponent_team_id",
            "opponent_team_name",
            "season",
            "round",
            "match_datetime",
            "is_home",
            "pre_match_elo",
            "opponent_pre_match_elo",
            "home_advantage_applied",
            "expected_win_prob",
            "actual_result",
            "elo_change",
            "post_match_elo",
            "team_match_number",
            "season_match_number",
            "_dbt_loaded_at",
        ]
    ]

    return session.createDataFrame(df)
