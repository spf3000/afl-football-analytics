SELECT
    team_id,
    CAST(squiggle_id AS INT) AS squiggle_id,
    team_name,
    nick_name,
    mascot,
    primary_colour,
    secondary_colour,
    home_state,
    home_city,
    founded_year
FROM {{ ref('seed_teams') }}
