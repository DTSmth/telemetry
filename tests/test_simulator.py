"""End-to-end: run the simulator into a temporary folder and check what it wrote."""

import json
from pathlib import Path

from telemetry_sim.cli import main
from telemetry_sim.faults import FaultConfig
from telemetry_sim.gen import telemetry_pb2 as pb
from telemetry_sim.simulator import SimConfig, run_simulation

START_NS = 1_800_000_000_000_000_000


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_clean_run_writes_expected_batches(tmp_path):
    config = SimConfig(vehicles=3, duration_s=30, hz=10, batch_seconds=10, start_ns=START_NS)

    summary = run_simulation(config, tmp_path)

    manifest = read_jsonl(tmp_path / "manifest.jsonl")
    assert summary.batches == 9  # 3 vehicles x 3 batches of 10 s
    assert summary.frames == 900
    assert len(manifest) == 9
    assert (tmp_path / "ground_truth.jsonl").read_text() == ""

    first = manifest[0]
    batch = pb.UploadBatch()
    batch.ParseFromString((tmp_path / first["file"]).read_bytes())
    assert batch.batch_id == first["batch_id"] == "AV-0000-00000"
    assert len(batch.frames) == 100


def test_same_seed_gives_identical_output(tmp_path):
    faults = FaultConfig(drop_rate=0.05, corrupt_rate=0.3, delay_rate=0.3)
    config = SimConfig(vehicles=2, duration_s=20, seed=99, start_ns=START_NS, faults=faults)

    run_simulation(config, tmp_path / "a")
    run_simulation(config, tmp_path / "b")

    for name in ("manifest.jsonl", "ground_truth.jsonl"):
        assert (tmp_path / "a" / name).read_text() == (tmp_path / "b" / name).read_text()


def test_ground_truth_points_at_real_batches(tmp_path):
    faults = FaultConfig(drop_rate=0.05, clock_skew_rate=0.5, corrupt_rate=0.5)
    config = SimConfig(vehicles=4, duration_s=60, start_ns=START_NS, faults=faults)

    run_simulation(config, tmp_path)

    batch_ids = {row["batch_id"] for row in read_jsonl(tmp_path / "manifest.jsonl")}
    truth = read_jsonl(tmp_path / "ground_truth.jsonl")
    assert truth, "with these rates some faults must be recorded"
    assert all(row["batch_id"] in batch_ids for row in truth)


def test_cli_runs(tmp_path, caplog):
    caplog.set_level("INFO")

    main(["--vehicles", "2", "--duration", "20", "--out", str(tmp_path), "--drop-rate", "0.1"])

    assert (tmp_path / "manifest.jsonl").exists()
    assert "wrote 4 batches" in caplog.text
