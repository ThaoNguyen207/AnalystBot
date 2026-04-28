import pandas as pd
import re
from typing import List, Dict


def clean_products(raw_items: List[Dict]) -> List[Dict]:
    """Clean and normalise a list of raw product dicts."""
    if not raw_items:
        return []

    df = pd.DataFrame(raw_items)

    # ── Drop exact duplicates ─────────────────────────────────────────────────
    df.drop_duplicates(subset=["name", "price"], inplace=True)

    # ── Name ─────────────────────────────────────────────────────────────────
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["name"] = df["name"].apply(_clean_name)
    df = df[df["name"].str.len() > 0]

    # ── Price ─────────────────────────────────────────────────────────────────
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
    df["price_raw"] = df["price_raw"].fillna("").astype(str).str.strip()

    # Remove rows where price is suspiciously large (> 10B) or negative
    df = df[(df["price"] >= 0) & (df["price"] < 1e10)]

    # ── Category ─────────────────────────────────────────────────────────────
    df["category"] = df["category"].fillna("Unknown").astype(str).str.strip()
    df["category"] = df["category"].apply(lambda x: x if x else "Unknown")

    # ── Rating ────────────────────────────────────────────────────────────────
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0)
    df["rating"] = df["rating"].clip(0, 5)

    # ── URL / image ───────────────────────────────────────────────────────────
    df["url"] = df["url"].fillna("").astype(str)
    df["image_url"] = df["image_url"].fillna("").astype(str)
    df["extra_data"] = df["extra_data"].fillna("{}").astype(str)

    # ── Reset index ───────────────────────────────────────────────────────────
    df.reset_index(drop=True, inplace=True)

    return df.to_dict(orient="records")


def _clean_name(name: str) -> str:
    # Remove excessive whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Remove leading/trailing punctuation noise
    name = re.sub(r"^[^\w\u00C0-\u024F]+|[^\w\u00C0-\u024F]+$", "", name)
    return name[:300]


def products_to_dataframe(products) -> pd.DataFrame:
    """Convert SQLAlchemy Product objects to a pandas DataFrame."""
    records = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "price_raw": p.price_raw,
            "category": p.category,
            "rating": p.rating,
            "url": p.url,
            "image_url": p.image_url,
            "created_at": p.created_at,
            "session_id": p.session_id,
        }
        for p in products
    ]
    return pd.DataFrame(records) if records else pd.DataFrame()
