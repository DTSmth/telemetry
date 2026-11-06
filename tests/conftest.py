"""Shared pytest fixtures. Any test can ask for these by naming them as a parameter."""

import random

import pytest

from telemetry_sim.gen import telemetry_pb2 as pb
from telemetry_sim.vehicle import SimulatedVehicle

START_NS = 1_800_000_000_000_000_000  # a fixed time so tests are repeatable


@pytest.fixture
def rng() -> random.Random:
    return random.Random(1234)


@pytest.fixture
def sample_batch(rng: random.Random) -> pb.UploadBatch:
    """A clean batch of 100 frames (10 seconds at 10 Hz) from one vehicle."""
    vehicle = SimulatedVehicle(vehicle_id="AV-TEST", rng=rng)
    frames = [vehicle.step(START_NS + i * 100_000_000, 0.1) for i in range(100)]
    return pb.UploadBatch(
        batch_id="AV-TEST-00000",
        vehicle_id="AV-TEST",
        created_at_ns=frames[-1].timestamp_ns,
        frames=frames,
    )
