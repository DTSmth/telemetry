
# Vehicle Telemetry Pipeline

A simulated vehicle fleet that emits Protobuf telemetry with injectable faults, built as the first stage of a fleet data pipeline.

## Quick start

```bash
pip install -e ".[dev]"
python -m grpc_tools.protoc -I proto --python_out=src/telemetry_sim/gen --pyi_out=src/telemetry_sim/gen proto/telemetry.proto
pytest
simulate --vehicles 5 --duration 60 --drop-rate 0.01 --corrupt-rate 0.1
```

## Output

- `out/batches/*.pb` — one Protobuf `UploadBatch` per file
- `out/manifest.jsonl` — one line per batch: checksum, frame count, upload delay
- `out/ground_truth.jsonl` — every injected fault, by batch
