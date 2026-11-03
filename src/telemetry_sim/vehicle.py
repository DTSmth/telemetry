"""A simulated vehicle that drives around and emits telemetry frames."""

import math
import random
from dataclasses import dataclass, field

from telemetry_sim.gen import telemetry_pb2 as pb

EARTH_RADIUS_M = 6_371_000.0
GRAVITY_MPS2 = 9.81
NS_PER_S = 1_000_000_000


@dataclass
class SimulatedVehicle:
    """Holds one vehicle's state and advances it one time step at a time."""

    vehicle_id: str
    rng: random.Random
    latitude_deg: float = 35.2271  # Charlotte, NC
    longitude_deg: float = -80.8431
    heading_deg: float = 0.0
    speed_mps: float = 13.0  # about 29 mph
    sequence: int = 0
    _last_speed_mps: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._last_speed_mps = self.speed_mps

    def step(self, timestamp_ns: int, dt_s: float) -> pb.TelemetryFrame:
        """Move the vehicle forward by dt_s seconds and return a frame describing it."""
        # Drift speed gently and keep it within normal city/highway limits.
        self.speed_mps = min(35.0, max(0.0, self.speed_mps + self.rng.gauss(0, 0.5)))
        # Turn a little, now and then a lot (a corner).
        turn_deg = self.rng.gauss(0, 1.0)
        if self.rng.random() < 0.01:
            turn_deg += self.rng.choice([-90.0, 90.0])
        self.heading_deg = (self.heading_deg + turn_deg) % 360

        # Convert distance travelled into a change in latitude and longitude.
        distance_m = self.speed_mps * dt_s
        heading_rad = math.radians(self.heading_deg)
        dlat = (distance_m * math.cos(heading_rad)) / EARTH_RADIUS_M
        dlon = (distance_m * math.sin(heading_rad)) / (
            EARTH_RADIUS_M * math.cos(math.radians(self.latitude_deg))
        )
        self.latitude_deg += math.degrees(dlat)
        self.longitude_deg += math.degrees(dlon)

        forward_accel = (self.speed_mps - self._last_speed_mps) / dt_s
        self._last_speed_mps = self.speed_mps

        frame = pb.TelemetryFrame(
            vehicle_id=self.vehicle_id,
            sequence=self.sequence,
            timestamp_ns=timestamp_ns,
            gps=pb.GpsFix(
                latitude_deg=self.latitude_deg,
                longitude_deg=self.longitude_deg,
                altitude_m=230.0,
            ),
            speed_mps=self.speed_mps,
            imu=pb.Imu(
                accel_x_mps2=forward_accel,
                accel_y_mps2=self.rng.gauss(0, 0.2),
                accel_z_mps2=GRAVITY_MPS2 + self.rng.gauss(0, 0.05),
                gyro_z_dps=turn_deg / dt_s,
            ),
        )
        self.sequence += 1
        return frame


def make_fleet(count: int, rng: random.Random) -> list[SimulatedVehicle]:
    """Create `count` vehicles with different starting headings and speeds."""
    return [
        SimulatedVehicle(
            vehicle_id=f"AV-{i:04d}",
            rng=random.Random(rng.getrandbits(32)),
            heading_deg=rng.uniform(0, 360),
            speed_mps=rng.uniform(8, 25),
        )
        for i in range(count)
    ]