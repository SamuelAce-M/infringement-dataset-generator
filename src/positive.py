"""Positive sample generator with 5 programmatic transforms."""
import os
import random
import logging
from PIL import Image, ImageDraw, ImageEnhance

logger = logging.getLogger(__name__)

class PositiveGenerator:
    """Generate infringing positive samples by transforming registry images."""

    def __init__(self, output_dir: str = "datasets/training/外观设计专利/positive"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def apply_hue_shift(img: Image.Image, factor: float = None) -> Image.Image:
        """Shift image hues while preserving structure."""
        if factor is None:
            factor = random.uniform(-60, 60)
        hsv = img.convert("HSV")
        h, s, v = hsv.split()
        h_data = list(h.getdata())
        h_data = [(x + int(factor * 255 / 360)) % 256 for x in h_data]
        h.putdata(h_data)
        return Image.merge("HSV", (h, s, v)).convert("RGB")

    @staticmethod
    def apply_saturation(img: Image.Image, factor: float = None) -> Image.Image:
        if factor is None:
            factor = random.uniform(0.6, 1.8)
        return ImageEnhance.Color(img).enhance(factor)

    @staticmethod
    def apply_brightness(img: Image.Image, factor: float = None) -> Image.Image:
        if factor is None:
            factor = random.uniform(0.7, 1.5)
        return ImageEnhance.Brightness(img).enhance(factor)

    @staticmethod
    def apply_logo_overlay(img: Image.Image) -> Image.Image:
        """Overlay a generated logo-like element."""
        result = img.copy()
        draw = ImageDraw.Draw(result)
        x = random.randint(20, 400)
        y = random.randint(20, 400)
        w = random.randint(40, 100)
        h = random.randint(20, 60)
        color = tuple(random.randint(0, 255) for _ in range(3))
        overlay = Image.new("RGBA", (w, h), (*color, 180))
        result.paste(overlay, (x, y), overlay)
        draw.text((x + 5, y + 5), "LOGO", fill=(255, 255, 255))
        return result

    @staticmethod
    def apply_local_warp(img: Image.Image, strength: float = None) -> Image.Image:
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
        return result

    @staticmethod
    def apply_crop_stitch(img: Image.Image) -> Image.Image:
        """Crop a small portion and stitch back with offset."""
        w, h = img.size
        crop_w = int(w * random.uniform(0.05, 0.20))
        crop_h = int(h * random.uniform(0.05, 0.20))
        src_x = random.randint(0, w - crop_w)
        src_y = random.randint(0, h - crop_h)
        dst_x = random.randint(0, w - crop_w)
        dst_y = random.randint(0, h - crop_h)
        result = img.copy()
        patch = img.crop((src_x, src_y, src_x + crop_w, src_y + crop_h))
        result.paste(patch, (dst_x, dst_y))
        return result

    @staticmethod
    def apply_mirror(img: Image.Image) -> Image.Image:
        """Flip horizontally or vertically."""
        return img.transpose(
            Image.FLIP_LEFT_RIGHT if random.random() > 0.5 else Image.FLIP_TOP_BOTTOM
        )

    def generate(self, registry_path: str, registry_id: str, count: int = 20) -> list[str]:
        """Generate count positive samples from one registry image."""
        paths = []
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
            result = img.copy()
            applied = []
            n_transforms = random.randint(2, 4)
            selected = random.sample(transforms, n_transforms)
            for name, fn in selected:
                result = fn(result)
                applied.append(name)

            filename = f"positive_{registry_id}_{i+1:03d}.png"
            output_path = os.path.join(self.output_dir, filename)
            result.save(output_path, "PNG")
            paths.append(output_path)
            logger.debug(f"Generated {filename} with transforms: {applied}")

        return paths
