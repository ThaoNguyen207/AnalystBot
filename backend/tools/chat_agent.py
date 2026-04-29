import re
from typing import Dict, List, Tuple, Optional
import pandas as pd

# ─── Intent definitions ────────────────────────────────────────────────────────

INTENTS = {
    "CRAWL": {
        "patterns": [r"crawl", r"cào", r"lấy dữ liệu", r"thu thập", r"scrape", r"tải trang", r"nhập url", r"fetch"],
        "desc": "Crawl dữ liệu từ URL",
    },
    "SCORERS": {
        "patterns": [r"ghi bàn", r"scorer", r"goal", r"bàn thắng", r"ai ghi", r"ghi được", r"top ghi"],
        "desc": "Top cầu thủ ghi bàn nhiều nhất",
    },
    "ASSISTERS": {
        "patterns": [r"kiến tạo", r"assist", r"chuyền", r"phát động", r"top kiến"],
        "desc": "Top cầu thủ kiến tạo nhiều nhất",
    },
    "POINTS": {
        "patterns": [r"điểm fpl", r"fpl point", r"tổng điểm", r"nhiều điểm nhất", r"top điểm", r"điểm cao"],
        "desc": "Top điểm FPL",
    },
    "TEAM_STATS": {
        "patterns": [r"đội bóng", r"team", r"câu lạc bộ", r"clb", r"thống kê đội", r"bảng đội"],
        "desc": "Thống kê theo đội bóng",
    },
    "ANALYZE": {
        "patterns": [r"phân tích", r"analyze", r"thống kê", r"tóm tắt", r"summary", r"tổng hợp", r"xem kết quả"],
        "desc": "Phân tích dữ liệu hiện tại",
    },
    "TOP_N": {
        "patterns": [r"top\s*\d*", r"đắt nhất", r"rẻ nhất", r"cao nhất", r"thấp nhất", r"xếp hạng", r"best", r"worst"],
        "desc": "Lấy top N sản phẩm",
    },
    "CHART": {
        "patterns": [r"biểu đồ", r"chart", r"đồ thị", r"vẽ", r"graph", r"plot", r"histogram"],
        "desc": "Xem biểu đồ",
    },
    "INSIGHT": {
        "patterns": [r"insight", r"nhận xét", r"đánh giá", r"gợi ý", r"xu hướng", r"trend", r"so sánh"],
        "desc": "Insight tự động",
    },
    "HISTORY": {
        "patterns": [r"lịch sử", r"history", r"report cũ", r"trước đây", r"session"],
        "desc": "Xem lịch sử phân tích",
    },
    "EXPORT": {
        "patterns": [r"xuất", r"export", r"tải xuống", r"download", r"csv", r"excel"],
        "desc": "Xuất dữ liệu",
    },
    "TOTAL": {
        "patterns": [r"tổng", r"bao nhiêu", r"how many", r"số lượng", r"đếm", r"tổng cộng", r"tất cả"],
        "desc": "Tính tổng số lượng hoặc giá trị",
    },
    "AVERAGE": {
        "patterns": [r"trung bình", r"average", r"giá tb", r"điểm tb", r"mức chung", r"tb"],
        "desc": "Tính giá trị trung bình",
    },
    "SEARCH": {
        "patterns": [r"tìm", r"find", r"search", r"đâu", r"có không", r"kiếm", r"lọc"],
        "desc": "Tìm kiếm bản ghi cụ thể",
    },
    "COMPARE": {
        "patterns": [r"so sánh", r"khác biệt", r"hơn", r"kém", r"chênh lệch", r"vs", r"compare"],
        "desc": "So sánh giữa các thực thể",
    },
    "HELP": {
        "patterns": [r"giúp", r"help", r"hướng dẫn", r"làm gì được", r"tính năng", r"có thể làm"],
        "desc": "Hướng dẫn sử dụng",
    },
    "CLEAR": {
        "patterns": [r"xóa", r"clear", r"reset", r"làm mới", r"bắt đầu lại"],
        "desc": "Xóa dữ liệu hiện tại",
    },
}

HELP_TEXT = """
🤖 **Data Analyst Bot — Hướng dẫn sử dụng**

Bạn có thể hỏi tôi bằng **tiếng Việt hoặc tiếng Anh**. Ví dụ:

📥 **Thu thập dữ liệu:**
- "Crawl trang books.toscrape.com"
- "Lấy dữ liệu từ https://..."

📊 **Phân tích:**
- "Phân tích dữ liệu"
- "Thống kê tổng hợp"

🏆 **Top sản phẩm:**
- "Top 5 sản phẩm đắt nhất"
- "Top 10 rẻ nhất loại Mystery"

📈 **Biểu đồ:**
- "Xem biểu đồ giá"
- "Vẽ chart theo danh mục"

💡 **Insight:**
- "Nhận xét về dữ liệu"
- "So sánh với lần trước"

📤 **Export:**
- "Xuất CSV"

📜 **Lịch sử:**
- "Xem lịch sử phân tích"
"""


# ─── Agent class ──────────────────────────────────────────────────────────────

class ChatAgent:
    def __init__(self):
        self._compiled = {
            intent: [re.compile(p, re.IGNORECASE) for p in info["patterns"]]
            for intent, info in INTENTS.items()
        }

    def detect_intent(self, text: str) -> Tuple[str, int]:
        """Return (intent, score). Higher score = more confident."""
        scores: Dict[str, int] = {}
        for intent, patterns in self._compiled.items():
            score = sum(1 for p in patterns if p.search(text))
            if score:
                scores[intent] = score
        if not scores:
            return "UNKNOWN", 0
        best = max(scores, key=lambda k: scores[k])
        return best, scores[best]

    def detect_schema(self, df: Optional[pd.DataFrame]) -> Dict:
        if df is None or df.empty:
            return {"type": "general", "label": "bản ghi", "unit": ""}
        cols = [c.lower() for c in df.columns]
        
        if any(x in cols for x in ["goals", "assists"]):
            return {"type": "football", "label": "cầu thủ", "unit": "điểm"}
        
        # Check for book-related terms
        if any(x in cols for x in ["title", "author", "isbn", "pages"]):
             return {"type": "books", "label": "cuốn sách", "unit": "cuốn"}
             
        # Check if most price_raw strings contain £, $, €
        return {"type": "general", "label": "sản phẩm", "unit": "mục"}

    def extract_slots(self, text: str) -> Dict:
        slots = {"n": 5, "order": "desc", "category": "", "query": "", "provider": "auto"}
        t = text.lower()
        
        # Provider detection
        if "gemini" in t: slots["provider"] = "gemini"
        elif "openai" in t: slots["provider"] = "openai"
        elif "groq" in t: slots["provider"] = "groq"

        m = re.search(r"top\s*(\d+)", t)
        if m: slots["n"] = int(m.group(1))
        if any(k in t for k in ["rẻ", "thấp", "ít", "kém", "tệ"]): slots["order"] = "asc"
        
        # Extract subject/category robustly
        # Look for text between quotes or after common prepositions
        subject_m = re.search(r"['\"]([^'\"]+)['\"]", t) # Text in quotes
        if subject_m: 
            slots["category"] = subject_m.group(1).strip()
        else:
            # Fallback: capture text after "của", "về", "cuốn", "sách", "tên là"
            prep_m = re.search(r"(?:của|về|cuốn|sách|tên là|là)\s+([a-zA-ZÀ-ỹ0-9\s\-]{3,})", t)
            if prep_m:
                # Clean up: stop at "giá", "là", "nhiều"
                clean_val = re.split(r"\s+(?:giá|là|nhiều|bao|trong)\b", prep_m.group(1))[0]
                slots["category"] = clean_val.strip()
            
        return slots

    def respond(self, text: str, df: Optional[pd.DataFrame] = None, context: Dict = None) -> Dict:
        intent, score = self.detect_intent(text)
        slots = self.extract_slots(text)

        # Fallback: If intent is weak but we have a candidate name/subject, force SEARCH
        if slots["category"] and (intent == "UNKNOWN" or intent == "AVERAGE" or score < 1):
            intent = "SEARCH"

        context = context or {}

        if intent == "HELP" or (intent == "UNKNOWN" and score == 0):
            return {
                "intent": "HELP",
                "message": HELP_TEXT,
                "action": None,
                "slots": slots,
                "data": None,
            }

        if intent == "CRAWL":
            # Try to extract URL from message
            url_m = re.search(r"https?://[^\s]+", text)
            url = url_m.group() if url_m else None
            if not url:
                # Try to find domain-like text
                dom_m = re.search(r"(?:trang|site|web|url|từ)\s+([\w\-\.]+\.\w{2,})", text, re.IGNORECASE)
                url = "http://" + dom_m.group(1) if dom_m else None
            return {
                "intent": "CRAWL",
                "message": f"🕷️ Chuẩn bị crawl: **{url or 'Vui lòng nhập URL'}**",
                "action": "crawl",
                "slots": {**slots, "url": url},
                "data": None,
            }

        if intent == "SCORERS":
            return {
                "intent": "SCORERS",
                "message": f"⚽ Đang tải top {slots['n']} cầu thủ ghi bàn nhiều nhất...",
                "action": "top_scorers",
                "slots": slots,
                "data": None,
            }

        if intent == "ASSISTERS":
            return {
                "intent": "ASSISTERS",
                "message": f"🎯 Đang tải top {slots['n']} cầu thủ kiến tạo nhiều nhất...",
                "action": "top_assisters",
                "slots": slots,
                "data": None,
            }

        if intent == "POINTS":
            return {
                "intent": "POINTS",
                "message": f"🏆 Đang tải top {slots['n']} cầu thủ nhiều điểm FPL nhất...",
                "action": "top_points",
                "slots": slots,
                "data": None,
            }

        if intent == "TEAM_STATS":
            return {
                "intent": "TEAM_STATS",
                "message": "🏟️ Đang tải thống kê theo đội bóng...",
                "action": "team_stats",
                "slots": slots,
                "data": None,
            }

        if intent == "TOP_N":
            if df is None or df.empty:
                return self._no_data()
            from tools.analyzer import get_top_products
            top = get_top_products(df, n=slots["n"], order=slots["order"], category=slots["category"])
            label = "đắt nhất" if slots["order"] == "desc" else "rẻ nhất"
            cat_label = f" loại **{slots['category']}**" if slots["category"] else ""
            msg = f"🏆 Top {slots['n']} sản phẩm {label}{cat_label}:"
            return {
                "intent": "TOP_N",
                "message": msg,
                "action": None,
                "slots": slots,
                "data": top,
            }

        if intent == "ANALYZE":
            if df is None or df.empty:
                return self._no_data()
            return {
                "intent": "ANALYZE",
                "message": "📊 Đang chạy phân tích toàn diện...",
                "action": "analyze",
                "slots": slots,
                "data": None,
            }

        if intent == "CHART":
            return {
                "intent": "CHART",
                "message": "📈 Đang tải biểu đồ...",
                "action": "show_chart",
                "slots": slots,
                "data": None,
            }

        if intent == "INSIGHT":
            if df is None or df.empty:
                return self._no_data()
            return {
                "intent": "INSIGHT",
                "message": "💡 Đang tạo insight tự động...",
                "action": "insight",
                "slots": slots,
                "data": None,
            }

        if intent == "HISTORY":
            return {
                "intent": "HISTORY",
                "message": "📜 Đang tải lịch sử phân tích...",
                "action": "history",
                "slots": slots,
                "data": None,
            }

        if intent == "EXPORT":
            return {
                "intent": "EXPORT",
                "message": "📤 Chuẩn bị file CSV để tải xuống...",
                "action": "export",
                "slots": slots,
                "data": None,
            }

        if intent == "TOTAL":
            if df is None or df.empty: return self._no_data()
            count = len(df)
            msg = f"📊 Tổng cộng có **{count}** bản ghi trong bộ dữ liệu hiện tại."
            if "category" in slots and slots["category"]:
                c_df = df[df['category'].str.contains(slots["category"], case=False, na=False)]
                msg = f"📊 Có **{len(c_df)}** bản ghi thuộc danh mục **{slots['category']}**."
            return {"intent": "TOTAL", "message": msg, "action": None, "slots": slots, "data": None}

        if intent == "AVERAGE":
            if df is None or df.empty: return self._no_data()
            avg_price = df['price'].mean()
            msg = f"💰 Giá trị trung bình của toàn bộ dữ liệu là **{avg_price:,.2f}**."
            if "category" in slots and slots["category"]:
                c_df = df[df['category'].str.contains(slots["category"], case=False, na=False)]
                if not c_df.empty:
                    msg = f"💰 Giá trị trung bình của danh mục **{slots['category']}** là **{c_df['price'].mean():,.2f}**."
            return {"intent": "AVERAGE", "message": msg, "action": None, "slots": slots, "data": None}

        if intent == "SEARCH":
            if df is None or df.empty: return self._no_data()
            # Extract query - everything after "tìm" or "search"
            q = re.sub(r"tìm|search|find|kiếm|đâu|có không", "", text, flags=re.IGNORECASE).strip()
            results = df[df['name'].str.contains(q, case=False, na=False)].head(10).to_dict('records')
            if not results:
                return {"intent": "SEARCH", "message": f"🔍 Không tìm thấy kết quả nào cho: **{q}**", "action": None, "slots": slots, "data": None}
            return {"intent": "SEARCH", "message": f"🔍 Tìm thấy **{len(results)}** kết quả cho: **{q}** (hiển thị tối đa 10):", "action": "show_search", "slots": slots, "data": results}

        if intent == "COMPARE":
             return {"intent": "COMPARE", "message": "⚖️ Tính năng so sánh nâng cao đang được kích hoạt. Hãy thử hỏi 'So sánh giá của X và Y' hoặc 'Xem chênh lệch danh mục A và B'", "action": "compare", "slots": slots, "data": None}

        if intent == "CLEAR":
            return {
                "intent": "CLEAR",
                "message": "🗑️ Xác nhận xóa toàn bộ dữ liệu? Hãy nhấn nút Xác nhận trên dashboard.",
                "action": "confirm_clear",
                "slots": slots,
                "data": None,
            }

        return {
            "intent": "UNKNOWN",
            "message": "🤔 Tôi chưa hiểu yêu cầu này. Gõ **help** để xem các lệnh hỗ trợ.",
            "action": None,
            "slots": slots,
            "data": None,
        }

    def _no_data(self) -> Dict:
        return {
            "intent": "NO_DATA",
            "message": "⚠️ Chưa có dữ liệu. Hãy crawl một URL trước nhé!",
            "action": "prompt_crawl",
            "slots": {},
            "data": None,
        }
