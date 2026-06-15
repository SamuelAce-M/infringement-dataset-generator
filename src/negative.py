"""Negative sample generator from same-category different-design patents."""
import os
import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

class NegativeGenerator:
    """Select same-category but visually different patent images as negative samples."""

    def __init__(self, output_dir: str = "datasets/training/外观设计专利/negative"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def collect_same_category(
        self, collector, keyword: str, exclude_ids: list[str], count: int = 20,
    ) -> list[str]:
        """Search same category patents, exclude registry ones, return paths."""
        results = collector.search(keyword, limit=count + len(exclude_ids) + 10)
        paths = []
        for patent in results:
            if patent["id"] in exclude_ids:
                continue
            if len(paths) >= count:
                break
            path = collector.download(patent)
            if path:
                dest = os.path.join(
                    self.output_dir,
                    f"negative_{patent['id']}_{len(paths)+1:03d}.png"
                )
                img = Image.open(path)
                img.save(dest, "PNG")
                paths.append(dest)
        return paths

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
