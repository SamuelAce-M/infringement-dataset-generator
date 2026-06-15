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
    c = RegistryCollector("datasets/registry/外观设计专利")
    results = c.search("保温杯", limit=3)
    assert isinstance(results, list)
    assert len(results) == 3
    assert "id" in results[0]
    assert "title" in results[0]

def test_collector_download_creates_file(tmp_path):
    d = str(tmp_path)
    c = RegistryCollector(d)
    patent = {"id": "CN202430100001", "title": "Test", "image_url": "https://placehold.co/512x512/png"}
    path = c.download(patent)
    assert path is not None
    assert os.path.exists(path)
    img = Image.open(path)
    assert img.size == (512, 512)
    assert img.mode == "RGB"

def test_collector_download_skips_existing(tmp_path):
    d = str(tmp_path)
    c = RegistryCollector(d)
    patent = {"id": "CN202430100001", "title": "Test", "image_url": "https://placehold.co/512x512/png"}
    path1 = c.download(patent)
    path2 = c.download(patent)
    assert path1 == path2
