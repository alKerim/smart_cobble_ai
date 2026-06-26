from machine import Pin
import neopixel
import time

DATA_PIN = 0      # Change this if your data wire is on another GPIO
NUM_LEDS = 8      # Your ring looks like 8 LEDs
LOOP_SECONDS = 10
BRIGHTNESS = 1 # 0.0 to 1.0, keep low for USB power

np = neopixel.NeoPixel(Pin(DATA_PIN), NUM_LEDS)

def wheel(pos):
    # pos: 0 to 255
    if pos < 85:
        r = 255 - pos * 3
        g = pos * 3
        b = 0
    elif pos < 170:
        pos -= 85
        r = 0
        g = 255 - pos * 3
        b = pos * 3
    else:
        pos -= 170
        r = pos * 3
        g = 0
        b = 255 - pos * 3

    return (
        int(r * BRIGHTNESS),
        int(g * BRIGHTNESS),
        int(b * BRIGHTNESS)
    )

steps = 256
delay = LOOP_SECONDS / steps

while True:
    for step in range(steps):
        color = wheel(step)

        for i in range(NUM_LEDS):
            np[i] = color

        np.write()
        time.sleep(delay)