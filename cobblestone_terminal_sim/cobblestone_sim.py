#!/usr/bin/env python3
"""
Cobblestone LED guidance terminal simulator.

Run with:
    python cobblestone_sim.py

Controls in live mode:
    1-9  select animation
    R/G/B/... select a color palette
    i    toggle stone IDs
    b    cycle brightness preset
    s    cycle speed preset
    0/q  quit

If curses is unavailable, the program falls back to a simple prompt mode where
you type a command, then the chosen animation preview runs for a few seconds.
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import curses
except ImportError:  # pragma: no cover - platform dependent
    curses = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_STONES = 23
LEDS_PER_STONE = 19
FRAME_TIME = 0.08
FALLBACK_PREVIEW_SECONDS = 5.0
BREATHING_MAX = 0.45
IDLE_DIM = 0.08
WARNING_FLASHES = 3
WARNING_FLASH_DURATION = 0.22
SPINNER_TAIL = 3
SPARKLE_COUNT = 5

BRIGHTNESS_PRESETS = [0.10, 0.25, 0.50, 0.75, 1.00]
SPEED_PRESETS = [0.5, 0.75, 1.0, 1.5, 2.0]

COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (60, 220, 255)
COLOR_BLUE = (40, 120, 255)
COLOR_RED = (255, 70, 40)
COLOR_AMBER = (255, 180, 40)
COLOR_GREEN = (80, 255, 120)
COLOR_MAGENTA = (255, 80, 220)
COLOR_YELLOW = (255, 235, 80)
COLOR_ORANGE = (255, 140, 40)
COLOR_PURPLE = (155, 95, 255)
COLOR_LIME = (175, 255, 70)
COLOR_TEAL = (40, 210, 180)

# Each number is one cobblestone ID.
# None means empty space.
LAYOUT = [
    [None, None, None, 0, None, 1, None, None, None, None],
    [None, None, None, None, 2, None, None, 3, None, None],
    [None, None, 4, None, None, None, 5, None, None, None],
    [6, None, None, 7, None, 8, None, None, 9, None],
    [None, None, 10, None, None, None, None, 11, None, 12],
    [None, 13, None, 14, None, 15, None, None, 16, None],
    [None, None, 17, None, None, None, 18, None, None, None],
    [None, None, None, 19, None, 20, None, 21, None, None],
    [None, None, None, None, 22, None, None, None, None, None],
]


@dataclass
class StoneState:
    color: Tuple[int, int, int] = COLOR_BLACK
    brightness: float = 0.0


@dataclass
class AppState:
    animation_id: int = 5
    show_ids: bool = False
    brightness_index: int = 2
    speed_index: int = 2
    color_key: str = "C"
    frame: int = 0
    running: bool = True

    @property
    def brightness_scale(self) -> float:
        return BRIGHTNESS_PRESETS[self.brightness_index]

    @property
    def speed_scale(self) -> float:
        return SPEED_PRESETS[self.speed_index]

    @property
    def color_name(self) -> str:
        return COLOR_OPTIONS[self.color_key][0]

    @property
    def base_color(self) -> Tuple[int, int, int]:
        return COLOR_OPTIONS[self.color_key][1]


STONE_COORDS: Dict[int, Tuple[int, int]] = {
    stone_id: (row, col)
    for row, layout_row in enumerate(LAYOUT)
    for col, stone_id in enumerate(layout_row)
    if stone_id is not None
}

VISUAL_ORDER = [
    stone_id
    for row in LAYOUT
    for stone_id in row
    if stone_id is not None
]

ROW_GROUPS: List[List[int]] = [
    [stone_id for stone_id in row if stone_id is not None] for row in LAYOUT
]

COL_GROUPS: List[List[int]] = []
for col_index in range(len(LAYOUT[0])):
    group = []
    for row in LAYOUT:
        stone_id = row[col_index]
        if stone_id is not None:
            group.append(stone_id)
    if group:
        COL_GROUPS.append(group)

CENTER_POINT = (
    sum(row for row, _ in STONE_COORDS.values()) / NUM_STONES,
    sum(col for _, col in STONE_COORDS.values()) / NUM_STONES,
)
DISTANCE_ORDER = sorted(
    STONE_COORDS,
    key=lambda stone_id: math.dist(STONE_COORDS[stone_id], CENTER_POINT),
)
MAX_CENTER_DISTANCE = max(
    math.dist(coords, CENTER_POINT) for coords in STONE_COORDS.values()
)

ANIMATION_NAMES = {
    1: "Top to Bottom Flow",
    2: "Bottom to Top Flow",
    3: "Left to Right Flow",
    4: "Right to Left Flow",
    5: "Idle Breathing",
    6: "Loading Spinner",
    7: "Center Ripple",
    8: "Warning Flash",
    9: "Random Sparkle",
}

ANIMATION_DETAILS = {
    1: "Rows light downward with fading trails.",
    2: "Rows light upward with fading trails.",
    3: "Columns sweep from left to right.",
    4: "Columns sweep from right to left.",
    5: "All stones softly breathe in and out.",
    6: "A moving highlight loops through the layout.",
    7: "A pulse expands outward from the center.",
    8: "All stones flash red and amber three times.",
    9: "Short colorful sparkles pop across the grid.",
}

COLOR_OPTIONS = {
    "R": ("Red", COLOR_RED),
    "G": ("Green", COLOR_GREEN),
    "B": ("Blue", COLOR_BLUE),
    "Y": ("Yellow", COLOR_YELLOW),
    "C": ("Cyan", COLOR_CYAN),
    "M": ("Magenta", COLOR_MAGENTA),
    "W": ("White", COLOR_WHITE),
    "O": ("Orange", COLOR_ORANGE),
    "P": ("Purple", COLOR_PURPLE),
    "L": ("Lime", COLOR_LIME),
    "A": ("Amber", COLOR_AMBER),
    "T": ("Teal", COLOR_TEAL),
}

CELL_WIDTH = 2
COLUMN_SPACING = 1


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def scale_color(color: Tuple[int, int, int], brightness: float) -> Tuple[int, int, int]:
    brightness = clamp(brightness)
    return tuple(int(channel * brightness) for channel in color)


def blend_colors(
    first: Tuple[int, int, int], second: Tuple[int, int, int], mix: float
) -> Tuple[int, int, int]:
    mix = clamp(mix)
    return tuple(int(a + (b - a) * mix) for a, b in zip(first, second))


def dim_color(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(int(channel * clamp(factor)) for channel in color)


def supports_ansi() -> bool:
    return sys.stdout.isatty() and os.getenv("TERM") not in (None, "", "dumb")


def reset_stones() -> List[StoneState]:
    return [StoneState() for _ in range(NUM_STONES)]


def stone_label(stone_id: int, state: StoneState, show_ids: bool) -> str:
    if show_ids:
        return f"{stone_id:02d}"

    if state.brightness <= 0.02:
        return ".."
    if state.brightness <= 0.18:
        return "::"
    if state.brightness <= 0.45:
        return "++"
    if state.brightness <= 0.75:
        return "[]"
    return "##"


def ansi_cell(stone_id: int, state: StoneState, show_ids: bool) -> str:
    label = stone_label(stone_id, state, show_ids)
    r, g, b = scale_color(state.color, state.brightness)
    if state.brightness <= 0.02:
        return "  "
    return f"\x1b[38;2;{r};{g};{b}m{label}\x1b[0m"


def text_cell(stone_id: int, state: StoneState, show_ids: bool) -> str:
    return stone_label(stone_id, state, show_ids)


def build_header_lines(state: AppState) -> List[str]:
    selected_name = state.color_name
    color_legend = "  ".join(
        f"{key}={name}{'*' if key == state.color_key else ''}"
        for key, (name, _) in COLOR_OPTIONS.items()
    )
    lines = [
        "Cobblestone LED Guidance Simulator",
        f"Animation: {ANIMATION_NAMES[state.animation_id]}",
        f"Meaning: {ANIMATION_DETAILS[state.animation_id]}",
        (
            f"Brightness: {int(state.brightness_scale * 100)}%    "
            f"Speed: {state.speed_scale:.2f}x    Color: {selected_name} ({state.color_key})"
        ),
        "Keys: 1-9 animations | i IDs | b brightness | s speed | color letters | 0/q quit",
        f"Colors: {color_legend}",
        "Animations:",
    ]

    for animation_id in sorted(ANIMATION_NAMES):
        marker = ">" if animation_id == state.animation_id else " "
        lines.append(
            f"{marker} {animation_id}: {ANIMATION_NAMES[animation_id]} - "
            f"{ANIMATION_DETAILS[animation_id]}"
        )

    lines.extend(["", "Grid:"])
    return lines


def render_lines(state: AppState, stones: Sequence[StoneState], use_ansi: bool) -> List[str]:
    lines = build_header_lines(state)

    for row in LAYOUT:
        cells = []
        for stone_id in row:
            if stone_id is None:
                cells.append("  ")
            else:
                cell = (
                    ansi_cell(stone_id, stones[stone_id], state.show_ids)
                    if use_ansi
                    else text_cell(stone_id, stones[stone_id], state.show_ids)
                )
                cells.append(cell)
        lines.append(" ".join(cells))

    return lines


def render_curses(
    screen: "curses._CursesWindow",
    state: AppState,
    stones: Sequence[StoneState],
    color_pairs: Optional[Dict[str, int]],
) -> None:
    lines = build_header_lines(state)
    screen.erase()
    height, width = screen.getmaxyx()
    for index, line in enumerate(lines[: height - 1]):
        try:
            screen.addnstr(index, 0, line, width - 1)
        except curses.error:
            pass

    grid_row_offset = len(lines)
    for row_index, row in enumerate(LAYOUT):
        screen_y = grid_row_offset + row_index
        if screen_y >= height - 1:
            break

        current_x = 0
        for stone_id in row:
            if stone_id is None:
                current_x += CELL_WIDTH + COLUMN_SPACING
                continue

            label = text_cell(stone_id, stones[stone_id], state.show_ids)
            attrs = stone_curses_attr(stones[stone_id], color_pairs)
            try:
                screen.addnstr(screen_y, current_x, label, CELL_WIDTH, attrs)
            except curses.error:
                pass
            current_x += CELL_WIDTH + COLUMN_SPACING
    screen.refresh()


def strip_ansi(text: str) -> str:
    result = []
    inside = False
    for char in text:
        if char == "\x1b":
            inside = True
            continue
        if inside and char == "m":
            inside = False
            continue
        if not inside:
            result.append(char)
    return "".join(result)


def print_frame(state: AppState, stones: Sequence[StoneState], use_ansi: bool) -> None:
    lines = render_lines(state, stones, use_ansi)
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")
    sys.stdout.flush()


def closest_named_color(color: Tuple[int, int, int]) -> str:
    named_colors = {
        "black": COLOR_BLACK,
        "red": COLOR_RED,
        "green": COLOR_GREEN,
        "yellow": COLOR_YELLOW,
        "blue": COLOR_BLUE,
        "magenta": COLOR_MAGENTA,
        "cyan": COLOR_CYAN,
        "white": COLOR_WHITE,
    }
    return min(
        named_colors,
        key=lambda name: sum(
            (component - reference) ** 2
            for component, reference in zip(color, named_colors[name])
        ),
    )


def init_curses_colors() -> Optional[Dict[str, int]]:
    if curses is None or not curses.has_colors():
        return None

    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass

    base_colors = {
        "black": curses.COLOR_BLACK,
        "red": curses.COLOR_RED,
        "green": curses.COLOR_GREEN,
        "yellow": curses.COLOR_YELLOW,
        "blue": curses.COLOR_BLUE,
        "magenta": curses.COLOR_MAGENTA,
        "cyan": curses.COLOR_CYAN,
        "white": curses.COLOR_WHITE,
    }
    color_pairs: Dict[str, int] = {}
    pair_number = 1
    for name, color_value in base_colors.items():
        try:
            curses.init_pair(pair_number, color_value, -1)
            color_pairs[name] = pair_number
            pair_number += 1
        except curses.error:
            continue
    return color_pairs or None


def stone_curses_attr(
    state: StoneState, color_pairs: Optional[Dict[str, int]]
) -> int:
    if curses is None:
        return 0

    attrs = curses.A_NORMAL
    if state.brightness >= 0.75:
        attrs |= curses.A_BOLD
    elif state.brightness <= 0.08:
        attrs |= curses.A_DIM

    if not color_pairs or state.brightness <= 0.02:
        return attrs

    color_name = closest_named_color(state.color)
    pair_number = color_pairs.get(color_name)
    if pair_number is not None:
        attrs |= curses.color_pair(pair_number)
    return attrs


def set_all(
    stones: Sequence[StoneState], color: Tuple[int, int, int], brightness: float
) -> None:
    for stone in stones:
        stone.color = color
        stone.brightness = clamp(brightness)


def set_group(
    stones: Sequence[StoneState],
    stone_ids: Iterable[int],
    color: Tuple[int, int, int],
    brightness: float,
) -> None:
    for stone_id in stone_ids:
        stones[stone_id].color = color
        stones[stone_id].brightness = clamp(brightness)


def base_dim(stones: Sequence[StoneState], color: Tuple[int, int, int], brightness: float) -> None:
    set_all(stones, color, brightness)


def animate_flow(
    stones: Sequence[StoneState],
    groups: Sequence[Sequence[int]],
    frame: int,
    color: Tuple[int, int, int],
    brightness_scale: float,
    reverse: bool = False,
) -> None:
    ordered_groups = list(reversed(groups)) if reverse else list(groups)
    pulse_index = frame % max(1, len(ordered_groups))
    base_dim(stones, dim_color(color, 0.35), 0.06 * brightness_scale)

    for index, group in enumerate(ordered_groups):
        distance = abs(index - pulse_index)
        if distance == 0:
            brightness = 1.0 * brightness_scale
        elif distance == 1:
            brightness = 0.45 * brightness_scale
        elif distance == 2:
            brightness = 0.18 * brightness_scale
        else:
            continue
        set_group(stones, group, color, brightness)


def animate_breathing(
    stones: Sequence[StoneState],
    frame: int,
    brightness_scale: float,
    base_color: Tuple[int, int, int],
) -> None:
    phase = frame / (10.0 / brightness_scale)
    pulse = (math.sin(phase) + 1.0) / 2.0
    brightness = (IDLE_DIM + pulse * BREATHING_MAX) * brightness_scale
    soft_color = blend_colors(dim_color(base_color, 0.65), COLOR_WHITE, pulse * 0.25)
    set_all(stones, soft_color, brightness)


def animate_spinner(
    stones: Sequence[StoneState],
    frame: int,
    brightness_scale: float,
    base_color: Tuple[int, int, int],
) -> None:
    base_dim(stones, dim_color(base_color, 0.4), 0.05 * brightness_scale)
    head_index = frame % len(VISUAL_ORDER)
    for offset in range(SPINNER_TAIL):
        stone_id = VISUAL_ORDER[(head_index - offset) % len(VISUAL_ORDER)]
        mix = 1.0 - (offset / SPINNER_TAIL)
        color = blend_colors(base_color, COLOR_WHITE, mix * 0.35)
        brightness = (0.35 + mix * 0.65) * brightness_scale
        stones[stone_id].color = color
        stones[stone_id].brightness = clamp(brightness)


def animate_ripple(
    stones: Sequence[StoneState],
    frame: int,
    brightness_scale: float,
    base_color: Tuple[int, int, int],
) -> None:
    base_dim(stones, dim_color(base_color, 0.35), 0.04 * brightness_scale)
    wave_radius = (frame * 0.45 * brightness_scale) % (MAX_CENTER_DISTANCE + 1.2)
    for stone_id, coords in STONE_COORDS.items():
        distance = math.dist(coords, CENTER_POINT)
        delta = abs(distance - wave_radius)
        if delta < 0.6:
            brightness = (1.0 - delta / 0.6) * brightness_scale
            color = blend_colors(base_color, COLOR_WHITE, clamp(1.0 - delta))
            stones[stone_id].color = color
            stones[stone_id].brightness = brightness


def animate_warning(
    stones: Sequence[StoneState],
    frame: int,
    brightness_scale: float,
    base_color: Tuple[int, int, int],
) -> None:
    cycle_length = max(1, int((WARNING_FLASH_DURATION / FRAME_TIME) / brightness_scale))
    total_cycles = WARNING_FLASHES * 2
    cycle_index = frame // cycle_length
    if cycle_index >= total_cycles:
        animate_breathing(
            stones,
            frame - (cycle_length * total_cycles),
            brightness_scale,
            base_color,
        )
        return

    phase_in_cycle = frame % cycle_length
    color = COLOR_RED if cycle_index % 2 == 0 else COLOR_AMBER
    brightness = (1.0 if phase_in_cycle < cycle_length // 2 or cycle_length == 1 else 0.06)
    brightness *= brightness_scale
    set_all(stones, color, brightness)


def animate_sparkle(
    stones: Sequence[StoneState],
    frame: int,
    brightness_scale: float,
    base_color: Tuple[int, int, int],
) -> None:
    random.seed(frame)
    base_dim(stones, dim_color(base_color, 0.35), 0.06 * brightness_scale)
    palette = [
        base_color,
        blend_colors(base_color, COLOR_WHITE, 0.4),
        blend_colors(base_color, COLOR_MAGENTA, 0.5),
        blend_colors(base_color, COLOR_GREEN, 0.5),
        blend_colors(base_color, COLOR_AMBER, 0.5),
    ]
    sparkle_ids = random.sample(range(NUM_STONES), k=min(SPARKLE_COUNT, NUM_STONES))
    for stone_id in sparkle_ids:
        stones[stone_id].color = random.choice(palette)
        stones[stone_id].brightness = random.uniform(0.55, 1.0) * brightness_scale


def apply_animation(state: AppState, stones: Sequence[StoneState]) -> None:
    base_color = state.base_color
    if state.animation_id == 1:
        animate_flow(stones, ROW_GROUPS, state.frame, base_color, state.brightness_scale)
    elif state.animation_id == 2:
        animate_flow(
            stones, ROW_GROUPS, state.frame, base_color, state.brightness_scale, reverse=True
        )
    elif state.animation_id == 3:
        animate_flow(stones, COL_GROUPS, state.frame, base_color, state.brightness_scale)
    elif state.animation_id == 4:
        animate_flow(
            stones, COL_GROUPS, state.frame, base_color, state.brightness_scale, reverse=True
        )
    elif state.animation_id == 5:
        animate_breathing(stones, state.frame, state.brightness_scale, base_color)
    elif state.animation_id == 6:
        animate_spinner(stones, state.frame, state.brightness_scale, base_color)
    elif state.animation_id == 7:
        animate_ripple(stones, state.frame, state.brightness_scale, base_color)
    elif state.animation_id == 8:
        animate_warning(stones, state.frame, state.brightness_scale, base_color)
    elif state.animation_id == 9:
        animate_sparkle(stones, state.frame, state.brightness_scale, base_color)
    else:
        animate_breathing(stones, state.frame, state.brightness_scale, base_color)


def handle_keypress(state: AppState, key: str) -> None:
    if key in "123456789":
        state.animation_id = int(key)
        state.frame = 0
    elif key == "i":
        state.show_ids = not state.show_ids
    elif key == "b":
        state.brightness_index = (state.brightness_index + 1) % len(BRIGHTNESS_PRESETS)
    elif key == "s":
        state.speed_index = (state.speed_index + 1) % len(SPEED_PRESETS)
    elif key in {"0", "q", "Q"}:
        state.running = False
    else:
        color_key = key.upper()
        if color_key in COLOR_OPTIONS:
            state.color_key = color_key


def run_curses(screen: "curses._CursesWindow") -> None:
    curses.curs_set(0)
    screen.nodelay(True)
    screen.timeout(0)
    color_pairs = init_curses_colors()

    state = AppState()
    stones = reset_stones()

    while state.running:
        key_code = screen.getch()
        if key_code != -1:
            try:
                handle_keypress(state, chr(key_code))
            except ValueError:
                pass

        apply_animation(state, stones)
        render_curses(screen, state, stones, color_pairs)
        state.frame += 1
        time.sleep(FRAME_TIME / state.speed_scale)


def run_prompt_fallback() -> None:
    state = AppState()
    use_ansi = supports_ansi()

    while state.running:
        preview_end = time.time() + FALLBACK_PREVIEW_SECONDS
        while time.time() < preview_end and state.running:
            stones = reset_stones()
            apply_animation(state, stones)
            print_frame(state, stones, use_ansi)
            state.frame += 1
            time.sleep(FRAME_TIME / state.speed_scale)

        command = input(
            "Command (1-9 animation, color letter, i IDs, b brightness, s speed, 0/q quit): "
        ).strip()
        if not command:
            continue
        for char in command:
            handle_keypress(state, char)


def main() -> int:
    if curses is not None and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            curses.wrapper(run_curses)
            return 0
        except curses.error:
            pass

    run_prompt_fallback()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
