import math
from typing import List, Optional, Dict

import pandas as pd
import polars as pl
from fastapi import APIRouter, Header, Path, Query
from pydantic import BaseModel
from util.utility import obj_to_df, obj_to_df_polars, get_months_in_range, convert_uint32_to_float
from database import get_db
from model.data_layer import get_sensors_by_room
from model.data_layer import get_virtual_sensors
from model.data_layer import get_measurements_for_period
from model.patterns import function_patterns_graph2_polars, nwh_detection_polars
from model.bounds import find_bounds
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter(
    prefix='/api',
    tags=['Room Patterns'],
    # dependencies=[Security(validate_is_admin)]
)


class Graph2Output(BaseModel):
    units: int
    data: Dict[str, Optional[float]]
    optimal_bounds: List[float]


@router.get('/people/rooms/{room_id}/patterns/average', response_model=Graph2Output)
async def graph_2_api(
        room_id: int = Path(..., description="Room ID"),
        metric_id: int = Query(200, description="Metric"),
        sensor_id: int = Query(..., description="Sensor ID (-1 for all sensors)"),
        time_aggregation: int = Query(..., description="Time aggregation"),
        date_from: str = Query(..., description="Start date"),
        date_to: str = Query(..., description="End date"),
        exclude_non_working_hours: bool = Query(True, description="Exclude non-working hours"),
        exclude_anomalies: bool = Query(True, description="Exclude anomalies"),
        x_pilot: int = Header(..., description="Pilot ID to determine database connection"),
        db: Session = Depends(get_db),
):

    # Use Polars to load data
    if sensor_id == -1:
        sensors_in_room = obj_to_df_polars(get_sensors_by_room(db, x_pilot, room_id))
        sensor_ids = sensors_in_room['id'].to_list()
        virtual_sensors_in_room = obj_to_df_polars(
            get_virtual_sensors(db, x_pilot, metric_id=200, sensor_ids=sensor_ids))
    else:
        virtual_sensors_in_room = obj_to_df_polars(get_virtual_sensors(db, x_pilot, vs_ids=sensor_id))

    months_in_range = get_months_in_range(date_from, date_to)
    optimal_bounds = (find_bounds(db, x_pilot, room_id, 200, months_in_range)
                      [['lower_bound', 'upper_bound']].values[0].tolist())

    # Get all sensor measurements at once and use Polars for merging
    room_data_list = [
        obj_to_df_polars(get_measurements_for_period(db, x_pilot, date_from, date_to, vs_id))
        for vs_id in virtual_sensors_in_room['id'].to_list()
    ]
    room_data = pl.concat(room_data_list)

    # Check if room_data is empty
    if room_data.is_empty():
        graph_output = {str(i): [] for i in range(time_aggregation)}
    else:
        working_hours = nwh_detection_polars(date_from, date_to)

        graph_output = function_patterns_graph2_polars(
            room_data,
            time_aggregation,
            working_hours,
            exclude_non_working_hours,
            exclude_anomalies
        )

        graph_output = convert_uint32_to_float(graph_output)

        graph_output = {
            str(k): None if pd.isna(v) else math.ceil(v)
            # str(k): None if pd.isna(v) else round(v, 2)
            for k, v in graph_output.items()
        }

    units_used = int(virtual_sensors_in_room['unit_id'][0])

    return Graph2Output(
        units=units_used,
        data=graph_output,
        optimal_bounds=optimal_bounds
    )
