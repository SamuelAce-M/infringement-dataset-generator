"""Tests for experimental WIPO export."""
import csv
import json
from src.wipo import WipoInspectReport
from src.wipo_export import export_wipo_manifest, write_wipo_export_report


def test_wipo_export_blocks_without_acknowledgement(tmp_path, monkeypatch):
    output = tmp_path / "manifest.csv"

    result = export_wipo_manifest("cup", str(output), acknowledge_limits=False)

    assert not result.ok
    assert any("--acknowledge-limits" in blocker for blocker in result.blockers)
    with open(output, newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [["registry_id", "image_path"]]


def test_wipo_export_reports_qz_blocker(tmp_path, monkeypatch):
    from src import wipo_export as wipo_export_module

    inspect = WipoInspectReport(
        url="https://designdb.wipo.int/designdb/en/",
        ok=True,
        status_code=200,
        qk_present=True,
        qk="abc",
        endpoints=["https://designdb.wipo.int/designdb/jsp/select.jsp"],
        search_fields=["PROD"],
        usage_warnings=["Search requests use compressed qz state; direct q= queries return INVALID_INPUT."],
    )
    monkeypatch.setattr(wipo_export_module, "inspect_wipo", lambda timeout: inspect)

    output = tmp_path / "manifest.csv"
    result = export_wipo_manifest("cup", str(output), acknowledge_limits=True)

    assert not result.ok
    assert any("compressed qz" in blocker for blocker in result.blockers)


def test_write_wipo_export_report(tmp_path):
    output = tmp_path / "manifest.csv"
    report_path = tmp_path / "report.json"
    result = export_wipo_manifest("cup", str(output), acknowledge_limits=False)

    write_wipo_export_report(result, str(report_path))

    payload = json.loads(report_path.read_text())
    assert payload["report"]["keyword"] == "cup"
