import pandas as pd

from util.utility import obj_to_df
from model.data_layer import get_bounds

def find_bounds(db, x_pilot, room_id, metric_id, months):
    # Ensure `months` is a list for consistent processing
    months = [months] if isinstance(months, int) else months

    room_ids = [room_id] if isinstance(room_id, int) else room_id
    bounds = obj_to_df(get_bounds(db, x_pilot, room_ids=room_ids))

    # Determine the season(s) for the given months
    seasons = set()
    if -1 in months:  # Handle `-1` explicitly
        seasons = {0, 1}  # All seasons: Winter and Summer
    else:
        for month in months:
            if 5 <= month <= 9:
                seasons.add(1)  # Summer season
            elif month <= 4 or month >= 10:
                seasons.add(0)  # Winter season

    # Handle multiple seasons
    if len(seasons) > 1:
        season_num = -1  # Mixed seasons
    else:
        season_num = seasons.pop()  # Single season (0 or 1)

    # Get bounds for the metric_id and season_num
    specific_bounds_table = bounds[
        (bounds['metric_id'] == metric_id) & (bounds['season'] == season_num)
    ]

    # If no bounds found for the given season, try for mixed season (-1)
    if specific_bounds_table.empty:
        specific_bounds_table = bounds[
            (bounds['metric_id'] == metric_id) & (bounds['season'] == -1)
        ]

    # If multiple season-specific bounds exist, average them (if needed)
    if len(specific_bounds_table) > 1:
        # For now, let's average the bounds across seasons if multiple rows exist
        lower_bound_avg = specific_bounds_table['lower_bound'].mean()
        upper_bound_avg = specific_bounds_table['upper_bound'].mean()

        # Create a new DataFrame with averaged bounds
        specific_bounds_table = pd.DataFrame(
            data=[[metric_id, room_id, season_num, lower_bound_avg, upper_bound_avg]],
            columns=['metric_id', 'room_id', 'season', 'lower_bound', 'upper_bound']
        )

    # Add default bounds for thermal comfort if no bounds were found
    if metric_id == 4 and specific_bounds_table.empty:
        specific_bounds_table = pd.DataFrame(
            data=[[4, room_id, season_num, -0.5, 0.5]],
            columns=['metric_id', 'room_id', 'season', 'lower_bound', 'upper_bound']
        )

    # Impose limit on bounds for metric_id == 6
    if metric_id == 6 and not specific_bounds_table.empty:
        specific_bounds_table.loc[:, 'upper_bound'] = specific_bounds_table['upper_bound'].clip(upper=2000)

    return specific_bounds_table
