from machine import UART, Pin
import time

# UART0 on GP0 (TX) and GP1 (RX)
# TF-Luna TXD -> Pico GP1
# TF-Luna RXD -> Pico GP0
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

def read_tfluna():
    # Look for a frame header: 0x59 0x59
    while True:
        if uart.any() >= 9:
            first = uart.read(1)
            if first and first[0] == 0x59:
                second = uart.read(1)
                if second and second[0] == 0x59:
                    rest = uart.read(7)
                    if rest and len(rest) == 7:
                        # Typical 9-byte frame:
                        # 0:0x59 1:0x59 2:Dist_L 3:Dist_H 4:Amp_L 5:Amp_H 6:Temp_L 7:Temp_H 8:Checksum
                        dist = rest[0] | (rest[1] << 8)
                        strength = rest[2] | (rest[3] << 8)
                        temp_raw = rest[4] | (rest[5] << 8)
                        temp_c = temp_raw / 8 - 256

                        return dist, strength, temp_c
        time.sleep_ms(5)

while True:
    try:
        distance, strength, temp_c = read_tfluna()
    time.sleep(0.1)