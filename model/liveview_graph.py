import pandas as pd
import math

def function_liveview_graph(room_data, exclude_anomalies):
    # Check if the input data is empty
    if room_data.empty:
        # If no data, return None values
        return pd.DataFrame({
            'hour': range(24),
            'value': [None] * 24,
            'anomaly': [None] * 24
        })

    df = room_data.copy()

    # Remove anomalies if needed
    if exclude_anomalies:
        df = anomaly_detection(df, 0.95, 0.05, 1.5)
    else:
        df["anomaly"] = 0

    # Datetime Transformations
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df['hour'] = df['timestamp'].dt.hour  # Extract hour from timestamp

    # Find the max hour for each day
    df['Date'] = df['timestamp'].dt.date  # Get the date part of the timestamp
    last_record = df['Date'].max()  # Get the latest date in the data
    df = df[df['Date'] == last_record]  # Filter data for the last day

    # Group by hour and find the max record for each hour
    hourly_df = df.groupby('hour').agg({'value': 'mean'}).reset_index()

    hourly_df['value'] = hourly_df['value'].apply(lambda x: math.ceil(x) if pd.notna(x) else x)

    # Create a full list of hours (0 to 23)
    all_hours = pd.DataFrame({'hour': range(24)})

    # Merge with the hourly data
    hourly_df = all_hours.merge(hourly_df, on='hour', how='left')

    # Replace NaN with None explicitly for JSON compatibility
    hourly_df['value'] = hourly_df['value'].where(hourly_df['value'].notna(), None)

    # Merge with the original data to keep the anomalies, including 'hour'
    df = df[['timestamp', 'value', 'anomaly', 'hour']].drop_duplicates()

    # Merge anomalies, getting max anomaly per hour (1 if any anomaly exists)
    anomalies_per_hour = df.groupby('hour')['anomaly'].max().reset_index()
    result_df = hourly_df.merge(anomalies_per_hour, on='hour', how='left')
    result_df['anomaly'] = result_df['anomaly'].where(result_df['anomaly'].notna(), None)
    result_df['value'] = result_df['value'].round(2)

    return result_df[['hour', 'value', 'anomaly']]

def anomaly_detection(data, quantile_top, quantile_bot, iqr_times):

    q1 = data['value'].quantile(quantile_top)
    q3 = data['value'].quantile(quantile_bot)
    iqr = q1 - q3

    # Set a threshold for anomaly detection (e.g., 1.5 times IQR)
    threshold_lower = q1 - iqr_times * iqr
    threshold_upper = q3 + iqr_times * iqr

    # Identify anomalies
    data['anomaly'] = 0
    data.loc[((data['value'] < threshold_lower) | (data['value'] > threshold_upper)), 'anomaly'] = 1
    # print(data.loc[((data['value'] < threshold_lower) | (data['value'] > threshold_upper)), 'anomaly'])

    return data

def function_liveview_graph_minutes(room_data, exclude_anomalies, time_window):
    # Validate time_window parameter
    if time_window not in [5, 10, 15]:
        raise ValueError("time_window must be 5, 10, or 15 minutes")

    # Check if the input data is empty
    if room_data.empty:
        # Calculate number of time windows in a day
        windows_per_day = 24 * 60 // time_window
        # If no data, return None values
        return pd.DataFrame({
            'time_window': range(windows_per_day),
            'value': [None] * windows_per_day,
            'anomaly': [None] * windows_per_day
        })

    df = room_data.copy()

    # Remove anomalies if needed
    if exclude_anomalies:
        df = anomaly_detection(df, 0.95, 0.05, 1.5)
    else:
        df["anomaly"] = 0

    # Datetime Transformations
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Create a time window column
    df['Date'] = df['timestamp'].dt.date  # Get the date part of the timestamp
    df['hour'] = df['timestamp'].dt.hour  # Extract hour from timestamp
    df['minute'] = df['timestamp'].dt.minute  # Extract minute from timestamp

    # Calculate the time window index (0 to N-1 where N is number of windows per day)
    df['time_window'] = (df['hour'] * 60 + df['minute']) // time_window

    # Find the latest date in the data
    last_record = df['Date'].max()
    df = df[df['Date'] == last_record]  # Filter data for the last day

    # Group by time_window and calculate the mean value for each window
    window_df = df.groupby('time_window').agg({'value': 'mean'}).reset_index()

    # Round up to the next integer
    window_df['value'] = window_df['value'].apply(lambda x: math.ceil(x) if pd.notna(x) else x)

    # Create a full list of time windows (0 to windows_per_day-1)
    windows_per_day = 24 * 60 // time_window
    all_windows = pd.DataFrame({'time_window': range(windows_per_day)})

    # Merge with the window data
    window_df = all_windows.merge(window_df, on='time_window', how='left')

    # Replace NaN with None explicitly for JSON compatibility
    window_df['value'] = window_df['value'].where(window_df['value'].notna(), None)

    # Merge with the original data to keep the anomalies
    df = df[['timestamp', 'value', 'anomaly', 'time_window']].drop_duplicates()

    # Merge anomalies, getting max anomaly per time window (1 if any anomaly exists)
    anomalies_per_window = df.groupby('time_window')['anomaly'].max().reset_index()
    result_df = window_df.merge(anomalies_per_window, on='time_window', how='left')
    result_df['anomaly'] = result_df['anomaly'].where(result_df['anomaly'].notna(), None)

    return result_df[['time_window', 'value', 'anomaly']]
