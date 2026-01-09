SELECT
    venue_id,
    venue_name,
    current_sponsored_name,
    aliases,
    city,
    state,
    capacity,
    first_afl_use,
    current_tenants
FROM {{ ref('seed_venues') }}
