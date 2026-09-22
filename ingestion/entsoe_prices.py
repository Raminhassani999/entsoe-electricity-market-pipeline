import argparse
import os
import re
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()

API_URL = "https://web-api.tp.entsoe.eu/api"

# Italy North bidding zone
BIDDING_ZONE = "10Y1001A1001A73I"

TIMEZONE_NAME = "Europe/Rome"

try:
    LOCAL_TIMEZONE = ZoneInfo(TIMEZONE_NAME)
except ZoneInfoNotFoundError:
    raise RuntimeError(
        "Europe/Rome timezone data not found. "
        "Install it with: uv add tzdata"
    )


def parse_arguments():
    """
    Parse command-line arguments.

    --date is optional.

    Example:
        python ingestion/entsoe_prices.py

    uses yesterday.

    Example:
        python ingestion/entsoe_prices.py --date 2026-09-20

    fetches the specified date.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Fetch ENTSO-E day-ahead electricity prices "
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



def get_target_date(date_argument: str | None):
    """
    Determine which Italian calendar date to fetch.

    If --date was provided, use that date.

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


def build_request_period(target_date):
    """
    Build the ENTSO-E request period for one
    Italian calendar day.

    Returns:
        period_start
        period_end
        start_local
        end_local
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

    period_start = start_local.strftime(
        "%Y%m%d%H%M"
    )

    period_end = end_local.strftime(
        "%Y%m%d%H%M"
    )

    return (
        period_start,
        period_end,
        start_local,
        end_local,
    )


def parse_resolution(
    resolution: str,
) -> timedelta:
    """
    Convert an ENTSO-E resolution such as
    PT15M or PT1H into a timedelta.
    """

    match = re.fullmatch(
        r"PT(\d+)(M|H)",
        resolution,
    )

    if not match:
        raise ValueError(
            f"Unsupported resolution: {resolution}"
        )

    value = int(
        match.group(1)
    )

    unit = match.group(2)

    if unit == "M":
        return timedelta(
            minutes=value
        )

    return timedelta(
        hours=value
    )


def parse_datetime(
    value: str,
) -> datetime:
    """
    Convert an ENTSO-E ISO timestamp ending
    in Z into a timezone-aware datetime.
    """

    return datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )



def fetch_day_ahead_prices(
    token: str,
    period_start: str,
    period_end: str,
    bidding_zone: str = BIDDING_ZONE,
) -> str:
    """
    Fetch day-ahead prices from ENTSO-E.
    """

    params = {
        "securityToken": token,
        "documentType": "A44",
        "in_Domain": bidding_zone,
        "out_Domain": bidding_zone,
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


def parse_prices(
    xml_text: str,
) -> pd.DataFrame:
    """
    Parse ENTSO-E A44 XML into a DataFrame.
    """

    root = ET.fromstring(
        xml_text
    )

    # Document metadata
    revision_number = root.findtext(
        "{*}revisionNumber"
    )

    created_datetime = root.findtext(
        "{*}createdDateTime"
    )

    rows = []


    for time_series in root.findall(
        "{*}TimeSeries"
    ):

        domain = time_series.findtext(
            "{*}in_Domain.mRID"
        )

        currency = time_series.findtext(
            "{*}currency_Unit.name"
        )

        unit = time_series.findtext(
            "{*}price_Measure_Unit.name"
        )


        for period in time_series.findall(
            "{*}Period"
        ):

            period_start_text = period.findtext(
                "{*}timeInterval/{*}start"
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

                price_text = point.findtext(
                    "{*}price.amount"
                )

                if (
                    not position_text
                    or not price_text
                ):
                    continue

                position = int(
                    position_text
                )

                price = float(
                    price_text
                )

                # Calculate actual delivery timestamp
                delivery_start = (
                    period_start
                    + interval
                    * (position - 1)
                )

                rows.append(
                    {
                        "delivery_start_utc":
                            delivery_start,

                        "price_eur_mwh":
                            price,

                        "bidding_zone":
                            domain,

                        "currency":
                            currency,

                        "unit":
                            unit,

                        "resolution":
                            resolution,

                        "revision_number":
                            (
                                int(revision_number)
                                if revision_number
                                else None
                            ),

                        "published_at_utc":
                            (
                                parse_datetime(
                                    created_datetime
                                )
                                if created_datetime
                                else None
                            ),
                    }
                )


    df = pd.DataFrame(
        rows
    )

    if df.empty:
        raise ValueError(
            "ENTSO-E returned no price points."
        )

    # Make timestamps proper timezone-aware datetimes
    df["delivery_start_utc"] = (
        pd.to_datetime(
            df["delivery_start_utc"],
            utc=True,
        )
    )

    df["published_at_utc"] = (
        pd.to_datetime(
            df["published_at_utc"],
            utc=True,
        )
    )

    # Sort chronologically
    df = (
        df
        .sort_values(
            "delivery_start_utc"
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
    Keep only timestamps belonging to the target
    Italian calendar day.
    """

    # Convert local boundaries to UTC
    start_utc = (
        start_local.astimezone(
            timezone.utc
        )
    )

    end_utc = (
        end_local.astimezone(
            timezone.utc
        )
    )

    mask = (
        (df["delivery_start_utc"] >= start_utc)
        &
        (df["delivery_start_utc"] < end_utc)
    )

    day_df = df.loc[
        mask
    ].copy()

    # Add local timestamp
    day_df["delivery_start_local"] = (
        day_df["delivery_start_utc"]
        .dt.tz_convert(
            TIMEZONE_NAME
        )
    )

    # Add local calendar date
    day_df["delivery_date_local"] = (
        day_df["delivery_start_local"]
        .dt.date
    )

    return (
        day_df
        .reset_index(
            drop=True
        )
    )

def validate_day(
    df: pd.DataFrame,
    start_local: datetime,
    end_local: datetime,
):
    """
    Validate the target day's timestamps.

    Returns:
        missing timestamps
    """

    if df.empty:
        raise ValueError(
            "No price data exists for the target day."
        )


    resolutions = (
        df["resolution"]
        .dropna()
        .unique()
    )

    if len(resolutions) != 1:
        raise ValueError(
            f"Unexpected resolutions: {resolutions}"
        )

    resolution = resolutions[0]

    interval = parse_resolution(
        resolution
    )


    start_utc = (
        start_local.astimezone(
            timezone.utc
        )
    )

    end_utc = (
        end_local.astimezone(
            timezone.utc
        )
    )


    expected_times = pd.date_range(
        start=start_utc,
        end=end_utc - interval,
        freq=interval,
        tz="UTC",
    )

    missing_times = (
        expected_times
        .difference(
            df["delivery_start_utc"]
        )
    )


    duplicate_count = (
        df["delivery_start_utc"]
        .duplicated()
        .sum()
    )


    print(
        "\nData quality check:"
    )

    print(
        "Expected rows:",
        len(expected_times),
    )

    print(
        "Actual rows:",
        len(df),
    )

    print(
        "Missing rows:",
        len(missing_times),
    )

    print(
        "Duplicate rows:",
        duplicate_count,
    )

    if len(missing_times) > 0:

        print(
            "\nMissing timestamps:"
        )

        for timestamp in missing_times:
            print(timestamp)

    else:

        print(
            "Missing timestamps: None"
        )

    return missing_times


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
        "\nFetching ENTSO-E day-ahead prices..."
    )

    xml_text = fetch_day_ahead_prices(
        token=token,
        period_start=period_start,
        period_end=period_end,
    )

    print(
        "Received XML:",
        len(xml_text),
        "characters",
    )

    raw_dir = Path(
        "data/raw/entsoe"
    )

    raw_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_file = (
        raw_dir
        / f"day_ahead_prices_{target_date}.xml"
    )

    raw_file.write_text(
        xml_text,
        encoding="utf-8",
    )

    print(
        "Raw XML saved to:",
        raw_file,
    )

    all_prices = parse_prices(
        xml_text
    )

    print(
        "\nRows returned by ENTSO-E:",
        len(all_prices),
    )

    df = filter_to_target_day(
        all_prices,
        start_local,
        end_local,
    )

    print(
        "Rows for target day:",
        len(df),
    )

    missing_times = validate_day(
        df,
        start_local,
        end_local,
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


    processed_dir = Path(
        "data/processed"
    )

    processed_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed_file = (
        processed_dir
        / f"day_ahead_prices_{target_date}.csv"
    )

    df.to_csv(
        processed_file,
        index=False,
    )

    print(
        "\nNormalized CSV saved to:",
        processed_file,
    )


    print(
        "\nPipeline result:"
    )

    print(
        "Target date:",
        target_date,
    )

    print(
        "Rows loaded:",
        len(df),
    )

    print(
        "Missing timestamps:",
        len(missing_times),
    )

    print(
        "Processed file:",
        processed_file,
    )


if __name__ == "__main__":
    main()