#!/usr/bin/env python3
"""Render every profile panel in assets/ from data/profile.toml.

    python3 scripts/render.py            # static panels + globe/data.json
    python3 scripts/render.py activity   # live commit panel (needs `gh` auth)

One visual system: near-black panels, a fine grid, registration marks, and a single
orange "signal" that travels each panel's path. Panels are 720 wide so that essential
text (>= 17px) still renders ~8px on a phone. Motion is CSS, so viewers with
prefers-reduced-motion get still frames. Stdlib only.
"""
import json, math, os, subprocess, sys, tomllib, urllib.request
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS, DATA = os.path.join(ROOT, "assets"), os.path.join(ROOT, "data")
USER = os.environ.get("GH_USER", "DEEPESH-845")

# ── design tokens ───────────────────────────────────────────────────────────
BG, SURFACE, BORDER, HAIR = "#0B0D11", "#11151B", "#222933", "#171C24"
TEXT, TEXT2, MUTED = "#ECEFF4", "#A7B0BE", "#7A8494"
SIGNAL, SIGNAL_SOFT, WARM = "#FF7A1A", "#FFA766", "#1A120B"
COOL = "#7D9BBF"
SANS = "ui-sans-serif,-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
W = 720

STYLE = f"""<style>
.s{{font-family:{SANS}}} .m{{font-family:{MONO}}}
.p{{stroke-dasharray:.035 1.2;stroke-dashoffset:.035;animation:run var(--d,5s) linear infinite var(--o,0s)}}
.b{{animation:blink 2.4s ease-in-out infinite}}
@keyframes run{{to{{stroke-dashoffset:-1.165}}}}
@keyframes blink{{50%{{opacity:.2}}}}
@media (prefers-reduced-motion:reduce){{.p{{animation:none;opacity:0}}.b{{animation:none}}}}
</style>"""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def panel(h, label, body):
    """Shared frame: grid, corner registration marks, hairline border."""
    marks = "".join(
        f'<path d="M{x-6} {y}h12M{x} {y-6}v12" stroke="{MUTED}" stroke-opacity=".55"/>'
        for x, y in ((18, 18), (W - 18, 18), (18, h - 18), (W - 18, h - 18)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
            f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title>{STYLE}'
            f'<defs><pattern id="g" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<path d="M24 0H0V24" fill="none" stroke="#fff" stroke-opacity=".03"/></pattern>'
            f'<clipPath id="c"><rect width="{W}" height="{h}" rx="14"/></clipPath></defs>'
            f'<g clip-path="url(#c)"><rect width="{W}" height="{h}" fill="{BG}"/>'
            f'<rect width="{W}" height="{h}" fill="url(#g)"/>{marks}{body}'
            f'<rect x=".5" y=".5" width="{W-1}" height="{h-1}" rx="14" fill="none" stroke="{BORDER}"/></g></svg>\n')


def text(x, y, s, size, fill=TEXT, cls="s", anchor="start", weight=400, ls=0, extra=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    w = f' font-weight="{weight}"' if weight != 400 else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"{a}{w}{l}{extra}>{esc(s)}</text>'


def node(x, y, hot=False):
    c = SIGNAL if hot else MUTED
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{BG}" stroke="{c}" stroke-width="1.4"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{c}"/>')


def signal(d, dur=5, offset=0, width=3.2):
    """A wire plus the packet that travels it. `d` is any SVG path."""
    return (f'<path d="{d}" fill="none" stroke="{BORDER}" stroke-width="1.4"/>'
            f'<path class="p" style="--d:{dur}s;--o:{offset}s" d="{d}" pathLength="1" fill="none" '
            f'stroke="{SIGNAL}" stroke-width="{width}" stroke-linecap="round"/>')


# ── panels ──────────────────────────────────────────────────────────────────
def hero(d):
    i, tops = d["identity"], [a for a in d["award"] if a["tier"] == 1]
    label = (f'{i["name"]}, based in {i["base"].title()}. {i["tagline"]}. {i["line1"]} {i["line2"]} '
             + ". ".join(f'{a["title"].title()}, {a["event"]}' for a in tops) + f'. {i["now"].capitalize()}.')
    b = [f'<circle class="b" cx="44" cy="52" r="4" fill="{SIGNAL}"/>',
         text(58, 57, i["now"], 14, TEXT2, "m", ls=1.2),
         text(38, 138, i["name"], 66, TEXT, weight=700, ls=-1.6),
         text(40, 182, i["tagline"].upper(), 17, SIGNAL, "m", ls=3),
         text(616, 248, "BASE · " + i["base"], 12, MUTED, "m", "middle", ls=1.5),
         text(40, 232, i["line1"], 23, TEXT2),
         text(40, 264, i["line2"], 23, TEXT2),
         signal("M40 318H680", dur=6)]
    for k, a in enumerate(tops):
        x = 40 + k * 222
        b += [node(x, 318, hot=k == 0),
              text(x - 2, 352, a.get("hero_title", a["title"]), 16.5, SIGNAL_SOFT if k == 0 else TEXT, "m", weight=700, ls=.6),
              text(x - 2, 375, a["hero"], 13.5, MUTED, "m", ls=.8)]
    b.append(f'<path d="M680 312l8 6-8 6" fill="none" stroke="{MUTED}" stroke-width="1.4"/>')
    base = next(p for p in d["place"] if p["kind"] == "base")
    b.insert(0, sphere(projector(base["lat"] + 8, base["lon"] - 18, 0, 78, 616, 146), 78, 616, 146, d["place"], small=True))
    return panel(400, label, "".join(b))


def targets(d):
    rows = d["target"]
    top, rh = 64, 62
    h = top + rh * len(rows) + 18
    label = "Where my models run: " + "; ".join(
        f'{r["where"]}, {r["project"].title()}, {r["metric"]}' for r in rows) + "."
    b = [text(72, 38, "DEPLOYMENT TARGET · SYSTEM", 13, MUTED, "m", ls=2),
         text(680, 38, "MEASURED", 13, MUTED, "m", "end", ls=2),
         signal(f"M44 {top + rh/2}V{top + rh*(len(rows)-.5)}", dur=4.5, width=3.6)]
    for k, r in enumerate(rows):
        y = top + k * rh
        if k:
            b.append(f'<path d="M72 {y}H680" stroke="{HAIR}"/>')
        b += [node(44, y + rh / 2, hot=k == len(rows) - 1),
              text(72, y + 29, r["where"], 20, TEXT),
              text(72, y + 50, r["project"], 13, MUTED, "m", ls=2),
              text(680, y + 38, r["metric"], 22, SIGNAL_SOFT, anchor="end", weight=600)]
    return panel(h, label, "".join(b))


def strip(name, s):
    """Six stages as two rows of three; the trace wraps like a line of text."""
    bw, bh, xs, ys = 196, 66, (40, 262, 484), (30, 152)
    cy1, cy2, mid = ys[0] + bh / 2, ys[1] + bh / 2, (ys[0] + bh + ys[1]) / 2
    trace = (f"M14 {cy1}H692q14 0 14 14V{mid-14}q0 14-14 14H28q-14 0-14 14V{cy2-14}"
             f"q0 14 14 14H706")
    label = f'{name.title()} pipeline: ' + ", then ".join(f"{a} ({b})" for a, b in s["stages"]) + "."
    b = [signal(trace, dur=7)]
    for k, (title, sub) in enumerate(s["stages"]):
        x, y, hot = xs[k % 3], ys[k // 3], k == s["hot"]
        b += [f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{WARM if hot else SURFACE}" '
              f'stroke="{SIGNAL if hot else BORDER}" stroke-opacity="{.7 if hot else 1}"/>',
              text(x + 12, y + 17, f"{k+1:02d}", 11, MUTED, "m"),
              text(x + bw / 2, y + 33, title, 17, SIGNAL_SOFT if hot else TEXT, "m", "middle", 700, .5),
              text(x + bw / 2, y + 54, sub, 14, TEXT2, anchor="middle")]
    return panel(248, label, "".join(b))


def record(d):
    t1, t2 = [a for a in d["award"] if a["tier"] == 1], [a for a in d["award"] if a["tier"] == 2]
    label = "Record. " + " ".join(
        f'{a["title"].title()}, {a["event"]}: {a["figure"]} {a["figure_sub"]}; {a["meta"].lower()}.' for a in t1) + \
        " Also: " + "; ".join(f'{a["title"].title()}, {a["event"]} {a["meta"].lower()}' for a in t2) + "."
    b, y = [], 22
    for k, a in enumerate(t1):
        if k:
            b.append(f'<path d="M40 {y}H680" stroke="{HAIR}"/>')
        b += [text(40, y + 40, a["title"], 24, SIGNAL if k == 0 else TEXT, weight=700, ls=.3),
              text(40, y + 68, a["event"], 18, TEXT2),
              text(40, y + 92, a["meta"], 13.5, MUTED, "m", ls=1),
              text(680, y + 54, a["figure"], 40, TEXT, anchor="end", weight=700, ls=-1),
              text(680, y + 80, a["figure_sub"], 13, MUTED, "m", "end", ls=.5)]
        y += 108
    b += [f'<path d="M40 {y+6}H680" stroke="{BORDER}"/>', text(40, y + 36, "ALSO ON THE RECORD", 13, MUTED, "m", ls=2)]
    y += 54
    for k, a in enumerate(t2):
        x, yy = 40 + (k % 2) * 330, y + (k // 2) * 78
        b += [f'<path d="M{x} {yy+6}v58" stroke="{SIGNAL if k == 0 else BORDER}" stroke-width="2"/>',
              text(x + 16, yy + 24, a["title"], 15, TEXT, "m", weight=700, ls=.6),
              text(x + 16, yy + 46, a["event"], 16, TEXT2),
              text(x + 16, yy + 66, a["meta"], 12.5, MUTED, "m", ls=1)]
    return panel(y + 2 * 78 + 14, label, "".join(b))


def footer(d):
    b = [signal("M40 64H330", dur=4), signal("M680 64H390", dur=4, offset=-2),
         f'<circle cx="360" cy="64" r="22" fill="none" stroke="{BORDER}"/>',
         f'<circle cx="360" cy="64" r="13" fill="none" stroke="{SIGNAL}" stroke-opacity=".45"/>',
         f'<circle class="b" cx="360" cy="64" r="4" fill="{SIGNAL}"/>',
         text(360, 128, "Make it real. Then make it checkable.", 24, TEXT, anchor="middle", weight=600),
         text(360, 156, "DEEPESH KAKKAR · AI / FULL-STACK ENGINEER", 13, MUTED, "m", "middle", ls=2)]
    return panel(184, "Make it real. Then make it checkable. Deepesh Kakkar.", "".join(b))


# ── globe ───────────────────────────────────────────────────────────────────
LAND_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"


def fib(n):
    """n near-uniform points on the sphere as (lat, lon) degrees."""
    g = math.pi * (3 - math.sqrt(5))
    return [(math.degrees(math.asin(1 - 2 * (k + .5) / n)), (math.degrees(k * g) + 180) % 360 - 180) for k in range(n)]


def inside(lon, lat, ring):
    hit, j = False, len(ring) - 1
    for i in range(len(ring)):
        (xi, yi), (xj, yj) = ring[i], ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def land(n=11000):
    """Land points, cached in data/land.json. Natural Earth 110m, fetched once."""
    path = os.path.join(DATA, "land.json")
    if os.path.exists(path):
        return json.load(open(path))
    geo = json.load(urllib.request.urlopen(LAND_URL))
    polys = []
    for f in geo["features"]:
        g = f["geometry"]
        for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            r = p[0]
            polys.append((min(x for x, _ in r), max(x for x, _ in r), min(y for _, y in r), max(y for _, y in r), r))
    pts = [[round(la, 2), round(lo, 2)] for la, lo in fib(n)
           if any(a <= lo <= b and c <= la <= e and inside(lo, la, r) for a, b, c, e, r in polys)]
    json.dump(pts, open(path, "w"), separators=(",", ":"))
    return pts


def vec(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))


def view(places, max_lat=52):
    """North-up centre that keeps every place furthest from the limb."""
    vs = [vec(p["lat"], p["lon"]) for p in places]
    return max(((la, lo) for la in range(0, max_lat + 1, 2) for lo in range(-180, 180, 2)),
               key=lambda c: min(sum(a * b for a, b in zip(vec(*c), v)) for v in vs))


def projector(lat0, lon0, roll, R, cx, cy):
    p0, l0 = math.radians(lat0), math.radians(lon0)
    cr, sr = math.cos(roll), math.sin(roll)

    def proj(v, r=1.0):
        x, y, z = v
        lam = math.atan2(y, x)
        phi = math.asin(max(-1, min(1, z / math.sqrt(x * x + y * y + z * z))))
        X = math.cos(phi) * math.sin(lam - l0)
        Y = math.cos(p0) * math.sin(phi) - math.sin(p0) * math.cos(phi) * math.cos(lam - l0)
        Z = math.sin(p0) * math.sin(phi) + math.cos(p0) * math.cos(phi) * math.cos(lam - l0)
        X, Y = X * cr - Y * sr, X * sr + Y * cr
        return cx + R * r * X, cy - R * r * Y, Z
    return proj


def arc(a, b, lift=.22, n=72):
    """Great circle from a to b, raised mid-flight so it reads as a path through space.
    Short hops rise less, so a domestic arc hugs the surface."""
    om = math.acos(max(-1, min(1, sum(x * y for x, y in zip(a, b)))))
    lift *= min(1, om / (math.pi / 2))
    out = []
    for k in range(n + 1):
        t = k / n
        s1, s2 = math.sin((1 - t) * om) / math.sin(om), math.sin(t * om) / math.sin(om)
        out.append((tuple(s1 * x + s2 * y for x, y in zip(a, b)), 1 + lift * math.sin(math.pi * t)))
    return out


def sphere(proj, R, cx, cy, places, small=False):
    """Particle Earth: graticule, land points in depth buckets, arcs from base, nodes."""
    base = next(p for p in places if p["kind"] == "base")
    others = [p for p in places if p is not base]
    gid = "sh" if small else "sph"
    b = [f'<defs><radialGradient id="{gid}" cx="40%" cy="36%" r="72%">'
         f'<stop offset="0" stop-color="#17222F"/><stop offset="1" stop-color="{BG}"/></radialGradient></defs>',
         f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#{gid})"/>']
    for lat in range(-60, 90, 30):
        b.append(line_path([proj(vec(lat, lo)) for lo in range(-180, 181, 3)], COOL, .13))
    for lon in range(-180, 180, 30):
        b.append(line_path([proj(vec(la, lon)) for la in range(-88, 89, 3)], COOL, .13))
    buckets = [[] for _ in range(4)]
    for la, lo in land():
        x, y, z = proj(vec(la, lo))
        if z > .02:
            buckets[min(3, int(z * 4))].append(f"M{x:.1f} {y:.1f}h0")
    for k, pts in enumerate(buckets):
        b.append(f'<path d="{"".join(pts)}" stroke="{COOL}" stroke-opacity="{.2 + .2 * k:.2f}" '
                 f'stroke-width="{(1.7 + .45 * k) * (.75 if small else 1):.2f}" stroke-linecap="round"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{COOL}" stroke-opacity=".35"/>')
    for k, p in enumerate(others):
        pts = [proj(v, r) for v, r in arc(vec(base["lat"], base["lon"]), vec(p["lat"], p["lon"]))]
        if small:   # stub: only the part that leaves the visible face
            pts = pts[:24]
        pts = [q for q in pts if q[2] > -.05 or math.hypot(q[0] - cx, q[1] - cy) > R]
        dd = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y, _ in pts)
        b.append(f'<path d="{dd}" fill="none" stroke="{SIGNAL}" stroke-opacity=".4" stroke-width="1.3"/>')
        b.append(f'<path class="p" style="--d:{3.6 if small else 4.8}s;--o:{-1.6 * k}s" d="{dd}" pathLength="1" '
                 f'fill="none" stroke="{SIGNAL_SOFT}" stroke-width="{2.6 if small else 3.4}" stroke-linecap="round"/>')
    tags = []
    for k, p in enumerate(places):
        x, y, z = proj(vec(p["lat"], p["lon"]))
        if z < 0:
            continue
        hot = p is base
        b.append(node(x, y, hot))
        if hot:
            b.append(f'<circle class="b" cx="{x:.1f}" cy="{y:.1f}" r="13" fill="none" stroke="{SIGNAL}" stroke-opacity=".5"/>')
        if small:
            continue
        dx, dy = x - cx, y - cy
        n = math.hypot(dx, dy) or 1
        tx, ty = x + dx / n * 24, y + dy / n * 24 + 5
        if tx < 34 or tx > W - 34:     # would leave the panel: tag inward instead
            tx, ty = x + (24 if tx < 34 else -24), y + 5
        while any(abs(tx - a) < 26 and abs(ty - c) < 16 for a, c in tags):
            ty += 16
        tags.append((tx, ty))
        b.append(text(tx, ty, f"{k:02d}", 13, SIGNAL_SOFT if hot else TEXT2, "m", "middle", 700))
    return "".join(b)


def globe(d):
    places = d["place"]
    base = next(p for p in places if p["kind"] == "base")
    others = [p for p in places if p is not base]
    lat0, lon0 = d.get("globe", {}).get("centre") or view(places)
    R, cx, cy = 208, 240, 300
    b = [sphere(projector(lat0, lon0, 0, R, cx, cy), R, cx, cy, places)]
    lx, ly = 470, 74
    b += [text(lx, ly - 22, "BUILT IN INDIA", 14, SIGNAL, "m", weight=700, ls=2)]
    for k, p in enumerate(places):
        y = ly + 16 + k * 76
        b += [text(lx, y + 4, f"{k:02d}", 13, SIGNAL_SOFT if p is base else MUTED, "m", weight=700),
              text(lx + 30, y + 5, p["label"], 17, TEXT, "m", weight=700, ls=.5),
              text(lx + 30, y + 28, p["org"], 15, TEXT2),
              text(lx + 30, y + 48, p["what"], 13.5, MUTED)]
    b.append(text(lx, 400, "All work done from India.", 13, MUTED))
    label = ("Global reach: a particle globe with arcs from " + base["label"].title() + " to " +
             ", ".join(f'{p["label"].title()} ({p["org"]}, {p["what"]})' for p in others) +
             ". All work was done from India.")
    json.dump({"view": {"lat": lat0, "lon": lon0}, "places": places, "land": land()},
              open(os.path.join(ROOT, "globe", "data.json"), "w"), separators=(",", ":"))
    return panel(464, label, "".join(b))


def line_path(pts, color, op):
    segs, cur = [], []
    for x, y, z in pts:
        if z > 0:
            cur.append(f"{x:.1f} {y:.1f}")
        elif cur:
            segs.append(cur); cur = []
    if cur:
        segs.append(cur)
    d = "".join("M" + "L".join(s) for s in segs if len(s) > 1)
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{op}" stroke-width=".8"/>' if d else ""


# ── activity (live) ─────────────────────────────────────────────────────────
QUERY = """{ user(login: "%s") { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount } } } } } }"""


def smooth(pts):
    """Catmull-Rom through every point, emitted as cubic beziers."""
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)


def rolling(vals, n=4):
    """Trailing n-point mean; the raw weekly series is too bursty to read."""
    return [sum(vals[max(i - n + 1, 0):i + 1]) / min(i + 1, n) for i in range(len(vals))]


assert rolling([0, 4, 8, 12, 16]) == [0, 2, 4, 6, 10]


def activity(d, cal):
    weeks = [(w["contributionDays"][0]["date"], sum(x["contributionCount"] for x in w["contributionDays"]))
             for w in cal["weeks"]]
    vals = rolling([v for _, v in weeks])
    peak, n, total = max(vals) or 1, len(weeks), cal["totalContributions"]
    X0, X1, Y0, Y1 = 40, 680, 110, 238
    pts = [(X0 + i * (X1 - X0) / (n - 1), Y1 - v / peak * (Y1 - Y0)) for i, v in enumerate(vals)]
    line = smooth(pts)
    b = [text(40, 46, "COMMITS · 4-WEEK ROLLING AVERAGE", 13, MUTED, "m", ls=2),
         f'<text class="s" x="40" y="82" font-size="28" font-weight="700" fill="{TEXT}">{total:,}'
         f'<tspan font-size="17" font-weight="400" fill="{TEXT2}"> contributions in the last 12 months</tspan></text>',
         '<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{SIGNAL}" stop-opacity=".3"/><stop offset="1" stop-color="{SIGNAL}" stop-opacity="0"/>'
         '</linearGradient></defs>']
    b += [f'<path d="M{X0} {Y1 - f * (Y1 - Y0):.1f}H{X1}" stroke="{HAIR}"/>' for f in (0, .5, 1)]
    b += [f'<path d="{line} L{X1},{Y1} L{X0},{Y1} Z" fill="url(#f)"/>', signal(line, dur=7, width=3.4).replace(
        f'stroke="{BORDER}" stroke-width="1.4"', f'stroke="{SIGNAL}" stroke-width="2.2"')]
    first = date.fromisoformat(weeks[0][0])
    for m in d.get("milestone", []):
        i = (date.fromisoformat(m["date"]) - first).days / 7
        if 0 <= i <= n - 1:
            x = X0 + i * (X1 - X0) / (n - 1)
            y = pts[min(int(round(i)), n - 1)][1]
            b += [f'<path d="M{x:.1f} {y - 8:.1f}V{Y0 - 14}" stroke="{SIGNAL}" stroke-opacity=".5" stroke-dasharray="2 3"/>',
                  node(x, y, True)]
    # labels stacked so neighbours never collide
    ms = [m for m in d.get("milestone", []) if 0 <= (date.fromisoformat(m["date"]) - first).days / 7 <= n - 1]
    for k, m in enumerate(ms):
        x = X0 + (date.fromisoformat(m["date"]) - first).days / 7 * (X1 - X0) / (n - 1)
        b.append(text(min(x, X1), Y0 - 18 - 16 * (len(ms) - 1 - k), m["label"], 12.5, SIGNAL_SOFT, "m", "end", 700, 1))
    seen, last = set(), -99
    for i, (iso, _) in enumerate(weeks):
        dt, x = date.fromisoformat(iso), X0 + i * (X1 - X0) / (n - 1)
        if dt.month not in seen and dt.day <= 7 and x - last > 44:
            seen.add(dt.month); last = x
            b.append(text(x, Y1 + 26, dt.strftime("%b").upper(), 12, MUTED, "m", "middle"))
    label = (f"Commit activity over the last twelve months, four-week rolling average: {total} contributions. "
             "Marked: " + "; ".join(m["label"].lower() for m in ms) + ".")
    return panel(282, label, "".join(b))


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def write(name, svg):
    open(os.path.join(ASSETS, name), "w").write(svg)
    print(f"  {name:22s} {len(svg.encode()) / 1024:6.1f} KB", file=sys.stderr)


if __name__ == "__main__":
    d = tomllib.load(open(os.path.join(DATA, "profile.toml"), "rb"))
    if sys.argv[1:] == ["activity"]:
        cal = json.loads(gh("api", "graphql", "-f", "query=" + QUERY % USER))
        write("activity.svg", activity(d, cal["data"]["user"]["contributionsCollection"]["contributionCalendar"]))
        sys.exit()
    write("hero.svg", hero(d))
    write("targets.svg", targets(d))
    for k, s in d["system"].items():
        write(f"sys-{k}.svg", strip(k, s))
    write("record.svg", record(d))
    write("globe.svg", globe(d))
    write("footer.svg", footer(d))
