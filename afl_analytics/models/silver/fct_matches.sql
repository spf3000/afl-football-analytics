-- Silver Layer: Fact Matches
-- Joins match results with team and venue dimensions
-- Provides foreign keys for star schema querying

{{ config(
    materialized='table',
    tags=['silver', 'fact']
) }}

WITH match_results AS (
    SELECT * FROM {{ ref('stg_match_results') }}
),

teams AS (
    SELECT * FROM {{ ref('dim_teams') }}
),

venues AS (
    SELECT * FROM {{ ref('dim_venues') }}
),

-- Match venues using name, sponsored name, or aliases
venue_lookup AS (
    SELECT
        m.match_datetime,
        m.home_team,
        m.away_team,
        m.venue AS venue_raw,
        v.venue_id
    FROM match_results m
    LEFT JOIN venues v
        ON m.venue = v.venue_name
        OR m.venue = v.current_sponsored_name
        OR CONCAT(';', COALESCE(v.aliases, ''), ';') LIKE CONCAT('%;', m.venue, ';%')
)

SELECT
    -- Surrogate key (season + round + teams + datetime for uniqueness)
    {{ dbt_utils.generate_surrogate_key(['m.season', 'm.round', 'm.home_team', 'm.away_team', 'm.match_datetime']) }} AS match_id,

    -- Dimension foreign keys
    ht.team_id AS home_team_id,
    at.team_id AS away_team_id,
    vl.venue_id,

    -- Match details
    m.season,
    m.round,
    m.match_datetime,

    -- Scores and metrics
    m.home_score,
    m.away_score,
    m.margin,
    m.result,
    m.crowd AS attendance,

    -- Raw values for debugging/reference
    m.home_team AS home_team_name,
    m.away_team AS away_team_name,
    m.venue AS venue_name_raw,

    -- Metadata
    m._dbt_loaded_at,
    m._source_system

FROM match_results m

-- Join home team (match on team_name or team_id for cases like GWS)
LEFT JOIN teams ht
    ON m.home_team = ht.team_name
    OR m.home_team = ht.team_id

-- Join away team (match on team_name or team_id for cases like GWS)
LEFT JOIN teams at
    ON m.away_team = at.team_name
    OR m.away_team = at.team_id

-- Join venue (via lookup CTE to handle multiple match conditions)
LEFT JOIN venue_lookup vl
    ON m.match_datetime = vl.match_datetime
    AND m.home_team = vl.home_team
    AND m.away_team = vl.away_team
