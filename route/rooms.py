import logging
from typing import List

import pandas as pd
from fastapi import APIRouter, Header, Path
from pydantic import BaseModel

from util.utility import obj_to_df
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from model.data_layer import get_sensors_by_room
from model.data_layer import get_virtual_sensors

logger = logging.getLogger('uvicorn')

router = APIRouter(prefix="/api")


class SensorRoomOutput(BaseModel):
    sensor_id: int
    sensor_name: str
    metric_id: int
    units: int


@router.get("/people/rooms/{room_id}/sensors", response_model=List[SensorRoomOutput])
async def get_room_people_sensors_api(
        room_id: int = Path(..., description="Room ID"),
        x_pilot: int = Header(..., description="Pilot ID to determine database connection"),
        db: Session = Depends(get_db),
) -> List[SensorRoomOutput]:
    try:
        sensors_in_room = obj_to_df(get_sensors_by_room(db, x_pilot, room_id))

        # Check if there are no sensors in the room
        if sensors_in_room.empty:
            return []

        sensors_in_room = sensors_in_room.rename(columns={'id': 'sensor_id'})

        virtual_sensors_in_room = obj_to_df(
            get_virtual_sensors(db, x_pilot, sensor_ids=list(sensors_in_room['sensor_id']))
        )

        merged_sensors_in_room = pd.merge(
            sensors_in_room, virtual_sensors_in_room, on='sensor_id', how='left'
        )

        # FILTER OUT THOSE SENSORS THAT ARE NOT IN VIRTUAL SENSORS
        merged_sensors_in_room = merged_sensors_in_room.dropna(subset=['id'])

        merged_sensors_in_room = merged_sensors_in_room[(merged_sensors_in_room['metric_id'] == 200)]

        merged_sensors_in_room[['id', 'metric_id']] = merged_sensors_in_room[['id', 'metric_id']].fillna(0)
        merged_sensors_in_room['name'] = merged_sensors_in_room[['name']].fillna('UNKNOWN')

        sensors_list = [
            SensorRoomOutput(
                sensor_id=row['id'],
                sensor_name=row['name'],
                metric_id=row['metric_id'],
                units=row['unit_id']
            )
            for _, row in merged_sensors_in_room.iterrows()
        ]

        return sensors_list

    except Exception as e:
        # logger.error(f"Error processing sensors for room {room_id}: {e}")
        return []