"""One test per fault type, plus the injector that combines them."""

import random
import zlib

import pytest

from telemetry_sim.faults import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_bytes,
    drop_frames,
    duplicate_frames,
    make_out_of_range,
    skew_clock,
)
from telemetry_sim.gen import telemetry_pb2 as pb


def test_drop_frames_removes_exactly_the_reported_frames(sample_batch, rng):
    before = [f.sequence for f in sample_batch.frames]

    dropped = drop_frames(sample_batch, rate=0.2, rng=rng)

    after = [f.sequence for f in sample_batch.frames]
    assert dropped, "with a 20% rate over 100 frames, something should drop"
    assert sorted(after + dropped) == before


def test_duplicate_frames_repeats_reported_frames(sample_batch, rng):
    duplicated = duplicate_frames(sample_batch, rate=0.1, rng=rng)

    sequences = [f.sequence for f in sample_batch.frames]
    assert len(sequences) == 100 + len(duplicated)
    for seq in duplicated:
        assert sequences.count(seq) == 2


def test_out_of_range_values_are_physically_impossible(sample_batch, rng):
    affected = make_out_of_range(sample_batch, rate=0.1, rng=rng)

    assert affected
    for frame in sample_batch.frames:
        broken = frame.speed_mps > 100 or abs(frame.gps.latitude_deg) > 90
        assert broken == (frame.sequence in affected)


def test_skew_clock_shifts_every_timestamp_equally(sample_batch, rng):
    before = [f.timestamp_ns for f in sample_batch.frames]

    skew_s = skew_clock(sample_batch, max_skew_s=3600, rng=rng)

    after = [f.timestamp_ns for f in sample_batch.frames]
    assert 60 <= abs(skew_s) <= 3600
    assert all(a - b == skew_s * 1_000_000_000 for a, b in zip(after, before, strict=True))


def test_corrupt_bytes_changes_payload_and_breaks_checksum(sample_batch, rng):
    payload = sample_batch.SerializeToString()

    corrupted, positions = corrupt_bytes(payload, rng)

    assert len(corrupted) == len(payload)
    assert len(positions) == 8
    assert zlib.crc32(corrupted) != zlib.crc32(payload)


def test_no_faults_by_default(sample_batch, rng):
    original = sample_batch.SerializeToString()

    result = FaultInjector(FaultConfig(), rng).apply(sample_batch)

    assert result.faults == []
    assert result.payload == original
    assert result.upload_delay_s == 0


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (FaultConfig(drop_rate=0.5), FaultType.DROPPED_FRAMES),
        (FaultConfig(duplicate_rate=0.5), FaultType.DUPLICATE_FRAMES),
        (FaultConfig(out_of_range_rate=0.5), FaultType.OUT_OF_RANGE),
        (FaultConfig(clock_skew_rate=1.0), FaultType.CLOCK_SKEW),
        (FaultConfig(corrupt_rate=1.0), FaultType.CORRUPT_PAYLOAD),
        (FaultConfig(delay_rate=1.0), FaultType.DELAYED_UPLOAD),
    ],
)
def test_injector_records_each_fault(sample_batch, config, expected):
    result = FaultInjector(config, random.Random(7)).apply(sample_batch)

    assert [f.fault for f in result.faults] == [expected]
    assert result.faults[0].batch_id == "AV-TEST-00000"


def test_checksum_is_of_the_clean_payload(sample_batch):
    result = FaultInjector(FaultConfig(corrupt_rate=1.0), random.Random(7)).apply(sample_batch)

    assert result.checksum == zlib.crc32(sample_batch.SerializeToString())
    assert result.checksum != zlib.crc32(result.payload)


def test_invalid_rate_is_rejected():
    with pytest.raises(ValueError, match="drop_rate"):
        FaultConfig(drop_rate=1.5)


def test_payload_is_still_a_valid_batch_when_not_corrupted(sample_batch):
    result = FaultInjector(FaultConfig(drop_rate=0.3), random.Random(7)).apply(sample_batch)

    decoded = pb.UploadBatch()
    decoded.ParseFromString(result.payload)
    assert len(decoded.frames) < 100
