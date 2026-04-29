import os
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json

from models.database import get_db, CrawlSession, Product

router = APIRouter()

@router.post("/file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload Excel/CSV and save to database as a crawl session."""
    filename = file.filename.lower()
    
    # 1. Read file
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file .csv hoặc .xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc file: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="File không có dữ liệu.")

    # 2. Normalize Columns (Tên, Giá, Loại,...)
    # We try to map common columns to our product schema
    col_map = {
        "name": ["name", "tên", "sản phẩm", "tiêu đề", "title", "product"],
        "price": ["price", "giá", "đơn giá", "cost", "tiền"],
        "category": ["category", "loại", "danh mục", "nhóm", "type"],
        "rating": ["rating", "sao", "đánh giá", "score", "stars"],
        "url": ["url", "link", "đường dẫn"]
    }
    
    # Map columns
    new_cols = {}
    for standard, aliases in col_map.items():
        for col in df.columns:
            if col.lower() in aliases:
                new_cols[col] = standard
                break
    
    df = df.rename(columns=new_cols)

    # 3. Create Session
    session = CrawlSession(
        url=f"Upload: {file.filename}",
        site_name="Local Upload",
        total_items=len(df),
        strategy="file_upload",
        status="success"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 4. Save Products
    products = []
    for _, row in df.iterrows():
        # Basic cleanup
        name = str(row.get("name", "Unknown"))
        price = 0.0
        try:
            p_val = row.get("price", 0)
            if isinstance(p_val, str):
                p_val = p_val.replace(",", "").replace(".", "").replace("đ", "").strip()
            price = float(p_val)
        except:
            pass

        products.append(Product(
            session_id=session.id,
            name=name[:500],
            price=price,
            price_raw=str(row.get("price", price)) + " (Upload)",
            category=str(row.get("category", "Unknown")),
            rating=float(row.get("rating", 0.0)) if "rating" in row else 0.0,
            url=str(row.get("url", "")),
            extra_data=json.dumps(row.to_dict(), ensure_ascii=False)
        ))
    
    db.bulk_save_objects(products)
    db.commit()

    return {
        "success": True,
        "session_id": session.id,
        "total": len(products),
        "message": f"Đã tải lên {len(products)} bản ghi từ file {file.filename}"
    }
