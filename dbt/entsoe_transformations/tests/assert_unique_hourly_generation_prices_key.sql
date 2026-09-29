SELECT
    bidding_zone,
    hour_start_utc,
    psr_type,
    COUNT(*) AS duplicate_count

FROM {{ ref('hourly_generation_prices') }}

GROUP BY
    bidding_zone,
    hour_start_utc,
    psr_type

HAVING COUNT(*) > 1