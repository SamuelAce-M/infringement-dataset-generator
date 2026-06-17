"""Negative sample generator from same-category different-design patents."""
import csv
import os
import tempfile
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class NegativeSample:
    path: str
    sample_id: str
    registry_id: str
    similarity_score: float
    similarity_band: str = "negative"
    source: str = "local_manifest"

class NegativeGenerator:
    """Select same-category but visually different patent images as negative samples."""

    def __init__(self, output_dir: str = "datasets/training/外观设计专利/negative"):
        self.output_dir = output_dir
        self.session = requests.Session()
        os.makedirs(output_dir, exist_ok=True)

    def collect_from_file(
        self,
        manifest_path: str,
        registry_paths: dict[str, str],
        count: int = 20,
    ) -> list[NegativeSample]:
        """Import negative samples from a CSV manifest.

        Rows: sample_id,image_path[,registry_id][,similarity_score]
        """
        samples = []
        with open(manifest_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().startswith("#"):
                    continue
                if row[0].strip() == "sample_id":
                    continue
                sample_id = row[0].strip()
                image_ref = row[1].strip() if len(row) > 1 else ""
                registry_id = row[2].strip() if len(row) > 2 else ""
                score = float(row[3]) if len(row) > 3 and row[3].strip() else None
                if not image_ref:
                    logger.warning("Skipping negative %s; image source missing", sample_id)
                    continue
                if score is None:
                    if self._is_url(image_ref):
                        logger.warning("Skipping negative %s; URL sources require explicit similarity_score", sample_id)
                        continue
                    score = self._estimate_against_registry(image_ref, registry_paths, registry_id)
                if score >= 0.40:
                    logger.warning("Skipping negative %s; similarity %.2f is not < 0.40", sample_id, score)
                    continue
                dest = os.path.join(self.output_dir, f"negative_{sample_id}_{len(samples)+1:03d}.png")
                image = self._open_source_image(image_ref)
                if image is None:
                    logger.warning("Skipping negative %s; image unavailable: %s", sample_id, image_ref)
                    continue
                image.convert("RGB").resize((512, 512), Image.LANCZOS).save(dest, "PNG")
                source = "url_manifest" if self._is_url(image_ref) else "local_manifest"
                samples.append(NegativeSample(dest, sample_id, registry_id, score, source=source))
                if len(samples) >= count:
                    break
        return samples

    def collect_same_category(
        self,
        CollectorClass,
        keyword: str,
        exclude_ids: list[str],
        count: int = 20,
        allow_placeholder: bool = False,
    ) -> list[NegativeSample]:
        """Search same category patents, exclude registry ones, return paths.
        
        Uses a temp directory for downloads to avoid polluting the registry.
        CollectorClass should be RegistryCollector (the class, not an instance).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = CollectorClass(output_dir=tmpdir, allow_placeholder=allow_placeholder)
            results = collector.search(keyword, limit=count + len(exclude_ids) + 10)
            samples = []
            for patent in results:
                if patent["id"] in exclude_ids:
                    continue
                if len(samples) >= count:
                    break
                path = collector.download(patent)
                if path:
                    dest = os.path.join(
                        self.output_dir,
                        f"negative_{patent['id']}_{len(samples)+1:03d}.png"
                    )
                    img = Image.open(path)
                    img.save(dest, "PNG")
                    samples.append(NegativeSample(
                        dest,
                        patent["id"],
                        "",
                        0.20,
                        source="fixture" if allow_placeholder else "online",
                    ))
            return samples

    def verify_difference(self, registry_path: str, candidate_path: str) -> bool:
        """Check that two images are meaningfully different."""
        try:
            r = Image.open(registry_path).resize((128, 128))
            c = Image.open(candidate_path).resize((128, 128))
            r_data = list(r.getdata())
            c_data = list(c.getdata())
            diff_pixels = sum(
                1 for i in range(len(r_data))
                if sum(abs(a - b) for a, b in zip(r_data[i], c_data[i])) > 30
            )
            similarity = 1 - (diff_pixels / len(r_data))
            return similarity < 0.70
        except Exception:
            return True

    def similarity_score(self, registry_path: str, candidate_path: str) -> float:
        """Return a lightweight pixel-difference similarity score from 0.0 to 1.0."""
        r = Image.open(registry_path).resize((128, 128))
        c = Image.open(candidate_path).resize((128, 128))
        r_data = list(r.getdata())
        c_data = list(c.getdata())
        diff_pixels = sum(
            1 for i in range(len(r_data))
            if sum(abs(a - b) for a, b in zip(r_data[i], c_data[i])) > 30
        )
        return 1 - (diff_pixels / len(r_data))

    def _estimate_against_registry(
        self,
        candidate_path: str,
        registry_paths: dict[str, str],
        preferred_registry_id: str = "",
    ) -> float:
        if preferred_registry_id and preferred_registry_id in registry_paths:
            return self.similarity_score(registry_paths[preferred_registry_id], candidate_path)
        if not registry_paths:
            return 0.0
        return max(self.similarity_score(path, candidate_path) for path in registry_paths.values())

    def _open_source_image(self, image_ref: str) -> Image.Image | None:
        try:
            if self._is_url(image_ref):
                response = self.session.get(image_ref, timeout=30)
                response.raise_for_status()
                return Image.open(BytesIO(response.content))
            if os.path.exists(image_ref):
                return Image.open(image_ref)
        except Exception as exc:
            logger.warning("Failed to open image source %s: %s", image_ref, exc)
        return None

    @staticmethod
    def _is_url(value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")
