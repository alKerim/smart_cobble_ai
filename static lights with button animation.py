from machine import Pin
import rp2
import time

DATA_PIN = 0
NUM_LEDS = 150
BRIGHTNESS = 200
CYCLE_TIME = 5
UPDATE_DELAY = 0.05


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


def scale_color(color):
    r, g, b = color
    return (
        int(r * BRIGHTNESS / 255),
        int(g * BRIGHTNESS / 255),
        int(b * BRIGHTNESS / 255),
    )


def send_pixel(r, g, b):
    value = (g << 16) | (r << 8) | b
    sm.put(value << 8)


def show_progress(amount_on, color):
    r, g, b = scale_color(color)

    for i in range(NUM_LEDS):
        if i < amount_on:
            send_pixel(r, g, b)
        else:
            send_pixel(0, 0, 0)

    time.sleep_ms(1)


def show_all(color):
    show_progress(NUM_LEDS, color)


def blend(color_a, color_b, amount):
    r1, g1, b1 = color_a
    r2, g2, b2 = color_b

    return (
        int(r1 + (r2 - r1) * amount),
        int(g1 + (g2 - g1) * amount),
        int(b1 + (b2 - b1) * amount),
    )


def check_button():
    global mode, last_button

    button = rp2.bootsel_button()

    if button and not last_button:
        mode = 1 - mode
        time.sleep_ms(250)

    last_button = button


colors = [
    (255, 0, 0),      # red
    (255, 80, 0),     # orange
    (255, 255, 0),    # yellow
    (0, 255, 0),      # green
    (0, 255, 255),    # cyan
    (0, 0, 255),      # blue
    (120, 0, 255),    # purple
    (255, 0, 120),    # pink
]

color_index = 0
mode = 0
last_button = False

# mode 0 = progress animation
# mode 1 = all LEDs on

while True:
    color_a = colors[color_index]
    color_b = colors[(color_index + 1) % len(colors)]

    # Fade from color_a to color_b while animation runs
    start_time = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start_time) < CYCLE_TIME * 1000:
        check_button()

        elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000
        progress = elapsed / CYCLE_TIME
        current_color = blend(color_a, color_b, progress)

        if mode == 0:
            leds_on = int(progress * NUM_LEDS)
            show_progress(leds_on, current_color)
        else:
            show_all(current_color)

        time.sleep(UPDATE_DELAY)

    # Fade from color_b back to color_a while animation goes down
    start_time = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start_time) < CYCLE_TIME * 1000:
        check_button()

        elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000
        progress = elapsed / CYCLE_TIME
        current_color = blend(color_b, color_a, progress)

        if mode == 0:
            leds_on = int((1 - progress) * NUM_LEDS)
            show_progress(leds_on, current_color)
        else:
            show_all(current_color)

        time.sleep(UPDATE_DELAY)

    color_index = (color_index + 1) % len(colors)