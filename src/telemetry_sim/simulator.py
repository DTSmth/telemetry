"""Runs the fleet: drives every vehicle, groups frames into batches, injects faults,
and writes batches, a manifest, and the ground-truth fault log to disk."""

import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from telemetry_sim.faults import FaultConfig, FaultInjector
from telemetry_sim.gen import telemetry_pb2 as pb
from telemetry_sim.vehicle import NS_PER_S, make_fleet


@dataclass(frozen=True)
class SimConfig:
    vehicles: int = 5
    duration_s: int = 60
    hz: int = 10  # frames per second per vehicle
    batch_seconds: int = 10  # each upload batch covers this many seconds
    seed: int = 42
    start_ns: int | None = None  # simulation start time; defaults to now
    faults: FaultConfig = field(default_factory=FaultConfig)


@dataclass
class SimSummary:
    batches: int = 0
    frames: int = 0
    faults: dict[str, int] = field(default_factory=dict)


def run_simulation(config: SimConfig, out_dir: Path) -> SimSummary:
    """Simulate the whole run instantly (simulated time, no sleeping)."""
    rng = random.Random(config.seed)
    fleet = make_fleet(config.vehicles, rng)
    injector = FaultInjector(config.faults, random.Random(rng.getrandbits(32)))
    start_ns = config.start_ns if config.start_ns is not None else time.time_ns()
    dt_s = 1 / config.hz
    frames_per_batch = config.hz * config.batch_seconds
    total_frames = config.hz * config.duration_s

    batch_dir = out_dir / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    summary = SimSummary()

    with (
        open(out_dir / "manifest.jsonl", "w") as manifest,
        open(out_dir / "ground_truth.jsonl", "w") as ground_truth,
    ):
        for vehicle in fleet:
            for batch_index, first in enumerate(range(0, total_frames, frames_per_batch)):
                count = min(frames_per_batch, total_frames - first)
                frames = [
                    vehicle.step(start_ns + int((first + i) * dt_s * NS_PER_S), dt_s)
                    for i in range(count)
                ]
                batch = pb.UploadBatch(
                    batch_id=f"{vehicle.vehicle_id}-{batch_index:05d}",
                    vehicle_id=vehicle.vehicle_id,
                    created_at_ns=frames[-1].timestamp_ns,
                    frames=frames,
                )

                result = injector.apply(batch)

                file_name = f"{batch.batch_id}.pb"
                (batch_dir / file_name).write_bytes(result.payload)
                manifest.write(
                    json.dumps(
                        {
                            "batch_id": batch.batch_id,
                            "vehicle_id": batch.vehicle_id,
                            "file": f"batches/{file_name}",
                            "created_at_ns": batch.created_at_ns,
                            "frames_recorded": count,
                            "crc32": result.checksum,
                            "upload_delay_s": result.upload_delay_s,
                        }
                    )
                    + "\n"
                )
                for fault in result.faults:
                    ground_truth.write(json.dumps(asdict(fault)) + "\n")
                    summary.faults[fault.fault] = summary.faults.get(fault.fault, 0) + 1

                summary.batches += 1
                summary.frames += count

    return summary
