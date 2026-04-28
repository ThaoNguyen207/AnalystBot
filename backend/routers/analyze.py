from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models.database import get_db, Product, CrawlSession
from tools.cleaner import products_to_dataframe
from tools.analyzer import analyze
import io
import csv

router = APIRouter()


def _get_df(session_id, db):
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    products = q.all()
    return products_to_dataframe(products)


@router.get("/")
def run_analysis(
    session_id: int = Query(None, description="Phân tích session cụ thể (None = tất cả)"),
    db: Session = Depends(get_db),
):
    df = _get_df(session_id, db)
    if df.empty:
        raise HTTPException(404, "Không có dữ liệu. Hãy crawl trước!")

    # Compare with previous session if session_id specified
    prev_df = None
    if session_id:
        sessions = (
            db.query(CrawlSession)
            .order_by(CrawlSession.created_at.desc())
            .all()
        )
        ids = [s.id for s in sessions]
        if session_id in ids:
            idx = ids.index(session_id)
            if idx + 1 < len(ids):
                prev_df = _get_df(ids[idx + 1], db)

    result = analyze(df, prev_df)
    return result


@router.get("/export/csv")
def export_csv(
    session_id: int = Query(None),
    db: Session = Depends(get_db),
):
    df = _get_df(session_id, db)
    if df.empty:
        raise HTTPException(404, "Không có dữ liệu")

    output = io.StringIO()
    cols = ["name", "price", "price_raw", "category", "rating", "url"]
    available = [c for c in cols if c in df.columns]
    df[available].to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )
