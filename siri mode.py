from machine import Pin
import rp2
import time
import array
import math

DATA_PIN = 0
NUM_LEDS = 200
BRIGHTNESS = 80
FRAME_DELAY_MS = 30

SECTIONS = [
    (26, 37),
    (80, 90),
    (125, 136),
]

# Change these if one row appears to move in the wrong direction
REVERSE_ROWS = [
    False,   # top row
    False,   # middle row
    False,   # bottom row
]


@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=24,
)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3

    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0) [T3 - 1]
    jmp(not_x, "do_zero")   .side(1) [T1 - 1]
    jmp("bitloop")          .side(1) [T2 - 1]
    label("do_zero")
    nop()                   .side(0) [T2 - 1]
    wrap()


sm = rp2.StateMachine(
    0,
    ws2812,
    freq=8_000_000,
    sideset_base=Pin(DATA_PIN),
)

sm.active(1)

pixels = array.array("I", [0 for _ in range(NUM_LEDS)])

PI2 = 6.2831853
mode = 0
last_button = False


def clear_pixels():
    for i in range(NUM_LEDS):
        pixels[i] = 0


def wheel(pos):
    pos = pos % 255

    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)

    if pos < 170:
        pos = pos - 85
        return (0, 255 - pos * 3, pos * 3)

    pos = pos - 170
    return (pos * 3, 0, 255 - pos * 3)


def set_led(index, r, g, b, level):
    if index < 0 or index >= NUM_LEDS:
        return

    if level < 0:
        level = 0

    if level > 1:
        level = 1

    r = int(r * BRIGHTNESS * level / 255)
    g = int(g * BRIGHTNESS * level / 255)
    b = int(b * BRIGHTNESS * level / 255)

    pixels[index] = (g << 16) | (r << 8) | b


def show_pixels():
    sm.put(pixels, 8)
    time.sleep_ms(1)


def row_pixels(row_number):
    start, end = SECTIONS[row_number]
    length = end - start + 1

    for n in range(length):
        index = start + n

        if length <= 1:
            x = 0
        else:
            x = n / (length - 1)

        if REVERSE_ROWS[row_number]:
            x = 1 - x

        if len(SECTIONS) <= 1:
            y = 0
        else:
            y = row_number / (len(SECTIONS) - 1)

        yield index, x, y


def update_button():
    global mode, last_button

    button = rp2.bootsel_button()

    if button and not last_button:
        mode = mode + 1

        if mode > 2:
            mode = 0

        time.sleep_ms(250)

    last_button = button


def draw_diagonal_wave(t):
    clear_pixels()

    for row in range(len(SECTIONS)):
        for index, x, y in row_pixels(row):
            wave = (math.sin(PI2 * (x * 1.4 + y * 0.7 - t * 0.45)) + 1) / 2
            level = wave * wave

            hue = int(t * 35 + x * 80 + y * 90)
            r, g, b = wheel(hue)

            set_led(index, r, g, b, level)

    show_pixels()


def draw_row_wave(t):
    clear_pixels()

    for row in range(len(SECTIONS)):
        for index, x, y in row_pixels(row):
            wave = (math.sin(PI2 * (y * 1.2 - t * 0.55)) + 1) / 2
            level = 0.08 + wave * wave * 0.92

            hue = int(t * 30 + y * 120)
            r, g, b = wheel(hue)

            set_led(index, r, g, b, level)

    show_pixels()


def draw_ripple_wave(t):
    clear_pixels()

    for row in range(len(SECTIONS)):
        for index, x, y in row_pixels(row):
            dx = x - 0.5
            dy = y - 0.5
            distance = math.sqrt(dx * dx + dy * dy)

            wave = (math.sin(PI2 * (distance * 2.8 - t * 0.7)) + 1) / 2
            level = wave * wave * wave

            hue = int(t * 45 + distance * 160)
            r, g, b = wheel(hue)

            set_led(index, r, g, b, level)

    show_pixels()


clear_pixels()
show_pixels()

while True:
    update_button()

    t = time.ticks_ms() / 1000

    if mode == 0:
        draw_diagonal_wave(t)

    elif mode == 1:
        draw_row_wave(t)

    else:
        draw_ripple_wave(t)

    time.sleep_ms(FRAME_DELAY_MS)