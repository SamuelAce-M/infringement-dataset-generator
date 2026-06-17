"""Tests for Pipeline orchestration."""
import csv
import json
from PIL import Image
from src.pipeline import Pipeline


def test_pipeline_writes_structured_metadata(tmp_path):
    registry_manifest = tmp_path / "registry.csv"
    negative_manifest = tmp_path / "negative.csv"
    source_dir = tmp_path / "sources"
    source_dir.mkdir()

    registry_rows = ["registry_id,image_path"]
    for i in range(3):
        path = source_dir / f"registry_{i}.png"
        Image.new("RGB", (128, 128), (50 + i * 20, 100, 150)).save(path)
        registry_rows.append(f"REG{i},{path}")
    registry_manifest.write_text("\n".join(registry_rows) + "\n")

    negative_rows = ["sample_id,image_path,registry_id,similarity_score"]
    for i in range(2):
        path = source_dir / f"negative_{i}.png"
        Image.new("RGB", (128, 128), (200, 20 + i * 20, 20)).save(path)
        negative_rows.append(f"NEG{i},{path},REG0,0.20")
    negative_manifest.write_text("\n".join(negative_rows) + "\n")

    output = tmp_path / "datasets"
    pipeline = Pipeline(str(output))
    pipeline.run(
        infringement_type="外观设计专利",
        registry_mode="file",
        registry_value=str(registry_manifest),
        negative_source=str(negative_manifest),
        registry_count=3,
        positive_count=5,
        negative_count=2,
    )

    with open(output / "metadata.csv", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 7
    assert set(rows[0]) == {
        "image_path",
        "label",
        "similarity_band",
        "similarity_score",
        "infringement_type",
        "registry_id",
        "source",
        "transformations",
    }
    positives = [row for row in rows if row["label"] == "positive"]
    negatives = [row for row in rows if row["label"] == "negative"]
    assert len(positives) == 5
    assert len(negatives) == 2
    assert all(json.loads(row["transformations"]) for row in positives)
