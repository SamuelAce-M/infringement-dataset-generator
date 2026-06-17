"""Tests for PositiveGenerator."""
import os
import pytest
from PIL import Image
from src.positive import PositiveGenerator

@pytest.fixture
def sample_registry(tmp_path):
    img = Image.new("RGB", (512, 512), (100, 150, 200))
    path = str(tmp_path / "test_patent.png")
    img.save(path)
    return path

def test_generator_creates_output_dir(tmp_path):
    d = str(tmp_path / "positive")
    g = PositiveGenerator(d)
    assert os.path.isdir(d)

def test_generate_creates_correct_count(sample_registry, tmp_path):
    d = str(tmp_path / "positive")
    g = PositiveGenerator(d)
    samples = g.generate(sample_registry, "TEST001", count=5)
    assert len(samples) == 5
    for sample in samples:
        assert os.path.exists(sample.path)
        assert sample.transformations
        assert sample.similarity_band in {"positive", "mid"}
        assert sample.similarity_score >= 0.40

def test_generate_output_is_valid_image(sample_registry, tmp_path):
    d = str(tmp_path / "positive")
    g = PositiveGenerator(d)
    samples = g.generate(sample_registry, "TEST001", count=3)
    for sample in samples:
        img = Image.open(sample.path)
        assert img.size == (512, 512)
        assert img.mode == "RGB"

def test_generate_applies_different_transforms(sample_registry, tmp_path):
    d = str(tmp_path / "positive")
    g = PositiveGenerator(d)
    samples = g.generate(sample_registry, "TEST001", count=3)
    images = [Image.open(sample.path) for sample in samples]
    hashes = [hash(img.tobytes()) for img in images]
    assert len(set(hashes)) >= 2

def test_individual_transforms(sample_registry):
    img = Image.open(sample_registry)
    for name in ["hue_shift", "saturation", "brightness", "local_warp", "mirror"]:
        fn = getattr(PositiveGenerator, f"apply_{name}")
        result, meta = fn(img)
        assert result.size == (512, 512)
        assert "name" in meta
        assert "params" in meta
    result, meta = PositiveGenerator.apply_logo_overlay(img)
    assert result.size == (512, 512)
    assert meta["name"] == "logo_overlay"
    result, meta = PositiveGenerator.apply_crop_stitch(img)
    assert result.size == (512, 512)
    assert meta["name"] == "crop_stitch"
