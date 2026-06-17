"""Tests for RegistryCollector."""
import os
import pytest
from PIL import Image
from src.registry import RegistryCollector

def test_collector_init_creates_dir(tmp_path):
    d = tmp_path / "registry"
    c = RegistryCollector(str(d))
    assert os.path.isdir(d)

def test_collector_search_returns_list():
    c = RegistryCollector("datasets/registry/外观设计专利", allow_placeholder=True)
    results = c.search("保温杯", limit=3)
    assert isinstance(results, list)
    assert len(results) == 3
    assert "id" in results[0]
    assert "title" in results[0]

def test_collector_download_creates_file(tmp_path):
    d = str(tmp_path)
    c = RegistryCollector(d, allow_placeholder=True)
    patent = {"id": "CN202430100001", "title": "Test", "image_url": "https://placehold.co/512x512/png"}
    path = c.download(patent)
    assert path is not None
    assert os.path.exists(path)
    img = Image.open(path)
    assert img.size == (512, 512)
    assert img.mode == "RGB"

def test_collector_download_skips_existing(tmp_path):
    d = str(tmp_path)
    c = RegistryCollector(d, allow_placeholder=True)
    patent = {"id": "CN202430100001", "title": "Test", "image_url": "https://placehold.co/512x512/png"}
    path1 = c.download(patent)
    path2 = c.download(patent)
    assert path1 == path2

def test_collector_does_not_placeholder_by_default(tmp_path):
    c = RegistryCollector(str(tmp_path))
    patent = {"id": "CN202430100001", "title": "Test", "image_url": None}
    assert c.download(patent) is None

def test_collect_from_file_imports_local_image(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (64, 64), (10, 20, 30)).save(source)
    manifest = tmp_path / "registry.csv"
    manifest.write_text(f"registry_id,image_path\nREG001,{source}\n")

    c = RegistryCollector(str(tmp_path / "registry"))
    records = c.collect_from_file(str(manifest), limit=1)

    assert len(records) == 1
    assert records[0]["id"] == "REG001"
    img = Image.open(records[0]["path"])
    assert img.size == (512, 512)

def test_collect_from_file_accepts_url_manifest(tmp_path):
    manifest = tmp_path / "registry.csv"
    manifest.write_text("registry_id,image_path\nREG001,https://example.com/image.png\n")

    c = RegistryCollector(str(tmp_path / "registry"))
    records = []
    patents = []
    original_download = c.download

    def fake_download(patent):
        patents.append(patent)
        return None

    c.download = fake_download
    records = c.collect_from_file(str(manifest), limit=1)
    c.download = original_download

    assert records == []
    assert patents[0]["image_url"] == "https://example.com/image.png"
    assert patents[0]["source"] == "url_manifest"
