from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models.database import get_db, Product
import json

router = APIRouter()


@router.get("/products")
def get_products(
    session_id: int = Query(None),
    limit: int = Query(200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    total = q.count()
    products = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "price_raw": p.price_raw,
                "category": p.category,
                "rating": p.rating,
                "url": p.url,
                "image_url": p.image_url,
                "session_id": p.session_id,
                "created_at": p.created_at.isoformat(),
            }
            for p in products
        ],
    }


@router.get("/stats/quick")
def quick_stats(session_id: int = Query(None), db: Session = Depends(get_db)):
    from sqlalchemy import func
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    total = q.count()
    priced = q.filter(Product.price > 0)
    agg = priced.with_entities(
        func.avg(Product.price), func.max(Product.price),
        func.min(Product.price), func.count(Product.category.distinct()),
    ).first()
    return {
        "total_items": total,
        "avg_price":   round(float(agg[0] or 0), 2),
        "max_price":   round(float(agg[1] or 0), 2),
        "min_price":   round(float(agg[2] or 0), 2),
        "categories":  int(agg[3] or 0),
    }


# ── Extra-data stat helpers ────────────────────────────────────────────────

def _parse_extra(products, key: str):
    """Return list of (product, int_value) sorted descending by key from extra_data."""
    rows = []
    for p in products:
        try:
            extra = json.loads(p.extra_data or "{}")
            val = int(extra.get(key, 0) or 0)
            rows.append((p, val, extra))
        except Exception:
            continue
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


def _player_dict(p, extra, **extra_fields):
    return {
        "name":         p.name,
        "team":         extra.get("team", ""),
        "position":     p.category,
        "price":        p.price_raw or f"£{p.price}M",
        "total_points": p.rating,
        "form":         extra.get("form", "0"),
        "selected_by":  extra.get("selected_by", ""),
        "goals":        int(extra.get("goals", 0) or 0),
        "assists":      int(extra.get("assists", 0) or 0),
        "minutes":      int(extra.get("minutes", 0) or 0),
        **extra_fields,
    }


@router.get("/top-scorers")
def top_scorers(
    session_id: int = Query(None),
    n:          int = Query(20),
    db: Session = Depends(get_db),
):
    """Top N players by goals scored."""
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    rows = _parse_extra(q.all(), "goals")
    rows = [(p, v, e) for p, v, e in rows if v > 0]
    return [_player_dict(p, e, goals=v) for p, v, e in rows[:n]]


@router.get("/top-assisters")
def top_assisters(
    session_id: int = Query(None),
    n:          int = Query(20),
    db: Session = Depends(get_db),
):
    """Top N players by assists."""
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    rows = _parse_extra(q.all(), "assists")
    rows = [(p, v, e) for p, v, e in rows if v > 0]
    return [_player_dict(p, e, assists=v) for p, v, e in rows[:n]]


@router.get("/top-points")
def top_points(
    session_id: int = Query(None),
    n:          int = Query(20),
    db: Session = Depends(get_db),
):
    """Top N players by FPL total points (rating field)."""
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    products = sorted(q.all(), key=lambda p: p.rating or 0, reverse=True)
    result = []
    for p in products[:n]:
        try:
            extra = json.loads(p.extra_data or "{}")
        except Exception:
            extra = {}
        result.append(_player_dict(p, extra))
    return result


@router.get("/team-stats")
def team_stats(
    session_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """Aggregate goals, assists, players per team."""
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    teams: dict = {}
    for p in q.all():
        try:
            extra = json.loads(p.extra_data or "{}")
            team  = extra.get("team", "Unknown")
            if team not in teams:
                teams[team] = {"team": team, "players": 0, "goals": 0, "assists": 0, "total_points": 0}
            teams[team]["players"]      += 1
            teams[team]["goals"]        += int(extra.get("goals",   0) or 0)
            teams[team]["assists"]      += int(extra.get("assists", 0) or 0)
            teams[team]["total_points"] += int(p.rating or 0)
        except Exception:
            continue
    return sorted(teams.values(), key=lambda x: x["goals"], reverse=True)

