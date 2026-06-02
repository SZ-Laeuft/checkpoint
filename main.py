import asyncio
import os
import threading
import time
import queue as ThreadQueue
from contextlib import asynccontextmanager
import datetime
import logging
import json

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.MFRC522Handler import myRFIDReader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from gpiozero import TonalBuzzer
from time import sleep
BUZZER_PIN = 18

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rfid_app")

class BuzzerHandler:
    def __init__(self, pin):
        try:
            self.buzzer = TonalBuzzer(pin, octaves=3)
        except Exception as e:
            print(f"Buzzer init failed: {e}")
            self.buzzer = None

    def success_beep(self):
        """Short high beep for successful scan"""
        if self.buzzer:
            # Three quick rising notes (C5, E5, G5) 
            # High frequency for outdoor piercing power
            for freq in [1046, 1318, 1568]: 
                self.buzzer.play(freq)
                sleep(0.08) # Short and punchy
            
            # Hold the last note slightly longer for 'triumph'
            self.buzzer.play(2093) # C6 (High C)
            sleep(0.15)
            self.buzzer.stop()

    def error_beep(self):
        """Two low beeps for error"""
        if self.buzzer:
            for _ in range(2):
                self.buzzer.play(400) 
                sleep(0.25)
                self.buzzer.stop()
                sleep(0.1)

buzzer = BuzzerHandler(BUZZER_PIN)

class UserDataMessage(BaseModel):
    name: str; surname: str; id: int; best_time: int; lap_count: int; round_time: int

class Runner(BaseModel):
    runnerId: int; firstname: str | None; lastname: str | None; gender: str | None; birthdate: str | None

class Participate(BaseModel):
    participateId: int
    runnerId: int | None
    tagId: str | None
    teamId: int | None
    eventId: int | None
    categoryId: int

class Round(BaseModel):
    roundId: int
    participateId: int
    roundTimestamp: str
    roundTime: int
    isValid: bool


# Global state
stop_event = threading.Event()
reader_thread = None
rfid_queue = ThreadQueue.Queue()
API_URL = os.getenv("API_URL", "http://192.168.68.35:8080/api")
reader1 = myRFIDReader(bus=0, dev=0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global reader_thread
    stop_event.clear()
    reader_thread = threading.Thread(
        target=rfid_reader_thread,
        args=(rfid_queue, stop_event),
        daemon=True
    )
    reader_thread.start()
    logger.info("RFID Reader Thread Started")
    yield
    logger.info("Shutting down RFID Reader...")
    stop_event.set()
    if reader_thread:
        reader_thread.join(timeout=2.0)
    if hasattr(reader1, "cleanup"):
        reader1.cleanup()
    logger.info("Shutdown Complete")

app = FastAPI(lifespan=lifespan)

def rfid_reader_thread(q, stop_evt):
    # Pass the stop event into the generator fix the hang
    for uid in reader1.get_uid(stop_evt):
        q.put(uid)
    logger.info("Hardware loop exited.")

async def send_error_msg(websocket):
    msg = UserDataMessage(id=-1, name="Error", surname="Error", best_time=0, lap_count=0, round_time=0)
    buzzer.error_beep()
    await websocket.send_text(msg.model_dump_json())

app.mount("/static", StaticFiles(directory="./static", html=True), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def keepalive_listener():
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
        except (WebSocketDisconnect, json.JSONDecodeError):
            logger.info("WS Client disconnected")

    async def rfid_sender():
        try:
            while True:
                uid = await asyncio.to_thread(rfid_queue.get)
                rfid_queue.task_done()

                with requests.Session() as session:
                    try:
                        reversed_hex = uid[6:8] + uid[4:6] + uid[2:4] + uid[0:2]

                        tag_id = f"{int(reversed_hex, 16):010d}"

                        logger.info(f"sending uid: {tag_id}")

                        # Get active event
                        events = session.get(f"{API_URL}/events").json()
                        active_event = next((e for e in events if str(e.get("isActive")).lower() == "true"), None)

                        if not active_event:
                            logger.warning("No active event found")
                            await send_error_msg(websocket)
                            continue

                        current_event_id = active_event["eventId"]
                        logger.info(f"Active event: {current_event_id}")

                        # Fetch participates for tag
                        res = session.get(f"{API_URL}/participates/by-tagId/{tag_id}").json()
                        if not res:
                            logger.warning(f"No runner for tag {tag_id} (response object: {res})")
                            await send_error_msg(websocket)
                            continue

                        # Keep only participates for the active event
                        matched = [p for p in res if p.get("eventId") == current_event_id]

                        if not isinstance(res, list) or not res:
                            logger.warning(f"No participate for tag {tag_id} in active event {current_event_id}")
                            await send_error_msg(websocket)
                            continue

                        part = Participate.model_validate(matched[0])

                        # Record Round
                        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                        session.post(f"{API_URL}/rounds/", json={"participateid": part.participateId, "roundtimestamp": ts})

                        # Fetch Metadata
                        runner_data = session.get(f"{API_URL}/runners/{part.runnerId}").json()
                        runner = Runner.model_validate(runner_data)

                        bt_res = session.get(f"{API_URL}/besttime/{part.participateId}").json()
                        best_time = int(bt_res.get("bestTime", 0))

                        round_res = session.get(f"{API_URL}/rounds/by-participateId/{part.participateId}").json()
                        round_time = int(round_res.get("roundTime", 0))

                        rc_res = session.get(f"{API_URL}/rounds/get-round-count/{part.participateId}")
                        count = int(rc_res.content)

                        user = UserDataMessage(
                            id=runner.runnerId, name=runner.firstname or "",
                            surname=runner.lastname or "", best_time=best_time, lap_count=count,
                            round_time=round_time
                        )
                        
                        # TRIGGER SUCCESS BEEP
                        buzzer.success_beep()
                        await websocket.send_text(user.model_dump_json())

                    except Exception:
                        logger.exception("Error processing RFID scan")
                        await send_error_msg(websocket)
        except asyncio.CancelledError:
            pass

    t1 = asyncio.create_task(keepalive_listener())
    t2 = asyncio.create_task(rfid_sender())
    await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    t1.cancel(); t2.cancel()
