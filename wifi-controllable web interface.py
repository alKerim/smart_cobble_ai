from machine import Pin
import neopixel
import network
import socket
import time
import math

DATA_PIN = 0
NUM_LEDS = 19

SSID = "Pico-LEDs"
PASSWORD = "12345678"

np = neopixel.NeoPixel(Pin(DATA_PIN), NUM_LEDS)

mode = "siri"
solid_color = (0, 120, 255)
brightness = 0.6
t = 0

siri_colors = [
    (0, 120, 255),
    (120, 0, 255),
    (255, 0, 180),
    (0, 255, 220),
]

html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico LED Controller</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial;
            text-align: center;
            background: #111;
            color: white;
            padding: 24px;
        }
        button, input {
            font-size: 20px;
            margin: 10px;
            padding: 14px;
            border-radius: 12px;
            border: none;
        }
        button {
            width: 220px;
        }
        input[type=color] {
            width: 120px;
            height: 70px;
        }
        input[type=range] {
            width: 260px;
        }
    </style>
</head>
<body>
    <h1>Pico LED Controller</h1>

    <p>Color</p>
    <input id="color" type="color" value="#0080ff">

    <p>Brightness</p>
    <input id="brightness" type="range" min="0" max="100" value="60">

    <br>

    <button onclick="sendMode('solid')">Solid Color</button>
    <button onclick="sendMode('siri')">Siri Fade</button>
    <button onclick="sendMode('off')">Off</button>

    <p id="status">Ready</p>

    <script>
        function sendMode(mode) {
            let color = document.getElementById("color").value.substring(1);
            let brightness = document.getElementById("brightness").value;

            fetch("/set?mode=" + mode + "&color=" + color + "&brightness=" + brightness)
                .then(response => response.text())
                .then(text => {
                    document.getElementById("status").innerText = text;
                })
                .catch(error => {
                    document.getElementById("status").innerText = "Connection error";
                });
        }

        document.getElementById("color").addEventListener("input", function() {
            sendMode("solid");
        });

        document.getElementById("brightness").addEventListener("input", function() {
            sendMode("solid");
        });
    </script>
</body>
</html>
"""

def scale_color(color, amount):
    return (
        int(color[0] * amount),
        int(color[1] * amount),
        int(color[2] * amount)
    )

def blend(c1, c2, mix):
    return (
        int(c1[0] * (1 - mix) + c2[0] * mix),
        int(c1[1] * (1 - mix) + c2[1] * mix),
        int(c1[2] * (1 - mix) + c2[2] * mix)
    )

def hex_to_rgb(value):
    try:
        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16)
        )
    except:
        return (0, 120, 255)

def parse_query(path):
    data = {}

    if "?" not in path:
        return data

    query = path.split("?", 1)[1]

    for part in query.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            data[key] = value

    return data

def send_response(conn, content, content_type):
    body = content.encode("utf-8")

    response = b"HTTP/1.1 200 OK\r\n"
    response += b"Content-Type: " + content_type.encode() + b"\r\n"
    response += b"Connection: close\r\n"
    response += b"Content-Length: " + str(len(body)).encode() + b"\r\n"
    response += b"\r\n"
    response += body

    conn.sendall(response)

def set_solid():
    c = scale_color(solid_color, brightness)

    for i in range(NUM_LEDS):
        np[i] = c

    np.write()

def set_off():
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)

    np.write()

def update_siri():
    global t

    for i in range(NUM_LEDS):
        wave = (math.sin(t + i * 0.45) + 1) / 2
        glow = 0.20 + wave * 0.80

        color_pos = (t * 0.25 + i * 0.18) % len(siri_colors)
        index = int(color_pos)
        mix = color_pos - index

        c1 = siri_colors[index]
        c2 = siri_colors[(index + 1) % len(siri_colors)]

        color = blend(c1, c2, mix)
        np[i] = scale_color(color, glow * brightness)

    np.write()
    t += 0.08

ap = network.WLAN(network.AP_IF)
ap.active(False)
time.sleep(1)

ap.config(essid=SSID, password=PASSWORD)
ap.active(True)

while not ap.active():
    time.sleep(0.2)

print("WiFi network created")
print("SSID:", SSID)
print("Password:", PASSWORD)
print("Open: http://192.168.4.1")
print("Config:", ap.ifconfig())

addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(addr)
server.listen(1)
server.setblocking(False)

print("Web server running")

while True:
    try:
        conn, addr = server.accept()
        conn.settimeout(2)

        request = conn.recv(1024).decode("utf-8", "ignore")

        first_line = request.split("\r\n")[0]
        print("Request:", first_line)

        path = "/"

        try:
            path = first_line.split(" ")[1]
        except:
            pass

        if path.startswith("/set"):
            params = parse_query(path)

            if "mode" in params:
                mode = params["mode"]

            if "color" in params:
                solid_color = hex_to_rgb(params["color"])

            if "brightness" in params:
                brightness = int(params["brightness"]) / 100

            if mode == "solid":
                set_solid()

            if mode == "off":
                set_off()

            send_response(conn, "Mode: " + mode, "text/plain")
        else:
            send_response(conn, html, "text/html")

        conn.close()

    except OSError:
        pass

    if mode == "siri":
        update_siri()
        time.sleep(0.03)
    else:
        time.sleep(0.02)