WITH home AS (
    SELECT
        season,
        expected_win_prob AS p,
        actual_result AS y
    FROM {{ ref('elo_ratings') }}
    WHERE is_home
)

SELECT
    season,
    COUNT(*) AS games,
    ROUND(AVG(POWER(p - y, 2)), 4) AS brier,        -- 0.25 = coin flip; lower is better
    ROUND(AVG(-(y * LN(p) + (1 - y) * LN(1 - p))), 4) AS log_loss,     -- 1.693 = coin flip
    ROUND(AVG(CASE
        WHEN y = 0.5 THEN 0.5
        WHEN (p >= 0.5) = (y = 1) THEN 1.0
        ELSE 0.0
    END), 3) AS tip_accuracy
FROM home
GROUP BY season
ORDER BY season
