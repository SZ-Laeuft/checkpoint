# python
import asyncio
import threading
import time
import queue as ThreadQueue
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from app.MFRC522Handler import myRFIDReader
from pydantic import BaseModel

class Runner(BaseModel):
    name: str
    surname: str
    id: int
    best_time: str
    lap_count: int

# Threading primitives and shared queue
stop_event = threading.Event()
reader_thread = None
rfid_queue = ThreadQueue.Queue()

# Initialize the reader once (hardware resource)
reader1 = myRFIDReader(bus=0, dev=0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global reader_thread
    if reader_thread is None or not reader_thread.is_alive():
        stop_event.clear()
        reader_thread = threading.Thread(
            target=rfid_reader_thread,
            args=(rfid_queue, stop_event),
            daemon=True
        )
        reader_thread.start()
        print("Started RFID reader thread")

    yield

    # signal the thread to stop and wait a short time for cleanup
    stop_event.set()
    if reader_thread is not None:
        reader_thread.join(timeout=2)

    # ensure hardware cleanup called (redundant with finally in thread)
    if hasattr(reader1, "close"):
        try:
            reader1.close()
        except Exception:
            pass
    if hasattr(reader1, "cleanup"):
        try:
            reader1.cleanup()
        except Exception:
            pass
    print("Shutdown complete: stop_event set and reader joined")
app = FastAPI(lifespan=lifespan)

def rfid_reader_thread(q: ThreadQueue.Queue, stop_evt: threading.Event):
    try:
        while not stop_evt.is_set():
            try:
                # Assume reader1.get_uid() yields/returns UIDs; adapt if API differs
                for uid in reader1.get_uid():
                    if stop_evt.is_set():
                        break
                    q.put(uid)
                # small sleep to avoid busy loop; adjust as needed
                time.sleep(0.01)
            except Exception as exc:
                print(f"RFID reader error: {exc}")
                time.sleep(0.5)
    finally:
        # optional hardware cleanup if available
        if hasattr(reader1, "close"):
            try:
                reader1.close()
            except Exception:
                pass
        if hasattr(reader1, "cleanup"):
            try:
                reader1.cleanup()
            except Exception:
                pass
        print("RFID reader thread exited")


html = """<!DOCTYPE html>
<html>
  <head>
    <title>WebSocket Test</title>
  </head>
  <body>
    <h1>WebSocket Test</h1>
    <script>
      const socket = new WebSocket(`ws://${window.location.host}/ws`);
      socket.onopen = function(e) { console.log("[open] Connection established"); };
      socket.onmessage = function(event) { console.log(`[message] Data received from server: ${event.data}`); };
      socket.onclose = function(event) {
        if (event.wasClean) {
          console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        } else {
          console.log('[close] Connection died');
        }
      };
      socket.onerror = function(error) { console.log(`[error]`, error); };
    </script>
    <ul id="list"></ul>
  </body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get():
    return html

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for next UID from thread-safe queue without blocking the event loop
            uid = await asyncio.to_thread(rfid_queue.get)
            rfid_queue.task_done()
            user = Runner(name="Unknown", surname="User", id=-1, best_time="N/A", lap_count=0)
            if uid == "04CE811B3E6180":
                user = Runner(name="Maximilian", surname="Dorninger", id=1, best_time="00:45:32", lap_count=5)
            if uid == "0451F21A3E6180":
                user = Runner(name="Manuel", surname="Hofmarcher", id=2, best_time="00:47:15", lap_count=4)
            if uid == "044CC51A3E6180":
                user = Runner(name="Alexander", surname="Thir", id=3, best_time="00:46:50", lap_count=6)

            print(f"Sending data: {user}")
            await websocket.send_text(user.model_dump_json())
            print("Successfully sent data")
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred in websocket: {e}")
    finally:
        print("WebSocket handler finished")
