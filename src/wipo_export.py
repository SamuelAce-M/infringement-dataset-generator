"""Experimental WIPO manifest export.

This module intentionally fails visible until WIPO's compressed qz search state
and image URL extraction are implemented and reviewed.
"""
import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.wipo import WipoInspectReport, inspect_wipo


@dataclass
class WipoExportReport:
    keyword: str
    limit: int
    output_manifest: str
    ok: bool
    exported_count: int = 0
    blockers: list[str] = field(default_factory=list)
    inspect: dict | None = None


def export_wipo_manifest(
    keyword: str,
    output_manifest: str,
    limit: int = 5,
    timeout: float = 10.0,
    acknowledge_limits: bool = False,
) -> WipoExportReport:
    """Attempt to export a WIPO registry URL manifest.

    Current implementation performs source inspection and writes a header-only
    manifest when export is blocked. It does not scrape records.
    """
    _write_registry_header(output_manifest)
    inspect_report = inspect_wipo(timeout=timeout)
    report = WipoExportReport(
        keyword=keyword,
        limit=limit,
        output_manifest=output_manifest,
        ok=False,
        inspect=asdict(inspect_report),
    )

    if not acknowledge_limits:
        report.blockers.append(
            "WIPO export requires --acknowledge-limits because the WIPO UI warns against automatic retrieval."
        )
        return report

    _add_inspect_blockers(report, inspect_report)
    if not report.blockers:
        report.blockers.append(
            "WIPO qz search-state generation and image URL extraction are not implemented yet."
        )
    return report


def write_wipo_export_report(report: WipoExportReport, output_path: str) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": asdict(report),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _write_registry_header(output_manifest: str) -> None:
    path = Path(output_manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["registry_id", "image_path"])


def _add_inspect_blockers(report: WipoExportReport, inspect_report: WipoInspectReport) -> None:
    if not inspect_report.ok:
        report.blockers.append(f"WIPO inspect failed: {inspect_report.error}")
        return
    if not inspect_report.qk_present:
        report.blockers.append("WIPO qk token was not found.")
    if "https://designdb.wipo.int/designdb/jsp/select.jsp" not in inspect_report.endpoints:
        report.blockers.append("WIPO select.jsp endpoint was not found.")
    if any("compressed qz" in warning for warning in inspect_report.usage_warnings):
        report.blockers.append("WIPO search uses compressed qz state; direct q= requests are invalid.")
