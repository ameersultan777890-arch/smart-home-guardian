"""Generates thumbnail.png (1500x1000, 3:2) for Devpost.  python make_thumbnail.py"""
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1500, 1000
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
f = lambda p, s: ImageFont.truetype(p, s)

# background gradient
img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    for x in range(W):
        t = (x / W) * 0.55 + (y / H) * 0.45
        px[x, y] = (int(8 + 10 * t), int(16 + 26 * t), int(38 + 42 * t))

# subtle grid
d = ImageDraw.Draw(img, "RGBA")
for x in range(0, W, 60):
    d.line([(x, 0), (x, H)], fill=(120, 190, 255, 14))
for y in range(0, H, 60):
    d.line([(0, y), (W, y)], fill=(120, 190, 255, 14))

# glow behind shield
cx, cy = 1100, 500
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([cx - 300, cy - 300, cx + 300, cy + 300], fill=(0, 220, 190, 90))
glow = glow.filter(ImageFilter.GaussianBlur(90))
img.paste(glow, (0, 0), glow)
d = ImageDraw.Draw(img, "RGBA")

# orbit rings + device nodes
for r in (280, 350):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 230, 200, 70), width=3)
nodes = [(-125, 350, "sensor"), (-75, 280, "lock"), (-25, 350, "cam"), (25, 280, "wifi"), (60, 350, "bulb"), (125, 280, "door")]
for ang, r, kind in nodes:
    a = math.radians(ang)
    nx, ny = cx + r * math.cos(a), cy + r * math.sin(a)
    d.line([(cx, cy), (nx, ny)], fill=(0, 230, 200, 45), width=2)
    d.ellipse([nx - 44, ny - 44, nx + 44, ny + 44], fill=(14, 30, 58, 255), outline=(0, 230, 200, 255), width=4)
    c = (0, 235, 205, 255)
    if kind == "lock":
        d.rounded_rectangle([nx - 17, ny - 4, nx + 17, ny + 22], 5, fill=c)
        d.arc([nx - 12, ny - 24, nx + 12, ny + 4], 180, 360, fill=c, width=5)
    elif kind == "cam":
        d.rounded_rectangle([nx - 22, ny - 13, nx + 10, ny + 13], 5, fill=c)
        d.polygon([(nx + 12, ny - 6), (nx + 24, ny - 13), (nx + 24, ny + 13), (nx + 12, ny + 6)], fill=c)
    elif kind == "wifi":
        for i, rr in enumerate((8, 18, 28)):
            d.arc([nx - rr, ny + 10 - rr, nx + rr, ny + 10 + rr], 225, 315, fill=c, width=5)
        d.ellipse([nx - 4, ny + 6, nx + 4, ny + 14], fill=c)
    elif kind == "bulb":
        d.ellipse([nx - 15, ny - 22, nx + 15, ny + 8], fill=c)
        d.rectangle([nx - 8, ny + 8, nx + 8, ny + 20], fill=c)
    elif kind == "door":
        d.rectangle([nx - 15, ny - 22, nx + 15, ny + 22], outline=c, width=5)
        d.ellipse([nx + 4, ny - 2, nx + 10, ny + 4], fill=c)
    else:
        d.ellipse([nx - 6, ny - 6, nx + 6, ny + 6], fill=c)
        for rr in (14, 24):
            d.arc([nx - rr, ny - rr, nx + rr, ny + rr], 300, 60, fill=c, width=4)
            d.arc([nx - rr, ny - rr, nx + rr, ny + rr], 120, 240, fill=c, width=4)

# shield
sw, sh = 190, 235
shield = [(cx, cy - sh), (cx + sw, cy - sh * 0.72), (cx + sw, cy + 20), (cx + sw * 0.82, cy + sh * 0.55),
          (cx, cy + sh), (cx - sw * 0.82, cy + sh * 0.55), (cx - sw, cy + 20), (cx - sw, cy - sh * 0.72)]
d.polygon(shield, fill=(10, 28, 56, 255))
d.line(shield + [shield[0]], fill=(0, 235, 205, 255), width=10, joint="curve")
inner = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.86) for x, y in shield]
d.line(inner + [inner[0]], fill=(0, 235, 205, 90), width=3, joint="curve")

# house inside shield (scaled)
k = 0.76
P = lambda dx, dy: (cx + dx * k, cy + dy * k)
d.polygon([P(0, -150), P(130, -40), P(-130, -40)], fill=(0, 235, 205, 255))
d.rectangle([*P(-100, -40), *P(100, 110)], fill=(0, 235, 205, 255))
d.rectangle([*P(58, -120), *P(90, -70)], fill=(0, 235, 205, 255))
d.line([P(-52, 28), P(-12, 70), P(56, -12)], fill=(10, 28, 56, 255), width=20, joint="curve")

# voice waveform under shield
bars = [18, 40, 72, 48, 90, 56, 30, 64, 24]
bx = cx - (len(bars) * 26) / 2
for i, h in enumerate(bars):
    x0 = bx + i * 26
    d.rounded_rectangle([x0, 860 - h / 2, x0 + 12, 860 + h / 2], 6, fill=(0, 235, 205, 230))

# text
d.rounded_rectangle([80, 120, 640, 176], 28, fill=(0, 235, 205, 38), outline=(0, 235, 205, 200), width=2)
d.text((110, 133), "ALEXA+ TRACK  •  VOICE SECURITY", font=f(BOLD, 26), fill=(0, 235, 205))
d.text((80, 262), "Smart Home", font=f(BOLD, 114), fill=(255, 255, 255))
d.text((80, 392), "Guardian", font=f(BOLD, 114), fill=(0, 235, 205))
d.text((84, 590), "Audit. Alert. Lock down.", font=f(BOLD, 48), fill=(225, 236, 250))
d.text((84, 665), "Secure your connected home\nby just talking to Alexa.", font=f(REG, 38), fill=(160, 184, 214), spacing=12)
d.text((84, 880), "Amazon Developer Hackathon 2026", font=f(REG, 28), fill=(120, 150, 190))

img.save("thumbnail.png", optimize=True)
print(img.size, "saved")
