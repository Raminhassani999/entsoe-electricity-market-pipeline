# ENTSO-E Electricity Market Pipeline

End-to-end data engineering pipeline for ingesting European electricity market data from the ENTSO-E API, storing raw and structured data in Google Cloud, transforming it with dbt, and orchestrating the workflow with Kestra.

## Status

✅ **Completed**

The pipeline successfully runs end-to-end:

```text
ENTSO-E API
     │
     ▼
Python Ingestion
     │
     ▼
Docker
     │
     ├──────────────► Google Cloud Storage
     │
     ▼
BigQuery Raw Tables
     │
     ▼
dbt
     │
     ├── Staging
     ├── Intermediate
     └── Analytics
     │
     ▼
hourly_energy_analysis

## Kestra orchestrates the complete workflow
Generation Ingestion
        │
        ▼
Price Ingestion
        │
        ▼
dbt Transformations
        │
        ▼
Analytics Tables

Project Overview
This project demonstrates a complete modern data engineering workflow using electricity market data from ENTSO-E.
The pipeline:
1. Retrieves electricity generation data from the ENTSO-E API.
2. Retrieves day-ahead electricity price data.
3. Stores raw data in Google Cloud Storage.
4. Loads structured data into BigQuery.
5. Transforms the raw data using dbt.
6. Performs automated data-quality checks.
7. Produces analytics-ready hourly electricity data.
8. Uses Kestra to orchestrate and schedule the complete workflow.
9. Runs ingestion and transformation components inside Docker containers.


Architecture

                         ┌─────────────────────┐
                         │     ENTSO-E API     │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
          ┌──────────────────┐           ┌──────────────────┐
          │ Generation       │           │ Day-Ahead Prices │
          │ Python Ingestion │           │ Python Ingestion │
          └────────┬─────────┘           └────────┬─────────┘
                   │                              │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Docker Containers│
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌──────────────────┐        ┌──────────────────┐
          │ Google Cloud     │        │ BigQuery         │
          │ Storage          │        │ Raw Tables       │
          │ Raw XML          │        │                  │
          └──────────────────┘        └────────┬─────────┘
                                               │
                                               ▼
                                      ┌──────────────────┐
                                      │       dbt        │
                                      ├──────────────────┤
                                      │ Staging          │
                                      │ Intermediate     │
                                      │ Analytics        │
                                      └────────┬─────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ hourly_energy_analysis │
                                  └────────────────────────┘

                         ┌──────────────────────┐
                         │       Kestra         │
                         │   Orchestration      │
                         └──────────────────────┘


Technology Stack

| Component | Technology |
|---|---|
| Data Source | ENTSO-E API |
| Ingestion | Python |
| Data Processing | Pandas |
| Containerization | Docker |
| Orchestration | Kestra |
| Raw Storage | Google Cloud Storage |
| Data Warehouse | Google BigQuery |
| Transformation | dbt |
| Cloud Platform | Google Cloud |
| Infrastructure | Terraform |
| Version Control | Git / GitHub |


Data Flow

1. Generation Data
The generation ingestion process retrieves actual electricity generation data for the Italian bidding zone.
The pipeline:
ENTSO-E API
    ↓
XML response
    ↓
Python parsing
    ↓
Data validation
    ↓
GCS raw XML
    ↓
BigQuery raw_generation

Generation data contains information such as:
- Delivery timestamp
- Generation in MW
- Bidding zone
- Production type
- PSR type
- Resolution
- Local delivery date


2. Day-Ahead Price Data
The price ingestion process retrieves day-ahead electricity prices for the Italian bidding zone

ENTSO-E API
    ↓
XML response
    ↓
Python parsing
    ↓
Data validation
    ↓
GCS raw XML
    ↓
BigQuery raw_prices

Price data includes:
- Delivery timestamp
- Price in EUR/MWh
- Bidding zone
- Currency
- Resolution
- Revision number
- Publication timestamp
- Local delivery date


dbt Transformation Layer
The dbt project is organized into three layers.
Staging
The staging layer provides clean views over the raw BigQuery tables.

stg_entsoe_generation
stg_entsoe_prices


esponsibilities include:
- Selecting required columns
- Standardizing the structure
- Providing a clean interface to raw data


Intermediate
The intermediate layer aggregates the source data into hourly measurements.
int_hourly_generation
int_hourly_prices

Generation data is aggregated by:
- Bidding zone
- Hour
- Production type
- PSR type
Price data is aggregated into hourly price statistics.

Analytics
The analytics layer combines generation and price information.
hourly_generation_prices
hourly_energy_analysis

The final analytical data includes information such as:
- Average generation
- Minimum generation
- Maximum generation
- Average electricity price
- Minimum electricity price
- Maximum electricity price
- Available generation intervals
- Available price intervals


Data Quality
The pipeline contains automated dbt tests covering:
- Null values
- Unique keys
- Valid hourly intervals
- Generation consistency
- Price consistency
- Generation and price availability
- Analytics model integrity
The pipeline also handles missing source intervals from ENTSO-E.
For example, if a generation hour exists but the corresponding price is unavailable, the pipeline reports a warning rather than failing the entire transformation workflow.
This allows downstream analytics to continue while still making source-data quality issues visible.

Orchestration with Kestra
Kestra manages the complete pipeline workflow.
The current workflow is:
run_generation
      │
      ▼
run_prices
      │
      ▼
run_dbt

Each task runs inside its corresponding Docker container.
The workflow is scheduled daily using
06:00 Europe/Rome

This means the pipeline can run automatically without manually executing the individual ingestion and transformation commands.

Docker
The project uses separate Docker environments for the ingestion and dbt components.
Ingestion image
entsoe-ingestion:latest
Runs the Python ingestion modules.
dbt image
entsoe-dbt:latest
Contains:
- Python
- dbt Core
- dbt BigQuery adapter
- Git
- dbt project
The dbt image is intentionally separated from the local development environment so that the transformation workflow is reproducible.

Google Cloud
The pipeline uses Google Cloud services for data storage and analytics.
Google Cloud Storage
Raw ENTSO-E XML files are retained in GCS.
Example structure:
raw/
└── entsoe/
    ├── generation/
    └── prices/

BigQuery
BigQuery contains the raw and transformed datasets.
Main raw tables:
raw_generation
raw_prices

Main analytical models:
hourly_generation_prices
hourly_energy_analysis


entsoe-pipeline/
│
├── dbt/
│   ├── Dockerfile
│   ├── .dockerignore
│   │
│   └── entsoe_transformations/
│       ├── models/
│       │   ├── staging/
│       │   ├── intermediate/
│       │   └── analytics/
│       │
│       ├── tests/
│       ├── dbt_project.yml
│       └── ...
│
├── ingestion/
│   ├── entsoe_generation.py
│   ├── entsoe_prices.py
│   └── test_connection.py
│
├── kestra/
│   ├── docker-compose.yml
│   └── flows/
│       └── entsoe_ingestion.yml
│
├── src/
│   └── ...
│
├── terraform/
│   └── ...
│
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md


Local Setup
Prerequisites
The project requires:
- Docker Desktop
- Python 3.13
- Google Cloud account/project
- Google Cloud CLI
- ENTSO-E API token
- Git


1. Clone the repository
git clone <repository-url>
cd entsoe-pipeline

2. Configure environment variables
Create a .env file based on .env.example.
The ENTSO-E API token should be stored locally and must not be committed to Git.


3. Configure Google Cloud authentication
Authenticate using Application Default Credentials:
gcloud auth application-default login

Set the project: gcloud auth application-default set-quota-project entso-e-electricity-pipeline

4. Start Kestra
From the project root: docker compose -f kestra/docker-compose.yml up -d
Kestra is available locally at: http://localhost:8080

5. Build the ingestion image
docker build -t entsoe-ingestion:latest .

6. Build the dbt image
docker build -t entsoe-dbt:latest ./dbt

7. Run the pipeline
The recommended workflow is to execute the pipeline through Kestra.
Kestra runs: Generation → Prices → dbt

Validation
The complete pipeline has been tested end-to-end.
Kestra
Generation ingestion    ✅
Price ingestion         ✅
dbt transformation      ✅

dbt
Tests:      42
Passed:     41
Warnings:    1
Errors:      0
Skipped:     0

The warning corresponds to a missing source interval in ENTSO-E data and does not prevent the analytics models from being generated.
Final analytics table
hourly_energy_analysis

The table contains hourly electricity generation and price information suitable for downstream analysis and visualization.

Key Engineering Challenges
Several practical data engineering problems were addressed during development:
Containerized authentication
Google Cloud authentication had to work from inside Docker containers rather than only from the host machine.
Docker and Kestra integration
Kestra was configured to execute the ingestion and dbt containers through its Docker task runner.
Historical data backfill
Historical generation and price data was backfilled to provide a continuous analytical dataset.
External data gaps
ENTSO-E occasionally provides incomplete intervals. The pipeline detects these issues through data-quality tests and reports them as warnings when appropriate.
Reproducible dbt environment
The dbt transformation environment was containerized with its required versions and dependencies, allowing the same transformation workflow to run independently from the local Python environment.


Future Improvements
Possible extensions include:
- Dashboarding with a BI tool
- Additional ENTSO-E datasets
- Weather data integration
- More advanced analytics
- Cloud-native orchestration
- Automated monitoring and alerting
These are optional extensions and are not required for the current pipeline to operate


Author
Ramin Hassani
Data Engineering Project