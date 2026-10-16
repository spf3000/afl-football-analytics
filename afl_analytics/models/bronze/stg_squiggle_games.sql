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
    '_squiggle_api' AS _source_system,
    cast(game_id AS BIGINT) AS game_id,

    -- Identifiers
    cast(season AS INT) AS season,
    cast(round AS INT) AS round_number,
    round_name AS round,
    cast(match_datetime AS TIMESTAMP) AS match_datetime,

    -- Timing
    tz AS timezone,
    home_team,

    -- Teams (Squiggle names + numeric ids; mapped to project codes in silver)
    cast(home_team_squiggle_id AS INT) AS home_team_squiggle_id,
    away_team,
    cast(away_team_squiggle_id AS INT) AS away_team_squiggle_id,
    cast(home_score AS INT) AS home_score,

    -- Scores
    cast(home_goals AS INT) AS home_goals,
    cast(home_behinds AS INT) AS home_behinds,
    cast(away_score AS INT) AS away_score,
    cast(away_goals AS INT) AS away_goals,
    cast(away_behinds AS INT) AS away_behinds,
    venue,

    winner,

    -- Derived fields
    cast(is_final AS BOOLEAN) AS is_final,
    cast(is_grand_final AS BOOLEAN) AS is_grand_final,
    cast(_ingested_at AS TIMESTAMP) AS _ingested_at,
    current_timestamp() AS _dbt_loaded_at,
    cast(home_score AS INT) - cast(away_score AS INT) AS margin,

    -- Ingestion lineage
    CASE
        WHEN home_score > away_score THEN 'home_win'
        WHEN away_score > home_score THEN 'away_win'
        ELSE 'draw'
    END AS result

FROM {{ source('raw', 'squiggle_games') }}

-- Only completed games have final scores
WHERE
    complete = 100
    AND match_datetime IS NOT NULL
    AND home_team IS NOT NULL
    AND away_team IS NOT NULL
