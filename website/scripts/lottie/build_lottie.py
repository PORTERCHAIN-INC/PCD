#!/usr/bin/env python3
"""Build the website's Lottie files into public/lottie/ (run: python3 scripts/lottie/build_lottie.py).

- van-route.json, success-check.json: authored here (PorterChain's own), shape layers only.
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "public", "lottie")
REPO = os.path.dirname(ROOT)

DROP = {"nm", "mn", "ix", "cl", "ln", "np", "cix", "bm", "ddd", "sr", "ao", "ct", "props", "markers", "meta", "fonts", "chars"}


def trim(node, digits=2):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in DROP:
                continue
            if k == "hd" and v is False:
                continue
            out[k] = trim(v, digits)
        return out
    if isinstance(node, list):
        return [trim(v, digits) for v in node]
    if isinstance(node, float):
        r = round(node, digits)
        return int(r) if r == int(r) else r
    return node


def dump(name, data):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"{name}: {os.path.getsize(path):,} bytes")


# ---- helpers for authored animations ---------------------------------------------------------
def static(v):
    return {"a": 0, "k": v}


def anim(frames):
    """frames: list of (t, value) with ease-in-out between keys."""
    ks = []
    for i, (t, v) in enumerate(frames):
        k = {"t": t, "s": v if isinstance(v, list) else [v]}
        if i < len(frames) - 1:
            n = len(k["s"])
            k["i"] = {"x": [0.4] * n, "y": [1] * n}
            k["o"] = {"x": [0.6] * n, "y": [0] * n}
        ks.append(k)
    return {"a": 1, "k": ks}


def tr(p=(0, 0), s=100, o=100, r=0):
    return {"ty": "tr", "p": static(list(p)), "a": static([0, 0]), "s": static([s, s]), "r": static(r), "o": static(o)}


def layer(ind, shapes, op, ks=None, parent=None):
    ks = ks or {}
    base = {"o": static(100), "r": static(0), "p": static([0, 0, 0]), "a": static([0, 0, 0]), "s": static([100, 100, 100])}
    base.update(ks)
    out = {"ind": ind, "ty": 4, "ks": base, "shapes": shapes, "ip": 0, "op": op, "st": 0}
    if parent:
        out["parent"] = parent
    return out


def fill(rgb, o=100):
    return {"ty": "fl", "c": static(rgb + [1]), "o": static(o), "r": 1}


def stroke(rgb, w, dash=None, o=100):
    s = {"ty": "st", "c": static(rgb + [1]), "o": static(o), "w": static(w), "lc": 2, "lj": 2}
    if dash:
        s["d"] = [{"n": "d", "v": static(dash[0])}, {"n": "g", "v": static(dash[1])}, {"n": "o", "v": static(0)}]
    return s


def rect(x, y, w, h, r=0):
    return {"ty": "rc", "d": 1, "p": static([x, y]), "s": static([w, h]), "r": static(r)}


def ellipse(x, y, d):
    return {"ty": "el", "d": 1, "p": static([x, y]), "s": static([d, d])}


def group(items, transform=None):
    return {"ty": "gr", "it": items + [transform or tr()]}


def hexrgb(h):
    h = h.lstrip("#")
    return [round(int(h[i : i + 2], 16) / 255, 3) for i in (0, 2, 4)]


NAVY, BLUE, LIGHT, WHITE, GREEN = hexrgb("0b1220"), hexrgb("1f56d8"), hexrgb("cbd5e1"), hexrgb("ffffff"), hexrgb("047857")


def van_route():
    W, H, FR, OP = 600, 200, 30, 150
    P0, P1, P2, P3 = (60, 140), (250, 150), (350, 50), (540, 64)

    def bez(t):
        mt = 1 - t
        return tuple(mt**3 * a + 3 * mt * mt * t * b + 3 * mt * t * t * c + t**3 * d for a, b, c, d in zip(P0, P1, P2, P3))

    def ease(x):  # matches the trim-path easing closely enough for a 3 s drive
        return x * x * (3 - 2 * x)

    path = {"ty": "sh", "ks": static({"c": False, "v": [list(P0), list(P3)],
            "o": [[P1[0] - P0[0], P1[1] - P0[1]], [0, 0]], "i": [[0, 0], [P2[0] - P3[0], P2[1] - P3[1]]]})}
    DRIVE = 90
    # Arc-length table so the van tracks the trim path instead of the raw bezier parameter.
    samples = [bez(i / 400) for i in range(401)]
    acc = [0.0]
    for a, b in zip(samples, samples[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    total = acc[-1]

    def at_length(frac):
        target = frac * total
        for i, l in enumerate(acc):
            if l >= target:
                return i / 400
        return 1.0

    pos, rot = [], []
    for f in range(0, DRIVE + 1, 6):
        u = at_length(0.9 * ease(f / DRIVE))  # park just short of the pin
        x, y = bez(u)
        x2, y2 = bez(min(1, u + 0.01))
        ang = math.degrees(math.atan2(y2 - y, x2 - x)) if u < 1 else rot[-1]["s"][0]
        pos.append({"t": f, "s": [round(x, 1), round(y, 1), 0]})
        rot.append({"t": f, "s": [round(ang, 1)]})
    pos.append({"t": OP, "s": pos[-1]["s"]})
    rot.append({"t": OP, "s": rot[-1]["s"]})
    for seq in (pos, rot):
        for k in seq[:-1]:
            n = len(k["s"])
            k["i"] = {"x": [0.5] * n, "y": [0.5] * n}
            k["o"] = {"x": [0.5] * n, "y": [0.5] * n}

    route_bg = layer(5, [group([path, stroke(LIGHT, 6, dash=(2, 14))])], OP)
    route_done = layer(4, [group([path, {"ty": "tm", "s": static(0), "e": anim([(0, 0), (DRIVE, 100)]), "o": static(0), "m": 1}, stroke(BLUE, 6)])], OP)
    pickup = layer(3, [group([ellipse(P0[0], P0[1], 22), fill(NAVY)]), group([ellipse(P0[0], P0[1], 8), fill(WHITE)])], OP)
    drop_shapes = [
        group([{"ty": "sh", "ks": static({"c": True, "v": [[0, 0], [-14, -22], [14, -22]], "i": [[0, 0], [0, 0], [0, 0]], "o": [[0, 0], [0, 0], [0, 0]]})}, fill(BLUE)]),
        group([ellipse(0, -26, 28), fill(BLUE)]),
        group([ellipse(0, -26, 10), fill(WHITE)]),
    ]
    drop = layer(2, drop_shapes, OP, ks={"p": static([P3[0], P3[1] - 2, 0]), "s": anim([(0, [100, 100, 100]), (DRIVE, [100, 100, 100]), (DRIVE + 8, [122, 122, 100]), (DRIVE + 16, [100, 100, 100])])})
    van = layer(1, [
        group([rect(-6, 0, 40, 22, 4), fill(NAVY)]),          # cargo box
        group([rect(19, 3, 14, 16, 4), fill(BLUE)]),          # cab
        group([rect(23, -1, 6, 7, 1.5), fill(WHITE)]),        # windscreen
        group([ellipse(-14, 11, 9), fill(NAVY)]),
        group([ellipse(14, 11, 9), fill(NAVY)]),
        group([ellipse(-14, 11, 4), fill(WHITE)]),
        group([ellipse(14, 11, 4), fill(WHITE)]),
    ], OP, ks={"p": {"a": 1, "k": pos}, "r": {"a": 1, "k": rot}, "a": static([0, 10, 0])})
    return {"v": "5.7.4", "fr": FR, "ip": 0, "op": OP, "w": W, "h": H, "assets": [], "layers": [drop, van, pickup, route_done, route_bg]}


def success_check():
    S, OP = 96, 40
    circle = layer(2, [group([ellipse(0, 0, 80), fill(GREEN)])], OP, ks={"p": static([48, 48, 0]), "s": anim([(0, [0, 0, 100]), (12, [108, 108, 100]), (18, [100, 100, 100])])})
    tick_path = {"ty": "sh", "ks": static({"c": False, "v": [[-16, 1], [-5, 12], [17, -11]], "i": [[0, 0], [0, 0], [0, 0]], "o": [[0, 0], [0, 0], [0, 0]]})}
    tick = layer(1, [group([tick_path, {"ty": "tm", "s": static(0), "e": anim([(10, 0), (26, 100)]), "o": static(0), "m": 1}, stroke(WHITE, 8)])], OP, ks={"p": static([48, 48, 0])})
    return {"v": "5.7.4", "fr": 30, "ip": 0, "op": OP, "w": S, "h": S, "assets": [], "layers": [tick, circle]}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    dump("van-route.json", van_route())
    dump("success-check.json", success_check())
