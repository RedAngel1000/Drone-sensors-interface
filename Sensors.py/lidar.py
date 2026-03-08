from machine import UART, Pin
import time

# UART1 on GP4 (TX) and GP5 (RX)
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

def read_tfluna():
    while True:
        if uart.any() >= 9:
            first = uart.read(1)
            if first and first[0] == 0x59:
                second = uart.read(1)
                if second and second[0] == 0x59:
                    rest = uart.read(7)
                    if rest and len(rest) == 7:
                        dist = rest[0] | (rest[1] << 8)
                        strength = rest[2] | (rest[3] << 8)
                        temp_raw = rest[4] | (rest[5] << 8)
                        temp_c = temp_raw / 8 - 256
                        return dist, strength, temp_c
        time.sleep_ms(5)

while True:
    try:
        distance, strength, temp_c = read_tfluna()
        print("Distance:", distance, "Strength:", strength, "Temp:", round(temp_c, 1), "C")
    except Exception as e:
        print("Read error:", e)

    time.sleep(0.1)