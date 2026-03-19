from AHT21_ENT160 import read_environment_data
from lidar import get_lidar_data
import network
import socket
import time
import ujson
from machine import Pin, SPI, UART
from bno055_base import BNO055_BASE
import os
import sdcard

# Hardware Constants
time1=0
SPI_BUS = 0
SCK_PIN = 6
MOSI_PIN = 3
MISO_PIN = 4
CS_PIN = 5
SD_MOUNT_PATH = '/sd'
FILE_PATH = '/sd/sensor_log.csv' 

# External LED connected to GPIO15
led = Pin(15, Pin.OUT)
led_state = False
led.value(0)

# BNO055 magnetometer setup over UART
# Adjust tx/rx pins if your wiring is different.
BNO_UART_ID = 0
BNO_BAUDRATE = 115200
BNO_TX_PIN = 0
BNO_RX_PIN = 1

mag_sensor = None

try:
    bno_uart = UART(BNO_UART_ID, baudrate=BNO_BAUDRATE, tx=Pin(BNO_TX_PIN), rx=Pin(BNO_RX_PIN))
    mag_sensor = BNO055_BASE(bno_uart)
    print("BNO055 magnetometer initialized.")
except Exception as e:
    print("BNO055 setup error:", e)

def setup_sd_card():
    """Initializes the SPI bus, mounts the SD card, and creates a file header if needed."""
    try:
        # Init SPI communication
        spi = SPI(SPI_BUS, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
        cs = Pin(CS_PIN)
        sd = sdcard.SDCard(spi, cs)
        
        # Mount microSD card
        os.mount(sd, SD_MOUNT_PATH)
        print("MicroSD card mounted successfully at", SD_MOUNT_PATH)
        
        # Check if our log file already exists. If not, create it and write column headers.
        if 'sensor_log.csv' not in os.listdir(SD_MOUNT_PATH):
            with open(FILE_PATH, "w") as file:
                file.write("Time(s),Temp(C),Humidity(%),AQI,TVOC(ppb),eCO2(ppm),Distance(cm)\n")
            print("Created new data file with headers.")
        else:
            print("Found existing data file. Appending new data...")
            
        return True
        
    except Exception as e:
        print('SD Card setup error:', e)
        return False


def get_magnetometer_data():
    """Returns magnetic field data from the BNO055 as a dict."""
    if mag_sensor is None:
        return {
            "x": "--",
            "y": "--",
            "z": "--",
            "display": "-- uT"
        }

    try:
        mag_x, mag_y, mag_z = mag_sensor.mag()
        return {
            "x": round(mag_x, 2),
            "y": round(mag_y, 2),
            "z": round(mag_z, 2),
            "display": "{:.2f}, {:.2f}, {:.2f} uT".format(mag_x, mag_y, mag_z)
        }
    except Exception as e:
        print("Magnetometer read error:", e)
        return {
            "x": "--",
            "y": "--",
            "z": "--",
            "display": "-- uT"
        }

# Setup the Pico W as an Access Point
ap = network.WLAN(network.AP_IF)
ap.config(essid='Cobber-Sensor Drone', password='cobbers!')
ap.active(True)

# Wait until it's active
while not ap.active():
    time.sleep(1)

print('Access Point IP:', ap.ifconfig()[0])

#note: Parts of this HTML was generated with Chatgpt to speed up development, and then modified by me to fit the project.
html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drone Telemetry</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 0;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        .section {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 0 8px rgba(0,0,0,0.1);
        }
        .label {
            font-size: 1.2em;
            color: #555;
        }
        .value {
            font-size: 2em;
            font-weight: bold;
            color: #222;
        }
        .button {
            width: 100%;
            padding: 14px;
            font-size: 1.1em;
            border: none;
            border-radius: 8px;
            background-color: #333;
            color: white;
            cursor: pointer;
        }
        .button:active {
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <h1>Drone Telemetry</h1>

    <div class="section">
        <div class="label">Temperature</div>
        <div class="value" id="temp">-- C</div>
    </div>

    <div class="section">
        <div class="label">Humidity</div>
        <div class="value" id="humidity">-- %</div>
    </div>

    <div class="section">
        <div class="label">TVOC</div>
        <div class="value" id="tvoc">-- ppb</div>
    </div>

    <div class="section">
        <div class="label">eCO2</div>
        <div class="value" id="eco2">-- ppm</div>
    </div>

    <div class="section">
        <div class="label">LIDAR Distance</div>
        <div class="value" id="lidar_distance">-- cm</div>
    </div>

    <div class="section">
        <div class="label">Velocity</div>
        <div class="value" id="velocity">-- m/s</div>
    </div>

    <div class="section">
        <div class="label">Magnetic Field</div>
        <div class="value" id="magnetic_field">-- uT</div>
    </div>

    <div class="section">
        <div class="label">LED Status</div>
        <div class="value" id="led_status">OFF</div>
    </div>

    <div class="section">
        <button class="button" onclick="toggleLed()">Toggle LED</button>
    </div>

    <script>
        function updateData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('temp').textContent = data.temp + ' C';
                    document.getElementById('humidity').textContent = data.humidity + ' %';
                    document.getElementById('tvoc').textContent = data.tvoc + ' ppb';
                    document.getElementById('eco2').textContent = data.eco2 + ' ppm';
                    document.getElementById('lidar_distance').textContent = data.lidar_distance + ' cm';
                    document.getElementById('led_status').textContent = data.led_state;
                    document.getElementById('magnetic_field').textContent = data.magnetic_field;
                })
                .catch(err => {
                    console.log('Data fetch failed:', err);
                });
        }

        function toggleLed() {
            fetch('/led/toggle')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('led_status').textContent = data.led_state;
                })
                .catch(err => {
                    console.log('LED toggle failed:', err);
                });
        }

        updateData();
        setInterval(updateData, 200);
    </script>
</body>
</html>
"""

# Start socket server on port 80
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('Web server running...')

# Only start logging if the SD card mounted successfully
if setup_sd_card():
    print("Starting data logging... Press Ctrl+C in the console to stop.")
else:
    print("Halting execution. Please check your SD card wiring and try again.")

#Show the connected clients and handle requests
while True:
    cl, addr = s.accept()
    print('Client connected from', addr)
    cl_file = cl.makefile('rwb', 0)
    request_line = cl_file.readline()

    while True:
        line = cl_file.readline()
        if not line or line == b'\r\n':
            break

    request = request_line.decode()

    #collection of data for the webpage
    if 'GET /data' in request:
        try:
            env = read_environment_data()
            lidar = get_lidar_data()
            mag = get_magnetometer_data()
            payload = {
                'temp': round(env['temperature'], 2),
                'humidity': round(env['humidity'], 2),
                'tvoc': env['tvoc'],
                'eco2': env['eco2'],
                'lidar_distance': lidar['distance'],
                'magnetic_field': mag['display'],
                'led_state': 'ON' if led_state else 'OFF'
            }
        except Exception as e:
            payload = {
                'temp': '--',
                'humidity': '--',
                'tvoc': '--',
                'eco2': '--',
                'lidar_distance': '--',
                'magnetic_field': '-- uT',
                'led_state': 'ON' if led_state else 'OFF',
                'error': str(e)
            }

        response = ujson.dumps(payload)
        cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n')
        cl.send(response)

    #LED toggle endpoint
    elif 'GET /led/toggle' in request:
        led_state = not led_state
        led.value(led_state)

        payload = {
            'led_state': 'ON' if led_state else 'OFF'
        }

        response = ujson.dumps(payload)
        cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n')
        cl.send(response)
        
    else:
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(html)
        
    try:
        # 1. Fetch data from sensors
        env_data = read_environment_data()
        lid_data = get_lidar_data()
        mag_data = get_magnetometer_data()
            
        # 2. Get a simple timestamp (milliseconds since the Pico booted)
        timestamp = time.ticks_ms()
            
        # 3. Ensure we actually received data from both sensors before writing
        if env_data and lid_data:
                    
            # Format the data as a comma-separated string
            data_row = "{}, {:.2f}, {:.2f}, {}, {}, {}, {}\n".format(
                time1,
                env_data["temperature"],
                env_data["humidity"],
                env_data["aqi"],
                env_data["tvoc"],
                env_data["eco2"],
                lid_data["distance"],
                mag_data["x"],
                mag_data["y"],
                mag_data["z"]
            )
                    
            # 4. Open the file in Append mode ("a") and write the row
            with open(FILE_PATH, "a") as file:
                file.write(data_row)
                        
            # Print to the console so you know it's working
            print("Logged:", data_row.strip())
            time1=time1+1
                    
        else:
            print("Waiting for stable sensor data...")
                    
    except Exception as e:
        print("Logging error during main loop:", e)
        
    cl.close()
