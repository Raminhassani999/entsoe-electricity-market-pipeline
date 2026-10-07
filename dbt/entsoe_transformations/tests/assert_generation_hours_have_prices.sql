{{ config(severity='warn') }}

WITH generation_hours AS (
    SELECT DISTINCT
        bidding_zone,
        hour_start_utc
    FROM {{ ref('int_hourly_generation') }}
),

price_hours AS (
    SELECT DISTINCT
        bidding_zone,
        hour_start_utc
    FROM {{ ref('int_hourly_prices') }}
)

SELECT
    g.bidding_zone,
    g.hour_start_utc
FROM generation_hours AS g
LEFT JOIN price_hours AS p
    ON g.bidding_zone = p.bidding_zone
    AND g.hour_start_utc = p.hour_start_utc
WHERE p.hour_start_utc IS NULL