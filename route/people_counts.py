import logging
from typing import List

from fastapi import APIRouter, Header
from pydantic import BaseModel
import pandas as pd

from util.utility import obj_to_df
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from model.data_layer import get_counters, get_virtual_sensors

logger = logging.getLogger('uvicorn')

router = APIRouter(prefix="/api")


# class PeopleCounter(BaseModel):
#     id: str
#     name: str

class SensorsOutput(BaseModel):
    sensor_id: int
    sensor_name: str
    metric_id: int
    units: int


@router.get("/people/sensors", response_model=List[SensorsOutput])
async def get_people_sensor_ids(x_pilot: int = Header(..., description="Pilot ID to determine database connection"),
                                db: Session = Depends(get_db)) -> List[SensorsOutput]:
    # TODO: Put the pilot ID on a list of pilots that supports people counting.
    if not x_pilot == 200: return []

    # counters = obj_to_df(get_counters(db, x_pilot))[["id", "name"]]
    # counters_list = [
    #     PeopleCounter(
    #         id=str(row['id']),
    #         name=row['name']
    #     )
    #     for _, row in counters.iterrows()
    # ]
    #
    # return counters_list

    sensors = obj_to_df(get_counters(db, x_pilot))
    sensors = sensors.rename(columns={'id': 'sensor_id'})
    virtual_sensors = obj_to_df(get_virtual_sensors(db, x_pilot, sensor_ids=list(list(sensors['sensor_id']))))
    merged_sensors = pd.merge(sensors, virtual_sensors, on='sensor_id', how='left')

    # FILTER OUT THOSE SENSORS THAT ARE NOT IN VIRTUAL SENSORS?
    merged_sensors = merged_sensors.dropna(subset=['id'])

    merged_sensors[['id', 'metric_id']] = merged_sensors[['id', 'metric_id']].fillna(0)
    merged_sensors['name'] = merged_sensors[['name']].fillna('UNKNOWN')
    merged_sensors['unit_id'] = merged_sensors[['unit_id']].fillna(0)

    sensors_list = [
        SensorsOutput(
            sensor_id=row['id'],
            sensor_name=row['name'],
            metric_id=row['metric_id'],
            units=row['unit_id']
        )
        for _, row in merged_sensors.iterrows()
    ]

    return sensors_list


