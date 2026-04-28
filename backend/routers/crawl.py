from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import get_db, CrawlSession, Product
from tools.crawler import SmartCrawler
from tools.cleaner import clean_products

router = APIRouter()
crawler = SmartCrawler()


class CrawlRequest(BaseModel):
    url: str


@router.post("/")
def crawl_url(req: CrawlRequest, db: Session = Depends(get_db)):
    if not req.url.strip():
        raise HTTPException(400, "URL không được để trống")

    url = req.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    result = crawler.crawl(url)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Crawl thất bại"))

    raw_items = result.get("items", [])
    cleaned = clean_products(raw_items)

    # Save crawl session
    session = CrawlSession(
        url=url,
        site_name=result.get("site_name", "Unknown"),
        total_items=len(cleaned),
        strategy=result.get("strategy", "auto"),
        status="success",
    )
    db.add(session)
    db.flush()

    # Save products
    for item in cleaned:
        p = Product(
            session_id=session.id,
            name=item.get("name", ""),
            price=item.get("price", 0.0),
            price_raw=item.get("price_raw", ""),
            category=item.get("category", "Unknown"),
            rating=item.get("rating", 0.0),
            url=item.get("url", ""),
            image_url=item.get("image_url", ""),
            extra_data=item.get("extra_data", "{}"),
        )
        db.add(p)

    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "site_name": session.site_name,
        "strategy": session.strategy,
        "total_items": session.total_items,
        "items": cleaned[:20],  # Preview first 20
        "message": f"✅ Crawl thành công {session.total_items} sản phẩm từ {session.site_name}",
    }


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(CrawlSession)
        .order_by(CrawlSession.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": s.id,
            "url": s.url,
            "site_name": s.site_name,
            "total_items": s.total_items,
            "strategy": s.strategy,
            "created_at": s.created_at.isoformat(),
            "status": s.status,
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session không tồn tại")
    db.delete(session)
    db.commit()
    return {"message": f"Đã xóa session #{session_id}"}
