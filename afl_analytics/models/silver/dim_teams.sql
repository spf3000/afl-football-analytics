SELECT
    team_id,
    team_name,
    nick_name,
    mascot,
    primary_colour,
    secondary_colour,
    home_state,
    home_city,
    founded_year
FROM {{ ref('seed_teams') }}
