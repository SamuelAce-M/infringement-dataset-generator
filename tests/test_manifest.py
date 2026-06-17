"""Tests for local manifest generation."""
import csv
from PIL import Image
from src.manifest import build_negative_manifest, build_registry_manifest


def test_build_registry_manifest(tmp_path):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(registry_dir / "patent_REG001.png")

    output = tmp_path / "registry.csv"
    count = build_registry_manifest(str(registry_dir), str(output))

    assert count == 1
    with open(output, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"registry_id": "REG001", "image_path": str(registry_dir / "patent_REG001.png")}]


def test_build_negative_manifest_strips_sequence_suffix(tmp_path):
    negative_dir = tmp_path / "negative"
    negative_dir.mkdir()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(negative_dir / "negative_NEG001_003.png")

    output = tmp_path / "negative.csv"
    count = build_negative_manifest(str(negative_dir), str(output), default_similarity=0.25)

    assert count == 1
    with open(output, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["sample_id"] == "NEG001"
    assert rows[0]["similarity_score"] == "0.2500"
