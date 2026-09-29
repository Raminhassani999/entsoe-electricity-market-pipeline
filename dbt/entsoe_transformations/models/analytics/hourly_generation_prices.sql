{{ config(materialized='view') }}

SELECT
    g.bidding_zone,
    g.hour_start_utc,
    g.psr_type,
    g.production_type,

    p.average_price_eur_mwh,
    p.minimum_price_eur_mwh,
    p.maximum_price_eur_mwh,

    g.average_generation_mw,
    g.minimum_generation_mw,
    g.maximum_generation_mw,

    g.intervals_available AS generation_intervals_available,
    p.intervals_available AS price_intervals_available

FROM {{ ref('int_hourly_generation') }} AS g

INNER JOIN {{ ref('int_hourly_prices') }} AS p
    ON g.bidding_zone = p.bidding_zone
    AND g.hour_start_utc = p.hour_start_utc