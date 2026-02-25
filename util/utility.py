import math

from datetime import datetime
import numpy as np
import polars as pl
import pandas as pd

def obj_to_df(obj: object) -> pd.DataFrame:
    if isinstance(obj, list):
        return pd.DataFrame([o.__dict__ for o in obj]).drop('_sa_instance_state', axis=1, errors='ignore')
    else:
        return pd.DataFrame([obj.__dict__]).drop('_sa_instance_state', axis=1, errors='ignore')

def replace_nan_with_none(data):
    if isinstance(data, list):
        return [None if math.isnan(x) else x for x in data]
    return data

def obj_to_df_polars(obj: object) -> pl.DataFrame:
    if isinstance(obj, list):
        # Convert a list of objects to a Polars DataFrame
        return pl.DataFrame([o.__dict__ for o in obj]).drop('_sa_instance_state')
    else:
        # Convert a single object to a Polars DataFrame
        return pl.DataFrame([obj.__dict__]).drop('_sa_instance_state')

def get_months_in_range(date_from: str, date_to: str) -> list:
    # Convert from and to dates to datetime objects
    date_from = datetime.strptime(date_from, "%Y-%m-%d")
    date_to = datetime.strptime(date_to, "%Y-%m-%d")

    # Generate a list of unique months within the range
    months_in_range = set()

    # Iterate over the date range
    current_date = date_from
    while current_date <= date_to:
        months_in_range.add(current_date.month)
        # Move to the next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    # Convert the set to a sorted list of months
    return sorted(list(months_in_range))

def convert_uint32_to_float(data):
    if isinstance(data, dict):
        return {float(k) if isinstance(k, np.uint32) else k: convert_uint32_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_uint32_to_float(item) for item in data]
    elif isinstance(data, np.uint32):
        return float(data)
    return data