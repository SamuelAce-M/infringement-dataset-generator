"""Tests for NegativeGenerator."""
import os
import pytest
from PIL import Image
from src.negative import NegativeGenerator
from src.registry import RegistryCollector

@pytest.fixture
def two_images(tmp_path):
    img1 = Image.new("RGB", (512, 512), (255, 0, 0))
    img2 = Image.new("RGB", (512, 512), (0, 0, 255))
    p1 = str(tmp_path / "img1.png")
    p2 = str(tmp_path / "img2.png")
    img1.save(p1)
    img2.save(p2)
    return p1, p2

def test_generator_creates_output_dir(tmp_path):
    d = str(tmp_path / "negative")
    g = NegativeGenerator(d)
    assert os.path.isdir(d)

def test_verify_difference_different_images(two_images):
    g = NegativeGenerator()
    assert g.verify_difference(two_images[0], two_images[1]) is True

def test_verify_difference_same_image(two_images):
    g = NegativeGenerator()
    assert g.verify_difference(two_images[0], two_images[0]) is False

def test_collect_same_category(tmp_path):
    d = str(tmp_path)
    g = NegativeGenerator(str(tmp_path / "negative"))
    samples = g.collect_same_category(
        RegistryCollector,
        "保温杯",
        exclude_ids=["CN202430100001"],
        count=3,
        allow_placeholder=True,
    )
    assert len(samples) == 3
    for sample in samples:
        assert os.path.exists(sample.path)
        assert sample.similarity_band == "negative"

def test_collect_from_file_filters_by_similarity(tmp_path, two_images):
    manifest = tmp_path / "negative.csv"
    manifest.write_text(f"sample_id,image_path,registry_id,similarity_score\nNEG001,{two_images[1]},REG001,0.20\nNEG002,{two_images[0]},REG001,0.60\n")

    g = NegativeGenerator(str(tmp_path / "negative"))
    samples = g.collect_from_file(str(manifest), {"REG001": two_images[0]}, count=5)

    assert len(samples) == 1
    assert samples[0].sample_id == "NEG001"
    assert os.path.exists(samples[0].path)
