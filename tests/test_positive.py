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
    paths = g.generate(sample_registry, "TEST001", count=5)
    assert len(paths) == 5
    for p in paths:
        assert os.path.exists(p)

def test_generate_output_is_valid_image(sample_registry, tmp_path):
    d = str(tmp_path / "positive")
    g = PositiveGenerator(d)
    paths = g.generate(sample_registry, "TEST001", count=3)
    for p in paths:
        img = Image.open(p)
        assert img.size == (512, 512)
        assert img.mode == "RGB"

def test_generate_applies_different_transforms(sample_registry, tmp_path):
    d = str(tmp_path / "positive")
    g = PositiveGenerator(d)
    paths = g.generate(sample_registry, "TEST001", count=3)
    images = [Image.open(p) for p in paths]
    hashes = [hash(img.tobytes()) for img in images]
    assert len(set(hashes)) >= 2

def test_individual_transforms(sample_registry):
    img = Image.open(sample_registry)
    for name in ["hue_shift", "saturation", "brightness", "local_warp", "mirror"]:
        fn = getattr(PositiveGenerator, f"apply_{name}")
        result = fn(img)
        assert result.size == (512, 512)
    result = PositiveGenerator.apply_logo_overlay(img)
    assert result.size == (512, 512)
    result = PositiveGenerator.apply_crop_stitch(img)
    assert result.size == (512, 512)
