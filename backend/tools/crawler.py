import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PRICE_RE = re.compile(
    r"(?:₫|VNĐ|VND|đ)\s*[\d,\.]+|"
    r"[\d,\.]+\s*(?:₫|VNĐ|VND|đồng|nghìn|triệu|k\b)|"
    r"\$\s*[\d,\.]+|"
    r"[\d,\.]+\s*(?:USD|EUR|GBP|\$|€|£)|"
    r"£\s*[\d,\.]+",
    re.IGNORECASE,
)

RATING_RE = re.compile(r"(\d(?:[.,]\d)?)\s*(?:/\s*5|sao|stars?|\*)", re.IGNORECASE)


class SmartCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def crawl(self, url: str) -> Dict:
        """Main entry — auto-detect strategy and extract items from any URL."""
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as e:
            return {"success": False, "error": str(e), "items": [], "total": 0}

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        site_name = self._site_name(url)
        domain = urlparse(url).netloc.lower()

        # Specialized strategies first
        if "toscrape" in domain or "books" in domain:
            items = self._crawl_books(soup, url)
            strategy = "books_toscrape"
        elif "premierleague" in domain or "fantasy.premierleague" in domain:
            return self._crawl_premier_league(url)
        elif "shopee" in domain:
            return self._crawl_shopee(url)
        else:
            items, strategy = self._auto_strategy(soup, url)

        items = [i for i in items if i.get("name") or i.get("price", 0) > 0]

        return {
            "success": True,
            "site_name": site_name,
            "strategy": strategy,
            "url": url,
            "total": len(items),
            "items": items[:300],
        }

    # ─── Strategies ───────────────────────────────────────────────────────────

    def _auto_strategy(self, soup, url: str):
        items = self._extract_tables(soup)
        if len(items) >= 2:
            return items, "html_table"

        items = self._extract_articles(soup, url)
        if len(items) >= 2:
            return items, "article_cards"

        items = self._extract_price_elements(soup, url)
        if len(items) >= 2:
            return items, "price_pattern"

        return self._extract_general(soup), "general"

    # ─── Premier League (FPL public API) ───────────────────────────────────────

    def _crawl_premier_league(self, url: str) -> Dict:
        """Use Fantasy PL public API — returns 500+ players with stats."""
        FPL_API = "https://fantasy.premierleague.com/api/bootstrap-static/"
        try:
            resp = self.session.get(FPL_API, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return {"success": False, "error": f"Không lấy được dữ liệu PL: {e}", "items": [], "total": 0}

        teams     = {t["id"]: t["name"] for t in data.get("teams", [])}
        positions = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}

        items = []
        for p in data.get("elements", []):
            cost_m = round(p.get("now_cost", 0) / 10, 1)   # FPL stores price ×10
            team   = teams.get(p.get("team"), "Unknown")
            pos    = positions.get(p.get("element_type"), "Unknown")
            items.append({
                "name":       f"{p.get('first_name','')} {p.get('second_name','')}".strip(),
                "price":      cost_m,
                "price_raw":  f"£{cost_m}M",
                "category":   pos,
                "rating":     float(p.get("total_points", 0)),
                "url":        f"https://www.premierleague.com/players/{p.get('id')}/",
                "image_url":  "",
                "extra_data": json.dumps({
                    "team":        team,
                    "goals":       p.get("goals_scored", 0),
                    "assists":     p.get("assists", 0),
                    "minutes":     p.get("minutes", 0),
                    "form":        p.get("form", "0"),
                    "selected_by": str(p.get("selected_by_percent", "0")) + "%",
                    "status":      p.get("status", ""),
                }, ensure_ascii=False),
            })

        return {
            "success":   True,
            "site_name": "PremierLeague",
            "strategy":  "fpl_api",
            "url":       url,
            "total":     len(items),
            "items":     items,
        }

    # ─── Shopee (Attempting search API) ───────────────────────────────────────

    def _crawl_shopee(self, url: str) -> Dict:
        """Shopee is JS-heavy. Attempt to find keywords in URL or fall back to generic."""
        keyword = ""
        parsed = urlparse(url)
        if "keyword" in parsed.query:
            match = re.search(r"keyword=([^&]+)", parsed.query)
            if match:
                keyword = match.group(1)
        
        if not keyword and "search" not in url:
            # Maybe it's a category/shop URL, try to extract something
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                keyword = path_parts[-1].replace("-", " ")

        if not keyword:
            keyword = "khuyến mãi" # Default search

        # Shopee Search API v4
        API_URL = f"https://shopee.vn/api/v4/search/search_items?by=relevancy&keyword={keyword}&limit=30&newest=0&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2"
        
        headers = HEADERS.copy()
        headers["Referer"] = "https://shopee.vn/"
        
        try:
            resp = self.session.get(API_URL, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = []
                for p in data.get("items", []):
                    item_info = p.get("item_basic", {})
                    if not item_info: continue
                    
                    price = float(item_info.get("price", 0)) / 100000 # Shopee price scaling
                    items.append({
                        "name":      item_info.get("name", "Unknown"),
                        "price":     price,
                        "price_raw": f"{price:,.0f} ₫".replace(",", "."),
                        "category":  "Shopee Item",
                        "rating":    float(item_info.get("item_rating", {}).get("rating_star", 0)),
                        "url":       f"https://shopee.vn/product/{item_info.get('shopid')}/{item_info.get('itemid')}",
                        "image_url": f"https://down-vn.img.susercontent.com/file/{item_info.get('image')}",
                        "extra_data": json.dumps({
                            "shop_location": item_info.get("shop_location"),
                            "historical_sold": item_info.get("historical_sold"),
                            "stock": item_info.get("stock")
                        }, ensure_ascii=False)
                    })
                
                return {
                    "success": True,
                    "site_name": "Shopee",
                    "strategy": "shopee_api",
                    "url": url,
                    "total": len(items),
                    "items": items
                }
        except:
            pass

        # If API fails (most likely), fall back to generic BeautifulSoup BUT warn
        return {
            "success": False, 
            "error": "Shopee chặn truy cập tự động. Vui lòng thử tìm kiếm trên Premier League hoặc Books to Scrape để thấy sức mạnh phân tích của tôi!",
            "items": [], 
            "total": 0
        }

    # ─── books.toscrape.com ───────────────────────────────────────────────────

    def _crawl_books(self, soup, base_url: str) -> List[Dict]:
        items = []
        STARS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
        for art in soup.find_all("article", class_="product_pod"):
            try:
                h3 = art.find("h3")
                a_tag = h3.find("a") if h3 else None
                name = (a_tag.get("title") or a_tag.get_text(strip=True)) if a_tag else "Unknown"

                price_el = art.find("p", class_="price_color")
                price_raw = price_el.get_text(strip=True) if price_el else "£0"
                price = self._parse_price(price_raw)

                rating_el = art.find("p", class_="star-rating")
                rating = 0.0
                if rating_el:
                    for cls in rating_el.get("class", []):
                        if cls in STARS:
                            rating = float(STARS[cls])

                link = art.find("a")
                href = urljoin(base_url, link.get("href", "")) if link else ""
                img = art.find("img")
                img_url = urljoin(base_url, img.get("src", "")) if img else ""
                cat = self._cat_from_url(href) or "Books"

                items.append({
                    "name": name[:300],
                    "price": price,
                    "price_raw": price_raw,
                    "category": cat,
                    "rating": rating,
                    "url": href,
                    "image_url": img_url,
                    "extra_data": "{}",
                })
            except Exception:
                continue
        return items

    # ─── HTML Table ───────────────────────────────────────────────────────────

    def _extract_tables(self, soup) -> List[Dict]:
        items = []
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if not cells:
                    continue
                raw = {headers[i] if i < len(headers) else f"col_{i}": v for i, v in enumerate(cells)}
                norm = self._normalize_row(raw)
                if norm:
                    items.append(norm)
        return items

    def _normalize_row(self, row: Dict) -> Optional[Dict]:
        NAME_K = ["name", "title", "product", "item", "tên", "sản phẩm", "mã"]
        PRICE_K = ["price", "cost", "giá", "đơn giá", "tiền"]
        CAT_K = ["category", "type", "loại", "danh mục"]
        RATE_K = ["rating", "score", "stars", "điểm"]

        name = price_raw = category = ""
        price = rating = 0.0
        extras = {}

        for k, v in row.items():
            kl = k.lower()
            if any(x in kl for x in NAME_K):
                name = v
            elif any(x in kl for x in PRICE_K):
                price_raw = v
                price = self._parse_price(v)
            elif any(x in kl for x in CAT_K):
                category = v
            elif any(x in kl for x in RATE_K):
                try:
                    rating = float(re.sub(r"[^\d\.]", "", v))
                except Exception:
                    pass
            else:
                extras[k] = v

        # Fallback: scan all values for price pattern
        if price == 0.0:
            for v in row.values():
                if PRICE_RE.search(v):
                    price_raw = v
                    price = self._parse_price(v)
                    break

        if not name:
            name = next(iter(row.values()), "")

        return {
            "name": name[:300],
            "price": price,
            "price_raw": price_raw,
            "category": category or "Unknown",
            "rating": rating,
            "url": "",
            "image_url": "",
            "extra_data": json.dumps(extras, ensure_ascii=False),
        }

    # ─── Article / Product Cards ──────────────────────────────────────────────

    def _extract_articles(self, soup, base_url: str) -> List[Dict]:
        candidates = soup.find_all("article")
        if not candidates:
            for ul in soup.find_all("ul"):
                lis = ul.find_all("li", recursive=False)
                if len(lis) >= 3 and sum(1 for li in lis[:5] if PRICE_RE.search(li.get_text())) >= 2:
                    candidates = lis
                    break
        return [i for i in (self._elem_to_item(e, base_url) for e in candidates) if i]

    def _elem_to_item(self, elem, base_url: str) -> Optional[Dict]:
        text = elem.get_text(separator="|", strip=True)
        parts = [p.strip() for p in text.split("|") if p.strip()]
        if not parts:
            return None

        price_raw = ""
        price = 0.0
        for p in parts:
            if PRICE_RE.search(p):
                price_raw = p
                price = self._parse_price(p)
                break

        name_cands = [p for p in parts if not PRICE_RE.search(p) and len(p) > 3]
        name = max(name_cands, key=len) if name_cands else parts[0]

        link = elem.find("a")
        img = elem.find("img")

        rating = 0.0
        m = RATING_RE.search(text)
        if m:
            try:
                rating = float(m.group(1).replace(",", "."))
            except Exception:
                pass

        return {
            "name": name[:300],
            "price": price,
            "price_raw": price_raw,
            "category": "Unknown",
            "rating": rating,
            "url": urljoin(base_url, link.get("href", "")) if link else "",
            "image_url": img.get("src", "") if img else "",
            "extra_data": "{}",
        }

    # ─── Price-element scan ───────────────────────────────────────────────────

    def _extract_price_elements(self, soup, base_url: str) -> List[Dict]:
        items = []
        seen = set()
        for node in soup.find_all(string=PRICE_RE):
            container = node.parent
            for _ in range(5):
                if not container or not container.name:
                    break
                if container.name in ("div", "li", "article", "section", "tr"):
                    cid = id(container)
                    if cid not in seen:
                        seen.add(cid)
                        item = self._elem_to_item(container, base_url)
                        if item:
                            items.append(item)
                    break
                container = container.parent
        return items

    # ─── General fallback ─────────────────────────────────────────────────────

    def _extract_general(self, soup) -> List[Dict]:
        items = []
        seen_prices = set()
        for el in soup.find_all(["p", "span", "div", "td", "li"]):
            text = el.get_text(strip=True)
            m = PRICE_RE.search(text)
            if not m or m.group() in seen_prices:
                continue
            seen_prices.add(m.group())
            price_raw = m.group()
            price = self._parse_price(price_raw)
            prev = el.find_previous_sibling()
            name = prev.get_text(strip=True) if prev else text[:80]
            items.append({
                "name": name[:300],
                "price": price,
                "price_raw": price_raw,
                "category": "General",
                "rating": 0.0,
                "url": "",
                "image_url": "",
                "extra_data": "{}",
            })
        return items[:60]

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _parse_price(self, s: str) -> float:
        if not s:
            return 0.0
        cleaned = re.sub(r"[₫đVNĐVNDUSDEURGBP$€£\s,]", "", s, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^\d\.]", "", cleaned)
        # Multiple dots = VN thousand separator  e.g. 1.990.000
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")
        try:
            return float(cleaned)
        except Exception:
            return 0.0

    def _site_name(self, url: str) -> str:
        host = urlparse(url).netloc.replace("www.", "").replace("m.", "")
        return host.split(".")[0].capitalize() if host else "Unknown"

    def _cat_from_url(self, url: str) -> str:
        parts = [p for p in urlparse(url).path.split("/") if p and p != "catalogue"]
        return parts[-2].replace("-", " ").title() if len(parts) >= 2 else ""
