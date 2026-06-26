from machine import Pin
import rp2
import time
import array

DATA_PIN = 0
NUM_LEDS = 200
BRIGHTNESS = 2

COLOR = (255, 0, 0)  # red

SECTIONS = [
    (26, 37),
    (80, 90),
    (125, 136),
]

# SECTIONS = [
#    (22, 42),
#    (75, 95),
#    (121, 144),
#]


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


def led_is_in_section(index):
    for start, end in SECTIONS:
        if start <= index <= end:
            return True
    return False


def show_sections():
    on_color = rgb_to_grb(COLOR[0], COLOR[1], COLOR[2])

    for i in range(NUM_LEDS):
        if led_is_in_section(i):
            pixels[i] = on_color
        else:
            pixels[i] = 0

    sm.put(pixels, 8)
    time.sleep_ms(10)


while True:
    show_sections()
    time.sleep(1)