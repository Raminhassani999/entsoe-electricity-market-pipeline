import argparse
import os
from datetime import datetime, timedelta, time, timezone
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

from ingestion.entsoe_prices import (
    parse_datetime,
    parse_resolution,
)


load_dotenv()


API_URL = "https://web-api.tp.entsoe.eu/api"

BIDDING_ZONE = "10Y1001A1001A73I"
TIMEZONE_NAME = "Europe/Rome"

LOCAL_TIMEZONE = ZoneInfo(TIMEZONE_NAME)


# ENTSO-E production type codes
PSR_TYPE_NAMES = {
    "B01": "Biomass",
    "B03": "Fossil Coal-derived Gas",
    "B04": "Fossil Gas",
    "B05": "Fossil Hard Coal",
    "B06": "Fossil Oil",
    "B10": "Hydro Pumped Storage",
    "B11": "Hydro Run-of-river and Poundage",
    "B12": "Hydro Water Reservoir",
    "B16": "Solar",
    "B19": "Wind Onshore",
    "B20": "Other",
    "B25": "Energy Storage",
}


def parse_arguments():
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Fetch ENTSO-E actual electricity generation "
            "for an Italian delivery date."
        )
    )

    parser.add_argument(
        "--date",
        type=str,
        help=(
            "Delivery date in YYYY-MM-DD format. "
            "If omitted, yesterday is used."
        ),
    )

    return parser.parse_args()


def get_target_date(
    date_argument: str | None,
):
    """
    Determine which Italian calendar date to fetch.

    If --date is provided, use that date.
    Otherwise, use yesterday in Europe/Rome.
    """

    if date_argument:
        try:
            return datetime.strptime(
                date_argument,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            raise ValueError(
                "Invalid date format. "
                "Use YYYY-MM-DD, for example 2026-09-20."
            )

    now_italy = datetime.now(
        LOCAL_TIMEZONE
    )

    return (
        now_italy.date()
        - timedelta(days=1)
    )


def build_request_period(
    target_date,
):
    """
    Build the ENTSO-E request period for one
    Italian calendar day.

    The local Italian midnight boundaries are
    converted to UTC before being sent to ENTSO-E.
    """

    start_local = datetime.combine(
        target_date,
        time.min,
        tzinfo=LOCAL_TIMEZONE,
    )

    end_local = datetime.combine(
        target_date + timedelta(days=1),
        time.min,
        tzinfo=LOCAL_TIMEZONE,
    )

    # Convert Italian local boundaries to UTC.
    start_utc = start_local.astimezone(
        timezone.utc
    )

    end_utc = end_local.astimezone(
        timezone.utc
    )

    period_start = start_utc.strftime(
        "%Y%m%d%H%M"
    )

    period_end = end_utc.strftime(
        "%Y%m%d%H%M"
    )

    return (
        period_start,
        period_end,
        start_local,
        end_local,
    )


def fetch_actual_generation(
    token: str,
    period_start: str,
    period_end: str,
    bidding_zone: str = BIDDING_ZONE,
) -> str:
    """
    Fetch actual generation per production type
    from ENTSO-E.

    A75 = Actual generation per type
    A16 = Realised process
    """

    params = {
        "securityToken": token,
        "documentType": "A75",
        "processType": "A16",
        "in_Domain": bidding_zone,
        "periodStart": period_start,
        "periodEnd": period_end,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def parse_generation(
    xml_text: str,
) -> pd.DataFrame:
    """
    Parse ENTSO-E A75 actual generation XML
    into a Pandas DataFrame.
    """

    root = ET.fromstring(
        xml_text
    )

    rows = []

    for time_series in root.findall(
        "{*}TimeSeries"
    ):

        # Generation series contain
        # inBiddingZone_Domain.mRID.
        #
        # Consumption series are not included.
        generation_domain = (
            time_series.findtext(
                "{*}inBiddingZone_Domain.mRID"
            )
        )

        if not generation_domain:
            continue

        psr_type = time_series.findtext(
            "{*}MktPSRType/{*}psrType"
        )

        production_type = PSR_TYPE_NAMES.get(
            psr_type,
            "Unknown",
        )

        unit = time_series.findtext(
            "{*}quantity_Measure_Unit.name"
        )

        for period in time_series.findall(
            "{*}Period"
        ):

            period_start_text = (
                period.findtext(
                    "{*}timeInterval/{*}start"
                )
            )

            resolution = period.findtext(
                "{*}resolution"
            )

            if (
                not period_start_text
                or not resolution
            ):
                continue

            period_start = parse_datetime(
                period_start_text
            )

            interval = parse_resolution(
                resolution
            )

            for point in period.findall(
                "{*}Point"
            ):

                position_text = point.findtext(
                    "{*}position"
                )

                quantity_text = point.findtext(
                    "{*}quantity"
                )

                if (
                    not position_text
                    or not quantity_text
                ):
                    continue

                position = int(
                    position_text
                )

                quantity = float(
                    quantity_text
                )

                # Calculate the actual timestamp
                # of this generation point.
                delivery_start = (
                    period_start
                    + interval * (position - 1)
                )

                rows.append(
                    {
                        "delivery_start_utc":
                            delivery_start,

                        "generation_mw":
                            quantity,

                        "bidding_zone":
                            generation_domain,

                        "psr_type":
                            psr_type,

                        "production_type":
                            production_type,

                        "unit":
                            unit,

                        "resolution":
                            resolution,
                    }
                )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        raise ValueError(
            "ENTSO-E returned no generation points."
        )

    # Make timestamps timezone-aware UTC timestamps.
    df["delivery_start_utc"] = (
        pd.to_datetime(
            df["delivery_start_utc"],
            utc=True,
        )
    )

    # Sort by production type and timestamp.
    df = (
        df
        .sort_values(
            [
                "psr_type",
                "delivery_start_utc",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return df


def filter_to_target_day(
    df: pd.DataFrame,
    start_local: datetime,
    end_local: datetime,
) -> pd.DataFrame:
    """
    Keep only generation timestamps belonging
    to the target Italian calendar day.
    """

    start_utc = start_local.astimezone(
        timezone.utc
    )

    end_utc = end_local.astimezone(
        timezone.utc
    )

    mask = (
        (df["delivery_start_utc"] >= start_utc)
        &
        (df["delivery_start_utc"] < end_utc)
    )

    day_df = df.loc[
        mask
    ].copy()

    # Add Italian local timestamp.
    day_df["delivery_start_local"] = (
        day_df["delivery_start_utc"]
        .dt.tz_convert(
            TIMEZONE_NAME
        )
    )

    # Add Italian calendar date.
    day_df["delivery_date_local"] = (
        day_df["delivery_start_local"]
        .dt.date
    )

    return (
        day_df
        .sort_values(
            [
                "psr_type",
                "delivery_start_utc",
            ]
        )
        .reset_index(
            drop=True
        )
    )
    
def validate_generation(
    df: pd.DataFrame,
    start_local: datetime,
    end_local: datetime,
) -> None:
    """
    Validate actual generation data.

    Checks:
    - DataFrame is not empty
    - Required columns are not null
    - Each production type has one resolution
    - No duplicate business keys
    - Reports missing intervals against the full
      Italian target day
    """

    if df.empty:
        raise ValueError(
            "No generation data available."
        )

    required_columns = [
        "delivery_start_utc",
        "generation_mw",
        "bidding_zone",
        "psr_type",
        "production_type",
        "unit",
        "resolution",
    ]

    for column in required_columns:
        if df[column].isna().any():
            raise ValueError(
                f"Null values found in column: {column}"
            )

    # Make sure each production type uses
    # only one resolution.
    resolution_counts = (
        df.groupby("psr_type")["resolution"]
        .nunique()
    )

    invalid_resolutions = (
        resolution_counts[
            resolution_counts > 1
        ]
    )

    if not invalid_resolutions.empty:
        raise ValueError(
            "Multiple resolutions found for "
            f"production types: "
            f"{invalid_resolutions.index.tolist()}"
        )

    # Business key:
    # one zone + production type + timestamp
    duplicate_count = (
        df.duplicated(
            subset=[
                "bidding_zone",
                "psr_type",
                "delivery_start_utc",
            ]
        )
        .sum()
    )

    print(
        "\nGeneration data quality check:"
    )

    print(
        "Total rows:",
        len(df),
    )

    print(
        "Duplicate rows:",
        duplicate_count,
    )

    if duplicate_count > 0:
        raise ValueError(
            "Duplicate generation business keys found."
        )

    # Convert the full Italian calendar-day
    # boundaries to UTC.
    start_utc = start_local.astimezone(
        timezone.utc
    )

    end_utc = end_local.astimezone(
        timezone.utc
    )

    print(
        "\nRows and missing intervals by production type:"
    )

    for psr_type, group in df.groupby(
        "psr_type"
    ):

        production_type = (
            group["production_type"]
            .iloc[0]
        )

        resolution = (
            group["resolution"]
            .iloc[0]
        )

        interval = parse_resolution(
            resolution
        )

        # Expected timestamps for the ENTIRE
        # target Italian calendar day.
        expected_times = pd.date_range(
            start=start_utc,
            end=end_utc - interval,
            freq=interval,
            tz="UTC",
        )

        actual_times = pd.DatetimeIndex(
            group["delivery_start_utc"]
        )

        missing_times = (
            expected_times
            .difference(actual_times)
        )

        print(
            f"{psr_type} "
            f"({production_type}): "
            f"{len(group)} rows, "
            f"{len(missing_times)} missing"
        )


def main():

    args = parse_arguments()

    token = os.getenv(
        "ENTSOE_API_TOKEN"
    )

    if not token:
        raise ValueError(
            "ENTSOE_API_TOKEN not found. "
            "Check your .env file."
        )

    target_date = get_target_date(
        args.date
    )

    (
        period_start,
        period_end,
        start_local,
        end_local,
    ) = build_request_period(
        target_date
    )

    print(
        "Target Italian delivery date:",
        target_date,
    )

    print(
        "Request period:",
        period_start,
        "→",
        period_end,
    )

    print(
        "\nFetching ENTSO-E actual generation..."
    )

    xml_text = fetch_actual_generation(
        token=token,
        period_start=period_start,
        period_end=period_end,
    )

    print(
        "Received XML:",
        len(xml_text),
        "characters",
    )

    all_generation = parse_generation(
        xml_text
    )

    print(
        "\nGeneration rows parsed:",
        len(all_generation),
    )

    df = filter_to_target_day(
        all_generation,
        start_local,
        end_local,
    )
    validate_generation(
    df,
    start_local,
    end_local,
)

    print(
        "Generation rows for target day:",
        len(df),
    )

    print(
        "\nRows by production type:"
    )

    print(
        df.groupby(
            [
                "psr_type",
                "production_type",
            ]
        )
        .size()
        .to_string()
    )

    print(
        "\nFirst 10 rows:"
    )

    print(
        df.head(10)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()