SELECT
    bidding_zone,
    psr_type,
    delivery_start_utc,
    COUNT(*) AS duplicate_count

FROM {{ ref('stg_entsoe_generation') }}

GROUP BY
    bidding_zone,
    psr_type,
    delivery_start_utc

HAVING COUNT(*) > 1