"""
AI Test Case Generator — Application Launcher

Starts the FastAPI server and waits for it to be healthy before
printing the "ready" confirmation. Prevents "connection refused" on
quick-launch because the browser opens before the server is ready.

Usage:
    python run.py
"""
import sys
import os
import threading
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Validate imports before starting — catches config/syntax errors early
try:
    from backend.config.settings import settings
    from backend.main import app  # noqa: F401 — triggers all imports
except Exception as e:
    print("\n" + "="*60)
    print("  STARTUP ERROR — Could not load application")
    print("="*60)
    print(f"\n  {type(e).__name__}: {e}")
    print("\n  Fix the error above, then run 'python run.py' again.\n")
    sys.exit(1)

import uvicorn


BANNER = """
╔══════════════════════════════════════════════════════════╗
║           AI Test Case Generator — QA Assistant          ║
╚══════════════════════════════════════════════════════════╝
"""

READY_MSG = """
  ✓  Server is ready!

  → UI:       http://localhost:{port}
  → API Docs: http://localhost:{port}/docs
  → Exports:  {exports_dir}

  Press Ctrl+C to stop the server.
"""


def _wait_for_health(port: int, timeout: int = 30) -> None:
    """Background thread: polls /health until the server responds or times out."""
    url   = f"http://127.0.0.1:{port}/health"
    start = time.time()

    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2):
                elapsed = time.time() - start
                exports_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "exports"
                )
                print(READY_MSG.format(port=port, exports_dir=exports_dir))
                return
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)

    print(
        "\n  ✗ Server did not respond within 30 seconds.\n"
        "    Check the error output above for startup failures.\n"
    )


def main() -> None:
    print(BANNER)
    print(f"  Starting server on port {settings.app_port}...")
    print(f"  AI model  : gemini-flash-latest")
    print(f"  Min limit : {'ON (≥'+str(settings.min_test_cases)+')' if settings.enable_min_limit else 'OFF'}")
    print(f"  Waiting for server to be ready...\n")

    # Start the health-check watcher in a daemon thread
    watcher = threading.Thread(
        target=_wait_for_health,
        args=(settings.app_port,),
        daemon=True,
    )
    watcher.start()

    try:
        uvicorn.run(
            "backend.main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=False,          # reload=True can mask startup errors
            log_level=settings.log_level.lower(),
        )
    except KeyboardInterrupt:
        print("\n  Server stopped. Goodbye!\n")


if __name__ == "__main__":
    main()
