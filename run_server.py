from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from app import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
