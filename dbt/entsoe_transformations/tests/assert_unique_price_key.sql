SELECT
    bidding_zone,
    delivery_start_utc,
    COUNT(*) AS duplicate_count
FROM {{ ref('stg_entsoe_prices') }}
GROUP BY
    bidding_zone,
    delivery_start_utc
HAVING COUNT(*) > 1
