from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import get_db, Product, AnalysisHistory
from tools.cleaner import products_to_dataframe
from tools.chat_agent import ChatAgent
from tools.llm_provider import LLMProvider
from tools.analyzer import generate_context_summary
from routers.data import _parse_extra, _player_dict
import json

router = APIRouter()
agent = ChatAgent()
llm = LLMProvider()

class ChatRequest(BaseModel):
    message: str
    session_id: int = None

@router.post("/")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    text = req.message.strip()
    if not text:
        return {"message": "Hãy nhập câu hỏi!", "intent": "EMPTY"}

    # Load current dataframe
    q = db.query(Product)
    if req.session_id:
        q = q.filter(Product.session_id == req.session_id)
    df = products_to_dataframe(q.all())

    # Get rule-based response (as draft context)
    draft_response = agent.respond(text, df if not df.empty else None)
    action = draft_response.get("action")
    slots  = draft_response.get("slots", {})
    n      = slots.get("n", 10)
    
    # ── Heavy Context Preparation ───────────────────────────────────────────
    summary = generate_context_summary(df)
    data_context = ""
    
    # Run targeted actions to get raw data for the LLM
    if action == "top_scorers":
        products = q.all()
        rows = _parse_extra(products, "goals")
        rev = slots.get("order", "desc") == "desc"
        rows = sorted([(p, v, e) for p, v, e in rows if v > 0], key=lambda x: x[1], reverse=rev)[:n]
        data_context = f"Dữ liệu Top {n} ghi bàn: {json.dumps([_player_dict(p, e, goals=v) for p, v, e in rows])}"
        
    elif action == "top_assisters":
        products = q.all()
        rows = _parse_extra(products, "assists")
        rev = slots.get("order", "desc") == "desc"
        rows = sorted([(p, v, e) for p, v, e in rows if v > 0], key=lambda x: x[1], reverse=rev)[:n]
        data_context = f"Dữ liệu Top {n} kiến tạo: {json.dumps([_player_dict(p, e, assists=v) for p, v, e in rows])}"

    elif action == "SEARCH":
        query_val = slots.get("category")
        if query_val:
            # Tìm kiếm không phân biệt hoa thường (Case-insensitive)
            found = db.query(Product).filter(Product.name.ilike(f"%{query_val}%")).all()
            
            if found:
                results = []
                for p in found[:5]: # Tên cầu thủ có thể xuất hiện nhiều lần, lấy top 5
                    try: extra = json.loads(p.extra_data or "{}")
                    except: extra = {}
                    results.append({
                        "name": p.name,
                        "goals": extra.get("goals") or extra.get("goals_scored") or 0,
                        "assists": extra.get("assists") or 0,
                        "team": p.category or "Unknown"
                    })
                data_context = f"DỮ LIỆU TÌM ĐƯỢC: {json.dumps(results)}"
            else:
                data_context = f"Không tìm thấy cầu thủ nào tên là '{query_val}'"

    # ── Final LLM Synthesis ────────────────────────────────────────────────
    system_prompt = (
        "Bạn là một Trợ lý Phân tích Dữ liệu Siêu Thông Minh. "
        "Dựa trên dữ liệu khách hàng đã cào được sau đây:\n"
        f"TÓM TẮT CHUNG: {summary}\n"
        f"DỮ LIỆU CHI TIẾT CÂU HỎI: {data_context}\n\n"
        "NHIỆM VỤ: Trả lời câu hỏi của khách hàng một cách tự nhiên, sâu sắc và chuyên nghiệp. "
        "Đừng trả lời kiểu máy móc. Hãy như một người bạn am hiểu dữ liệu đang tư vấn."
    )
    
    provider = slots.get("provider", "auto")
    ai_msg = await llm.ask(text, system_prompt, provider=provider)
    
    # Construct final response
    response = {
        "message": ai_msg,
        "intent": "AI_SYNTHESIS",
        "action": action,
        "data": draft_response.get("data") # Keep raw data for UI charts if needed
    }

    # ── History Save ─────────────────────────────────────────────────────────
    history = AnalysisHistory(
        session_id=req.session_id,
        query=text,
        result=json.dumps(response.get("data") or {}, ensure_ascii=False)[:5000],
        insight=response.get("message", "")[:2000],
    )
    db.add(history)
    db.commit()

    return response

@router.get("/history")
def get_history(limit: int = Query(20), db: Session = Depends(get_db)):
    items = db.query(AnalysisHistory).order_by(AnalysisHistory.created_at.desc()).limit(limit).all()
    return [
        {
            "id": h.id,
            "query": h.query,
            "insight": h.insight,
            "created_at": h.created_at.isoformat(),
            "session_id": h.session_id,
        }
        for h in items
    ]
