"""Patent image collector for design patent datasets."""
import csv
import os
import logging
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class RegistryCollector:
    """Import or download design patent registry images."""

    BASE_URL = "http://epub.sipo.gov.cn"
    SEARCH_URL = f"{BASE_URL}/advancedSearch"

    def __init__(
        self,
        output_dir: str = "datasets/registry/外观设计专利",
        allow_placeholder: bool = False,
    ):
        self.output_dir = output_dir
        self.allow_placeholder = allow_placeholder
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        os.makedirs(output_dir, exist_ok=True)

    def collect_from_file(self, manifest_path: str, limit: int | None = None) -> list[dict]:
        """Import registry images from a CSV manifest.

        Supported rows:
        - registry_id,image_path
        - registry_id
        - registry_id,image_url
        """
        records = []
        with open(manifest_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().startswith("#"):
                    continue
                if row[0].strip() == "registry_id":
                    continue
                registry_id = row[0].strip()
                image_ref = row[1].strip() if len(row) > 1 else ""
                is_url = self._is_url(image_ref)
                patent = {
                    "id": registry_id,
                    "title": registry_id,
                    "image_path": image_ref if image_ref and not is_url else None,
                    "image_url": image_ref if is_url else None,
                    "source": "url_manifest" if is_url else "local_manifest",
                }
                path = self.download(patent)
                if path:
                    records.append({**patent, "path": path})
                if limit is not None and len(records) >= limit:
                    break
        return records

    def search(self, keyword: str, limit: int = 5) -> list[dict]:
        """Search design patents by keyword. Returns list of {id, title, image_url}."""
        results = []
        try:
            search_url = "http://epub.sipo.gov.cn/patentoutline.action"
            params = {
                "showType": "1",
                "pageSize": str(limit),
                "pageNow": "1",
                "searchExp": keyword,
                "patentType": "design",
            }
            resp = self.session.get(search_url, params=params, timeout=30)
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select("table.table_list tr")[1:]
            for item in items[:limit]:
                cols = item.find_all("td")
                if len(cols) >= 3:
                    patent_id = cols[1].get_text(strip=True)
                    title = cols[2].get_text(strip=True)
                    img_url = self._build_image_url(patent_id)
                    results.append({"id": patent_id, "title": title, "image_url": img_url})
        except Exception as e:
            logger.warning(f"Search failed for '{keyword}': {e}")

        if not results:
            if self.allow_placeholder:
                results = self._fallback_search(keyword, limit)
            else:
                logger.warning("No search results for '%s'; placeholder disabled", keyword)
        return results

    @staticmethod
    def _is_url(value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")

    def _build_image_url(self, patent_id: str) -> str:
        return f"http://epub.sipo.gov.cn/patentimg/{patent_id}"

    def _fallback_search(self, keyword: str, limit: int) -> list[dict]:
        results = []
        for i in range(limit):
            fake_id = f"CN202430{100000 + i}"
            results.append({
                "id": fake_id,
                "title": f"{keyword} 外观设计专利",
                "image_url": None  # Force local placeholder generation
            })
        return results

    def download(self, patent: dict) -> str | None:
        """Download a single patent image, return local path."""
        patent_id = patent["id"]
        output_path = os.path.join(self.output_dir, f"patent_{patent_id}.png")
        if os.path.exists(output_path):
            return output_path
        local_path = patent.get("image_path")
        if local_path:
            try:
                img = Image.open(local_path)
                img = self.normalize(img)
                img.save(output_path, "PNG")
                return output_path
            except Exception as e:
                logger.warning("Local import failed for %s: %s", patent_id, e)
        try:
            url = patent.get("image_url")
            if url:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    img = Image.open(BytesIO(resp.content))
                    img = self.normalize(img)
                    img.save(output_path, "PNG")
                    return output_path
        except Exception as e:
            logger.warning(f"Download failed for {patent_id}: {e}")
        if self.allow_placeholder:
            return self._generate_placeholder(patent_id, output_path)
        logger.warning("Skipping %s; no usable image source and placeholder disabled", patent_id)
        return None

    def _generate_placeholder(self, patent_id: str, path: str) -> str:
        """Generate a deterministic fixture image for tests and demos only."""
        from PIL import ImageDraw
        import hashlib
        h = hashlib.md5(patent_id.encode()).hexdigest()
        
        # Every visual element derived from different hash bytes → unique per ID
        bg_r = int(h[0:2], 16)
        bg_g = int(h[2:4], 16)
        bg_b = int(h[4:6], 16)
        
        img = Image.new("RGB", (512, 512), (bg_r, bg_g, bg_b))
        draw = ImageDraw.Draw(img)
        
        # Extract many parameters from the hash for unique geometry
        p = [int(h[i:i+2], 16) for i in range(0, 32, 2)]  # 16 params (0-255)
        
        # P1: product body type (8 variations)
        body_type = p[0] % 8
        
        # P2-3: body dimensions (unique per patent)
        bx = 40 + p[1] % 80          # 40-120
        by = 60 + p[2] % 120          # 60-180
        bw = 280 + p[3] % 150         # 280-430
        bh = 200 + p[4] % 130         # 200-330
        
        # P4: body color
        body_color = (p[5], p[6], p[7])
        
        # P5: accent / detail color
        accent_color = (p[8], p[9], p[10])
        
        # P6-7: detail element positions (unique per patent)
        dx1 = bx + 20 + p[11] % (bw - 80)
        dy1 = by + 20 + p[12] % (bh - 80)
        dx2 = bx + 20 + p[13] % (bw - 80)
        dy2 = by + 20 + p[14] % (bh - 80)
        
        # P8: extra element type
        extra_type = p[15] % 4
        
        if body_type == 0:
            draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=30, fill=body_color, outline=accent_color, width=3)
        elif body_type == 1:
            draw.ellipse([bx, by, bx+bw, by+bh], fill=body_color, outline=accent_color, width=3)
        elif body_type == 2:
            draw.rectangle([bx, by, bx+bw, by+bh], fill=body_color, outline=accent_color, width=3)
        elif body_type == 3:
            # Rounded top, flat bottom
            draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=50, fill=body_color, outline=accent_color, width=3)
            draw.rectangle([bx+20, by+bh//2, bx+bw-20, by+bh], fill=accent_color)
        elif body_type == 4:
            # Two-part shape
            draw.rounded_rectangle([bx, by, bx+bw, by+bh//2], radius=25, fill=body_color, outline=accent_color, width=3)
            draw.rounded_rectangle([bx+15, by+bh//2, bx+bw-15, by+bh], radius=15, fill=accent_color, outline=body_color, width=2)
        elif body_type == 5:
            # Vertical split
            draw.rectangle([bx, by, bx+bw//2, by+bh], fill=body_color, outline=accent_color, width=2)
            draw.rectangle([bx+bw//2, by, bx+bw, by+bh], fill=accent_color, outline=body_color, width=2)
        elif body_type == 6:
            # Horizontal bands
            for i in range(3):
                yy = by + i * bh // 3
                color = body_color if i % 2 == 0 else accent_color
                draw.rectangle([bx, yy, bx+bw, yy+bh//3], fill=color)
        else:
            # Hexagonal
            cx, cy = bx + bw//2, by + bh//2
            r = min(bw, bh) // 2
            import math
            pts = []
            for i in range(6):
                angle = math.pi/3 * i - math.pi/6
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            draw.polygon(pts, fill=body_color, outline=accent_color, width=3)
        
        # Add unique detail elements (position varies per patent)
        if extra_type == 0:
            draw.ellipse([dx1-15, dy1-15, dx1+15, dy1+15], fill=accent_color)
            draw.ellipse([dx2-10, dy2-10, dx2+10, dy2+10], fill=body_color)
        elif extra_type == 1:
            draw.rectangle([dx1-20, dy1-10, dx1+20, dy1+10], fill=accent_color)
            draw.rectangle([dx2-10, dy2-20, dx2+10, dy2+20], fill=body_color)
        elif extra_type == 2:
            draw.line([(dx1, dy1-20), (dx1, dy1+20)], fill=accent_color, width=4)
            draw.line([(dx1-20, dy1), (dx1+20, dy1)], fill=accent_color, width=4)
        else:
            pts = [(dx1, dy1-15), (dx1+15, dy1+10), (dx1-15, dy1+10)]
            draw.polygon(pts, fill=accent_color)
        
        # Watermark
        draw.text((10, 10), f"Patent {patent_id}", fill=(255, 255, 255))
        draw.text((10, 490), "Design Patent", fill=accent_color)

        img.save(path, "PNG")
        return path

    def normalize(self, img: Image.Image) -> Image.Image:
        """Normalize image to 512x512 PNG RGB."""
        img = img.convert("RGB")
        img = img.resize((512, 512), Image.LANCZOS)
        return img
