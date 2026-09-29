SELECT
    g.bidding_zone,
    g.hour_start_utc,
    g.psr_type

FROM {{ ref('int_hourly_generation') }} AS g

LEFT JOIN {{ ref('int_hourly_prices') }} AS p
    ON g.bidding_zone = p.bidding_zone
    AND g.hour_start_utc = p.hour_start_utc

WHERE p.bidding_zone IS NULL