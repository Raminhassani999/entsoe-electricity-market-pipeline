SELECT
    bidding_zone,
    hour_start_utc,
    COUNT(*) AS duplicate_count
FROM {{ ref('int_hourly_prices') }}
GROUP BY
    bidding_zone,
    hour_start_utc
HAVING COUNT(*) > 1
