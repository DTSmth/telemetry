"""Command-line entry point: `simulate --vehicles 5 --duration 60`."""

import argparse
import logging
from pathlib import Path

from telemetry_sim.faults import FaultConfig
from telemetry_sim.simulator import SimConfig, run_simulation

log = logging.getLogger("telemetry_sim")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simulate a fleet of vehicles emitting telemetry.")
    p.add_argument("--vehicles", type=int, default=5, help="number of vehicles")
    p.add_argument("--duration", type=int, default=60, help="seconds of driving to simulate")
    p.add_argument("--hz", type=int, default=10, help="frames per second per vehicle")
    p.add_argument("--batch-seconds", type=int, default=10, help="seconds of data per batch")
    p.add_argument("--seed", type=int, default=42, help="random seed (same seed = same output)")
    p.add_argument("--out", type=Path, default=Path("out"), help="output directory")

    f = p.add_argument_group("fault injection (probabilities from 0 to 1)")
    f.add_argument("--drop-rate", type=float, default=0.0, help="per frame")
    f.add_argument("--duplicate-rate", type=float, default=0.0, help="per frame")
    f.add_argument("--out-of-range-rate", type=float, default=0.0, help="per frame")
    f.add_argument("--clock-skew-rate", type=float, default=0.0, help="per batch")
    f.add_argument("--corrupt-rate", type=float, default=0.0, help="per batch")
    f.add_argument("--delay-rate", type=float, default=0.0, help="per batch")
    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    config = SimConfig(
        vehicles=args.vehicles,
        duration_s=args.duration,
        hz=args.hz,
        batch_seconds=args.batch_seconds,
        seed=args.seed,
        faults=FaultConfig(
            drop_rate=args.drop_rate,
            duplicate_rate=args.duplicate_rate,
            out_of_range_rate=args.out_of_range_rate,
            clock_skew_rate=args.clock_skew_rate,
            corrupt_rate=args.corrupt_rate,
            delay_rate=args.delay_rate,
        ),
    )
    summary = run_simulation(config, args.out)

    log.info("wrote %d batches (%d frames) to %s", summary.batches, summary.frames, args.out)
    for fault, count in sorted(summary.faults.items()):
        log.info("  %s: %d batches", fault, count)


if __name__ == "__main__":
    main()
