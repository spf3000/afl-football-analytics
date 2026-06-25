-- Gold Layer: Elo Ratings
-- Computes team Elo ratings chronologically across all AFL matches.
-- One row per team per match (2 rows per game).
-- Uses recursive CTE processing round-by-round with a MAP of team ratings.
-- MAP serialized to JSON string to work around Spark recursive CTE type limitation.
--
-- Parameters: starting_elo=1500, K=40, home_advantage=45 Elo pts,
--   margin_multiplier=ln(|margin|+1)*2.2, season_regression=1/3 toward 1500

{{ config(
    materialized='table',
    tags=['gold', 'analytics']
) }}

WITH RECURSIVE

-- Initial ratings map: all teams start at 1500
initial_ratings AS (
    SELECT map_from_arrays(
        collect_list(team_id),
        collect_list(CAST(1500.0 AS DOUBLE))
    ) AS ratings
    FROM {{ ref('dim_teams') }}
),

-- Assign sequential round numbers across all seasons
round_info AS (
    SELECT
        season,
        `round`,
        round_start_dt,
        DENSE_RANK() OVER (ORDER BY round_start_dt) AS round_seq
    FROM (
        SELECT
            season,
            `round`,
            MIN(match_datetime) AS round_start_dt
        FROM {{ ref('fct_matches') }}
        GROUP BY season, `round`
    )
),

-- Attach round sequence to each match
numbered_matches AS (
    SELECT m.*, ri.round_seq
    FROM {{ ref('fct_matches') }} m
    JOIN round_info ri ON m.season = ri.season AND m.`round` = ri.`round`
),

-- Collect each round's matches into an array of structs for aggregate processing
round_match_arrays AS (
    SELECT
        ri.round_seq,
        ri.season,
        collect_list(
            named_struct(
                'match_id', nm.match_id,
                'home_team_id', nm.home_team_id,
                'away_team_id', nm.away_team_id,
                'margin', CAST(nm.margin AS DOUBLE)
            )
        ) AS match_list
    FROM numbered_matches nm
    JOIN round_info ri ON nm.round_seq = ri.round_seq
    GROUP BY ri.round_seq, ri.season
),

-- Recursive Elo: process one round at a time, ratings stored as JSON string
elo_state MAX RECURSION LEVEL 500 AS (
    -- Anchor: before any matches, all teams at 1500
    SELECT
        CAST(0 AS BIGINT) AS round_seq,
        CAST(NULL AS BIGINT) AS season,
        to_json(ratings) AS ratings_json
    FROM initial_ratings

    UNION ALL

    -- Recursive: compute updated ratings for the next round
    SELECT
        rma.round_seq,
        rma.season,
        to_json(
            aggregate(
                rma.match_list,
                -- Apply season regression if entering a new season
                CASE
                    WHEN e.season IS NOT NULL AND rma.season != e.season
                    THEN transform_values(
                        from_json(e.ratings_json, 'MAP<STRING,DOUBLE>'),
                        (k, v) -> v + (1500.0 - v) / 3.0
                    )
                    ELSE from_json(e.ratings_json, 'MAP<STRING,DOUBLE>')
                END,
                -- Process each match in the round (update in place to avoid duplicate keys)
                (acc, m) -> transform_values(acc, (k, v) ->
                    CASE
                        WHEN k = m.home_team_id THEN
                            v + 40.0 * ln(abs(m.margin) + 1.0) * 2.2 * (
                                CASE WHEN m.margin > 0 THEN 1.0
                                     WHEN m.margin < 0 THEN 0.0
                                     ELSE 0.5 END
                                - 1.0 / (1.0 + pow(10.0,
                                    -(acc[m.home_team_id] - acc[m.away_team_id] + 45.0) / 400.0))
                            )
                        WHEN k = m.away_team_id THEN
                            v + 40.0 * ln(abs(m.margin) + 1.0) * 2.2 * (
                                CASE WHEN m.margin < 0 THEN 1.0
                                     WHEN m.margin > 0 THEN 0.0
                                     ELSE 0.5 END
                                - 1.0
                                + 1.0 / (1.0 + pow(10.0,
                                    -(acc[m.home_team_id] - acc[m.away_team_id] + 45.0) / 400.0))
                            )
                        ELSE v
                    END
                )
            )
        ) AS ratings_json
    FROM elo_state e
    JOIN round_match_arrays rma ON rma.round_seq = e.round_seq + 1
),

-- Extract pre-round and post-round ratings for each round (deserialize from JSON)
round_ratings AS (
    SELECT
        curr.round_seq,
        curr.season,
        -- Pre-round ratings = previous round's post-ratings + regression if new season
        CASE
            WHEN prev.season IS NOT NULL AND curr.season != prev.season
            THEN transform_values(
                from_json(prev.ratings_json, 'MAP<STRING,DOUBLE>'),
                (k, v) -> v + (1500.0 - v) / 3.0
            )
            ELSE from_json(prev.ratings_json, 'MAP<STRING,DOUBLE>')
        END AS pre_ratings,
        from_json(curr.ratings_json, 'MAP<STRING,DOUBLE>') AS post_ratings
    FROM elo_state curr
    JOIN elo_state prev ON prev.round_seq = curr.round_seq - 1
    WHERE curr.round_seq > 0
),

-- Compute per-match Elo details
match_elo AS (
    SELECT
        nm.match_id,
        nm.home_team_id,
        nm.away_team_id,
        nm.home_team_name,
        nm.away_team_name,
        nm.season,
        nm.`round`,
        nm.match_datetime,
        nm.margin,
        ROUND(rr.pre_ratings[nm.home_team_id], 2) AS home_pre_elo,
        ROUND(rr.pre_ratings[nm.away_team_id], 2) AS away_pre_elo,
        ROUND(rr.post_ratings[nm.home_team_id], 2) AS home_post_elo,
        ROUND(rr.post_ratings[nm.away_team_id], 2) AS away_post_elo
    FROM numbered_matches nm
    JOIN round_ratings rr ON rr.round_seq = nm.round_seq
),

-- Home team perspective
home_records AS (
    SELECT
        match_id,
        home_team_id AS team_id,
        home_team_name AS team_name,
        away_team_id AS opponent_team_id,
        away_team_name AS opponent_team_name,
        season,
        `round`,
        match_datetime,
        TRUE AS is_home,
        home_pre_elo AS pre_match_elo,
        away_pre_elo AS opponent_pre_match_elo,
        45 AS home_advantage_applied,
        ROUND(1.0 / (1.0 + pow(10.0,
            -(home_pre_elo - away_pre_elo + 45.0) / 400.0)), 4) AS expected_win_prob,
        CASE WHEN margin > 0 THEN 1.0
             WHEN margin < 0 THEN 0.0
             ELSE 0.5 END AS actual_result,
        ROUND(home_post_elo - home_pre_elo, 2) AS elo_change,
        home_post_elo AS post_match_elo
    FROM match_elo
),

-- Away team perspective
away_records AS (
    SELECT
        match_id,
        away_team_id AS team_id,
        away_team_name AS team_name,
        home_team_id AS opponent_team_id,
        home_team_name AS opponent_team_name,
        season,
        `round`,
        match_datetime,
        FALSE AS is_home,
        away_pre_elo AS pre_match_elo,
        home_pre_elo AS opponent_pre_match_elo,
        0 AS home_advantage_applied,
        ROUND(1.0 - 1.0 / (1.0 + pow(10.0,
            -(home_pre_elo - away_pre_elo + 45.0) / 400.0)), 4) AS expected_win_prob,
        CASE WHEN margin < 0 THEN 1.0
             WHEN margin > 0 THEN 0.0
             ELSE 0.5 END AS actual_result,
        ROUND(away_post_elo - away_pre_elo, 2) AS elo_change,
        away_post_elo AS post_match_elo
    FROM match_elo
),

-- Combine home and away records
combined AS (
    SELECT * FROM home_records
    UNION ALL
    SELECT * FROM away_records
)

-- Final output with surrogate key and running counters
SELECT
    {{ dbt_utils.generate_surrogate_key(['match_id', 'team_id']) }} AS elo_record_id,
    match_id,
    team_id,
    team_name,
    opponent_team_id,
    opponent_team_name,
    season,
    `round`,
    match_datetime,
    is_home,
    pre_match_elo,
    opponent_pre_match_elo,
    home_advantage_applied,
    expected_win_prob,
    actual_result,
    elo_change,
    post_match_elo,
    ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY match_datetime, match_id) AS team_match_number,
    ROW_NUMBER() OVER (PARTITION BY team_id, season ORDER BY match_datetime, match_id) AS season_match_number,
    CURRENT_TIMESTAMP() AS _dbt_loaded_at
FROM combined
