import math
import socket
import time
from secrets import BACKEND_BASE_URL, DEVICE_ID, WIFI_PASSWORD, WIFI_SSID

import neopixel
import network
import urequests
from machine import Pin

DATA_PIN = 0
NUM_LEDS = 19
POLL_INTERVAL_MS = 1000
HEARTBEAT_INTERVAL_MS = 15000
WIFI_CONNECT_TIMEOUT_MS = 15000

np = neopixel.NeoPixel(Pin(DATA_PIN), NUM_LEDS)

mode = "off"
solid_color = (0, 128, 255)
brightness = 0.6
last_command_timestamp = 0
last_poll_ms = 0
last_heartbeat_ms = 0
t = 0

siri_colors = [
    (0, 120, 255),
    (120, 0, 255),
    (255, 0, 180),
    (0, 255, 220),
]


def scale_color(color, amount):
    return (
        int(color[0] * amount),
        int(color[1] * amount),
        int(color[2] * amount),
    )


def blend(c1, c2, mix):
    return (
        int(c1[0] * (1 - mix) + c2[0] * mix),
        int(c1[1] * (1 - mix) + c2[1] * mix),
        int(c1[2] * (1 - mix) + c2[2] * mix),
    )


def hex_to_rgb(value):
    try:
        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
        )
    except Exception:
        return (0, 128, 255)


def set_solid():
    color = scale_color(solid_color, brightness)

    for i in range(NUM_LEDS):
        np[i] = color

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


def apply_mode():
    if mode == "solid":
        set_solid()
    elif mode == "off":
        set_off()


def ensure_wifi():
    wlan = network.WLAN(network.STA_IF)

    if wlan.isconnected():
        return wlan

    print("Connecting to Wi-Fi:", WIFI_SSID)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    started_ms = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), started_ms) > WIFI_CONNECT_TIMEOUT_MS:
            print("Wi-Fi connect timeout, retrying...")
            wlan.disconnect()
            time.sleep(1)
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            started_ms = time.ticks_ms()
        time.sleep_ms(200)

    print("Wi-Fi connected:", wlan.ifconfig())
    return wlan


def api_url(path):
    return BACKEND_BASE_URL.rstrip("/") + path


def resolve_backend():
    raw = BACKEND_BASE_URL.rstrip("/")
    host = raw
    port = 443 if raw.startswith("https://") else 80

    if "://" in host:
        host = host.split("://", 1)[1]

    if "/" in host:
        host = host.split("/", 1)[0]

    if ":" in host:
        host, port_text = host.rsplit(":", 1)
        try:
            port = int(port_text)
        except Exception:
            pass

    try:
        addresses = socket.getaddrinfo(host, port)
        print("Backend DNS:", host, port, addresses[0][-1])
    except Exception as error:
        print("Backend DNS error:", host, port, error)


def fetch_latest_command():
    response = None
    url = api_url("/api/devices/" + DEVICE_ID + "/commands/latest")

    try:
        print("Fetching command:", url)
        response = urequests.get(url)
        if response.status_code != 200:
            print("Command fetch failed:", response.status_code)
            return None
        command = response.json()
        print("Command payload:", command)
        return command
    except Exception as error:
        print("Command fetch error:", type(error).__name__, error)
        return None
    finally:
        if response is not None:
            response.close()


def send_heartbeat():
    response = None
    url = api_url("/api/devices/" + DEVICE_ID + "/heartbeat")

    payload = {
        "mode": mode,
        "color": "%02x%02x%02x" % solid_color,
        "brightness": int(brightness * 100),
    }

    try:
        print("Sending heartbeat:", url, payload)
        response = urequests.post(url, json=payload)
        print("Heartbeat:", response.status_code)
    except Exception as error:
        print("Heartbeat error:", type(error).__name__, error)
    finally:
        if response is not None:
            response.close()


def apply_command(command):
    global mode
    global solid_color
    global brightness
    global last_command_timestamp

    if not command:
        return

    updated_at = int(command.get("updatedAt", 0))

    if updated_at <= last_command_timestamp:
        return

    new_mode = command.get("mode", "off")
    new_color = command.get("color", "000000")
    new_brightness = command.get("brightness", 0)

    mode = new_mode
    solid_color = hex_to_rgb(new_color)
    brightness = max(0, min(100, int(new_brightness))) / 100
    last_command_timestamp = updated_at

    print("Applied command:", mode, new_color, brightness, updated_at)
    apply_mode()


def main():
    global last_poll_ms
    global last_heartbeat_ms

    set_off()
    ensure_wifi()
    resolve_backend()

    while True:
        wlan = ensure_wifi()

        now_ms = time.ticks_ms()

        if (
            wlan.isconnected()
            and time.ticks_diff(now_ms, last_poll_ms) >= POLL_INTERVAL_MS
        ):
            command = fetch_latest_command()
            apply_command(command)
            last_poll_ms = now_ms

        if (
            wlan.isconnected()
            and time.ticks_diff(now_ms, last_heartbeat_ms) >= HEARTBEAT_INTERVAL_MS
        ):
            send_heartbeat()
            last_heartbeat_ms = now_ms

        if mode == "siri":
            update_siri()
            time.sleep_ms(50)
        else:
            time.sleep_ms(100)


main()
