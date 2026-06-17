"""Tests for the CLI contract."""
from click.testing import CliRunner
from PIL import Image
from main import main


def test_cli_accepts_registry_file_mode(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    registry_image = source_dir / "registry.png"
    negative_image = source_dir / "negative.png"
    Image.new("RGB", (128, 128), (80, 100, 120)).save(registry_image)
    Image.new("RGB", (128, 128), (220, 20, 20)).save(negative_image)

    registry_manifest = tmp_path / "registry.csv"
    registry_manifest.write_text(f"registry_id,image_path\nREG001,{registry_image}\n")
    negative_manifest = tmp_path / "negative.csv"
    negative_manifest.write_text(
        f"sample_id,image_path,registry_id,similarity_score\nNEG001,{negative_image},REG001,0.20\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "generate",
            "--type",
            "外观设计专利",
            "--registry",
            "file",
            str(registry_manifest),
            "--negative-source",
            str(negative_manifest),
            "--registry-count",
            "1",
            "--positive",
            "2",
            "--negative",
            "1",
            "--output",
            str(tmp_path / "datasets"),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "datasets" / "metadata.csv").exists()


def test_cli_prepare_and_validate_commands(tmp_path):
    source_dir = tmp_path / "sources"
    registry_dir = source_dir / "registry"
    negative_dir = source_dir / "negative"
    registry_dir.mkdir(parents=True)
    negative_dir.mkdir(parents=True)
    Image.new("RGB", (128, 128), (80, 100, 120)).save(registry_dir / "patent_REG001.png")
    Image.new("RGB", (128, 128), (220, 20, 20)).save(negative_dir / "negative_NEG001_001.png")

    registry_manifest = tmp_path / "registry.csv"
    negative_manifest = tmp_path / "negative.csv"
    runner = CliRunner()

    prepare_result = runner.invoke(
        main,
        [
            "prepare-manifests",
            "--registry-dir",
            str(registry_dir),
            "--negative-dir",
            str(negative_dir),
            "--registry-output",
            str(registry_manifest),
            "--negative-output",
            str(negative_manifest),
        ],
    )
    assert prepare_result.exit_code == 0
    assert registry_manifest.exists()
    assert negative_manifest.exists()

    dataset_root = tmp_path / "datasets"
    generate_result = runner.invoke(
        main,
        [
            "generate",
            "--type",
            "外观设计专利",
            "--registry",
            "file",
            str(registry_manifest),
            "--negative-source",
            str(negative_manifest),
            "--registry-count",
            "1",
            "--positive",
            "2",
            "--negative",
            "1",
            "--output",
            str(dataset_root),
        ],
    )
    assert generate_result.exit_code == 0

    validate_result = runner.invoke(main, ["validate", "--root", str(dataset_root)])
    assert validate_result.exit_code == 0


def test_cli_source_spike_writes_report(tmp_path, monkeypatch):
    from src import source_spike as source_spike_module
    from src.source_spike import SourceProbeResult

    result_record = SourceProbeResult(
        name="Fake",
        url="https://example.com",
        ok=True,
        status_code=200,
        content_type="text/html",
        error="",
        notes="test",
    )
    monkeypatch.setattr(source_spike_module, "run_source_spike", lambda timeout: [result_record])

    output = tmp_path / "source_spike.json"
    runner = CliRunner()
    result = runner.invoke(main, ["source-spike", "--output", str(output), "--timeout", "1"])

    assert result.exit_code == 0
    assert output.exists()
    assert "OK: Fake" in result.output


def test_cli_wipo_inspect_writes_report(tmp_path, monkeypatch):
    from src import wipo as wipo_module
    from src.wipo import WipoInspectReport

    report = WipoInspectReport(
        url="https://designdb.wipo.int/designdb/en/",
        ok=True,
        status_code=200,
        qk_present=True,
        qk="abc123",
        endpoints=["https://designdb.wipo.int/designdb/jsp/select.jsp"],
        search_fields=["PROD"],
        usage_warnings=["test warning"],
    )
    monkeypatch.setattr(wipo_module, "inspect_wipo", lambda timeout: report)

    output = tmp_path / "wipo.json"
    runner = CliRunner()
    result = runner.invoke(main, ["wipo-inspect", "--output", str(output), "--timeout", "1"])

    assert result.exit_code == 0
    assert output.exists()
    assert "qk present: True" in result.output


def test_cli_wipo_export_blocks_visible(tmp_path, monkeypatch):
    from src import wipo_export as wipo_export_module
    from src.wipo_export import WipoExportReport

    export_report = WipoExportReport(
        keyword="cup",
        limit=5,
        output_manifest=str(tmp_path / "manifest.csv"),
        ok=False,
        blockers=["not implemented"],
    )
    monkeypatch.setattr(wipo_export_module, "export_wipo_manifest", lambda **kwargs: export_report)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "wipo-export",
            "--keyword",
            "cup",
            "--output",
            str(tmp_path / "manifest.csv"),
            "--report",
            str(tmp_path / "report.json"),
            "--acknowledge-limits",
        ],
    )

    assert result.exit_code == 2
    assert "WIPO export blocked" in result.output
