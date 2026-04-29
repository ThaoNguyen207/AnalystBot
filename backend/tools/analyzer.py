import pandas as pd
import numpy as np
from typing import List, Dict, Optional


# ─── Main Analysis ────────────────────────────────────────────────────────────

def analyze(df: pd.DataFrame, prev_df: Optional[pd.DataFrame] = None) -> Dict:
    """Full statistical analysis + auto-generated insights."""
    if df.empty:
        return {"error": "Không có dữ liệu để phân tích"}

    priced = df[df["price"] > 0]

    result = {
        "summary": _summary(df, priced),
        "by_category": _by_category(df),
        "price_distribution": _price_distribution(priced),
        "top_expensive": _top_n(priced, "price", 10, ascending=False),
        "top_cheapest": _top_n(priced, "price", 10, ascending=True),
        "top_rated": _top_n(df[df["rating"] > 0], "rating", 10, ascending=False),
        "outliers": _outliers(priced),
        "insights": _insights(df, priced, prev_df),
        "chart_data": _chart_data(df, priced),
    }
    return result


# ─── Sub-functions ────────────────────────────────────────────────────────────

def _summary(df: pd.DataFrame, priced: pd.DataFrame) -> Dict:
    cats = df["category"].nunique()
    
    # Detect unit - try 'unit' column first, then fallback to parsing price_raw
    unit = "đ"
    if "unit" in df.columns and not df["unit"].dropna().empty:
        unit = df["unit"].mode().iloc[0]
    elif not priced.empty and "price_raw" in priced.columns:
        # Fallback: scan price_raw for symbols
        raw_text = " ".join(priced["price_raw"].astype(str).unique()[:10])
        if "£" in raw_text or "Â£" in raw_text: unit = "£"
        elif "$" in raw_text: unit = "$"
        elif "€" in raw_text: unit = "€"
        elif "đ" in raw_text or "VND" in raw_text: unit = "đ"
        
    return {
        "total_items": len(df),
        "items_with_price": len(priced),
        "categories": cats,
        "unit": unit,
        "avg_price": round(float(priced["price"].mean()), 2) if not priced.empty else 0,
        "median_price": round(float(priced["price"].median()), 2) if not priced.empty else 0,
        "min_price": round(float(priced["price"].min()), 2) if not priced.empty else 0,
        "max_price": round(float(priced["price"].max()), 2) if not priced.empty else 0,
        "std_price": round(float(priced["price"].std()), 2) if not priced.empty else 0,
        "avg_rating": round(float(df[df["rating"] > 0]["rating"].mean()), 2) if (df["rating"] > 0).any() else 0,
    }


def _by_category(df: pd.DataFrame) -> List[Dict]:
    if "category" not in df.columns:
        return []
    grp = df.groupby("category").agg(
        count=("name", "count"),
        avg_price=("price", "mean"),
        max_price=("price", "max"),
        min_price=("price", "min"),
        avg_rating=("rating", "mean"),
    ).reset_index()
    grp = grp.sort_values("count", ascending=False)
    grp["avg_price"] = grp["avg_price"].round(2)
    grp["max_price"] = grp["max_price"].round(2)
    grp["min_price"] = grp["min_price"].round(2)
    grp["avg_rating"] = grp["avg_rating"].round(2)
    return grp.to_dict(orient="records")


def _price_distribution(priced: pd.DataFrame) -> List[Dict]:
    if priced.empty:
        return []
    try:
        labels, bins = pd.cut(priced["price"], bins=6, retbins=True)
        counts = labels.value_counts(sort=False)
        dist = []
        for interval, count in counts.items():
            dist.append({
                "range": f"{interval.left:,.0f} – {interval.right:,.0f}",
                "count": int(count),
            })
        return dist
    except Exception:
        return []


def _top_n(df: pd.DataFrame, col: str, n: int, ascending: bool) -> List[Dict]:
    if df.empty:
        return []
    top = df.nsmallest(n, col) if ascending else df.nlargest(n, col)
    cols = [c for c in ["name", "price", "price_raw", "category", "rating", "url"] if c in top.columns]
    return top[cols].fillna("").round(2).to_dict(orient="records")


def _outliers(priced: pd.DataFrame) -> List[Dict]:
    if len(priced) < 4:
        return []
    q1 = priced["price"].quantile(0.25)
    q3 = priced["price"].quantile(0.75)
    iqr = q3 - q1
    mask = (priced["price"] < q1 - 1.5 * iqr) | (priced["price"] > q3 + 1.5 * iqr)
    out = priced[mask][["name", "price", "category"]].head(10)
    return out.fillna("").round(2).to_dict(orient="records")


def _insights(df: pd.DataFrame, priced: pd.DataFrame, prev_df: Optional[pd.DataFrame]) -> List[str]:
    insights = []
    
    # Detect unit for insights
    unit = "đ"
    if "unit" in df.columns and not df["unit"].dropna().empty:
        unit = df["unit"].mode().iloc[0]

    if priced.empty:
        insights.append("⚠️ Dữ liệu không chứa thông tin về giá/giá trị số.")
        return insights

    avg = priced["price"].mean()
    mx  = priced["price"].max()
    mn  = priced["price"].min()
    total = len(df)
    cats = df["category"].nunique()

    # 1. Tổng quan cấu trúc
    insights.append(f"📊 Bộ dữ liệu có {total} bản ghi thuộc {cats} nhóm ngành/danh mục.")
    
    # 2. Phân tích giá trị
    insights.append(f"💰 Trung bình: {avg:,.0f}{unit} | Thấp nhất: {mn:,.0f}{unit} | Cao nhất: {mx:,.0f}{unit}")

    # 3. Nồng độ dữ liệu (Category dominance)
    cat_counts = df["category"].value_counts()
    if not cat_counts.empty:
        top_cat = cat_counts.index[0]
        pct = (cat_counts.iloc[0] / total) * 100
        insights.append(f"📦 Nhóm '{top_cat}' chiếm ưu thế với {pct:.1f}% tổng lượng dữ liệu.")

    # 4. Nhóm đắt đỏ nhất
    cat_avg = priced.groupby("category")["price"].mean()
    if len(cat_avg) > 1:
        most_expensive_cat = cat_avg.idxmax()
        insights.append(f"🔝 Nhóm '{most_expensive_cat}' có giá trị trung bình cao nhất ({cat_avg.max():,.0f}{unit}).")

    # 5. Phân tích chất lượng (Rating)
    rated = df[df["rating"] > 0]
    if not rated.empty:
        avg_rat = rated["rating"].mean()
        insights.append(f"⭐ Đánh giá trung bình: {avg_rat:.2f}/5 stars.")

    # 6. Cảnh báo bất thường (Outliers)
    q1, q3 = priced["price"].quantile(0.25), priced["price"].quantile(0.75)
    iqr = q3 - q1
    n_outliers = int(((priced["price"] < q1 - 1.5 * iqr) | (priced["price"] > q3 + 1.5 * iqr)).sum())
    if n_outliers > 0:
        insights.append(f"⚠️ Phát hiện {n_outliers} bản ghi có giá trị chênh lệch lớn so với phần còn lại.")

    # 7. So sánh lịch sử (Trend)
    if prev_df is not None and not prev_df.empty:
        prev_priced = prev_df[prev_df["price"] > 0]
        if not prev_priced.empty:
            prev_avg = prev_priced["price"].mean()
            change = (avg - prev_avg) / prev_avg * 100
            trend = "📈 TĂNG" if change > 0 else "📉 GIẢM"
            insights.append(f"🔄 Xu hướng: Giá trung bình {trend} {abs(change):.1f}% so với phiên trước đó.")

    return insights


def _chart_data(df: pd.DataFrame, priced: pd.DataFrame) -> Dict:
    """Return data ready for Chart.js — handles both small and large datasets."""

    # ── Bar: items per category (top 12, merge rest into "Other") ─────────────
    cat_counts = df["category"].value_counts()
    if len(cat_counts) > 12:
        top12    = cat_counts.head(12)
        other_n  = cat_counts.iloc[12:].sum()
        cat_counts = pd.concat([top12, pd.Series({"Other": int(other_n)})])
    bar_cat = {
        "labels": [str(l) for l in cat_counts.index.tolist()],
        "data":   [int(v) for v in cat_counts.values.tolist()],
    }

    # ── Pie: price distribution (6 adaptive buckets) ──────────────────────────
    dist = _price_distribution(priced)
    pie_dist = {
        "labels": [d["range"] for d in dist],
        "data":   [d["count"] for d in dist],
    }

    # ── Horizontal bar: avg price per category (top 10) ───────────────────────
    if not priced.empty:
        cat_avg = (
            priced.groupby("category")["price"]
            .mean()
            .sort_values(ascending=False)
            .head(10)
            .round(2)
        )
        hbar = {
            "labels": [str(l) for l in cat_avg.index.tolist()],
            "data":   [float(v) for v in cat_avg.values.tolist()],
        }
    else:
        hbar = {"labels": [], "data": []}

    # ── Scatter: price vs rating (sample max 200 to keep it readable) ─────────
    scatter_df = df[(df["price"] > 0) & (df["rating"] > 0)].copy()
    if len(scatter_df) > 200:
        scatter_df = scatter_df.sample(200, random_state=42)
    scatter = [
        {"x": round(float(r["price"]), 2), "y": round(float(r["rating"]), 1)}
        for _, r in scatter_df.iterrows()
    ]

    # ── Line: avg price per category sorted by count (trend-style) ────────────
    if not priced.empty and len(priced["category"].unique()) >= 2:
        cat_order = df["category"].value_counts().head(10).index
        line_data = [
            round(float(priced[priced["category"] == c]["price"].mean()), 2)
            if len(priced[priced["category"] == c]) > 0 else 0
            for c in cat_order
        ]
        line = {"labels": [str(l) for l in cat_order.tolist()], "data": line_data}
    else:
        line = {"labels": [], "data": []}

    return {
        "bar_category":        bar_cat,
        "pie_distribution":    pie_dist,
        "hbar_avg_price":      hbar,
        "scatter_price_rating": scatter,
        "line_trend":          line,
    }



# ─── Query helpers (used by chat agent) ─────────────────────────────────────

def get_top_products(df: pd.DataFrame, n: int = 5, order: str = "desc", category: str = "") -> List[Dict]:
    sub = df.copy()
    if category:
        sub = sub[sub["category"].str.lower().str.contains(category.lower(), na=False)]
    priced = sub[sub["price"] > 0]
    if priced.empty:
        return []
    result = priced.nlargest(n, "price") if order == "desc" else priced.nsmallest(n, "price")
    return result[["name", "price", "price_raw", "category", "rating"]].fillna("").round(2).to_dict(orient="records")


def generate_context_summary(df: pd.DataFrame) -> str:
    """Create a textual summary of the dataset for LLM ingestion."""
    if df.empty: return "Trống (không có dữ liệu)."
    
    total = len(df)
    cats = df['category'].unique() if 'category' in df.columns else []
    avg_p = df['price'].mean() if 'price' in df.columns else 0
    max_p = df['price'].max() if 'price' in df.columns else 0
    top5 = df.nlargest(5, 'price')['name'].tolist() if 'price' in df.columns else []
    
    summary = f"Bộ dữ liệu hiện tại có {total} bản ghi.\n"
    summary += f"Danh mục: {', '.join([str(c) for c in cats[:10]])}...\n"
    summary += f"Giá trị trung bình: {avg_p:,.2f}.\n"
    summary += f"Cái cao nhất có giá trị: {max_p:,.2f}.\n"
    summary += f"Top 5 đối tượng hàng đầu: {', '.join(top5)}.\n"
    
    # Football specific
    if 'goals' in df.columns:
        top_scorer = df.nlargest(1, 'goals').iloc[0]
        summary += f"Top ghi bàn: {top_scorer['name']} với {top_scorer['goals']} bàn.\n"
        
    return summary
