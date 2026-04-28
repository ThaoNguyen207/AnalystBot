# 🤖 Data Analyst Bot

AI-powered data analyst assistant — crawl, analyze, visualize any website data.

## 🌐 Live Demo
> Deploy URL sẽ hiển thị sau khi deploy

## 🚀 Deploy nhanh

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

## 🛠️ Chạy local

```bash
# 1. Cài thư viện
pip install -r requirements.txt

# 2. Chạy web server
python run.py

# 3. Mở trình duyệt
# http://localhost:8000

# 4. Chạy CLI
python run.py cli
```

## 📦 Tech Stack
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Crawler**: BeautifulSoup (smart auto-detect)
- **Analysis**: Pandas + NumPy
- **Frontend**: HTML/CSS/JS + Chart.js
- **CLI**: Rich + Click

## 🔗 API Endpoints
- `POST /api/crawl/` — Crawl URL
- `GET  /api/analyze/` — Statistical analysis
- `POST /api/chat/` — Chat with bot
- `GET  /api/data/products` — Get products
- `GET  /api/docs` — Swagger UI
