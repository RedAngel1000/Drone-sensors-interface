from myENS160 import myENS160
import machine
import network
import socket
import time

# Setup the Pico W as an Access Point
ap = network.WLAN(network.AP_IF)
ap.config(essid='Cobber-Sensor Drone', password='cobbers!')  # Change password as needed
ap.active(True)

# Wait until it's active
while not ap.active():
    time.sleep(1)

print('Access Point IP:', ap.ifconfig()[0])

# Simple HTML page (Used ChatGPT to generate display to save time)
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
    </style>
</head>
<body>
    <h1>Drone Telemetry</h1>

    <div class="section">
        <div class="label">Temperature</div>
        <div class="value" id="temp">-- °C</div>
    </div>

    <div class="section">
        <div class="label">Humidity</div>
        <div class="value" id="humidity">-- %</div>
    </div>

    <div class="section">
        <div class="label">Elevation</div>
        <div class="value" id="elevation">-- m</div>
    </div>

    <div class="section">
        <div class="label">LIDAR Scan</div>
        <div class="value" id="lidar">Awaiting data...</div>
    </div>

    <script>
        function updateData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('temp').textContent = data.temp + ' °C';
                    document.getElementById('humidity').textContent = data.humidity + ' %';
                    document.getElementById('elevation').textContent = data.elevation + ' m';
                    document.getElementById('lidar').textContent = data.lidar || 'No data';
                })
                .catch(err => {
                    console.log('Data fetch failed:', err);
                });
        }

        setInterval(updateData, 1000); // Update every second
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

while True:
    cl, addr = s.accept()
    print('Client connected from', addr)
    cl_file = cl.makefile('rwb', 0)
    while True:
        line = cl_file.readline()
        if not line or line == b'\r\n':
            break
    response = html
    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    cl.send(response)
    cl.close()

#I2C init for sensors readout
#pin 11 & 12 is SDL  & SCA for ESP32-s3-nano
SCL_PIN=machine.Pin(11)
SDA_PIN=machine.Pin(12)
i2c=machine.I2C(0,scl=SCL_PIN, sda=SDA_PIN,freq=400000)

#init ENS160 sensor on the i2c bus
ens=myENS160(i2c)

# get data
TVOC=ens.getTVOC()
AQI=ens.getAQI()
ECO2=ens.getECO2()

#print data
print(AQI)
print(TVOC)
print(ECO2)
