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
import json # Don't forget to import json

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # listen for pings (keepalive messages) and pong back
    async def keepalive_listener():
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        print("Received Ping, sending Pong")
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            print("ping reader disconnected")

    # send data from rfid reader
    async def rfid_sender():
        try:
            while True:
                uid = await asyncio.to_thread(rfid_queue.get)
                rfid_queue.task_done()

                user = Runner(name="Unknown", surname="User", id=-1, best_time="N/A", lap_count=0)
                if uid == "04CE811B3E6180":
                    user = Runner(name="Maximilian", surname="Dorninger", id=1, best_time="00:45:32", lap_count=5)
                elif uid == "0451F21A3E6180":
                    user = Runner(name="Manuel", surname="Hofmarcher", id=2, best_time="00:47:15", lap_count=4)
                elif uid == "044CC51A3E6180":
                    user = Runner(name="Alexander", surname="Thir", id=3, best_time="00:46:50", lap_count=6)

                print(f"Sending data for UID: {uid}")
                await websocket.send_text(user.model_dump_json())
        except asyncio.CancelledError:
            print("RFID reader task cancelled")
        except Exception as e:
            print(f"Error in sender: {e}")


    listener_task = asyncio.create_task(keepalive_listener())
    sender_task = asyncio.create_task(rfid_sender())

    # If either one of the tasks finishes, the other one will be stopped
    # so it doesn't get stuck waiting forever
    done, pending = await asyncio.wait(
        [listener_task, sender_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()