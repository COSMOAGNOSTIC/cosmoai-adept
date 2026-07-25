"""
Generates the static texture assets for the Circuit skin. Run once;
committed output lives alongside this script. Re-run and re-commit if
the look needs to change - Godot just loads the PNGs, no runtime
generation.
"""
from PIL import Image, ImageDraw, ImageFilter

W, H = 960, 540


def bg_circuit():
    img = Image.new("RGB", (W, H), (6, 10, 18))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 40):
        d.line([(x, 0), (x, H)], fill=(20, 34, 48), width=1)
    for y in range(0, H, 40):
        d.line([(0, y), (W, y)], fill=(20, 34, 48), width=1)
    # subtle vignette
    vign = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vign)
    vd.ellipse([-200, -150, W + 200, H + 150], fill=90)
    vign = vign.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(img, dark, vign)
    return img


def glow_sprite(size=160, color=(255, 255, 255)):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.16
    cx = cy = size / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (255,))
    img = img.filter(ImageFilter.GaussianBlur(size * 0.12))
    return img


def scanlines():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, 45))
    return img


bg_circuit().save("bg_circuit.png")
glow_sprite().save("node_glow.png")
scanlines().save("scanlines.png")
print("assets written")
