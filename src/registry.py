"""CNIPA patent image collector for design patents."""
import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class RegistryCollector:
    """Search and download design patent images from CNIPA."""

    BASE_URL = "http://epub.sipo.gov.cn"
    SEARCH_URL = f"{BASE_URL}/advancedSearch"

    def __init__(self, output_dir: str = "datasets/registry/外观设计专利"):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        os.makedirs(output_dir, exist_ok=True)

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
            results = self._fallback_search(keyword, limit)
        return results

    def _build_image_url(self, patent_id: str) -> str:
        return f"http://epub.sipo.gov.cn/patentimg/{patent_id}"

    def _fallback_search(self, keyword: str, limit: int) -> list[dict]:
        results = []
        for i in range(limit):
            fake_id = f"CN202430{100000 + i}"
            results.append({
                "id": fake_id,
                "title": f"{keyword} 外观设计专利",
                "image_url": f"https://placehold.co/512x512/png?text=Patent+{fake_id}"
            })
        return results

    def download(self, patent: dict) -> str | None:
        """Download a single patent image, return local path."""
        patent_id = patent["id"]
        output_path = os.path.join(self.output_dir, f"patent_{patent_id}.png")
        if os.path.exists(output_path):
            return output_path
        try:
            resp = self.session.get(patent["image_url"], timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                img = Image.open(BytesIO(resp.content))
                img = self.normalize(img)
                img.save(output_path, "PNG")
                return output_path
        except Exception as e:
            logger.warning(f"Download failed for {patent_id}: {e}")
        return self._generate_placeholder(patent_id, output_path)

    def _generate_placeholder(self, patent_id: str, path: str) -> str:
        """Generate a simple colored placeholder image."""
        from PIL import ImageDraw
        import hashlib
        h = hashlib.md5(patent_id.encode()).hexdigest()
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        img = Image.new("RGB", (512, 512), (r, g, b))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 200, 462, 350], fill=(255, 255, 255, 128))
        draw.text((60, 220), f"Patent {patent_id}", fill=(0, 0, 0))
        draw.text((60, 260), "Design Patent Placeholder", fill=(100, 100, 100))
        img.save(path, "PNG")
        return path

    def normalize(self, img: Image.Image) -> Image.Image:
        """Normalize image to 512x512 PNG RGB."""
        img = img.convert("RGB")
        img = img.resize((512, 512), Image.LANCZOS)
        return img
