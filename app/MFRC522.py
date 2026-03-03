import spidev
import time

class MFRC522:
    MAX_LEN = 16

    PCD_IDLE       = 0x00
    PCD_AUTHENT    = 0x0E
    PCD_RECEIVE    = 0x08
    PCD_TRANSMIT   = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC    = 0x03

    PICC_REQIDL    = 0x26
    PICC_REQALL    = 0x52
    PICC_ANTICOLL1  = 0x93
    PICC_ANTICOLL2  = 0x95
    PICC_ANTICOLL3  = 0x97
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_READ       = 0x30
    PICC_WRITE      = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE   = 0xC2
    PICC_TRANSFER  = 0xB0
    PICC_HALT      = 0x50

    MI_OK       = 0
    MI_NOTAGERR = 1
    MI_ERR      = 2

    CommandReg     = 0x01
    CommIEnReg     = 0x02
    CommIrqReg     = 0x04
    DivIrqReg      = 0x05
    ErrorReg       = 0x06
    Status2Reg     = 0x08
    FIFODataReg    = 0x09
    FIFOLevelReg   = 0x0A
    ControlReg     = 0x0C
    BitFramingReg  = 0x0D
    ModeReg        = 0x11
    TxControlReg   = 0x14
    TxAutoReg      = 0x15
    TModeReg       = 0x2A
    TPrescalerReg  = 0x2B
    TReloadRegH    = 0x2C
    TReloadRegL    = 0x2D
    CRCResultRegM  = 0x21
    CRCResultRegL  = 0x22

    def __init__(self, bus=0, dev=0, spd=1000000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus=bus, device=dev)
        self.spi.max_speed_hz = spd
        self.MFRC522_Init()

    def MFRC522_Reset(self):
        self.Write_MFRC522(self.CommandReg, self.PCD_RESETPHASE)

    def Write_MFRC522(self, addr, val):
        self.spi.writebytes(((addr << 1) & 0x7E, val))

    def Read_MFRC522(self, addr):
        val = self.spi.xfer2((((addr << 1) & 0x7E) | 0x80, 0))
        return val[1]

    def SetBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp | mask)

    def ClearBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp & (~mask))

    def AntennaOn(self):
        temp = self.Read_MFRC522(self.TxControlReg)
        if not (temp & 0x03):
            self.SetBitMask(self.TxControlReg, 0x03)

    def MFRC522_ToCard(self, command, sendData):
        backData = []
        backLen = 0
        status = self.MI_ERR
        irqEn = 0x00
        waitIRq = 0x00

        if command == self.PCD_AUTHENT:
            irqEn = 0x12
            waitIRq = 0x10
        if command == self.PCD_TRANSCEIVE:
            irqEn = 0x77
            waitIRq = 0x30

        self.Write_MFRC522(self.CommIEnReg, irqEn | 0x80)
        self.ClearBitMask(self.CommIrqReg, 0x80)
        self.SetBitMask(self.FIFOLevelReg, 0x80)
        self.Write_MFRC522(self.CommandReg, self.PCD_IDLE)

        for byte in sendData:
            self.Write_MFRC522(self.FIFODataReg, byte)

        self.Write_MFRC522(self.CommandReg, command)

        if command == self.PCD_TRANSCEIVE:
            self.SetBitMask(self.BitFramingReg, 0x80)

        i = 2000
        while True:
            n = self.Read_MFRC522(self.CommIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x01) and not (n & waitIRq)):
                break

        self.ClearBitMask(self.BitFramingReg, 0x80)

        if i != 0:
            if (self.Read_MFRC522(self.ErrorReg) & 0x1B) == 0x00:
                status = self.MI_OK
                if n & irqEn & 0x01:
                    status = self.MI_NOTAGERR
                if command == self.PCD_TRANSCEIVE:
                    n = self.Read_MFRC522(self.FIFOLevelReg)
                    lastBits = self.Read_MFRC522(self.ControlReg) & 0x07
                    backLen = (n - 1) * 8 + lastBits if lastBits != 0 else n * 8
                    if n == 0: n = 1
                    if n > self.MAX_LEN: n = self.MAX_LEN
                    for _ in range(n):
                        backData.append(self.Read_MFRC522(self.FIFODataReg))
        return (status, backData, backLen)

    def MFRC522_Request(self, reqMode):
        self.Write_MFRC522(self.BitFramingReg, 0x07)
        TagType = [reqMode]
        (status, backData, backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, TagType)
        if (status != self.MI_OK) or (backBits != 0x10):
            status = self.MI_ERR
        return (status, backBits)

    def MFRC522_Anticoll(self, anticolN):
        self.Write_MFRC522(self.BitFramingReg, 0x00)
        serNum = [anticolN, 0x20]
        (status, backData, backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, serNum)
        if status == self.MI_OK:
            if len(backData) == 5:
                serNumCheck = 0
                for i in range(4):
                    serNumCheck ^= backData[i]
                if serNumCheck != backData[4]:
                    status = self.MI_ERR
            else:
                status = self.MI_ERR
        return (status, backData)

    def MFRC522_Anticoll1(self): return self.MFRC522_Anticoll(self.PICC_ANTICOLL1)
    def MFRC522_Anticoll2(self): return self.MFRC522_Anticoll(self.PICC_ANTICOLL2)
    def MFRC522_Anticoll3(self): return self.MFRC522_Anticoll(self.PICC_ANTICOLL3)

    def CalulateCRC(self, pIndata):
        self.ClearBitMask(self.DivIrqReg, 0x04)
        self.SetBitMask(self.FIFOLevelReg, 0x80)
        for byte in pIndata:
            self.Write_MFRC522(self.FIFODataReg, byte)
        self.Write_MFRC522(self.CommandReg, self.PCD_CALCCRC)
        i = 0xFF
        while True:
            n = self.Read_MFRC522(self.DivIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break
        return [self.Read_MFRC522(self.CRCResultRegL), self.Read_MFRC522(self.CRCResultRegM)]

    def MFRC522_PcdSelect(self, serNum, anticolN):
        buf = [anticolN, 0x70] + serNum[:5]
        pOut = self.CalulateCRC(buf)
        buf += pOut
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buf)
        return 1 if (status == self.MI_OK) and (backLen == 0x18) else 0

    def MFRC522_PcdSelect1(self, serNum): return self.MFRC522_PcdSelect(serNum, self.PICC_ANTICOLL1)
    def MFRC522_PcdSelect2(self, serNum): return self.MFRC522_PcdSelect(serNum, self.PICC_ANTICOLL2)
    def MFRC522_PcdSelect3(self, serNum): return self.MFRC522_PcdSelect(serNum, self.PICC_ANTICOLL3)

    def MFRC522_Init(self):
        self.MFRC522_Reset()
        self.Write_MFRC522(self.TModeReg, 0x8D)
        self.Write_MFRC522(self.TPrescalerReg, 0x3E)
        self.Write_MFRC522(self.TReloadRegL, 30)
        self.Write_MFRC522(self.TReloadRegH, 0)
        self.Write_MFRC522(self.TxAutoReg, 0x40)
        self.Write_MFRC522(self.ModeReg, 0x3D)
        self.AntennaOn()

    def MFRC522_SelectTagSN(self):
        valid_uid = []
        status, uid = self.MFRC522_Anticoll1()
        if status != self.MI_OK: return (self.MI_ERR, [])
        if self.MFRC522_PcdSelect1(uid) == 0: return (self.MI_ERR, [])

        if uid[0] == 0x88:
            valid_uid.extend(uid[1:4])
            status, uid = self.MFRC522_Anticoll2()
            if status != self.MI_OK or self.MFRC522_PcdSelect2(uid) == 0: return (self.MI_ERR, [])
            if uid[0] == 0x88:
                valid_uid.extend(uid[1:4])
                status, uid = self.MFRC522_Anticoll3()
                if status != self.MI_OK or self.MFRC522_PcdSelect3(uid) == 0: return (self.MI_ERR, [])
        valid_uid.extend(uid[0:4])
        return (self.MI_OK, valid_uid)

    def cleanup(self):
        self.spi.close()