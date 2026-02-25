import holidays

from dateutil import easter
from datetime import datetime, timedelta
import polars as pl
import pandas as pd

def nwh_detection_polars(date_from, date_to):
    # Ensure date_from and date_to are in the correct datetime format
    date_from = datetime.strptime(date_from, "%Y-%m-%d")
    date_to = datetime.strptime(date_to, "%Y-%m-%d")

    # Calculate the number of hours between the start and end date
    hours_range = (date_to - date_from).total_seconds() // 3600  # Total hours between the dates

    # Create a list of datetime objects with hourly intervals
    full_range = [date_from + timedelta(hours=i) for i in range(int(hours_range) + 1)]

    # Convert to a Polars DataFrame
    final_nwh = pl.DataFrame({"timestamp": full_range})

    # Create a column with date and time parts as FixedSizeList
    final_nwh = final_nwh.with_columns([
        pl.col("timestamp")
        .dt.strftime("%Y-%m-%d %H:%M:%S")  # Format the timestamp as string
        .str.split(" ")  # Split the string by the space between date and time
        .alias("Date_FullTime")
    ])

    # Split 'Date_FullTime' into separate columns for 'Date' and 'Full_Time'
    final_nwh = final_nwh.with_columns([
        pl.col("Date_FullTime").list.get(0).alias("Date"),
        pl.col("Date_FullTime").list.get(1).alias("Full_Time")
    ]).drop("Date_FullTime")

    # Assign all entries to 1 initially (for working hours)
    final_nwh = final_nwh.with_columns([
        pl.lit(1).alias("wh")
    ])

    # Mark weekends (Saturday and Sunday) as non-working hours (wh = 0)
    weekdays = final_nwh.with_columns([
        pl.col("Date").str.strptime(pl.Date, "%Y-%m-%d").dt.weekday().alias("Weekday")
    ])

    final_nwh = final_nwh.join(weekdays.select(["Date", "Weekday"]).unique(), on="Date")
    final_nwh = final_nwh.with_columns([
        pl.when(pl.col("Weekday").is_in([6, 7])).then(0).otherwise(pl.col("wh")).alias("wh")
    ]).drop("Weekday")

    # Mark public holidays and Easter dates as non-working hours (wh = 0)
    public_holidays = holidays.country_holidays('GR')

    years = final_nwh.select(
        pl.col("Date")
        .str.strptime(pl.Date, "%Y-%m-%d")  # Ensure it's in date format
        .dt.year()  # Extract the year
    ).to_numpy()

    years_list = years.flatten().tolist()
    unique_years = set(years_list)
    easter_dates = [pd.to_datetime(easter.easter(year)).strftime('%Y-%m-%d') for year in unique_years]

    # Mark holidays
    holiday_dates = set(public_holidays.keys()).union(easter_dates)
    final_nwh = final_nwh.with_columns([
        pl.when(pl.col("Date").is_in(list(holiday_dates))).then(0).otherwise(pl.col("wh")).alias("wh")
    ])

    # Mark nighttime hours (example: 20:00 to 8:00) as non-working hours (wh = 0)
    final_nwh = final_nwh.with_columns([
        pl.col("timestamp").dt.hour().alias("Hour")
    ])

    # Now apply the condition on the newly created 'Hour' column
    final_nwh = final_nwh.with_columns([
        pl.when((pl.col("Hour") >= 20) | (pl.col("Hour") < 8)).then(0).otherwise(pl.col("wh")).alias("wh")
    ])

    # Return the final DataFrame with 'timestamp' and 'wh'
    return final_nwh.select(["timestamp", "wh"])

def function_patterns_graph2_polars(room_data, time_resample, working_hours, working_time, anomaly_dtct):

    # Convert 'timestamp' column to date and hour
    room_data = room_data.with_columns([
        pl.col("timestamp").dt.date().alias("date"),
        pl.col("timestamp").dt.hour().alias("hour"),
        pl.col("timestamp").dt.year().alias("year"),
        pl.col("timestamp").dt.month().alias("month"),
        pl.col("timestamp").dt.day().alias("day"),
        pl.col("timestamp").dt.weekday().alias("weekday"),
        pl.col("timestamp").dt.week().alias("week_number")
    ])

    # Remove anomalies if needed
    if anomaly_dtct:
        room_data = anomaly_detection_polars(room_data, 0.95, 0.05, 1.5)
        room_data = room_data.filter(pl.col("anomaly") == 0)

    # Remove non-working hours if needed
    if working_time:
        working_hours = working_hours.with_columns([
            pl.col("timestamp").dt.date().alias("date"),
            pl.col("timestamp").dt.hour().alias("hour")
        ])
        room_data = room_data.join(working_hours[['date', 'hour', 'wh']], on=['date', 'hour'], how='left')
        room_data = room_data.with_columns([pl.col("wh").fill_null(0).cast(pl.Int32)])
        room_data = room_data.filter(pl.col("wh") == 1)

        room_data = room_data.with_columns(
            pl.when(pl.col("wh") == 0)
            .then(None)
            .otherwise(pl.col("value"))
            .alias("value")
        )

    # Flag seasons
    seasons = {1: 4, 2: 4, 3: 1, 4: 1, 5: 1,
               6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3, 12: 4}
    room_data = room_data.with_columns([
        pl.col("month").replace(seasons).alias("season")
    ])

    room_data = room_data.with_columns([
        pl.col("date").cast(pl.Utf8)
    ])

    final_dict = {}

    if time_resample == 1:  # Daily Resampling
        for d in room_data['date'].unique():
            daily_data = room_data.filter(pl.col('date') == d).group_by('date').agg(
                pl.col('value').mean().round(2)
            )
            final_dict[d] = daily_data.to_dict()['value'][0]

    elif time_resample == 2:  # Weekday Resampling
        for wd in room_data['weekday'].unique():
            weekday_data = room_data.filter(pl.col('weekday') == wd).group_by('weekday').agg(
                pl.col('value').mean().round(2)
            )
            final_dict[wd] = weekday_data.to_dict()['value'][0]

    elif time_resample == 3:  # Week Number Resampling
        week_dates = {}
        for w in room_data['week_number'].unique():
            start_of_week = room_data.filter(pl.col('week_number') == w).select(pl.col("date").min())
            start_of_week_date = start_of_week.to_numpy()[0][0]
            week_dates[w] = start_of_week_date

        for w, monday_date in week_dates.items():
            week_data = room_data.filter(pl.col('week_number') == w).group_by('week_number').agg(
                pl.col('value').mean().round(2)
            )
            final_dict[f"{w}:{monday_date}"] = week_data.to_dict()['value'][0]

    elif time_resample == 4:  # Monthly Resampling
        for m in room_data['month'].unique():
            month_data = room_data.filter(pl.col('month') == m).group_by('month').agg(
                pl.col('value').mean().round(2)
            )
            final_dict[m] = month_data.to_dict()['value'][0]

    elif time_resample == 5:  # Seasonal Resampling
        for s in room_data['season'].unique():
            season_data = room_data.filter(pl.col('season') == s).group_by('season').agg(
                pl.col('value').mean().round(2)
            )
            final_dict[s] = season_data.to_dict()['value'][0]

    # Return the final dictionary, filling missing values with None
    final_dict = {k: (v if v is not None else None) for k, v in final_dict.items()}

    return final_dict

def anomaly_detection_polars(data, quantile_top, quantile_bot, iqr_times):
    # Calculate quantiles
    q1 = data.select(pl.col("value").quantile(quantile_top)).to_numpy()[0][0]
    q3 = data.select(pl.col("value").quantile(quantile_bot)).to_numpy()[0][0]

    # Calculate IQR
    iqr = q1 - q3

    # Set thresholds for anomaly detection
    threshold_lower = q1 - iqr_times * iqr
    threshold_upper = q3 + iqr_times * iqr

    # Create a new column 'anomaly' and flag anomalies
    data = data.with_columns([
        (pl.col("value") < threshold_lower).or_(pl.col("value") > threshold_upper).cast(pl.Int32).alias("anomaly")
    ])

    return data