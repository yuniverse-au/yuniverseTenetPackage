"""Integer reference for the firmware dither (must match dither.c bit-for-bit)."""
import numpy as np, random
from PIL import Image
rng = random.Random(1234)
PERM = list(range(256)); rng.shuffle(PERM)
# 8 gradients, scaled so the noise spread matches the website shader
GX = [ 1,-1, 1,-1, 1,-1, 0, 0]
GY = [ 1, 1,-1,-1, 0, 0, 1,-1]
FADE = [0]*257
for i in range(257):
    t = i/256; FADE[i] = int(round((t*t*t*(t*(t*6-15)+10))*4096))
NSCALE = 5   # noise *NSCALE >> 2
def noise(x, y):                 # Q12 in, Q12 out
    xi, yi = x >> 12, y >> 12
    xf, yf = x & 4095, y & 4095
    def g(ix, iy, dx, dy):
        h = PERM[(PERM[ix & 255] + iy) & 255] & 7
        return GX[h]*dx + GY[h]*dy
    n00 = g(xi, yi, xf, yf); n10 = g(xi+1, yi, xf-4096, yf)
    n01 = g(xi, yi+1, xf, yf-4096); n11 = g(xi+1, yi+1, xf-4096, yf-4096)
    u = FADE[xf >> 4]; v = FADE[yf >> 4]
    a = n00 + (((n10 - n00) * u) >> 12)
    b = n01 + (((n11 - n01) * u) >> 12)
    r = a + (((b - a) * v) >> 12)
    return (r * NSCALE) >> 2
def fbm(x, y):
    a = abs(noise(x, y))
    b = abs(noise((x * 3277) >> 12, (y * 3277) >> 12))
    return a + ((b * 1229) >> 12)
LUT = [min(255, int(round(((i/255) ** 1.3) * 255))) for i in range(256)]
BAYER = [0,48,12,60,3,51,15,63,32,16,44,28,35,19,47,31,8,56,4,52,11,59,7,55,40,24,36,20,43,27,39,23,
 2,50,14,62,1,49,13,61,34,18,46,30,33,17,45,29,10,58,6,54,9,57,5,53,42,26,38,22,41,25,37,21]
DOT = 9
def grid(T):
    G = []
    for gy in range(9):
        v = 992 - 256*gy
        for gx in range(65):
            u = 256*gx + 32 - 8192
            w = fbm(u - T, v - T)
            f = fbm(u + w, v + w)
            m = ((f - 492) * 107) >> 10
            G.append(0 if m < 0 else 255 if m > 255 else m)
    return G
def frame(acc, logo):          # logo: 28 rows x 122 cols of 0..15 ; returns 32x256 levels
    T = (acc * 39) >> 3
    G = grid(T)
    dx = [0,1,2,1,0,-1,-2,-1][(acc >> 14) & 7]
    lx = 4 + dx
    out = np.zeros((32, 256), np.uint8)
    for y in range(32):
        gy, fy = y >> 2, y & 3
        for x in range(256):
            gx, fx = x >> 2, x & 3
            i = gy*65 + gx
            t = G[i] * (4 - fx) + G[i+1] * fx
            bt = G[i+65] * (4 - fx) + G[i+66] * fx
            m = (t * (4 - fy) + bt * fy) >> 4
            lit = LUT[m] > BAYER[(y & 7)*8 + (x & 7)] * 4
            d = DOT if lit else 0
            lg = 0
            if 2 <= y < 30 and lx <= x < lx + 122:
                lg = logo[y-2][x-lx]
            out[y, x] = abs(d - lg)
    return out
def load_logo(path='/home/claude/yuniverse_256x32.png'):
    im = Image.open(path).convert('L'); im = im.crop(im.getbbox())
    a = np.array(im) >> 4
    assert a.shape == (28, 122), a.shape
    return a.tolist()
