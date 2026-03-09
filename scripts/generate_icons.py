#!/usr/bin/env python3
"""
generate_icons.py — Creates SkillOS PWA icons in all required sizes.
Run once: python3 scripts/generate_icons.py
Requires: pip install Pillow
"""
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Install Pillow first: pip install Pillow --break-system-packages")
    sys.exit(1)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "icons")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    radius = size // 5
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=(124, 106, 247, 255))

    # "S" letter in center
    font_size = int(size * 0.55)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) // 2 - bbox[0]
    y = (size - h) // 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img


for size in SIZES:
    icon = create_icon(size)
    path = os.path.join(OUTPUT_DIR, f"icon-{size}.png")
    icon.save(path, "PNG")
    print(f"  Created {path}")

print(f"\nAll {len(SIZES)} icons generated in {OUTPUT_DIR}")
print("PWA icons are ready!")
