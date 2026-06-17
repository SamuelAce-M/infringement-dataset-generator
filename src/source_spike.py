"""Patent source probing for online dataset import."""
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import requests


DEFAULT_SOURCES = [
    {
        "name": "WIPO Global Design Database",
        "url": "https://designdb.wipo.int/designdb/en/",
        "notes": "Public web UI for industrial design records; API stability must be verified separately.",
    },
    {
        "name": "CNIPA legacy publication endpoint",
        "url": "http://epub.sipo.gov.cn/",
        "notes": "Legacy CNIPA endpoint used by older examples; availability may vary.",
    },
]


@dataclass
class SourceProbeResult:
    name: str
    url: str
    ok: bool
    status_code: int | None
    content_type: str
    error: str
    notes: str


def run_source_spike(timeout: float = 10.0, session: requests.Session | None = None) -> list[SourceProbeResult]:
    """Probe candidate patent/design data sources."""
    http = session or requests.Session()
    return [_probe_source(http, source, timeout) for source in DEFAULT_SOURCES]


def write_source_spike_report(
    results: list[SourceProbeResult],
    output_path: str,
) -> None:
    """Write a JSON probe report."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": [asdict(result) for result in results],
        "recommendation": (
            "Use local or URL manifests for production imports until a source has a stable "
            "record search and image download adapter."
        ),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _probe_source(
    session: requests.Session,
    source: dict[str, str],
    timeout: float,
) -> SourceProbeResult:
    try:
        response = session.get(source["url"], timeout=timeout)
        return SourceProbeResult(
            name=source["name"],
            url=source["url"],
            ok=200 <= response.status_code < 400,
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            error="",
            notes=source["notes"],
        )
    except Exception as exc:
        return SourceProbeResult(
            name=source["name"],
            url=source["url"],
            ok=False,
            status_code=None,
            content_type="",
            error=str(exc),
            notes=source["notes"],
        )
