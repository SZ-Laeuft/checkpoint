# python
import asyncio
import os
import threading
import time
import queue as ThreadQueue
from contextlib import asynccontextmanager
import datetime
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from app.MFRC522Handler import myRFIDReader
from pydantic import BaseModel


class UserDataMessage(BaseModel):
    name: str
    surname: str
    id: int
    best_time: int
    lap_count: int


class Runner(BaseModel):
    runnerId: int
    firstname: str | None
    lastname: str | None
    gender: str | None
    birthdate: str | None


class Participate(BaseModel):
    participateId: int
    teamId: int | None
    tagId: str | None
    runnerId: int | None
    eventId: int | None
    categoryId: int | None


# Threading primitives and shared queue
stop_event = threading.Event()
reader_thread = None
rfid_queue = ThreadQueue.Queue()

API_URL = os.getenv("API_URL", "http://192.168.68.31:8080/api")

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


import json  # Don't forget to import json


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

                with requests.session() as session:
                    tag_id = int(uid, 16)
                    participateObjects: list = session.get(f"{API_URL}/participates/by-tagId/{str(tag_id)}").json()
                    if len(participateObjects) == 0:
                        continue
                    participate = Participate.model_validate(participateObjects[0])
                    print(API_URL + "/runners/" + str(participate.runnerId))
                    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                    new_round_data = {"participateid": participate.participateId,
                                      "roundtimestamp": str(timestamp)}
                    print(f"new round data: {new_round_data}")
                    new_round = session.post(API_URL + "/rounds/", json=new_round_data)
                    print(new_round.status_code)

                    runner = session.get(API_URL + "/runners/" + str(participate.runnerId)).json()
                    runner = Runner.model_validate(runner)
                    print(runner)
                    best_time = session.get(API_URL + "/besttime/" + str(participate.runnerId)).json()
                    best_time = int(best_time.get("bestTime"))
                    print(best_time)
                    round_count = session.get(API_URL + "/rounds/get-round-count/" + str(participate.participateId))
                    round_count = int(round_count.content)

                    user = UserDataMessage(id=runner.runnerId, name=runner.firstname, surname=runner.lastname,
                                           best_time=best_time, lap_count=round_count)

                    print(f"Sending data: {user.model_dump_json()}")
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
