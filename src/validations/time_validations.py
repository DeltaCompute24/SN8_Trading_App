from datetime import datetime

import pytz


def convert_to_etc(start_time):
    utc_zone = pytz.utc
    et_zone = pytz.timezone("US/Eastern")

    # Assign the UTC timezone to the datetime object
    utc_time = utc_zone.localize(start_time)

    # Convert UTC time to ET time
    et_time = utc_time.astimezone(et_zone)

    # Format the datetime object into the desired format
    return et_time.strftime("%b %d %-I%p ET")


def convert_timestamp_to_datetime(timestamp_ms):
    timestamp_sec = timestamp_ms / 1000.0
    return datetime.fromtimestamp(timestamp_sec)
