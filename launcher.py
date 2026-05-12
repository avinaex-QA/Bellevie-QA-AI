import threading
import time
import webview
import uvicorn

from backend.main import app


def start_server():
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )


# Start backend server in background
server_thread = threading.Thread(
    target=start_server,
    daemon=True
)

server_thread.start()

# Wait for backend startup
time.sleep(8)

# Open desktop app window
webview.create_window(
    "AI Test Case Generator",
    "http://127.0.0.1:8000",
    width=1400,
    height=900
)

webview.start(debug=True)