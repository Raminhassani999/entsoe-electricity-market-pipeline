FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dbt-core==1.12.5 dbt-bigquery==1.12.1

COPY entsoe_transformations /app/entsoe_transformations

WORKDIR /app/entsoe_transformations

CMD ["dbt", "build"]