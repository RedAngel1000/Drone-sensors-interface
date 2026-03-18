from AHT21_ENT160 import read_environment_data
from lidar import get_lidar_data
import network
import socket
import time
import ujson
from machine import Pin

# External LED connected to GPIO15
led = Pin(15, Pin.OUT)
led_state = False
led.value(0)

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
            payload = {
                'temp': round(env['temperature'], 2),
                'humidity': round(env['humidity'], 2),
                'tvoc': env['tvoc'],
                'eco2': env['eco2'],
                'lidar_distance': lidar['distance'],
                'led_state': 'ON' if led_state else 'OFF'
            }
        except Exception as e:
            payload = {
                'temp': '--',
                'humidity': '--',
                'tvoc': '--',
                'eco2': '--',
                'lidar_distance': '--',
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

    cl.close()