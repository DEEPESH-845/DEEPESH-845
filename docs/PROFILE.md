# Profile system

How this README is built, how to change it, and where every claim comes from.

## Layout

```
README.md               hand-written copy; references the panels below
data/profile.toml       single source for every generated panel (awards, targets, pipelines, places)
data/land.json          particle positions for the globe (Natural Earth 110m, generated once)
scripts/render.py       renders assets/*.svg and globe/data.json. Stdlib only, Python 3.11+
assets/*.svg            generated panels. Never edit by hand
globe/index.html        interactive companion (vanilla canvas, no dependencies)
globe/data.json         generated; same places as the README globe
.github/workflows/contributions.yml   refreshes assets/activity.svg daily
```

## Common changes

| Change | Do this |
|---|---|
| New award | Add an `[[award]]` to `profile.toml` (`tier = 1` shows in the hero and as a large row, `tier = 2` in the grid). Run `python3 scripts/render.py`. Update the `alt` text on `record.svg` (and `hero.svg` for tier 1) in the README. |
| New current project | Edit `identity.now` in `profile.toml`, then the `07 Now` block in the README. |
| New deployment target | Add a `[[target]]`. Keep it to ~6 rows so the panel stays readable on a phone. |
| New pipeline diagram | Add `[system.<name>]` with exactly 6 stages (titles up to ~14 characters); it renders `assets/sys-<name>.svg`. |
| New client city | Add a `[[place]]` with `kind = "client"`. City level only, never a client name. It appears on both globes; the legend fits about 5 places. |
| Globe framing | `[globe] centre = [lat, lon]` in `profile.toml`. Delete it and `render.py` picks a centre that keeps every place visible. |
| Rebuild the land particles | Delete `data/land.json` and rerun (it fetches Natural Earth once). |
| Refresh activity locally | `python3 scripts/render.py activity` (needs `gh auth login`). |

Alt text in the README is written by hand, because GitHub uses the `<img alt>`, not the SVG's own label.
When a panel's facts change, change its alt text in the same commit.

## Interactive globe

The README cannot run JavaScript, so it shows the static `globe.svg` and links to `globe/`.
That link needs GitHub Pages enabled on this repository: **Settings → Pages → Deploy from branch → `main` / root**.
It is then served at `https://deepesh-845.github.io/DEEPESH-845/globe/`.

## Design system

| Token | Value | Use |
|---|---|---|
| background | `#0B0D11` | every panel |
| surface | `#11151B` | stage boxes |
| border / hairline | `#222933` / `#171C24` | frames, dividers, idle wire |
| text | `#ECEFF4` | names, titles, figures |
| text 2 | `#A7B0BE` | supporting lines (8.7:1 on background) |
| muted | `#7A8494` | labels, metadata (5.0:1) |
| signal | `#FF7A1A` | the one accent: proof, live state, the travelling packet |
| signal soft | `#FFA766` | metrics, highlighted stage text |
| cool | `#7D9BBF` | geography and structure (globe particles, graticule) |

- **Motif:** a fine 24px grid, registration marks in each corner, and one *signal*. That's a wire plus a short orange packet travelling it. The packet appears in the hero, the deployment map, the pipelines, the globe arcs, the activity curve and the footer.
- **Type:** system sans for prose and figures, system mono (letter-spaced caps) for labels. No web fonts, because GitHub serves SVGs as images and blocks them.
- **Scale:** panels are 720 units wide. Essential text is at least 17 units, which renders about 8px on a 375px phone and 20px on desktop. Anything smaller is also present in the Markdown or the alt text.
- **Motion:** CSS only, so `prefers-reduced-motion` turns every packet off and leaves still frames.
- **Markdown:** no `<sub>`. GitHub gives it `line-height: 0`, and wrapped `<sub>` text overprints the next line on mobile. Labels use code spans instead.

## Verification ledger

Every number traces to `Resume-Updater/data/*.yaml` (the claims register) or to the project's own repository.

| Claim | Source |
|---|---|
| Global Winner, Snapdragon Multiverse 2026, overall 1st, team of 5 | `ach-snapdragon-2026`, `proj-dragverse` (register forbids "Top 8" framing) |
| National Runner-Up, PSB 2026, 2nd of 226, ₹3,00,000, with BehaviorDNA | `ach-psb-hackathon-2026`, `proj-behaviordna` |
| Samsung SFT 2026: National Top 5 in track, Top 20 overall, 40,000+ applications, with NeuroTrace | `ach-samsung-sft-2026` (never "Winner") |
| Qualcomm Edge AI Developer Hackathon 2025 Global Finalist, with SolarSage | `ach-qualcomm-finalist-2025`, SolarSage.Ai README |
| 89.2% at 2,671+ images/hour; 87.3% decision confidence | `exp-qualcomm-02`, `proj-solarsage-01/02` |
| Halliburton 18 → 6 min deploys, 5–10 releases/week, 20+ pages | `exp-halliburton-01/02` |
| BehaviorDNA ~14 ms vs 150 ms SLA, 40+ signals / 500 ms, ROC-AUC 0.944 / 0.868, leakage deletion, Redis < 1 ms | `proj-behaviordna-01/02/03` |
| NeuroTrace 3-minute check, 468 landmarks, 2 SD × 3 days, FHIR R4 | `proj-neurotrace-01/02/03` |
| Calnino 70–100 WAU, 10+ tools | `proj-calnino-01` |
| Guardiant 85% latency cut; Kinetic Keys 35% | `proj-guardiant-01`, `proj-kinetickeys-02` |
| Kavach ₹1,84,636 → ₹14,257 at equal human cost, ~1 ms | Kavach README (generated benchmark corpus; stated as such) |
| ZeroCloud ~2 s, 26-model catalog, < 5 MB, v0.1.0 (Aug 2026), 9.4% median error over 8 machines, 90% → 54.5% interval fix, pre-1.0 gate | ZeroCloud README and releases |
| Globe: client systems in Houston and San Francisco; Qualcomm apprenticeship, hybrid, Bengaluru | Stated by Deepesh, 2026-10-03 (hybrid matches `exp-qualcomm`; Bengaluru is not yet in the register) |

## Research summary (Oct 2026)

201 profile READMEs were fetched (the `awesome-github-profile-readme` list plus about 40 AI/ML, design-engineering and maintainer profiles) and scanned for structure. About 20 were then read closely.

- **Template signals:** 38% open with a wave or "Hi there", 27% embed stats cards, 20% have visitor counters, 13% use stock phrases ("passionate", "always learning"). None of these are used here.
- **What strong engineers do:** simonw, jxnl and hamelsmu lead with what they are building now and name specific evidence (products, a book, client counts). They use few visuals.
- **What stands out:** only 17% use self-hosted SVG, 2.5% use theme-aware `<picture>`, and about 19% have workflow-updated content. Owned, generated visuals plus live data are rare.
- **Signature pieces:** single, authored visuals (jh3y's one-SVG README, martonlederer's name mark) are what people remember.

Directions considered: (A) evolve V1's instrument reticle, (B) a light editorial notebook, (C) **signal path**. C won because every shipped system runs inference somewhere specific under a budget. That gives the section only this profile can have: *Where my models run*.
