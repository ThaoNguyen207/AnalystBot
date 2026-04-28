"""
run.py — Unified launcher for Data Analyst Bot
Usage:
  python run.py          → Start web server
  python run.py cli      → Start CLI mode
  python run.py install  → Install dependencies
"""
import sys
import os
import subprocess

ROOT    = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
DATA    = os.path.join(ROOT, "data")


def install():
    req = os.path.join(BACKEND, "requirements.txt")
    print("📦 Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req])
    print("✅ Done!")


def run_web():
    os.makedirs(DATA, exist_ok=True)
    os.chdir(BACKEND)
    print("\n" + "="*50)
    print("🤖 Data Analyst Bot — Web Mode")
    print("🌐 http://localhost:8000")
    print("📖 http://localhost:8000/api/docs")
    print("="*50 + "\n")
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=BACKEND)


def run_cli():
    os.makedirs(DATA, exist_ok=True)
    cli = os.path.join(ROOT, "cli", "bot_cli.py")
    subprocess.run([sys.executable, cli])


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "web"

    if mode == "install":
        install()
    elif mode == "cli":
        run_cli()
    else:
        run_web()
