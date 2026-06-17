"""Dataset validation utilities."""
import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image


REQUIRED_METADATA_FIELDS = {
    "image_path",
    "label",
    "similarity_band",
    "similarity_score",
    "infringement_type",
    "registry_id",
    "source",
    "transformations",
}

VALID_LABELS = {"positive", "negative"}
VALID_BANDS = {"positive", "mid", "negative"}


@dataclass
class ValidationReport:
    dataset_root: str
    total_rows: int = 0
    label_counts: dict[str, int] = field(default_factory=dict)
    band_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_dataset(dataset_root: str = "datasets") -> ValidationReport:
    """Validate dataset files and metadata consistency."""
    root = Path(dataset_root)
    report = ValidationReport(dataset_root=str(root))
    metadata_path = root / "metadata.csv"

    if not metadata_path.exists():
        report.errors.append(f"Missing metadata file: {metadata_path}")
        return report

    with open(metadata_path, newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        missing_fields = REQUIRED_METADATA_FIELDS - fields
        if missing_fields:
            report.errors.append(f"metadata.csv missing fields: {sorted(missing_fields)}")
            return report

        image_hashes: dict[str, str] = {}
        for row_number, row in enumerate(reader, start=2):
            report.total_rows += 1
            _validate_row(root, row, row_number, image_hashes, report)

    if report.total_rows == 0:
        report.errors.append("metadata.csv has no sample rows")

    if report.band_counts.get("mid", 0) == 0:
        report.warnings.append("No mid-band samples found; boundary coverage is missing")

    if report.band_counts.get("positive", 0) == 0:
        report.warnings.append("No positive-band samples found")

    if report.band_counts.get("negative", 0) == 0:
        report.warnings.append("No negative-band samples found")

    return report


def _validate_row(
    root: Path,
    row: dict[str, str],
    row_number: int,
    image_hashes: dict[str, str],
    report: ValidationReport,
) -> None:
    label = row["label"]
    band = row["similarity_band"]
    report.label_counts[label] = report.label_counts.get(label, 0) + 1
    report.band_counts[band] = report.band_counts.get(band, 0) + 1

    if label not in VALID_LABELS:
        report.errors.append(f"Row {row_number}: invalid label '{label}'")

    if band not in VALID_BANDS:
        report.errors.append(f"Row {row_number}: invalid similarity_band '{band}'")

    score = _parse_score(row["similarity_score"], row_number, report)
    if score is not None:
        _validate_similarity_contract(label, band, score, row_number, report)

    image_path = root / row["image_path"]
    if not image_path.exists():
        report.errors.append(f"Row {row_number}: missing image file {image_path}")
    else:
        _validate_image(image_path, row_number, image_hashes, report)

    try:
        parsed_transformations = json.loads(row["transformations"] or "[]")
        if not isinstance(parsed_transformations, list):
            report.errors.append(f"Row {row_number}: transformations must be a JSON list")
    except json.JSONDecodeError as exc:
        report.errors.append(f"Row {row_number}: invalid transformations JSON: {exc}")

    if label == "positive" and not row["registry_id"]:
        report.errors.append(f"Row {row_number}: positive sample missing registry_id")


def _parse_score(value: str, row_number: int, report: ValidationReport) -> float | None:
    try:
        score = float(value)
    except ValueError:
        report.errors.append(f"Row {row_number}: invalid similarity_score '{value}'")
        return None
    if score < 0.0 or score > 1.0:
        report.errors.append(f"Row {row_number}: similarity_score out of range {score}")
    return score


def _validate_similarity_contract(
    label: str,
    band: str,
    score: float,
    row_number: int,
    report: ValidationReport,
) -> None:
    expected_band = "positive" if score >= 0.55 else "mid" if score >= 0.40 else "negative"
    if band != expected_band:
        report.errors.append(
            f"Row {row_number}: band '{band}' does not match score {score:.4f}; expected '{expected_band}'"
        )
    if label == "negative" and score >= 0.40:
        report.errors.append(f"Row {row_number}: negative sample score must be < 0.40")
    if label == "positive" and score < 0.40:
        report.errors.append(f"Row {row_number}: positive sample score must be >= 0.40")


def _validate_image(
    image_path: Path,
    row_number: int,
    image_hashes: dict[str, str],
    report: ValidationReport,
) -> None:
    try:
        with Image.open(image_path) as img:
            if img.size != (512, 512):
                report.errors.append(f"Row {row_number}: image must be 512x512, got {img.size}")
            if img.mode != "RGB":
                report.errors.append(f"Row {row_number}: image mode must be RGB, got {img.mode}")
            digest = hashlib.sha256(img.tobytes()).hexdigest()
    except Exception as exc:
        report.errors.append(f"Row {row_number}: invalid image {image_path}: {exc}")
        return

    previous_path = image_hashes.get(digest)
    if previous_path:
        report.warnings.append(f"Row {row_number}: duplicate image content with {previous_path}")
    else:
        image_hashes[digest] = str(image_path)
