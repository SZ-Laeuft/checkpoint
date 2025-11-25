import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from app.MFRC522Handler import myRFIDReader
from pydantic import BaseModel


class Runner(BaseModel):
    name: str
    surname: str
    id: int

app = FastAPI()

# Initialize the reader once. It's safe because each websocket connection
# will spawn its own thread to interact with it.
reader1 = myRFIDReader(bus=0, dev=0)

html = """
<!DOCTYPE html>
<html>
  <head>
    <title>WebSocket Test</title>
  </head>
  <body>
    <h1>WebSocket Test</h1>
    <script>
      const socket = new WebSocket(`ws://${window.location.host}/ws`);
      
      socket.onopen = function(e) {
        console.log("[open] Connection established");
      };
      
      socket.onmessage = function(event) {
        console.log(`[message] Data received from server: ${event.data}`);        
      };
      
      socket.onclose = function(event) {
        if (event.wasClean) {
          console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        } else {
          console.log('[close] Connection died');
        }
      };
      
      socket.onerror = function(error) {
        console.log(`[error]`, error);
        
      };
    </script>
    
    <ul id="list">
    </ul>
  </body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get():
    return html


# This is a regular (synchronous) function that will run in a separate thread.
# It reads from the RFID device and puts the UID into a queue.
def rfid_reader_thread(queue: asyncio.Queue):
    # This loop will run forever in the background.
    for uid in reader1.get_uid():
        # 'put_nowait' is safe to call from a regular synchronous function.
        # It adds the item to the asyncio queue.
        queue.put_nowait(uid)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Create an asyncio Queue. This is a thread-safe way to pass
    # data between the asyncio event loop and other threads.
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    # Start the blocking RFID reader function in a separate thread.
    # It will start putting UIDs into the 'queue'.
    reader_task = loop.run_in_executor(
        None,  # Use the default thread pool executor
        rfid_reader_thread,
        queue
    )

    try:
        while True:
            # Wait for a UID to appear in the queue.
            # 'await queue.get()' will pause here without blocking the server,
            # waiting for the reader thread to add an item.
            uid = await queue.get()
            user = None
            if uid == "04CE811B3E6180":
                user = Runner(name="Maximilian", surname="Dorninger", id=1)
            if uid == "0451F21A3E6180":
                user = Runner(name="Manuel", surname="Hofmarcher", id=2)
            if uid == "044CC51A3E6180":
                user = Runner(name="Alexander", surname="Thir", id=3)

            print(f"Sending data: {user}")
            await websocket.send_text(user.model_dump_json())
            print("Successfully sent data")

            # Mark the queue task as done.
            queue.task_done()

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up the background task when the client disconnects.
        reader_task.cancel()
        print("Closing WebSocket connection and stopping reader thread.")
