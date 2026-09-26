{{ config(materialized='view') }}

SELECT
    delivery_start_utc,
    price_eur_mwh,
    bidding_zone,
    currency,
    unit,
    resolution,
    revision_number,
    published_at_utc,
    delivery_start_local,
    delivery_date_local
FROM {{ source('entsoe', 'raw_prices') }}
