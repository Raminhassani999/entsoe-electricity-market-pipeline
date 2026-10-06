{{ config(materialized='view') }}

SELECT
    hour_start_utc,
    bidding_zone,

    -- Total generation
    SUM(average_generation_mw) AS total_generation_mw,

    -- Renewable generation
    SUM(
        CASE
            WHEN production_type IN (
                'Biomass',
                'Hydro Run-of-river and Poundage',
                'Hydro Water Reservoir',
                'Solar',
                'Wind Onshore'
            )
            THEN average_generation_mw
            ELSE 0
        END
    ) AS renewable_generation_mw,

    -- Renewable share
    SAFE_DIVIDE(
        SUM(
            CASE
                WHEN production_type IN (
                    'Biomass',
                    'Hydro Run-of-river and Poundage',
                    'Hydro Water Reservoir',
                    'Solar',
                    'Wind Onshore'
                )
                THEN average_generation_mw
                ELSE 0
            END
        ),
        SUM(average_generation_mw)
    ) AS renewable_share,

    -- Individual renewable sources
    SUM(
        CASE
            WHEN production_type = 'Solar'
            THEN average_generation_mw
            ELSE 0
        END
    ) AS solar_mw,

    SUM(
        CASE
            WHEN production_type = 'Wind Onshore'
            THEN average_generation_mw
            ELSE 0
        END
    ) AS wind_onshore_mw,

    SUM(
        CASE
            WHEN production_type IN (
                'Hydro Run-of-river and Poundage',
                'Hydro Water Reservoir'
            )
            THEN average_generation_mw
            ELSE 0
        END
    ) AS hydro_mw,

    -- Fossil generation
    SUM(
        CASE
            WHEN production_type IN (
                'Fossil Coal-derived Gas',
                'Fossil Gas',
                'Fossil Hard Coal',
                'Fossil Oil'
            )
            THEN average_generation_mw
            ELSE 0
        END
    ) AS fossil_generation_mw,

    -- Fossil gas
    SUM(
        CASE
            WHEN production_type = 'Fossil Gas'
            THEN average_generation_mw
            ELSE 0
        END
    ) AS fossil_gas_mw,

    -- Electricity price
    MAX(average_price_eur_mwh) AS average_price_eur_mwh,
    MAX(minimum_price_eur_mwh) AS minimum_price_eur_mwh,
    MAX(maximum_price_eur_mwh) AS maximum_price_eur_mwh,

    -- Data completeness
    SUM(generation_intervals_available) AS generation_intervals_available,
    MAX(price_intervals_available) AS price_intervals_available

FROM {{ ref('hourly_generation_prices') }}

GROUP BY
    hour_start_utc,
    bidding_zone