"""Positive sample generator with 5 programmatic transforms."""
import os
import random
import logging
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageEnhance

logger = logging.getLogger(__name__)

@dataclass
class GeneratedSample:
    path: str
    transformations: list[dict]
    similarity_score: float
    similarity_band: str

class PositiveGenerator:
    """Generate infringing positive samples by transforming registry images."""

    def __init__(self, output_dir: str = "datasets/training/外观设计专利/positive"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def similarity_band(score: float) -> str:
        if score >= 0.55:
            return "positive"
        if score >= 0.40:
            return "mid"
        return "negative"

    @staticmethod
    def apply_hue_shift(img: Image.Image, factor: float = None) -> tuple[Image.Image, dict]:
        """Shift image hues while preserving structure."""
        if factor is None:
            factor = random.uniform(-60, 60)
        hsv = img.convert("HSV")
        h, s, v = hsv.split()
        h_data = list(h.getdata())
        h_data = [(x + int(factor * 255 / 360)) % 256 for x in h_data]
        h.putdata(h_data)
        return Image.merge("HSV", (h, s, v)).convert("RGB"), {
            "name": "hue_shift",
            "params": {"hue_shift": round(factor, 3)},
            "similarity_delta": 0.03,
        }

    @staticmethod
    def apply_saturation(img: Image.Image, factor: float = None) -> tuple[Image.Image, dict]:
        if factor is None:
            factor = random.uniform(0.6, 1.8)
        return ImageEnhance.Color(img).enhance(factor), {
            "name": "saturation",
            "params": {"saturation": round(factor, 3)},
            "similarity_delta": 0.02,
        }

    @staticmethod
    def apply_brightness(img: Image.Image, factor: float = None) -> tuple[Image.Image, dict]:
        if factor is None:
            factor = random.uniform(0.7, 1.5)
        return ImageEnhance.Brightness(img).enhance(factor), {
            "name": "brightness",
            "params": {"brightness": round(factor, 3)},
            "similarity_delta": 0.02,
        }

    @staticmethod
    def apply_logo_overlay(img: Image.Image) -> tuple[Image.Image, dict]:
        """Overlay a generated logo-like element."""
        result = img.copy()
        draw = ImageDraw.Draw(result)
        x = random.randint(20, 400)
        y = random.randint(20, 400)
        w = random.randint(40, 100)
        h = random.randint(20, 60)
        opacity = 180
        color = tuple(random.randint(0, 255) for _ in range(3))
        overlay = Image.new("RGBA", (w, h), (*color, opacity))
        result.paste(overlay, (x, y), overlay)
        draw.text((x + 5, y + 5), "LOGO", fill=(255, 255, 255))
        return result, {
            "name": "logo_overlay",
            "params": {
                "position": [x, y],
                "scale": round(max(w, h) / 512, 3),
                "opacity": round(opacity / 255, 3),
            },
            "similarity_delta": 0.08,
        }

    @staticmethod
    def apply_local_warp(img: Image.Image, strength: float = None) -> tuple[Image.Image, dict]:
        """Apply subtle perspective warp."""
        if strength is None:
            strength = random.uniform(0.02, 0.10)
        w, h = img.size
        result = img.transform(
            (w, h), Image.PERSPECTIVE,
            (1, random.uniform(-strength, strength), 0,
             random.uniform(-strength, strength), 1, 0,
             0, 0),
            Image.BICUBIC
        )
        return result, {
            "name": "local_warp",
            "params": {"strength": round(strength, 3)},
            "similarity_delta": min(0.18, strength * 1.4),
        }

    @staticmethod
    def apply_crop_stitch(img: Image.Image) -> tuple[Image.Image, dict]:
        """Crop a small portion and stitch back with offset."""
        w, h = img.size
        crop_ratio = random.uniform(0.05, 0.20)
        crop_w = int(w * crop_ratio)
        crop_h = int(h * crop_ratio)
        src_x = random.randint(0, w - crop_w)
        src_y = random.randint(0, h - crop_h)
        dst_x = random.randint(0, w - crop_w)
        dst_y = random.randint(0, h - crop_h)
        result = img.copy()
        patch = img.crop((src_x, src_y, src_x + crop_w, src_y + crop_h))
        result.paste(patch, (dst_x, dst_y))
        return result, {
            "name": "crop_stitch",
            "params": {
                "crop_ratio": round(crop_ratio, 3),
                "source": [src_x, src_y],
                "destination": [dst_x, dst_y],
            },
            "similarity_delta": 0.12,
        }

    @staticmethod
    def apply_mirror(img: Image.Image, direction: str = None) -> tuple[Image.Image, dict]:
        """Flip horizontally or vertically."""
        if direction is None:
            direction = "horizontal" if random.random() > 0.5 else "vertical"
        method = Image.FLIP_LEFT_RIGHT if direction == "horizontal" else Image.FLIP_TOP_BOTTOM
        return img.transpose(method), {
            "name": "mirror",
            "params": {"direction": direction},
            "similarity_delta": 0.16 if direction == "horizontal" else 0.24,
        }

    def generate(self, registry_path: str, registry_id: str, count: int = 20) -> list[GeneratedSample]:
        """Generate count positive samples from one registry image."""
        samples = []
        img = Image.open(registry_path).convert("RGB")

        transforms = [
            ("hue", self.apply_hue_shift),
            ("sat", self.apply_saturation),
            ("bri", self.apply_brightness),
            ("logo", self.apply_logo_overlay),
            ("warp", self.apply_local_warp),
            ("crop", self.apply_crop_stitch),
            ("mirror", self.apply_mirror),
        ]

        for i in range(count):
            target_band = "mid" if count > 1 and i % 3 == 1 else "positive"
            result, applied, similarity_score, band = self._generate_variant(
                img, transforms, target_band
            )

            filename = f"positive_{registry_id}_{i+1:03d}.png"
            output_path = os.path.join(self.output_dir, filename)
            result.save(output_path, "PNG")
            samples.append(GeneratedSample(output_path, applied, similarity_score, band))
            logger.debug("Generated %s with transforms: %s", filename, applied)

        return samples

    def _generate_variant(
        self,
        img: Image.Image,
        transforms: list[tuple[str, object]],
        target_band: str,
    ) -> tuple[Image.Image, list[dict], float, str]:
        for _ in range(20):
            result = img.copy()
            applied = []
            n_transforms = random.randint(2, 4)
            selected = random.sample(transforms, n_transforms)
            for _name, fn in selected:
                result, meta = fn(result)
                applied.append(meta)
            score = self._estimate_similarity(applied)
            band = self.similarity_band(score)
            if band == target_band:
                return result, applied, score, band
        return self._fallback_variant(img, target_band)

    def _fallback_variant(self, img: Image.Image, target_band: str) -> tuple[Image.Image, list[dict], float, str]:
        result = img.copy()
        applied = []
        if target_band == "mid":
            for fn in (
                self.apply_logo_overlay,
                self.apply_crop_stitch,
                self.apply_local_warp,
            ):
                result, meta = fn(result)
                applied.append(meta)
            result, meta = self.apply_mirror(result, direction="vertical")
            applied.append(meta)
        else:
            for fn in (
                self.apply_hue_shift,
                self.apply_saturation,
                self.apply_brightness,
            ):
                result, meta = fn(result)
                applied.append(meta)
        score = self._estimate_similarity(applied)
        return result, applied, score, self.similarity_band(score)

    @staticmethod
    def _estimate_similarity(transformations: list[dict]) -> float:
        return max(
            0.40,
            min(0.95, 0.92 - sum(t["similarity_delta"] for t in transformations)),
        )
