import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import Depends

from fastapi import APIRouter, Header, Path, Query
from pydantic import BaseModel
from datetime import datetime
from util.utility import obj_to_df, replace_nan_with_none
from database import get_db
from model.data_layer import get_sensors_by_room
from model.data_layer import get_virtual_sensors
from model.data_layer import get_todays_measurements
from model.liveview_graph import function_liveview_graph, function_liveview_graph_minutes
from model.bounds import find_bounds

router = APIRouter(
    prefix='/api',
    tags=['Room Live View'],
    # dependencies=[Security(validate_is_admin)]
)


class LiveGraphOutput(BaseModel):
    units: int
    datapoints: Optional[List[Optional[float]]] = None
    outliers: Optional[List[Optional[float]]] = None
    optimal_bounds: List[float]

@router.get('/people/rooms/{room_id}/liveview/today', response_model=LiveGraphOutput)
async def live_graph(
        room_id: int = Path(..., description="Room ID"),
        exclude_anomalies: bool = Query(..., description="Exclude anomalies"),
        sensor_id: int = Query(..., description="Sensor ID (-1 for all sensors)"),
        accuracy: int = Query(None, description="Get values per 5, 10 or 15 minutes. Blank for 60 minutes."),
        x_pilot: int = Header(..., description="Pilot ID to determine database connection"),
        db: Session = Depends(get_db)
):

    # Determine current date and month
    current_date = datetime.now()
    # current_date = datetime(2024, 11, 13)
    current_month = current_date.month

    if sensor_id == -1:
        sensors_in_room = obj_to_df(get_sensors_by_room(db, x_pilot, room_id))
        sensor_ids = list(sensors_in_room['id'])
        virtual_sensors_in_room = obj_to_df(get_virtual_sensors(db, x_pilot, 200, sensor_ids))

    else:
        virtual_sensors_in_room = obj_to_df(get_virtual_sensors(db, x_pilot, vs_ids=sensor_id))

    if virtual_sensors_in_room.empty:
        specific_bounds_table = find_bounds(db, x_pilot, room_id, 200, current_month)
        optimal_bounds = specific_bounds_table[['lower_bound', 'upper_bound']].values[0].tolist()

        return LiveGraphOutput(
            units=0,
            datapoints=None,
            outliers=None,
            optimal_bounds=optimal_bounds
        )

    room_data = obj_to_df(get_todays_measurements(db, x_pilot, current_date, list(virtual_sensors_in_room['id'])))
    print(accuracy)

    if accuracy is None:
        graph_output = function_liveview_graph(
            room_data,
            exclude_anomalies
        )
    else:
        graph_output = function_liveview_graph_minutes(
            room_data,
            exclude_anomalies,
            accuracy
        )

    graph_output['value'] = graph_output['value'].fillna(float('nan'))
    graph_output['anomaly'] = graph_output['anomaly'].fillna(float('nan'))

    optimal_bounds = (find_bounds(db, x_pilot, room_id, 200, current_month)
                      [['lower_bound', 'upper_bound']].values[0].tolist())

    units_used = virtual_sensors_in_room['unit_id'].values[0]

    live_graph_output = LiveGraphOutput(
        units=units_used,
        datapoints=replace_nan_with_none(graph_output['value'].tolist()),
        outliers=replace_nan_with_none(graph_output['anomaly'].tolist()),
        optimal_bounds=replace_nan_with_none(optimal_bounds)
    )
    # print(live_graph_output)

    return live_graph_output
