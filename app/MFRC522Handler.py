from app.MFRC522 import MFRC522
import time
import logging

logger = logging.getLogger("rfid_app")

def uidToString(uid):
    if not uid: return ""
    return "".join(format(i, '02X') for i in uid)

class myRFIDReader(MFRC522):
    def __init__(self, bus=0, dev=0):
        super().__init__(bus=bus, dev=dev)
        self.key = None
        self.keyIn = False
        self.keyValidCount = 0

    def Read(self):
        status, TagType = self.MFRC522_Request(self.PICC_REQIDL)
        if status == self.MI_OK:
            status, uid = self.MFRC522_SelectTagSN()
            if status == self.MI_OK:
                self.keyIn = True
                self.keyValidCount = 2
                if self.key != uid:
                    self.key = uid
                    return uid is not None
        else:
            if self.keyIn:
                if self.keyValidCount > 0:
                    self.keyValidCount -= 1
                else:
                    self.keyIn = False
                    self.key = None
        return False

    def get_uid(self, stop_event):
        """Generator that yields UIDs until stop_event is set."""
        while not stop_event.is_set():
            try:
                if self.Read():
                    uid_str = uidToString(self.key)
                    yield uid_str
            except Exception:
                logger.exception("Hardware read error")
            time.sleep(0.05)