"""Fault injection: deliberately break batches the way real fleets break them.

Every fault applied is returned as a FaultRecord, so we always know the
ground truth of what went wrong in each batch.
"""

import random
import zlib
from dataclasses import dataclass, field
from enum import StrEnum

from telemetry_sim.gen import telemetry_pb2 as pb

NS_PER_S = 1_000_000_000


class FaultType(StrEnum):
    DROPPED_FRAMES = "dropped_frames"
    DUPLICATE_FRAMES = "duplicate_frames"
    OUT_OF_RANGE = "out_of_range"
    CLOCK_SKEW = "clock_skew"
    CORRUPT_PAYLOAD = "corrupt_payload"
    DELAYED_UPLOAD = "delayed_upload"


@dataclass(frozen=True)
class FaultConfig:
    """Probabilities for each fault. Frame faults are per frame; the rest per batch."""

    drop_rate: float = 0.0
    duplicate_rate: float = 0.0
    out_of_range_rate: float = 0.0
    clock_skew_rate: float = 0.0
    corrupt_rate: float = 0.0
    delay_rate: float = 0.0
    max_clock_skew_s: int = 7200
    max_delay_s: int = 600

    def __post_init__(self) -> None:
        for name in (
            "drop_rate",
            "duplicate_rate",
            "out_of_range_rate",
            "clock_skew_rate",
            "corrupt_rate",
            "delay_rate",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1, got {value}")


@dataclass
class FaultRecord:
    """One fault that was injected into one batch (a line of ground truth)."""

    batch_id: str
    vehicle_id: str
    fault: FaultType
    detail: dict = field(default_factory=dict)


# --- Individual faults. Each is a small function so it can be tested alone. ---


def drop_frames(batch: pb.UploadBatch, rate: float, rng: random.Random) -> list[int]:
    """Remove frames at random, as if they were lost. Returns dropped sequence numbers."""
    kept, dropped = [], []
    for frame in batch.frames:
        if rng.random() < rate:
            dropped.append(frame.sequence)
        else:
            kept.append(frame)
    _replace_frames(batch, kept)
    return dropped


def duplicate_frames(batch: pb.UploadBatch, rate: float, rng: random.Random) -> list[int]:
    """Repeat frames, as a buggy retry would. Returns duplicated sequence numbers."""
    result, duplicated = [], []
    for frame in batch.frames:
        result.append(frame)
        if rng.random() < rate:
            copy = pb.TelemetryFrame()
            copy.CopyFrom(frame)
            result.append(copy)
            duplicated.append(frame.sequence)
    _replace_frames(batch, result)
    return duplicated


def make_out_of_range(batch: pb.UploadBatch, rate: float, rng: random.Random) -> list[int]:
    """Set impossible sensor values, as a faulty sensor would. Returns affected sequences."""
    affected = []
    for frame in batch.frames:
        if rng.random() < rate:
            if rng.random() < 0.5:
                frame.speed_mps = rng.uniform(150, 400)  # far beyond any car's top speed
            else:
                frame.gps.latitude_deg = rng.uniform(91, 180)  # latitude must be -90..90
            affected.append(frame.sequence)
    return affected


def skew_clock(batch: pb.UploadBatch, max_skew_s: int, rng: random.Random) -> int:
    """Shift every timestamp by the same amount, as a drifting clock would."""
    skew_s = rng.choice([-1, 1]) * rng.randint(60, max_skew_s)
    for frame in batch.frames:
        frame.timestamp_ns += skew_s * NS_PER_S
    return skew_s


def corrupt_bytes(payload: bytes, rng: random.Random, count: int = 8) -> tuple[bytes, list[int]]:
    """Overwrite a few random bytes, as a bad transfer would. Returns (payload, positions)."""
    data = bytearray(payload)
    positions = sorted(rng.sample(range(len(data)), k=min(count, len(data))))
    for pos in positions:
        data[pos] = rng.randrange(256)
    return bytes(data), positions


def _replace_frames(batch: pb.UploadBatch, frames: list[pb.TelemetryFrame]) -> None:
    copies = []
    for frame in frames:
        copy = pb.TelemetryFrame()
        copy.CopyFrom(frame)
        copies.append(copy)
    del batch.frames[:]
    batch.frames.extend(copies)


# --- Putting it together ---


@dataclass
class InjectionResult:
    payload: bytes
    checksum: int  # CRC32 of the payload BEFORE any corruption, as the vehicle computed it
    upload_delay_s: int
    faults: list[FaultRecord]


class FaultInjector:
    def __init__(self, config: FaultConfig, rng: random.Random) -> None:
        self.config = config
        self.rng = rng

    def apply(self, batch: pb.UploadBatch) -> InjectionResult:
        """Apply faults to a batch (modified in place) and return the bytes to upload."""
        cfg, rng = self.config, self.rng
        faults: list[FaultRecord] = []

        def record(fault: FaultType, **detail) -> None:
            faults.append(FaultRecord(batch.batch_id, batch.vehicle_id, fault, detail))

        if dropped := drop_frames(batch, cfg.drop_rate, rng):
            record(FaultType.DROPPED_FRAMES, sequences=dropped)
        if duplicated := duplicate_frames(batch, cfg.duplicate_rate, rng):
            record(FaultType.DUPLICATE_FRAMES, sequences=duplicated)
        if affected := make_out_of_range(batch, cfg.out_of_range_rate, rng):
            record(FaultType.OUT_OF_RANGE, sequences=affected)
        if rng.random() < cfg.clock_skew_rate:
            record(FaultType.CLOCK_SKEW, skew_s=skew_clock(batch, cfg.max_clock_skew_s, rng))

        payload = batch.SerializeToString()
        checksum = zlib.crc32(payload)

        if rng.random() < cfg.corrupt_rate:
            payload, positions = corrupt_bytes(payload, rng)
            record(FaultType.CORRUPT_PAYLOAD, byte_positions=positions)

        delay_s = 0
        if rng.random() < cfg.delay_rate:
            delay_s = rng.randint(30, cfg.max_delay_s)
            record(FaultType.DELAYED_UPLOAD, delay_s=delay_s)

        return InjectionResult(
            payload=payload, checksum=checksum, upload_delay_s=delay_s, faults=faults
        )