"""Tests for WIPO inspection helpers."""
import json
from src.wipo import inspect_wipo, write_wipo_inspect_report


class FakeResponse:
    def __init__(self, text, url="https://designdb.wipo.int/designdb/en/", status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("bad status")


class FakeSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, timeout):
        if url.endswith("/en/"):
            return FakeResponse("""
            <script>var qk = "abc123";</script>
            <script src="../designdb.init.16015.min.js"></script>
            """)
        return FakeResponse("""
        c.solrManager({solrUrl:"../jsp/", servlet:"select.jsp", compressRequest:true, keyServlet:"qk.jsp"});
        c.solrManager("addWidget","solrSearch","design_search",{format:{fie:{order:["1"],"1":{fie:"PROD",op:"EQ"}}}});
        automatic retrieval of data from our system is specifically forbidden
        """, url=url)


def test_inspect_wipo_extracts_frontend_wiring():
    report = inspect_wipo(session=FakeSession())

    assert report.ok
    assert report.qk_present
    assert report.qk == "abc123"
    assert "https://designdb.wipo.int/designdb/jsp/select.jsp" in report.endpoints
    assert "PROD" in report.search_fields
    assert any("automatic retrieval" in warning for warning in report.usage_warnings)


def test_write_wipo_inspect_report(tmp_path):
    report = inspect_wipo(session=FakeSession())
    output = tmp_path / "wipo.json"

    write_wipo_inspect_report(report, str(output))

    payload = json.loads(output.read_text())
    assert payload["report"]["qk"] == "abc123"
