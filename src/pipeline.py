"""Pipeline orchestrator for training dataset generation."""
import csv
import logging
from pathlib import Path
from src.registry import RegistryCollector
from src.positive import PositiveGenerator
from src.negative import NegativeGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class Pipeline:
    """Orchestrate registry collection -> positive generation -> negative generation."""

    def __init__(self, output_root: str = "datasets"):
        self.output_root = Path(output_root)
        self.metadata = []

    def run(
        self, infringement_type: str, keyword: str,
        registry_count: int = 5, positive_count: int = 20, negative_count: int = 20,
    ):
        """Execute the full pipeline."""
        logger.info(f"Starting pipeline for {infringement_type}")

        reg_dir = self.output_root / "registry" / infringement_type
        pos_dir = self.output_root / "training" / infringement_type / "positive"
        neg_dir = self.output_root / "training" / infringement_type / "negative"

        # Step 1: Collect registry images
        logger.info("Step 1: Collecting registry images...")
        collector = RegistryCollector(str(reg_dir))
        patents = collector.search(keyword, limit=registry_count)
        registry_ids = []
        for patent in patents:
            path = collector.download(patent)
            if path:
                registry_ids.append(patent["id"])
                logger.info(f"  Downloaded: {patent['id']}")

        if not registry_ids:
            logger.error("No registry images collected. Aborting.")
            return

        # Step 2: Generate positive samples
        logger.info(f"Step 2: Generating {positive_count} positive samples...")
        pos_gen = PositiveGenerator(str(pos_dir))
        per_registry = max(1, positive_count // len(registry_ids))
        for reg_id in registry_ids:
            reg_path = reg_dir / f"patent_{reg_id}.png"
            if reg_path.exists():
                pos_gen.generate(str(reg_path), reg_id, count=per_registry)
                for i in range(per_registry):
                    self.metadata.append({
                        "image_path": f"training/{infringement_type}/positive/positive_{reg_id}_{i+1:03d}.png",
                        "label": "positive",
                        "infringement_type": infringement_type,
                        "registry_id": reg_id,
                        "transformations": "composite",
                    })

        # Step 3: Generate negative samples
        logger.info(f"Step 3: Generating {negative_count} negative samples...")
        neg_gen = NegativeGenerator(str(neg_dir))
        neg_paths = neg_gen.collect_same_category(
            RegistryCollector, keyword, exclude_ids=registry_ids, count=negative_count
        )
        for p in neg_paths:
            fname = Path(p).name
            self.metadata.append({
                "image_path": f"training/{infringement_type}/negative/{fname}",
                "label": "negative",
                "infringement_type": infringement_type,
                "registry_id": "",
                "transformations": "",
            })

        # Step 4: Cross-validate negative vs registry (NO visual overlap allowed)
        logger.info("Step 4: Cross-validating negative vs registry...")
        violations = self._validate_negatives(neg_dir, reg_dir, registry_ids)
        if violations:
            logger.error(f"CROSS-VALIDATION FAILED: {len(violations)} violations")
            for v in violations[:5]:
                logger.error(f"  {v}")
            return

        # Step 5: Write metadata
        logger.info("Step 5: Writing metadata...")
        self.write_metadata()
        logger.info(f"Pipeline complete! {len(self.metadata)} samples generated.")
        self.print_summary()

    def write_metadata(self):
        csv_path = self.output_root / "metadata.csv"
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "image_path", "label", "infringement_type", "registry_id", "transformations"
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerows(self.metadata)

    def print_summary(self):
        positives = sum(1 for m in self.metadata if m["label"] == "positive")
        negatives = sum(1 for m in self.metadata if m["label"] == "negative")
        reg_count = len(set(m["registry_id"] for m in self.metadata if m["registry_id"]))
        print(f"\n{'='*50}")
        print(f"  Training Dataset Summary")
        print(f"{'='*50}")
        print(f"  Registry images:  {reg_count}")
        print(f"  Positive samples: {positives}")
        print(f"  Negative samples: {negatives}")
        print(f"  Total:            {positives + negatives}")
        print(f"  Metadata:         {self.output_root / 'metadata.csv'}")
        print(f"{'='*50}")

    def _validate_negatives(self, neg_dir: Path, reg_dir: Path, registry_ids: list[str]) -> list[str]:
        """Cross-validate: every negative MUST be visually distinct from ALL registry images."""
        from PIL import Image
        violations = []
        reg_files = [f"patent_{rid}.png" for rid in registry_ids]
        neg_files = sorted(neg_dir.glob("*.png"))

        for nf in neg_files:
            n_img = Image.open(nf)
            for rf_name in reg_files:
                rf_path = reg_dir / rf_name
                if not rf_path.exists():
                    continue
                r_img = Image.open(rf_path)

                # Identical pixel-level check
                if hash(n_img.tobytes()) == hash(r_img.tobytes()):
                    violations.append(f"IDENTICAL: {nf.name} == {rf_name}")

                # High similarity check (>75% similar = too close, might be "just recolored")
                n_small = n_img.resize((64, 64))
                r_small = r_img.resize((64, 64))
                nd = list(n_small.getdata())
                rd = list(r_small.getdata())
                diff = sum(1 for k in range(len(nd))
                           if sum(abs(x - y) for x, y in zip(nd[k], rd[k])) > 50)
                similarity = (1 - diff / len(nd)) * 100
                if similarity > 75:
                    violations.append(f"HIGH-SIM ({similarity:.0f}%): {nf.name} vs {rf_name}")

        return violations
