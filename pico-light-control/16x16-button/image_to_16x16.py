# image_to_16x16.py
# Usage:
# python image_to_16x16.py my_image.jpg

import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageOps
except ModuleNotFoundError:
    Image = None
    ImageEnhance = None
    ImageOps = None

SIZE = 16
PREVIEW_SIZE = 320
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
PIXEL_LINE_RE = re.compile(
    r"(?P<x>\d+),(?P<y>\d+):\s+\((?P<r>\d+),(?P<g>\d+),(?P<b>\d+)(?:,\d+)?\)"
)


def parse_args(argv):
    image_path = None
    contrast = 1.0
    index = 1

    while index < len(argv):
        arg = argv[index]
        if arg == "--contrast":
            index += 1
            if index >= len(argv):
                raise ValueError("Missing value after --contrast")
            contrast = float(argv[index])
        elif image_path is None:
            image_path = arg
        else:
            raise ValueError(f"Unexpected argument: {arg}")
        index += 1

    if image_path is None:
        raise ValueError("Usage: python image_to_16x16.py image.jpg [--contrast 2.5]")

    return Path(image_path), contrast


def apply_pillow_contrast(img, contrast):
    if contrast == 1.0:
        return img
    return ImageEnhance.Contrast(img).enhance(contrast)


def random_square_crop_box(width, height):
    if width == height:
        return width, 0, 0

    if width > height:
        crop_size = height
        left = random.randint(0, width - crop_size)
        top = 0
    else:
        crop_size = width
        left = 0
        top = random.randint(0, height - crop_size)

    return crop_size, left, top


def random_square_crop(img):
    width, height = img.size
    crop_size, left, top = random_square_crop_box(width, height)
    return img.crop((left, top, left + crop_size, top + crop_size))


def image_to_pixels_with_pillow(image_path, contrast):
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    img = random_square_crop(img)
    img = apply_pillow_contrast(img, contrast)
    img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

    pixels = []

    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            r, g, b = img.getpixel((x, y))
            row.append((r, g, b))
        pixels.append(row)

    return pixels, img


def find_imagemagick():
    for candidate in ("magick", "convert"):
        binary = shutil.which(candidate)
        if binary:
            return binary
    return None


def run_imagemagick(binary, args):
    result = subprocess.run(
        [binary, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_image_size_with_imagemagick(binary, image_path):
    size_text = run_imagemagick(binary, ["identify", "-format", "%w %h", str(image_path)])
    width_text, height_text = size_text.strip().split()
    return int(width_text), int(height_text)


def parse_pixels_from_imagemagick(pixel_text):
    pixels = [[None for _ in range(SIZE)] for _ in range(SIZE)]

    for line in pixel_text.splitlines():
        match = PIXEL_LINE_RE.search(line)
        if not match:
            continue

        x = int(match.group("x"))
        y = int(match.group("y"))
        r = int(match.group("r"))
        g = int(match.group("g"))
        b = int(match.group("b"))

        if x < SIZE and y < SIZE:
            pixels[y][x] = (r, g, b)

    if any(pixel is None for row in pixels for pixel in row):
        raise RuntimeError("ImageMagick did not return a complete 16x16 pixel grid.")

    return pixels


def image_to_pixels_with_imagemagick(image_path, preview_path, contrast):
    binary = find_imagemagick()
    if not binary:
        raise RuntimeError(
            "This script needs Pillow (`pip install Pillow`) or ImageMagick (`magick`)."
        )

    width, height = get_image_size_with_imagemagick(binary, image_path)
    crop_size, left, top = random_square_crop_box(width, height)
    crop_geometry = f"{crop_size}x{crop_size}+{left}+{top}"
    contrast_args = []
    if contrast != 1.0:
        contrast_amount = max(0.0, (contrast - 1.0) * 12.0)
        contrast_args = ["-sigmoidal-contrast", f"{contrast_amount:.2f}x50%"]

    pixel_text = run_imagemagick(
        binary,
        [
            str(image_path),
            "-auto-orient",
            "-crop",
            crop_geometry,
            "+repage",
            *contrast_args,
            "-resize",
            f"{SIZE}x{SIZE}!",
            "-alpha",
            "off",
            "-depth",
            "8",
            "txt:-",
        ],
    )
    pixels = parse_pixels_from_imagemagick(pixel_text)

    subprocess.run(
        [
            binary,
            str(image_path),
            "-auto-orient",
            "-crop",
            crop_geometry,
            "+repage",
            *contrast_args,
            "-resize",
            f"{SIZE}x{SIZE}!",
            "-sample",
            f"{PREVIEW_SIZE}x{PREVIEW_SIZE}!",
            str(preview_path),
        ],
        check=True,
    )

    return pixels, None


def image_to_pixels(image_path, preview_path, contrast):
    if Image is not None:
        return image_to_pixels_with_pillow(image_path, contrast)

    return image_to_pixels_with_imagemagick(image_path, preview_path, contrast)


def print_pixels(pixels):
    print("pixels = [")
    for row in pixels:
        print("    [" + ", ".join(f"({r},{g},{b})" for r, g, b in row) + "],")
    print("]")


def save_pixels_file(pixels, output_path):
    with open(output_path, "w", encoding="utf-8") as file:
        file.write("pixels = [\n")
        for row in pixels:
            file.write("    [" + ", ".join(f"({r},{g},{b})" for r, g, b in row) + "],\n")
        file.write("]\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python image_to_16x16.py image.jpg [--contrast 2.5]")
        return

    try:
        image_path, contrast = parse_args(sys.argv)
    except ValueError as error:
        print(error)
        return

    if not image_path.is_absolute():
        image_path = image_path.resolve()

    if not image_path.exists():
        print("Image not found")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    image_stem = image_path.stem
    pixels_path = OUTPUT_DIR / f"{image_stem}_pixels.py"
    preview_path = OUTPUT_DIR / f"{image_stem}_preview_16x16.png"

    pixels, small_img = image_to_pixels(image_path, preview_path, contrast)

    print_pixels(pixels)
    save_pixels_file(pixels, pixels_path)

    if small_img is not None:
        preview = small_img.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.NEAREST)
        preview.save(preview_path)

    print(f"Saved pixel data to {pixels_path}")
    print(f"Saved preview image to {preview_path}")


if __name__ == "__main__":
    main()
