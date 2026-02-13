-- Gold Layer: Crowd Analysis
-- Match-level enriched table for attendance analytics
-- Includes benchmark averages for deviation calculations

{{ config(
    materialized='table',
    tags=['gold', 'crowd_analytics']
) }}

WITH matches AS (
    SELECT * FROM {{ ref('fct_matches') }}
),

venues AS (
    SELECT * FROM {{ ref('dim_venues') }}
),

teams AS (
    SELECT * FROM {{ ref('dim_teams') }}
),

-- Calculate each team's average home attendance per season
-- (used for both home_team_season_avg and away_team_home_season_avg)
team_home_season_avg AS (
    SELECT
        home_team_id AS team_id,
        season,
        AVG(attendance) AS home_season_avg
    FROM matches
    WHERE attendance IS NOT NULL
    GROUP BY home_team_id, season
),

-- Calculate each team's average attendance at each venue per season
team_venue_season_avg AS (
    SELECT
        home_team_id AS team_id,
        venue_id,
        season,
        AVG(attendance) AS venue_season_avg
    FROM matches
    WHERE attendance IS NOT NULL
    GROUP BY home_team_id, venue_id, season
)

SELECT
    -- Base match identifiers
    m.match_id,
    m.season,
    m.round,
    m.match_datetime,

    -- Team foreign keys and names
    m.home_team_id,
    m.away_team_id,
    m.home_team_name,
    m.away_team_name,
    ht.team_name AS home_team_full_name,
    at.team_name AS away_team_full_name,

    -- Venue foreign key and details
    m.venue_id,
    m.venue_name_raw,
    v.venue_name,
    v.city AS venue_city,
    v.state AS venue_state,
    v.capacity AS venue_capacity,

    -- Match results
    m.home_score,
    m.away_score,
    m.margin,
    m.result,

    -- Attendance
    m.attendance,

    -- Calculated: Venue utilization
    CASE
        WHEN v.capacity IS NOT NULL AND v.capacity > 0
        THEN ROUND(m.attendance * 100.0 / v.capacity, 1)
        ELSE NULL
    END AS utilization_pct,

    -- Calculated: Finals flag
    CASE
        WHEN m.round LIKE '%Final%' THEN TRUE
        ELSE FALSE
    END AS is_finals,

    -- Calculated: Round number for ordering
    CASE
        WHEN m.round LIKE 'Round %' THEN TRY_CAST(REGEXP_EXTRACT(m.round, 'Round (\\d+)', 1) AS INT)
        WHEN m.round LIKE '%Qualifying Final%' THEN 25
        WHEN m.round LIKE '%Elimination Final%' THEN 25
        WHEN m.round LIKE '%Semi Final%' THEN 26
        WHEN m.round LIKE '%Preliminary Final%' THEN 27
        WHEN m.round LIKE '%Grand Final%' THEN 28
        ELSE NULL
    END AS season_round_num,

    -- Calculated: Team's match number in season (for time series)
    ROW_NUMBER() OVER (
        PARTITION BY m.home_team_id, m.season
        ORDER BY m.match_datetime
    ) AS home_team_season_match_num,

    ROW_NUMBER() OVER (
        PARTITION BY m.away_team_id, m.season
        ORDER BY m.match_datetime
    ) AS away_team_season_match_num,

    -- Benchmark: Home team's average attendance at their home games this season
    ROUND(hts.home_season_avg, 0) AS home_team_season_avg,

    -- Benchmark: Home team's average at THIS venue this season
    ROUND(htv.venue_season_avg, 0) AS home_team_venue_season_avg,

    -- Benchmark: Away team's average when THEY host (for comparison)
    ROUND(ats.home_season_avg, 0) AS away_team_home_season_avg,

    -- Metadata
    m._dbt_loaded_at,
    m._source_system

FROM matches m

-- Join venue details
LEFT JOIN venues v
    ON m.venue_id = v.venue_id

-- Join home team details
LEFT JOIN teams ht
    ON m.home_team_id = ht.team_id

-- Join away team details
LEFT JOIN teams at
    ON m.away_team_id = at.team_id

-- Join home team's season average
LEFT JOIN team_home_season_avg hts
    ON m.home_team_id = hts.team_id
    AND m.season = hts.season

-- Join home team's venue-specific average
LEFT JOIN team_venue_season_avg htv
    ON m.home_team_id = htv.team_id
    AND m.venue_id = htv.venue_id
    AND m.season = htv.season

-- Join away team's home season average (what they draw when hosting)
LEFT JOIN team_home_season_avg ats
    ON m.away_team_id = ats.team_id
    AND m.season = ats.season
