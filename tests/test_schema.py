"""The schema round-trip: what goes into bytes must come back out unchanged."""

from telemetry_sim.gen import telemetry_pb2 as pb


def test_batch_round_trip(sample_batch: pb.UploadBatch) -> None:
    data = sample_batch.SerializeToString()

    decoded = pb.UploadBatch()
    decoded.ParseFromString(data)

    assert decoded == sample_batch
    assert len(decoded.frames) == 100
    assert decoded.frames[0].vehicle_id == "AV-TEST"


def test_binary_is_smaller_than_text(sample_batch: pb.UploadBatch) -> None:
    """A talking point: binary Protobuf is far more compact than a text format."""
    binary_size = len(sample_batch.SerializeToString())
    text_size = len(str(sample_batch).encode())
    assert binary_size < text_size / 2


def test_sequences_increase_by_one(sample_batch: pb.UploadBatch) -> None:
    sequences = [f.sequence for f in sample_batch.frames]
    assert sequences == list(range(100))


def test_unknown_fields_are_ignored() -> None:
    """Schema evolution: an old reader can parse data from a newer writer.

    Field number 99 doesn't exist in our schema, so the parser must skip it.
    """
    frame = pb.TelemetryFrame(vehicle_id="AV-1", sequence=7)
    extra_field = bytes([0x98, 0x06, 0x01])  # field 99, varint, value 1
    decoded = pb.TelemetryFrame()
    decoded.ParseFromString(frame.SerializeToString() + extra_field)
    assert decoded.vehicle_id == "AV-1"
    assert decoded.sequence == 7