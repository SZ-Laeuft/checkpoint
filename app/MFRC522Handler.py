from app.MFRC522 import MFRC522
import signal
import time

continue_reading = True

def uidToString(uid):
    mystring = ""
    for i in uid:
        mystring = mystring + format(i, '02X')
    return mystring


def end_read(signal, frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    continue_reading = False

signal.signal(signal.SIGINT, end_read)

class myRFIDReader(MFRC522):
    def __init__(self,bus=0,dev=0):
        super().__init__(bus=bus,dev=dev)
        self.key = None
        self.keyIn = False
        self.keyValidCount=0;

    def Read(self):
        status, TagType = self.MFRC522_Request(super().PICC_REQIDL)
        if status == self.MI_OK:
            status, uid = self.MFRC522_SelectTagSN()
            if status == self.MI_OK:
                self.keyIn=True
                self.keyValidCount=2
                if self.key != uid:
                    self.key = uid
                    if uid is None:
                        return False
                    return True
        else:
            if self.keyIn:
                if self.keyValidCount>0:
                    self.keyValidCount= self.keyValidCount - 1
                else:
                    self.keyIn=False
                    self.key=None
        return False

    def get_uid(self):
        while True:
            if self.Read():
                uid = uidToString(self.key)
                print(f"Read UID: {uid}")
                yield uid
            time.sleep(0.010)