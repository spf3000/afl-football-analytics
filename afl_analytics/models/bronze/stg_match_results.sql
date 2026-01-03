-- Bronze Layer: Match Results
-- Reads from Python-parsed table (raw.match_results_parsed)
-- Adds dbt metadata and light transformations

{{ config(
    materialized='table',
    tags=['bronze', 'match_data']
) }}

SELECT
    -- dbt metadata
    current_timestamp() AS _dbt_loaded_at,
    '_python_parser' AS _source_system,

    -- From parsed table (Python script already cleaned)
    season,
    round,
    match_datetime,
    home_team,
    away_team,
    venue,
    crowd,
    home_score,
    away_score,

    -- Derived fields
    home_score - away_score AS margin,
    CASE
        WHEN home_score > away_score THEN 'home_win'
        WHEN away_score > home_score THEN 'away_win'
        ELSE 'draw'
    END AS result,

    -- Raw fields for reference
    result_raw,
    disposals_goals,
    scraped_at AS _python_scraped_at

FROM {{ source('raw', 'match_results_parsed') }}

-- Basic quality filters
WHERE
    match_datetime IS NOT NULL
    AND home_team IS NOT NULL
    AND away_team IS NOT NULL
    AND home_score IS NOT NULL
    AND away_score IS NOT NULL
