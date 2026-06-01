import json
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/openai_realtime_events.json")
README_PATH = Path("tests/fixtures/openai_realtime_events.README.md")


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_openai_realtime_fixture_covers_required_event_families() -> None:
    fixture = load_fixture()
    event_types = {event["type"] for event in fixture["server_events"]}
    client_event_types = {event["type"] for event in fixture["client_events"]}

    assert "response.output_audio_transcript.delta" in event_types
    assert "response.output_audio_transcript.done" in event_types
    assert "conversation.item.input_audio_transcription.segment" in event_types
    assert "conversation.item.done" in event_types
    assert "response.function_call_arguments.done" in event_types
    assert "response.done" in event_types
    assert "error" in event_types
    assert "conversation.item.create" in client_event_types
    assert "response.create" in client_event_types


def test_openai_realtime_fixture_records_source_and_retrieval_date() -> None:
    fixture = load_fixture()
    readme = README_PATH.read_text(encoding="utf-8")

    assert fixture["retrieved_at"] == "2026-05-31"
    assert "https://developers.openai.com/api/reference/resources/realtime" in readme
    assert "retrieved 2026-05-31" in readme
