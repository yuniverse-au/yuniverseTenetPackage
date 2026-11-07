"""Renders the yuniverse.au homepage dither + logo as a seamless looping GIF for the keyboard.

    python generate.py logo_256x32.png animation.gif

Same maths as the old firmware dither screen (fixed-point Perlin fBm with domain warp, the site's
8x8 Bayer matrix, the logo blended with "difference"), but the noise field is crossfaded between
time 0 and the loop length so the last frame flows into the first.
"""
import sys
import numpy as np
from PIL import Image
import dither_ref as ref

FRAMES, FPS = 60, 8
TICKS_PER_FRAME = 100 // FPS                    # firmware ticks are 10 ms
SPEED = lambda acc: (acc * 39) >> 3             # the slower v11 wave speed


def render(G, logo):
    out = np.zeros((32, 256), np.uint8)
    for y in range(32):
        gy, fy = y >> 2, y & 3
        for x in range(256):
            gx, fx = x >> 2, x & 3
            i = gy * 65 + gx
            t = G[i] * (4 - fx) + G[i + 1] * fx
            bt = G[i + 65] * (4 - fx) + G[i + 66] * fx
            m = (t * (4 - fy) + bt * fy) >> 4
            d = ref.DOT if ref.LUT[m] > ref.BAYER[(y & 7) * 8 + (x & 7)] * 4 else 0
            lg = logo[y - 2][x - 4] if 2 <= y < 30 and 4 <= x < 126 else 0
            out[y, x] = abs(d - lg)
    return out


def main(logo_path, out_path):
    logo = ref.load_logo(logo_path)
    loop = FRAMES * TICKS_PER_FRAME
    TL = SPEED(loop)
    frames = []
    for k in range(FRAMES):
        T = SPEED(k * TICKS_PER_FRAME)
        a = np.array(ref.grid(T), float)
        b = np.array(ref.grid(T - TL), float)
        w = k / FRAMES
        G = np.clip(np.round(a * (1 - w) + b * w), 0, 255).astype(int).tolist()
        frames.append(Image.fromarray((render(G, logo) * 17).astype(np.uint8)))
        print(f"\rframe {k + 1}/{FRAMES}", end="", flush=True)
    print()
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=1000 // FPS,
                   loop=0, optimize=False, disposal=1)
    print("wrote", out_path)


if __name__ == "__main__":
    main(*(sys.argv[1:3] if len(sys.argv) >= 3 else ("logo_256x32.png", "animation.gif")))
