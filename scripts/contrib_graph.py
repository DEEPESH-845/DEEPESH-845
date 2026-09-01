#!/usr/bin/env python3
"""Render assets/contributions.svg and assets/languages.svg from live GitHub data.

Kept in-repo so both panels match the profile palette and the README depends
on no third-party card service staying up. Refreshed by
.github/workflows/contributions.yml; run locally with GITHUB_TOKEN set.
"""
import json, os, subprocess, sys
from datetime import date

USER = os.environ.get("GH_USER", "DEEPESH-845")
ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

BG, TEXT, MUTED, ACCENT, EDGE = "#0A0C10", "#E7ECF3", "#5D6675", "#FF7A1A", "#242B36"
QUERY = """{ user(login: "%s") { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount } } } } } }"""


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def fetch():
    out = gh("api", "graphql", "-f", "query=" + QUERY % USER)
    return json.loads(out)["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def smooth(pts):
    """Catmull-Rom through every point, emitted as cubic beziers."""
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(d)


def render(cal):
    """Commits per week over the last year, as an area graph."""
    weeks = [(w["contributionDays"][0]["date"], sum(d["contributionCount"] for d in w["contributionDays"]))
             for w in cal["weeks"]]
    vals = [v for _, v in weeks]
    peak = max(vals) or 1
    W, H, X0, X1, Y0, Y1 = 1200, 306, 92, 1120, 112, 246
    PW, PH = X1 - X0, Y1 - Y0
    n = len(weeks)
    pts = [(X0 + i * PW / (n - 1), Y1 - v / peak * PH) for i, v in enumerate(vals)]
    line = smooth(pts)
    mono = 'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"'
    pk = vals.index(peak)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"'
         f' aria-label="Commit volume over the last twelve months: {cal["totalContributions"]} contributions,'
         f' peaking at {peak} in a single week.">',
         f'<title>{cal["totalContributions"]} contributions in the last year</title>',
         '<defs>',
         f'<clipPath id="cc"><rect width="{W}" height="{H}" rx="16"/></clipPath>',
         '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.34"/>'
         f'<stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>',
         '</defs>',
         f'<g clip-path="url(#cc)"><rect width="{W}" height="{H}" fill="{BG}"/>',
         f'<text x="{X0}" y="48" {mono} font-size="12" letter-spacing="3.2" fill="{MUTED}">'
         'COMMIT VOLUME · LAST 12 MONTHS</text>',
         f'<text x="{X0}" y="84" font-family="ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'
         f' font-size="26" font-weight="700" fill="{TEXT}">{cal["totalContributions"]:,}'
         f'<tspan font-size="17" font-weight="400" fill="#8B95A5"> contributions · peak {peak} in one week'
         '</tspan></text>']

    for f in (0, 0.5, 1):                                            # baseline grid
        y = Y1 - f * PH
        p.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="#1B212A"/>')

    p.append(f'<path d="{line} L{X1:.1f},{Y1} L{X0:.1f},{Y1} Z" fill="url(#fade)"/>')
    p.append(f'<path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="2.2" stroke-linecap="round"'
             f' stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0">'
             '<animate attributeName="stroke-dashoffset" from="1" to="0" dur="1.6s" fill="freeze"/></path>')

    px, py = pts[pk]
    p.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{Y1}" stroke="{ACCENT}" stroke-opacity="0.35"'
             ' stroke-dasharray="3 4"/>')
    p.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{BG}" stroke="{ACCENT}" stroke-width="2"/>')

    seen, last = set(), -99                                          # month ruler
    for i, (iso, _) in enumerate(weeks):
        d = date.fromisoformat(iso)
        x = X0 + i * PW / (n - 1)
        if d.month not in seen and d.day <= 7 and x - last > 62:
            seen.add(d.month); last = x
            p.append(f'<text x="{x:.1f}" y="{Y1 + 26}" text-anchor="middle" {mono} font-size="11"'
                     f' fill="{MUTED}">{d.strftime("%b").upper()}</text>')

    p.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="none" stroke="{EDGE}"/>')
    p.append("</g></svg>")
    return "\n".join(p) + "\n"


def fetch_languages(top=7):
    """Bytes per language across the user's own public, non-fork repositories."""
    repos = json.loads(gh("repo", "list", USER, "--limit", "200", "--no-archived",
                          "--visibility", "public", "--source",
                          "--json", "name,languages"))
    tot = {}
    for r in repos:
        for e in r.get("languages") or []:
            tot[e["node"]["name"]] = tot.get(e["node"]["name"], 0) + e["size"]
    ranked = sorted(tot.items(), key=lambda kv: -kv[1])
    head, tail = ranked[:top], ranked[top:]
    if tail:
        head.append(("Other", sum(v for _, v in tail)))
    return head, sum(tot.values())


RAMP = ["#FF7A1A", "#DB6A1C", "#B7591C", "#94491A", "#733A17", "#553019", "#3B2A1E", "#2A2E36"]


def render_languages(langs, total):
    named = sum(1 for n, _ in langs if n != "Other")
    W, H, BAR_X, BAR_W, BAR_Y = 1200, 236, 92, 1016, 104
    mono = 'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"'
    alt = ", ".join(f"{n} {100*v/total:.1f} percent" for n, v in langs)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"'
         f' role="img" aria-label="Code written, by language: {alt}.">',
         '<title>Code written, by language</title>',
         f'<defs><clipPath id="cl"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
         f'<clipPath id="bar"><rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_W}" height="26" rx="6"/></clipPath></defs>',
         f'<g clip-path="url(#cl)"><rect width="{W}" height="{H}" fill="{BG}"/>',
         f'<text x="{BAR_X}" y="48" {mono} font-size="12" letter-spacing="3.2" fill="{MUTED}">'
         f'CODE WRITTEN · PUBLIC REPOSITORIES</text>',
         f'<text x="{BAR_X}" y="82" font-family="ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'
         f' font-size="26" font-weight="700" fill="{TEXT}">{total/1e6:.1f} MB'
         f'<tspan font-size="17" font-weight="400" fill="#8B95A5"> of source across {named} languages</tspan></text>',
         f'<g clip-path="url(#bar)">']
    x = BAR_X
    for i, (name, v) in enumerate(langs):
        w = BAR_W * v / total
        p.append(f'<rect x="{x:.1f}" y="{BAR_Y}" width="{w:.1f}" height="26" fill="{RAMP[i % len(RAMP)]}"/>')
        x += w
    p.append("</g>")
    for i, (name, v) in enumerate(langs):          # legend, two rows of four
        col, row = i % 4, i // 4
        lx, ly = BAR_X + col * 254, 168 + row * 30
        p.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{RAMP[i % len(RAMP)]}"/>'
                 f'<text x="{lx + 18}" y="{ly}" {mono} font-size="12.5" fill="#B7C0CD">{name}'
                 f'<tspan fill="{MUTED}"> {100*v/total:.1f}%</tspan></text>')
    p.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="none" stroke="{EDGE}"/></g></svg>')
    return "\n".join(p) + "\n"


if __name__ == "__main__":
    cal = fetch()
    open(os.path.join(ASSETS, "activity.svg"), "w").write(render(cal))
    langs, total = fetch_languages()
    open(os.path.join(ASSETS, "languages.svg"), "w").write(render_languages(langs, total))
    print(f"contributions: {cal['totalContributions']} · languages: {len(langs)} / {total/1e6:.1f} MB", file=sys.stderr)
