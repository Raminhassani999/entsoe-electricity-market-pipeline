{{ config(materialized='view') }}

SELECT
    bidding_zone,
    psr_type,
    production_type,
    TIMESTAMP_TRUNC(
        delivery_start_utc,
        HOUR
    ) AS hour_start_utc,

    AVG(generation_mw) AS average_generation_mw,

    MIN(generation_mw) AS minimum_generation_mw,

    MAX(generation_mw) AS maximum_generation_mw,

    COUNT(*) AS intervals_available

FROM {{ ref('stg_entsoe_generation') }}

GROUP BY
    bidding_zone,
    psr_type,
    production_type,
    hour_start_utc