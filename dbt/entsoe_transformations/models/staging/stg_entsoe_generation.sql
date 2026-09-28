{{ config(materialized='view') }}

SELECT
    delivery_start_utc,
    generation_mw,
    bidding_zone,
    psr_type,
    production_type,
    unit,
    resolution,
    delivery_start_local,
    delivery_date_local
FROM {{ source('entsoe', 'raw_generation') }}