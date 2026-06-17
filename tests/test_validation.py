"""Tests for dataset validation."""
import csv
from PIL import Image
from src.validation import validate_dataset


FIELDNAMES = [
    "image_path",
    "label",
    "similarity_band",
    "similarity_score",
    "infringement_type",
    "registry_id",
    "source",
    "transformations",
]


def _write_metadata(root, rows):
    with open(root / "metadata.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_validate_dataset_accepts_valid_dataset(tmp_path):
    image_dir = tmp_path / "training" / "外观设计专利" / "positive"
    image_dir.mkdir(parents=True)
    positive = image_dir / "positive_REG001_001.png"
    mid = image_dir / "positive_REG001_002.png"
    Image.new("RGB", (512, 512), (10, 20, 30)).save(positive)
    Image.new("RGB", (512, 512), (40, 50, 60)).save(mid)

    negative_dir = tmp_path / "training" / "外观设计专利" / "negative"
    negative_dir.mkdir(parents=True)
    negative = negative_dir / "negative_NEG001_001.png"
    Image.new("RGB", (512, 512), (200, 10, 10)).save(negative)

    _write_metadata(tmp_path, [
        {
            "image_path": "training/外观设计专利/positive/positive_REG001_001.png",
            "label": "positive",
            "similarity_band": "positive",
            "similarity_score": "0.75",
            "infringement_type": "外观设计专利",
            "registry_id": "REG001",
            "source": "generated",
            "transformations": "[]",
        },
        {
            "image_path": "training/外观设计专利/positive/positive_REG001_002.png",
            "label": "positive",
            "similarity_band": "mid",
            "similarity_score": "0.45",
            "infringement_type": "外观设计专利",
            "registry_id": "REG001",
            "source": "generated",
            "transformations": "[]",
        },
        {
            "image_path": "training/外观设计专利/negative/negative_NEG001_001.png",
            "label": "negative",
            "similarity_band": "negative",
            "similarity_score": "0.20",
            "infringement_type": "外观设计专利",
            "registry_id": "",
            "source": "local_manifest",
            "transformations": "[]",
        },
    ])

    report = validate_dataset(str(tmp_path))

    assert report.ok
    assert report.total_rows == 3
    assert report.band_counts == {"positive": 1, "mid": 1, "negative": 1}


def test_validate_dataset_rejects_negative_above_threshold(tmp_path):
    image_dir = tmp_path / "training" / "外观设计专利" / "negative"
    image_dir.mkdir(parents=True)
    image = image_dir / "negative_NEG001_001.png"
    Image.new("RGB", (512, 512), (200, 10, 10)).save(image)

    _write_metadata(tmp_path, [{
        "image_path": "training/外观设计专利/negative/negative_NEG001_001.png",
        "label": "negative",
        "similarity_band": "negative",
        "similarity_score": "0.50",
        "infringement_type": "外观设计专利",
        "registry_id": "",
        "source": "local_manifest",
        "transformations": "[]",
    }])

    report = validate_dataset(str(tmp_path))

    assert not report.ok
    assert any("negative sample score must be < 0.40" in error for error in report.errors)
