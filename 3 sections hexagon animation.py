from machine import Pin
import rp2
import time
import array

DATA_PIN = 0
NUM_LEDS = 200
BRIGHTNESS = 200

COLOR = (255, 80, 0)  # orange

STEP_DELAY = 0.15
PAUSE_ALL_ON = 0.0
PAUSE_ALL_OFF = 0.0

ROWS_BOTTOM_TO_TOP = [
    [127, 133],        # row 1 bottom
    [80, 85, 90],      # row 2 middle
    [29, 35],          # row 3 top
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


def scale(value):
    return int(value * BRIGHTNESS / 255)


def rgb_to_grb(r, g, b):
    r = scale(r)
    g = scale(g)
    b = scale(b)

    return (g << 16) | (r << 8) | b


def clear_pixels():
    for i in range(NUM_LEDS):
        pixels[i] = 0


def set_led(index, color):
    if index < 0 or index >= NUM_LEDS:
        return

    pixels[index] = rgb_to_grb(color[0], color[1], color[2])


def show_pixels():
    sm.put(pixels, 8)
    time.sleep_ms(10)


def show_active_rows(active_rows):
    clear_pixels()

    for row in range(len(ROWS_BOTTOM_TO_TOP)):
        if active_rows[row]:
            for led in ROWS_BOTTOM_TO_TOP[row]:
                set_led(led, COLOR)

    show_pixels()


def animate_cycle():
    active_rows = [False, False, False]

    # turn on row 1, then row 2, then row 3
    for row in range(len(ROWS_BOTTOM_TO_TOP)):
        active_rows[row] = True
        show_active_rows(active_rows)
        time.sleep(STEP_DELAY)

    time.sleep(PAUSE_ALL_ON)

    # turn off row 1, then row 2, then row 3
    for row in range(len(ROWS_BOTTOM_TO_TOP)):
        active_rows[row] = False
        show_active_rows(active_rows)
        time.sleep(STEP_DELAY)

    time.sleep(PAUSE_ALL_OFF)


while True:
    animate_cycle()