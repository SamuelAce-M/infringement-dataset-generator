"""Manifest generation helpers for local dataset sources."""
import csv
from pathlib import Path


def build_registry_manifest(registry_dir: str, output_path: str) -> int:
    """Create a registry manifest from patent_*.png files."""
    registry_root = Path(registry_dir)
    rows = []
    for image_path in sorted(registry_root.glob("patent_*.png")):
        registry_id = image_path.stem.removeprefix("patent_")
        rows.append([registry_id, str(image_path)])
    _write_csv(output_path, ["registry_id", "image_path"], rows)
    return len(rows)


def build_negative_manifest(
    negative_dir: str,
    output_path: str,
    default_similarity: float = 0.20,
) -> int:
    """Create a negative manifest from negative_*.png files."""
    negative_root = Path(negative_dir)
    rows = []
    for image_path in sorted(negative_root.glob("negative_*.png")):
        sample_id = _negative_sample_id(image_path.stem)
        rows.append([sample_id, str(image_path), "", f"{default_similarity:.4f}"])
    _write_csv(
        output_path,
        ["sample_id", "image_path", "registry_id", "similarity_score"],
        rows,
    )
    return len(rows)


def _negative_sample_id(stem: str) -> str:
    value = stem.removeprefix("negative_")
    parts = value.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return value


def _write_csv(output_path: str, header: list[str], rows: list[list[str]]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
