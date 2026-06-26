-- Silver Layer: Fact Matches
-- Match results sourced from the Squiggle API (stg_squiggle_games) as the spine,
-- with team/venue foreign keys and crowd/attendance joined in from the legacy
-- .txt path (stg_match_results), which Squiggle does not provide.
-- Provides foreign keys for star schema querying.

{{ config(
    materialized='table',
    tags=['silver', 'fact']
) }}

WITH games AS (
    SELECT * FROM {{ ref('stg_squiggle_games') }}
),

teams AS (
    SELECT * FROM {{ ref('dim_teams') }}
),

venues AS (
    SELECT * FROM {{ ref('dim_venues') }}
),

-- Resolve each game's venue to a venue_id via canonical name, sponsored name, or aliases
venue_lookup AS (
    SELECT
        g.game_id,
        v.venue_id
    FROM games g
    LEFT JOIN venues v
        ON g.venue = v.venue_name
        OR g.venue = v.current_sponsored_name
        OR CONCAT(';', COALESCE(v.aliases, ''), ';') LIKE CONCAT('%;', g.venue, ';%')
),

-- Attendance from the legacy .txt path, with teams mapped to dim_teams ids.
-- Joined back to the Squiggle spine on season + team ids + match date.
txt_attendance AS (
    SELECT
        m.season,
        COALESCE(ht.team_id, m.home_team) AS home_team_id,
        COALESCE(at.team_id, m.away_team) AS away_team_id,
        DATE(m.match_datetime) AS match_date,
        m.crowd AS attendance
    FROM {{ ref('stg_match_results') }} m
    LEFT JOIN teams ht ON m.home_team = ht.team_name OR m.home_team = ht.team_id
    LEFT JOIN teams at ON m.away_team = at.team_name OR m.away_team = at.team_id
)

SELECT
    -- Surrogate key derived from the stable Squiggle game id
    {{ dbt_utils.generate_surrogate_key(['g.game_id']) }} AS match_id,
    g.game_id,

    -- Dimension foreign keys (teams mapped by stable Squiggle id)
    ht.team_id AS home_team_id,
    at.team_id AS away_team_id,
    vl.venue_id,

    -- Match details
    g.season,
    g.round,
    g.round_number,
    g.match_datetime,
    g.is_final,
    g.is_grand_final,

    -- Scores and metrics
    g.home_score,
    g.away_score,
    g.margin,
    g.result,
    ta.attendance,

    -- Raw values for debugging/reference
    g.home_team AS home_team_name,
    g.away_team AS away_team_name,
    g.venue AS venue_name_raw,

    -- Metadata
    g._dbt_loaded_at,
    g._source_system

FROM games g

-- Map teams via the stable Squiggle numeric id
LEFT JOIN teams ht ON g.home_team_squiggle_id = ht.squiggle_id
LEFT JOIN teams at ON g.away_team_squiggle_id = at.squiggle_id

-- Venue id via lookup CTE
LEFT JOIN venue_lookup vl ON g.game_id = vl.game_id

-- Attendance via the legacy .txt path
LEFT JOIN txt_attendance ta
    ON g.season = ta.season
    AND ht.team_id = ta.home_team_id
    AND at.team_id = ta.away_team_id
    AND DATE(g.match_datetime) = ta.match_date
