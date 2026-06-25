-- Bronze Layer: Squiggle Games
-- Reads from raw.squiggle_games (loaded by scripts/fetch_squiggle_games.py
-- from the Squiggle API) and types/cleans it into a match-results staging table.
-- Only completed games (complete = 100) are kept, since scores are final.

{{ config(
    materialized='table',
    tags=['bronze', 'match_data']
) }}

SELECT
    -- dbt metadata
    current_timestamp() AS _dbt_loaded_at,
    '_squiggle_api' AS _source_system,

    -- Identifiers
    CAST(game_id AS BIGINT) AS game_id,
    CAST(season AS INT) AS season,
    CAST(round AS INT) AS round_number,
    round_name AS round,

    -- Timing
    CAST(match_datetime AS TIMESTAMP) AS match_datetime,
    tz AS timezone,

    -- Teams (Squiggle names + numeric ids; mapped to project codes in silver)
    home_team,
    CAST(home_team_squiggle_id AS INT) AS home_team_squiggle_id,
    away_team,
    CAST(away_team_squiggle_id AS INT) AS away_team_squiggle_id,

    -- Scores
    CAST(home_score AS INT) AS home_score,
    CAST(home_goals AS INT) AS home_goals,
    CAST(home_behinds AS INT) AS home_behinds,
    CAST(away_score AS INT) AS away_score,
    CAST(away_goals AS INT) AS away_goals,
    CAST(away_behinds AS INT) AS away_behinds,

    venue,

    -- Derived fields
    CAST(home_score AS INT) - CAST(away_score AS INT) AS margin,
    CASE
        WHEN home_score > away_score THEN 'home_win'
        WHEN away_score > home_score THEN 'away_win'
        ELSE 'draw'
    END AS result,
    winner,
    CAST(is_final AS BOOLEAN) AS is_final,
    CAST(is_grand_final AS BOOLEAN) AS is_grand_final,

    -- Ingestion lineage
    CAST(_ingested_at AS TIMESTAMP) AS _ingested_at

FROM {{ source('raw', 'squiggle_games') }}

-- Only completed games have final scores
WHERE complete = 100
    AND match_datetime IS NOT NULL
    AND home_team IS NOT NULL
    AND away_team IS NOT NULL
