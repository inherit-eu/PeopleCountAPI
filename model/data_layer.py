from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, Float, String, Boolean, PrimaryKeyConstraint, DateTime
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta

from database import Base

##################### Sensors #####################

# _dynamic_c_table_cache = {}

def dynamic_counters_table(suffix):

    table_name = f'sensors_pilot_{suffix}' # This must be sensors.
    if table_name in _dynamic_s_table_cache:
        return _dynamic_s_table_cache[table_name]

    class CountersTable(Base):
        __tablename__ = table_name  # Table name is dynamically set
        __table_args__ = (
            {'schema': 'reporting'}
        )

        id = Column(Integer, primary_key=True)
        mac_address = Column(String)
        name = Column(String)
        room_id = Column(Integer)

    _dynamic_s_table_cache[table_name] = CountersTable
    return CountersTable

def get_counters(db: Session, suffix: int) -> List:

    CountersTable = dynamic_counters_table(suffix)
    counter__all = db.query(CountersTable).filter(CountersTable.name.startswith('People Counter')).all()
    return counter__all

##################### Sensors By Room #####################
_dynamic_s_table_cache = {}

def get_sensors_by_room(db: Session, suffix: int, room_id: int) -> List:
    """
    Retrieves the sensors filtered by room ID.
    :param db: The database session.
    :param suffix: The suffix to dynamically select the sensors table.
    :param room_id: The ID of the room to filter the sensors by.
    :return: A list of sensors associated with the given room.
    """

    SensorsTable = dynamic_sensors_table(suffix)

    # Query the SensorsTable, filtering by room_id
    return db.query(SensorsTable).filter(SensorsTable.room_id == room_id).all()

def dynamic_sensors_table(suffix: int):
    """
    Factory function to create or retrieve a cached SensorsTable class
    with a dynamic table name in the 'reporting' schema.
    """
    table_name = f'sensors_pilot_{suffix}'
    if table_name in _dynamic_s_table_cache:
        return _dynamic_s_table_cache[table_name]

    # Define the dynamic table class
    class SensorsTable(Base):
        __tablename__ = table_name  # Table name is dynamically set
        __table_args__ = (
            {'schema': 'reporting'}
        )

        id = Column(Integer, primary_key=True)
        mac_address = Column(String)
        name = Column(String)
        room_id = Column(Integer)

    # Cache the class for reuse
    _dynamic_s_table_cache[table_name] = SensorsTable
    return SensorsTable

##################### Virtual Sensors #####################
def get_virtual_sensors(
        db: Session,
        suffix: int,
        metric_id: Optional[int] = None,
        sensor_ids: Optional[List[int]] = None,
        vs_ids: Optional[List[int]] = None
) -> List:
    """
    Retrieves virtual sensors, optionally filtered by metric_id and sensor_ids.
    :param db: The database session.
    :param suffix: The suffix to dynamically select the virtual sensors table.
    :param metric_id: (Optional) The metric ID to filter by.
    :param sensor_ids: (Optional) A list of sensor IDs to filter by.
    :param vs_ids: (Optional) A list of virtual sensor IDs to filter by.
    :return: A list of virtual sensors matching the filters.
    """

    VirtualSensorsTable = dynamic_virtual_sensors_table(suffix)

    # Build the query
    query = db.query(VirtualSensorsTable)

    # Apply filters if provided
    if metric_id is not None:
        query = query.filter(VirtualSensorsTable.metric_id == metric_id)
    if sensor_ids:
        query = query.filter(VirtualSensorsTable.sensor_id.in_(sensor_ids))
    if vs_ids:
        query = query.filter(VirtualSensorsTable.id == vs_ids)

    return query.all()

_dynamic_vs_table_cache: Dict[str, type] = {}


def dynamic_virtual_sensors_table(suffix: int):

    """
    Factory function to create or retrieve a VirtualSensorsTable class with a dynamic table name
    in the 'reporting' schema.
    """
    table_name = f'virtual_sensors_pilot_{suffix}'

    if table_name in _dynamic_vs_table_cache:
        return _dynamic_vs_table_cache[table_name]

    # Dynamically create the class
    class VirtualSensorsTable(Base):
        __tablename__ = table_name  # Table name is dynamically set
        __table_args__ = (
            {'schema': 'reporting'}
        )

        id = Column(Integer, primary_key=True)
        sensor_id = Column(Integer)
        unit_id = Column(Integer)
        metric_id = Column(Integer)

    # Cache the class for reuse
    _dynamic_vs_table_cache[table_name] = VirtualSensorsTable

    return VirtualSensorsTable

##################### Bounds #####################

def get_bounds(
        db: Session,
        suffix: int,
        metric_id: Optional[int] = None,
        room_ids: Optional[Union[int, List[int]]] = None,
        season: Optional[int] = None
) -> List:
    """
    Retrieves bounds, optionally filtered by metric_id, room_ids, and season.
    :param db: The database session.
    :param suffix: The suffix to dynamically select the bounds table.
    :param metric_id: (Optional) The metric ID to filter by.
    :param room_ids: (Optional) A single room ID or a list of room IDs to filter by.
    :param season: (Optional) The season to filter by (-1 for all, 0 for winter, 1 for summer).
    :return: A list of bounds matching the filters.
    """

    BoundsTable = dynamic_bounds_table(suffix)

    # Ensure room_ids is a list
    if room_ids is not None and not isinstance(room_ids, list):
        room_ids = [room_ids]

    # Build the query
    query = db.query(BoundsTable)

    # Apply filters if provided
    if metric_id is not None:
        query = query.filter(BoundsTable.metric_id == metric_id)
    if room_ids:
        query = query.filter(BoundsTable.room_id.in_(room_ids))
    if season is not None:
        query = query.filter(BoundsTable.season == season)

    return query.all()

_dynamic_bounds_table_cache = {}


def dynamic_bounds_table(suffix: int):
    """
    Factory function to create or retrieve a BoundsTable class with a dynamic table name
    in the 'reporting' schema.
    """
    table_name = f'bounds_pilot_{suffix}'

    if table_name in _dynamic_bounds_table_cache:
        return _dynamic_bounds_table_cache[table_name]

    # Dynamically create the class
    class DynamicBoundsTable(Base):
        __tablename__ = table_name
        __table_args__ = (
            PrimaryKeyConstraint('room_id', 'metric_id', 'season'),
            {'schema': 'reporting'}  # Move the schema dictionary outside the tuple
        )

        room_id = Column(Integer, primary_key=True)
        metric_id = Column(Integer, primary_key=True)
        season = Column(Integer, primary_key=True)
        lower_bound = Column(Float)
        upper_bound = Column(Float)

    # Cache the class for reuse
    _dynamic_bounds_table_cache[table_name] = DynamicBoundsTable

    return DynamicBoundsTable

##################### Measurements #####################

def get_todays_measurements(
    db: Session,
    suffix: int,
    date: datetime,
    virtual_sensor_id: Union[List[int], int]
) -> List:
    """
    Returns the records for the specified sensors from the dynamically created table for the given date.

    :param db: A sqlalchemy.orm.session.Session object.
    :param suffix: The suffix used to generate the dynamic table name.
    :param date: The date for which to retrieve records.
    :param virtual_sensor_id: A single sensor ID or a list of sensor IDs to fetch records for.
    :return: A list of records filtered by sensor IDs and the given date.
    """
    # Create the dynamic MeasurementsTable class using the given suffix
    MeasurementsTable = dynamic_measurement_table(suffix)

    # Define the start and end of the specified date
    date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_end = date_start + timedelta(days=1)

    # Convert sensor_ids to a list if it’s a single value
    if isinstance(virtual_sensor_id, int):
        virtual_sensor_id = [virtual_sensor_id]

    # Query the table for the specified sensor IDs and the given date
    return (
        db.query(MeasurementsTable)
        .filter(MeasurementsTable.virtual_sensor_id.in_(virtual_sensor_id))
        .filter(MeasurementsTable.timestamp >= date_start)  # Assuming 'timestamp' is the column name
        .filter(MeasurementsTable.timestamp < date_end)
        .all()
    )

_measurement_table_cache = {}


def dynamic_measurement_table(suffix: int) -> object:
    """
    Factory function to create a HistoryTable class with a dynamic table name
    in the 'reporting' schema.
    """

    table_name = f"measurements_pilot_{suffix}"

    if table_name in _measurement_table_cache:
        return _measurement_table_cache[table_name]

    class MeasurementsTable(Base):
        __tablename__ = f'measurements_pilot_{suffix}'  # Table name is dynamically set
        __table_args__ = (
            {'schema': 'reporting'}
        )

        virtual_sensor_id = Column(Integer, primary_key=True)
        timestamp = Column(DateTime, primary_key=True)  # Changed to DateTime
        value = Column(Float)

    _measurement_table_cache[table_name] = MeasurementsTable
    return MeasurementsTable

##################### Measurements For Period #####################

def get_measurements_for_period(
    db: Session,
    suffix: int,
    date_from: str,
    date_to: str,
    virtual_sensor_id: Union[List[int], int]
) -> List:
    """
    Returns the records for the specified sensors from the dynamically created table for the given date range.

    :param db: A sqlalchemy.orm.session.Session object.
    :param suffix: The suffix used to generate the dynamic table name.
    :param date_from: The start date for the range.
    :param date_to: The end date for the range.
    :param virtual_sensor_id: A single sensor ID or a list of sensor IDs to fetch records for.
    :return: A list of records filtered by sensor IDs and the given date range.
    """

    date_from = datetime.strptime(date_from, "%Y-%m-%d")
    date_to = datetime.strptime(date_to, "%Y-%m-%d")

    date_from = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
    date_to = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Create the dynamic MeasurementsTable class using the given suffix
    MeasurementsTable = dynamic_measurement_table(suffix)

    # Convert sensor_ids to a list if it’s a single value
    if isinstance(virtual_sensor_id, int):
        virtual_sensor_id = [virtual_sensor_id]

    # Query the table for the specified sensor IDs and the given date range
    return (
        db.query(MeasurementsTable)
        .filter(MeasurementsTable.virtual_sensor_id.in_(virtual_sensor_id))
        .filter(MeasurementsTable.timestamp >= date_from)  # Filter records after date_from
        .filter(MeasurementsTable.timestamp <= date_to)  # Filter records before date_to
        .all()
    )
