SELECT
    *
FROM {{ ref('int_hourly_generation') }}
WHERE intervals_available < 1
OR intervals_available > 4