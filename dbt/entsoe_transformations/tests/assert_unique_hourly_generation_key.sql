SELECT
    bidding_zone,
    psr_type,
    hour_start_utc,
    COUNT(*) AS duplicate_count

FROM {{ ref('int_hourly_generation') }}

GROUP BY
    bidding_zone,
    psr_type,
    hour_start_utc

HAVING COUNT(*) > 1