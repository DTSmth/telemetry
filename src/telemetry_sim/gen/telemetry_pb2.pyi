from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GpsFix(_message.Message):
    __slots__ = ("latitude_deg", "longitude_deg", "altitude_m")
    LATITUDE_DEG_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_DEG_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_M_FIELD_NUMBER: _ClassVar[int]
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    def __init__(self, latitude_deg: _Optional[float] = ..., longitude_deg: _Optional[float] = ..., altitude_m: _Optional[float] = ...) -> None: ...

class Imu(_message.Message):
    __slots__ = ("accel_x_mps2", "accel_y_mps2", "accel_z_mps2", "gyro_x_dps", "gyro_y_dps", "gyro_z_dps")
    ACCEL_X_MPS2_FIELD_NUMBER: _ClassVar[int]
    ACCEL_Y_MPS2_FIELD_NUMBER: _ClassVar[int]
    ACCEL_Z_MPS2_FIELD_NUMBER: _ClassVar[int]
    GYRO_X_DPS_FIELD_NUMBER: _ClassVar[int]
    GYRO_Y_DPS_FIELD_NUMBER: _ClassVar[int]
    GYRO_Z_DPS_FIELD_NUMBER: _ClassVar[int]
    accel_x_mps2: float
    accel_y_mps2: float
    accel_z_mps2: float
    gyro_x_dps: float
    gyro_y_dps: float
    gyro_z_dps: float
    def __init__(self, accel_x_mps2: _Optional[float] = ..., accel_y_mps2: _Optional[float] = ..., accel_z_mps2: _Optional[float] = ..., gyro_x_dps: _Optional[float] = ..., gyro_y_dps: _Optional[float] = ..., gyro_z_dps: _Optional[float] = ...) -> None: ...

class TelemetryFrame(_message.Message):
    __slots__ = ("vehicle_id", "sequence", "timestamp_ns", "gps", "speed_mps", "imu")
    VEHICLE_ID_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_NS_FIELD_NUMBER: _ClassVar[int]
    GPS_FIELD_NUMBER: _ClassVar[int]
    SPEED_MPS_FIELD_NUMBER: _ClassVar[int]
    IMU_FIELD_NUMBER: _ClassVar[int]
    vehicle_id: str
    sequence: int
    timestamp_ns: int
    gps: GpsFix
    speed_mps: float
    imu: Imu
    def __init__(self, vehicle_id: _Optional[str] = ..., sequence: _Optional[int] = ..., timestamp_ns: _Optional[int] = ..., gps: _Optional[_Union[GpsFix, _Mapping]] = ..., speed_mps: _Optional[float] = ..., imu: _Optional[_Union[Imu, _Mapping]] = ...) -> None: ...

class UploadBatch(_message.Message):
    __slots__ = ("batch_id", "vehicle_id", "created_at_ns", "frames")
    BATCH_ID_FIELD_NUMBER: _ClassVar[int]
    VEHICLE_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_NS_FIELD_NUMBER: _ClassVar[int]
    FRAMES_FIELD_NUMBER: _ClassVar[int]
    batch_id: str
    vehicle_id: str
    created_at_ns: int
    frames: _containers.RepeatedCompositeFieldContainer[TelemetryFrame]
    def __init__(self, batch_id: _Optional[str] = ..., vehicle_id: _Optional[str] = ..., created_at_ns: _Optional[int] = ..., frames: _Optional[_Iterable[_Union[TelemetryFrame, _Mapping]]] = ...) -> None: ...
