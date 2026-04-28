import os
import sys

# Fix import paths when running from backend/
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from models.database import create_tables
from routers import crawl, analyze, chat, data

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Data Analyst Bot",
    description="🤖 AI-powered data analysis assistant — crawl, analyze, visualize",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(crawl.router,   prefix="/api/crawl",   tags=["🕷️ Crawl"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["📊 Analyze"])
app.include_router(chat.router,    prefix="/api/chat",    tags=["💬 Chat"])
app.include_router(data.router,    prefix="/api/data",    tags=["📦 Data"])

# ─── Static Frontend ─────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(PROJECT_ROOT, "frontend")

if os.path.exists(FRONTEND):
    app.mount("/assets", StaticFiles(directory=FRONTEND), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = os.path.join(FRONTEND, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Data Analyst Bot API", "docs": "/api/docs"}


# ─── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    create_tables()
    print("\n" + "="*50)
    print("🤖 Data Analyst Bot đã khởi động!")
    print("📊 Dashboard: http://localhost:8000")
    print("📖 API Docs : http://localhost:8000/api/docs")
    print("="*50 + "\n")


# ─── Entry ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
