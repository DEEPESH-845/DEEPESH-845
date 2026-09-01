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

BG, EMPTY, TEXT, MUTED, ACCENT, EDGE = "#0A0C10", "#141920", "#E7ECF3", "#5D6675", "#FF7A1A", "#242B36"
SCALE = ["#141920", "#4A2A10", "#8A4614", "#C96517", "#FF7A1A"]
CELL, GAP, PAD_L, TOP = 15, 4, 92, 108
QUERY = """{ user(login: "%s") { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount weekday } } } } } }"""


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def fetch():
    out = gh("api", "graphql", "-f", "query=" + QUERY % USER)
    return json.loads(out)["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def bucket(n, peak):
    if n == 0:
        return 0
    return min(4, 1 + int(3 * n / max(peak, 1)))


def render(cal):
    weeks = cal["weeks"]
    peak = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1)
    width, height = 1200, TOP + 7 * (CELL + GAP) + 46
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}"'
         f' role="img" aria-label="{cal["totalContributions"]} contributions by {USER} in the last year.">',
         f'<title>{cal["totalContributions"]} contributions in the last year</title>',
         f'<defs><clipPath id="cc"><rect width="{width}" height="{height}" rx="16"/></clipPath></defs>',
         f'<g clip-path="url(#cc)"><rect width="{width}" height="{height}" fill="{BG}"/>',
         f'<text x="{PAD_L}" y="48" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"'
         f' font-size="12" letter-spacing="3.2" fill="{MUTED}">COMMIT ACTIVITY · LAST 12 MONTHS</text>',
         f'<text x="{PAD_L}" y="82" font-family="ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'
         f' font-size="26" font-weight="700" fill="{TEXT}">{cal["totalContributions"]:,}'
         f'<tspan font-size="17" font-weight="400" fill="#8B95A5"> contributions</tspan></text>']

    mono = 'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"'
    seen, last_x = set(), -99
    for i, w in enumerate(weeks):                                   # month ruler
        d = date.fromisoformat(w["contributionDays"][0]["date"])
        x = PAD_L + i * (CELL + GAP)
        if d.month not in seen and d.day <= 7 and x - last_x > 52:
            seen.add(d.month); last_x = x
            p.append(f'<text x="{x}" y="{TOP - 10}" {mono} font-size="11" fill="{MUTED}">'
                     f'{d.strftime("%b").upper()}</text>')

    for row, lab in ((1, "MON"), (3, "WED"), (5, "FRI")):           # weekday ruler
        p.append(f'<text x="{PAD_L - 14}" y="{TOP + row * (CELL + GAP) + 12}" text-anchor="end" {mono}'
                 f' font-size="10" fill="#454D5A">{lab}</text>')

    for i, w in enumerate(weeks):
        for d in w["contributionDays"]:
            n = d["contributionCount"]
            x, y = PAD_L + i * (CELL + GAP), TOP + d["weekday"] * (CELL + GAP)
            p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3"'
                     f' fill="{SCALE[bucket(n, peak)]}"><title>{n} on {d["date"]}</title></rect>')

    ly = TOP + 7 * (CELL + GAP) + 22
    p.append(f'<text x="{PAD_L}" y="{ly + 11}" {mono} font-size="10.5" letter-spacing="1.4" fill="{MUTED}">LESS</text>')
    for i, c in enumerate(SCALE):
        p.append(f'<rect x="{PAD_L + 44 + i * 18}" y="{ly}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"/>')
    p.append(f'<text x="{PAD_L + 44 + 5 * 18 + 4}" y="{ly + 11}" {mono} font-size="10.5" letter-spacing="1.4"'
             f' fill="{MUTED}">MORE</text>')
    p.append(f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="none" stroke="{EDGE}"/>')
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
    open(os.path.join(ASSETS, "contributions.svg"), "w").write(render(cal))
    langs, total = fetch_languages()
    open(os.path.join(ASSETS, "languages.svg"), "w").write(render_languages(langs, total))
    print(f"contributions: {cal['totalContributions']} · languages: {len(langs)} / {total/1e6:.1f} MB", file=sys.stderr)
