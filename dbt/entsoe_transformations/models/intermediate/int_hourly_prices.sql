{{ config(materialized='view') }}

SELECT
    bidding_zone,

    TIMESTAMP_TRUNC(
        delivery_start_utc,
        HOUR
    ) AS hour_start_utc,

    AVG(price_eur_mwh) AS average_price_eur_mwh,
    MIN(price_eur_mwh) AS minimum_price_eur_mwh,
    MAX(price_eur_mwh) AS maximum_price_eur_mwh,

    COUNT(*) AS intervals_available

FROM {{ ref('stg_entsoe_prices') }}

GROUP BY
    bidding_zone,
    hour_start_utc
