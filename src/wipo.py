"""Experimental WIPO Global Design Database inspection."""
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests


WIPO_DESIGNDB_URL = "https://designdb.wipo.int/designdb/en/"


@dataclass
class WipoInspectReport:
    url: str
    ok: bool
    status_code: int | None
    qk_present: bool
    qk: str
    scripts: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    search_fields: list[str] = field(default_factory=list)
    usage_warnings: list[str] = field(default_factory=list)
    error: str = ""


def inspect_wipo(
    url: str = WIPO_DESIGNDB_URL,
    timeout: float = 10.0,
    session: requests.Session | None = None,
) -> WipoInspectReport:
    """Inspect WIPO DesignDB frontend wiring without scraping search results."""
    http = session or requests.Session()
    http.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        response = http.get(url, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        return WipoInspectReport(
            url=url,
            ok=False,
            status_code=None,
            qk_present=False,
            qk="",
            error=str(exc),
        )

    html = response.text
    scripts = _extract_scripts(html, response.url)
    qk = _extract_qk(html)
    report = WipoInspectReport(
        url=response.url,
        ok=True,
        status_code=response.status_code,
        qk_present=bool(qk),
        qk=qk,
        scripts=scripts,
    )

    for script_url in scripts:
        if not _is_designdb_script(script_url):
            continue
        try:
            script_response = http.get(script_url, timeout=timeout)
            if script_response.status_code != 200:
                continue
            _merge_script_findings(report, script_response.text)
        except Exception as exc:
            report.usage_warnings.append(f"Failed to inspect script {script_url}: {exc}")

    report.endpoints = sorted(set(report.endpoints))
    report.search_fields = sorted(set(report.search_fields))
    report.usage_warnings = sorted(set(report.usage_warnings))
    return report


def write_wipo_inspect_report(report: WipoInspectReport, output_path: str) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": asdict(report),
        "recommendation": (
            "Implement WIPO export as an explicit, low-volume adapter only after qz "
            "state compression and image URL extraction are verified. Do not use it "
            "as an uncontrolled bulk crawler."
        ),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _extract_qk(html: str) -> str:
    match = re.search(r"var\s+qk\s*=\s*['\"]([^'\"]+)['\"]", html)
    return match.group(1) if match else ""


def _extract_scripts(html: str, base_url: str) -> list[str]:
    scripts = re.findall(r"<script[^>]+src=['\"]([^'\"]+)", html, flags=re.I)
    return [urljoin(base_url, script) for script in scripts]


def _is_designdb_script(script_url: str) -> bool:
    return "/designdb/" in script_url and script_url.endswith(".js")


def _merge_script_findings(report: WipoInspectReport, script_text: str) -> None:
    if "solrUrl" in script_text and "select.jsp" in script_text:
        report.endpoints.append("https://designdb.wipo.int/designdb/jsp/select.jsp")
    if "qk.jsp" in script_text:
        report.endpoints.append("https://designdb.wipo.int/designdb/jsp/qk.jsp")
    if "compressRequest:true" in script_text:
        report.usage_warnings.append("Search requests use compressed qz state; direct q= queries return INVALID_INPUT.")
    if "automatic retrieval of data from our system is specifically forbidden" in script_text:
        report.usage_warnings.append(
            "WIPO UI text warns that automatic retrieval is forbidden; keep adapters low-volume and user-controlled."
        )

    for field in re.findall(r'fie:\s*["\']([A-Z_]+)["\']', script_text):
        report.search_fields.append(field)
