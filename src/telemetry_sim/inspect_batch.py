"""Print a summary of one batch file: `python -m telemetry_sim.inspect_batch out/batches/X.pb`."""

import sys
from pathlib import Path

from google.protobuf.message import DecodeError

from telemetry_sim.gen import telemetry_pb2 as pb


def main() -> None:
    path = Path(sys.argv[1])
    batch = pb.UploadBatch()
    try:
        batch.ParseFromString(path.read_bytes())
    except DecodeError as exc:
        print(f"{path.name}: could not decode ({exc}) - probably corrupted")
        return

    print(f"batch {batch.batch_id}  vehicle {batch.vehicle_id}  frames {len(batch.frames)}")
    for frame in batch.frames[:3]:
        print(
            f"  seq={frame.sequence} t={frame.timestamp_ns} "
            f"lat={frame.gps.latitude_deg:.5f} lon={frame.gps.longitude_deg:.5f} "
            f"speed={frame.speed_mps:.1f} m/s"
        )
    if len(batch.frames) > 3:
        print(f"  ... {len(batch.frames) - 3} more")


if __name__ == "__main__":
    main()
