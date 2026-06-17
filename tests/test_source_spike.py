"""Tests for source spike probing."""
import json
from src.source_spike import run_source_spike, write_source_spike_report


class FakeResponse:
    status_code = 200
    headers = {"content-type": "text/html"}


class FakeSession:
    def get(self, url, timeout):
        return FakeResponse()


def test_run_source_spike_with_fake_session():
    results = run_source_spike(timeout=1, session=FakeSession())

    assert results
    assert all(result.ok for result in results)


def test_write_source_spike_report(tmp_path):
    results = run_source_spike(timeout=1, session=FakeSession())
    output = tmp_path / "report.json"

    write_source_spike_report(results, str(output))

    payload = json.loads(output.read_text())
    assert "generated_at" in payload
    assert len(payload["results"]) == len(results)
