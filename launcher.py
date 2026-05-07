import threading
import webview
import uvicorn

def start_server():
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    # Start FastAPI in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Open desktop window
    webview.create_window(
        "AI Test Case Generator",
        "http://127.0.0.1:8000",
        width=1200,
        height=800
    )

    webview.start()