"""
Data Analyst Bot — CLI Interface
Run: python cli/bot_cli.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich import box
import json

from models.database import create_tables, SessionLocal, Product, CrawlSession
from tools.crawler import SmartCrawler
from tools.cleaner import clean_products, products_to_dataframe
from tools.analyzer import analyze
from tools.chat_agent import ChatAgent

console = Console()
crawler = SmartCrawler()
agent   = ChatAgent()

BANNER = """
[bold purple]╔══════════════════════════════════════════╗[/]
[bold purple]║  🤖  Data Analyst Bot  —  CLI Mode        ║[/]
[bold purple]╚══════════════════════════════════════════╝[/]
[dim]Gõ [bold]help[/] để xem lệnh · [bold]exit[/] để thoát[/]
"""

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def cmd_crawl(url: str, db):
    if not url:
        url = Prompt.ask("[cyan]Nhập URL cần crawl[/]")
    if not url.startswith("http"):
        url = "https://" + url

    with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True) as p:
        p.add_task(f"Đang crawl {url} ...")
        result = crawler.crawl(url)

    if not result.get("success"):
        console.print(f"[red]❌ {result.get('error')}[/]")
        return None

    raw = result.get("items", [])
    cleaned = clean_products(raw)

    session = CrawlSession(
        url=url,
        site_name=result.get("site_name", "Unknown"),
        total_items=len(cleaned),
        strategy=result.get("strategy", "auto"),
        status="success",
    )
    db.add(session)
    db.flush()

    for item in cleaned:
        db.add(Product(
            session_id=session.id,
            name=item.get("name", ""),
            price=item.get("price", 0.0),
            price_raw=item.get("price_raw", ""),
            category=item.get("category", "Unknown"),
            rating=item.get("rating", 0.0),
            url=item.get("url", ""),
            image_url=item.get("image_url", ""),
            extra_data=item.get("extra_data", "{}"),
        ))
    db.commit()

    console.print(Panel(
        f"[green]✅ Crawl thành công![/]\n"
        f"Site: [bold]{session.site_name}[/]\n"
        f"Items: [bold]{session.total_items}[/]\n"
        f"Strategy: {session.strategy}\n"
        f"Session ID: [dim]{session.id}[/]",
        title="Crawl Result", border_style="green"
    ))
    return session.id


def cmd_analyze(session_id, db):
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    df = products_to_dataframe(q.all())

    if df.empty:
        console.print("[yellow]⚠️ Không có dữ liệu — hãy crawl trước.[/]")
        return

    with Progress(SpinnerColumn(), TextColumn("[cyan]Đang phân tích ..."), transient=True) as p:
        p.add_task("")
        result = analyze(df)

    s = result["summary"]
    # Summary table
    t = Table(title="📊 Tổng hợp", box=box.ROUNDED, border_style="purple")
    t.add_column("Chỉ số", style="cyan")
    t.add_column("Giá trị", style="bold white")
    rows = [
        ("Tổng sản phẩm",    str(s["total_items"])),
        ("Có giá",           str(s["items_with_price"])),
        ("Danh mục",         str(s["categories"])),
        ("Giá trung bình",   f"{s['avg_price']:,.2f}"),
        ("Giá trung vị",     f"{s['median_price']:,.2f}"),
        ("Giá min",          f"{s['min_price']:,.2f}"),
        ("Giá max",          f"{s['max_price']:,.2f}"),
        ("Std deviation",    f"{s['std_price']:,.2f}"),
        ("Rating TB",        f"{s['avg_rating']:.2f}/5"),
    ]
    for k, v in rows:
        t.add_row(k, v)
    console.print(t)

    # Insights
    console.print("\n[bold]💡 Auto Insights:[/]")
    for ins in result["insights"]:
        console.print(f"  {ins}")

    # Top 5 expensive
    if result["top_expensive"]:
        t2 = Table(title="🏆 Top 5 đắt nhất", box=box.SIMPLE, border_style="yellow")
        t2.add_column("Tên", style="white", max_width=40)
        t2.add_column("Giá", style="green")
        t2.add_column("Loại", style="dim")
        for p in result["top_expensive"][:5]:
            t2.add_row(p.get("name", "")[:40], p.get("price_raw") or f"{p.get('price', 0):,.2f}", p.get("category", ""))
        console.print(t2)


def cmd_chat(session_id, db):
    console.print("[bold cyan]💬 Chế độ chat — gõ 'back' để quay lại menu[/]")
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    df = products_to_dataframe(q.all())

    while True:
        try:
            text = Prompt.ask("[purple]Bạn[/]")
        except (KeyboardInterrupt, EOFError):
            break
        if text.strip().lower() in ("back", "exit", "quit"):
            break

        res = agent.respond(text, df if not df.empty else None)
        intent  = res.get("intent", "")
        message = res.get("message", "")

        # Render message
        try:
            console.print(Markdown(message))
        except Exception:
            console.print(f"[cyan]Bot:[/] {message}")

        # Handle data payload
        if res.get("data") and isinstance(res["data"], list) and res["data"]:
            t = Table(box=box.SIMPLE, border_style="dim")
            t.add_column("#"); t.add_column("Tên", max_width=35)
            t.add_column("Giá", style="green"); t.add_column("Loại", style="dim")
            for i, p in enumerate(res["data"][:10], 1):
                t.add_row(str(i), p.get("name","")[:35], p.get("price_raw") or str(p.get("price",0)), p.get("category",""))
            console.print(t)

        if res.get("action") == "analyze":
            cmd_analyze(session_id, db)
        elif res.get("action") == "crawl":
            url = res.get("slots", {}).get("url")
            session_id = cmd_crawl(url or "", db) or session_id
            q2 = db.query(Product)
            if session_id:
                q2 = q2.filter(Product.session_id == session_id)
            df = products_to_dataframe(q2.all())


def cmd_sessions(db):
    sessions = db.query(CrawlSession).order_by(CrawlSession.created_at.desc()).limit(10).all()
    if not sessions:
        console.print("[yellow]Chưa có session nào.[/]")
        return None
    t = Table(title="📜 Sessions", box=box.ROUNDED, border_style="blue")
    t.add_column("ID"); t.add_column("Site"); t.add_column("Items"); t.add_column("Strategy"); t.add_column("Thời gian")
    for s in sessions:
        t.add_row(str(s.id), s.site_name, str(s.total_items), s.strategy, s.created_at.strftime("%d/%m %H:%M"))
    console.print(t)
    return sessions[0].id if sessions else None


def cmd_export(session_id, db):
    q = db.query(Product)
    if session_id:
        q = q.filter(Product.session_id == session_id)
    df = products_to_dataframe(q.all())
    if df.empty:
        console.print("[yellow]Không có dữ liệu.[/]"); return

    path = f"../data/export_session_{session_id or 'all'}.csv"
    cols = [c for c in ["name","price","price_raw","category","rating","url"] if c in df.columns]
    df[cols].to_csv(path, index=False, encoding="utf-8-sig")
    console.print(f"[green]✅ Đã xuất: {os.path.abspath(path)}[/]")


HELP = """
## Lệnh CLI

| Lệnh | Mô tả |
|------|-------|
| `crawl [url]`   | Crawl dữ liệu từ URL |
| `analyze`       | Phân tích dữ liệu hiện tại |
| `chat`          | Vào chế độ chat bot |
| `sessions`      | Xem danh sách session |
| `export`        | Xuất CSV |
| `switch <id>`   | Chuyển sang session khác |
| `help`          | Hiển thị trợ giúp |
| `exit`          | Thoát |
"""


def main():
    create_tables()
    console.print(BANNER)

    db = get_db()
    current_session = None

    # Auto-load last session
    last = db.query(CrawlSession).order_by(CrawlSession.created_at.desc()).first()
    if last:
        current_session = last.id
        console.print(f"[dim]📂 Tự động tải session #{current_session}: {last.site_name} ({last.total_items} items)[/]\n")

    while True:
        try:
            site = f"[{db.query(CrawlSession).filter(CrawlSession.id==current_session).first().site_name if current_session else 'no data'}]"
            cmd = Prompt.ask(f"[bold purple]Bot[/] [dim]{site}[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Tạm biệt! 👋[/]")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if action in ("exit", "quit", "q"):
            console.print("[dim]Tạm biệt! 👋[/]"); break

        elif action == "crawl":
            new_sid = cmd_crawl(arg, db)
            if new_sid:
                current_session = new_sid

        elif action == "analyze":
            cmd_analyze(current_session, db)

        elif action == "chat":
            cmd_chat(current_session, db)

        elif action == "sessions":
            cmd_sessions(db)

        elif action == "export":
            cmd_export(current_session, db)

        elif action == "switch" and arg.isdigit():
            current_session = int(arg)
            console.print(f"[green]✅ Đã chuyển sang session #{current_session}[/]")

        elif action == "help":
            console.print(Markdown(HELP))

        else:
            # Treat as chat message
            q = db.query(Product)
            if current_session:
                q = q.filter(Product.session_id == current_session)
            df = products_to_dataframe(q.all())
            res = agent.respond(cmd, df if not df.empty else None)
            try:
                console.print(Markdown(res.get("message", "")))
            except Exception:
                console.print(f"[cyan]Bot:[/] {res.get('message', '')}")


if __name__ == "__main__":
    main()
