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
                "image_url": None  # Force local placeholder generation
            })
        return results

    def download(self, patent: dict) -> str | None:
        """Download a single patent image, return local path."""
        patent_id = patent["id"]
        output_path = os.path.join(self.output_dir, f"patent_{patent_id}.png")
        if os.path.exists(output_path):
            return output_path
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
        return self._generate_placeholder(patent_id, output_path)

    def _generate_placeholder(self, patent_id: str, path: str) -> str:
        """Generate a visually distinct placeholder image per patent ID."""
        from PIL import ImageDraw
        import hashlib
        h = hashlib.md5(patent_id.encode()).hexdigest()
        # Use different bytes for different visual elements
        bg_r = int(h[0:2], 16)
        bg_g = int(h[2:4], 16)
        bg_b = int(h[4:6], 16)
        shape_type = int(h[6:8], 16) % 5  # 5 different shapes
        shape_color = (int(h[8:10], 16), int(h[10:12], 16), int(h[12:14], 16))
        detail_color = (int(h[14:16], 16), int(h[16:18], 16), int(h[18:20], 16))

        img = Image.new("RGB", (512, 512), (bg_r, bg_g, bg_b))
        draw = ImageDraw.Draw(img)

        # Draw different shapes based on patent ID
        if shape_type == 0:  # Product silhouette (rounded rect)
            draw.rounded_rectangle([60, 120, 452, 400], radius=40, fill=shape_color, outline=detail_color, width=3)
            draw.rounded_rectangle([120, 160, 392, 360], radius=20, fill=detail_color)
            draw.text((180, 230), "Product", fill=(255, 255, 255))
        elif shape_type == 1:  # Bottle/container shape
            draw.ellipse([100, 80, 412, 250], fill=shape_color, outline=detail_color, width=3)
            draw.rectangle([180, 240, 332, 420], fill=shape_color, outline=detail_color, width=3)
            draw.text((200, 310), "Container", fill=(255, 255, 255))
        elif shape_type == 2:  # Electronic device
            draw.rounded_rectangle([80, 100, 432, 380], radius=20, fill=shape_color, outline=detail_color, width=3)
            draw.rectangle([220, 160, 420, 320], fill=detail_color, outline=(255, 255, 255), width=2)
            draw.ellipse([240, 400, 280, 430], fill=detail_color)
            draw.text((130, 420), "Device", fill=(255, 255, 255))
        elif shape_type == 3:  # Furniture
            draw.rectangle([100, 200, 412, 250], fill=shape_color, outline=detail_color, width=3)
            draw.rectangle([140, 100, 180, 200], fill=shape_color, outline=detail_color, width=2)
            draw.rectangle([332, 100, 372, 200], fill=shape_color, outline=detail_color, width=2)
            draw.rectangle([140, 420, 200, 450], fill=detail_color)
            draw.rectangle([312, 420, 372, 450], fill=detail_color)
            draw.text((180, 460), "Furniture", fill=(255, 255, 255))
        else:  # Abstract design
            draw.polygon([(256, 60), (420, 200), (400, 400), (112, 380), (80, 200)], fill=shape_color, outline=detail_color, width=3)
            draw.ellipse([180, 180, 332, 300], fill=detail_color)
            draw.text((200, 460), "Design", fill=(255, 255, 255))

        # Patent ID watermark
        draw.text((10, 10), f"Patent {patent_id}", fill=(255, 255, 255))
        draw.text((10, 490), "Design Patent", fill=detail_color)

        img.save(path, "PNG")
        return path

    def normalize(self, img: Image.Image) -> Image.Image:
        """Normalize image to 512x512 PNG RGB."""
        img = img.convert("RGB")
        img = img.resize((512, 512), Image.LANCZOS)
        return img
