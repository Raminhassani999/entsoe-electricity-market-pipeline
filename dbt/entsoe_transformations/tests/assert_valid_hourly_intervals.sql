SELECT
    bidding_zone,
    hour_start_utc,
    intervals_available
FROM {{ ref('int_hourly_prices') }}
WHERE intervals_available < 1
   OR intervals_available > 4
