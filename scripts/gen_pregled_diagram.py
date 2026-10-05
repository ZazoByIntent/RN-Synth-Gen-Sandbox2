"""Generate the trajguard overview diagram (docs/PREGLED_RESITVE.md).

Writes the standalone SVG to docs/img/trajguard_pregled.svg and, with --html DIR, an
HTML page with the same SVG inline (used for the shared Artifact). Node positions are
laid out by hand on a 1340 x 1120 grid; the status of every node is one of
meas / val / prep / open (see the legend).  Usage: python scripts/gen_pregled_diagram.py
"""

# ruff: noqa: E501  (long CSS/HTML template lines)
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
_p = argparse.ArgumentParser(description="Regenerate the trajguard overview diagram.")
_p.add_argument("--html", type=Path, help="also write trajguard_pregled.html into this dir")
HTML_DIR = _p.parse_args().html
W, H = 1340, 1120

MONO = "'JetBrains Mono', 'Cascadia Mono', Consolas, Menlo, monospace"
SANS = "'Source Sans 3', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

parts: list[str] = []


def add(s: str) -> None:
    parts.append(s)


def t(x: float, y: float, text: str, cls: str, anchor: str = "start", extra: str = "") -> str:
    return (
        f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{extra}>{escape(text)}</text>'
    )


def node(x, y, w, title, sub=(), status="meas", mono=True, h=None):
    """Rounded box with a title line and 0-2 subtitle lines; returns (cx, cy, h)."""
    if h is None:
        h = 30 + 15 * len(sub) + (0 if sub else 0)
        if not sub:
            h = 34
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" class="node st-{status}"/>')
    tcls = "ttl-mono" if mono else "ttl"
    ty = y + 19 if sub else y + h / 2 + 4
    add(t(x + 12, ty, title, tcls))
    for i, line in enumerate(sub):
        add(t(x + 12, y + 34 + 15 * i, line, "sub"))
    return x + w / 2, y + h / 2, h


def pill(x, y, text, status="meas", w=None):
    w = w or int(len(text) * 7.3 + 18)
    add(f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="11" class="pill st-{status}"/>')
    add(t(x + w / 2, y + 15, text, "pill-txt", "middle"))
    return w


def group(x, y, w, h, title, dashed=False):
    cls = "grp grp-dashed" if dashed else "grp"
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>')
    add(t(x + 12, y + 16, title, "grp-ttl"))


def edge(points, label=None, status="flow", lx=None, ly=None, anchor="middle"):
    d = "M " + " L ".join(f"{px},{py}" for px, py in points)
    add(f'<path d="{d}" class="edge ed-{status}" marker-end="url(#arr)"/>')
    if label:
        if lx is None:
            (x1, y1), (x2, y2) = points[0], points[-1]
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 - 5
        add(t(lx, ly, label, "elbl", anchor))


def col_header(x, y, text):
    add(t(x, y, text, "col-ttl"))


# ---------------------------------------------------------------- column headers
col_header(30, 30, "1 · VIRI IN PRIPRAVA")
col_header(345, 30, "2 · ZAŠČITA")
col_header(705, 30, "3 · NAPADI")
col_header(1055, 30, "4 · METRIKE")

# ---------------------------------------------------------------- column 1: sources
node(30, 48, 128, "geolife", ["Geolife, Peking", "surovi .plt (data/raw)"], "meas")
node(172, 48, 128, "ldptrace_dat", ["Porto .dat", "le za validacijo"], "val")
node(
    30,
    130,
    270,
    "Čiščenje → CleanTrajectory",
    ["filter hitrosti in dolžine, prevzorčenje"],
    "meas",
    mono=False,
)
node(
    30,
    196,
    270,
    "Delitev train / test / shadow / attack",
    ["enkrat, po uporabniku, s split_seed", "oznaka split spremlja vse izpeljanke"],
    "meas",
    mono=False,
)
node(
    110,
    282,
    190,
    "osm",
    ["zemljevid OSM → RoadNetwork", "pogoj map.region = native_region"],
    "meas",
)
node(
    30, 366, 270, "leuven", ["map-matching → MatchedTrajectory", "privzeta pot »segments«"], "meas"
)
node(
    30,
    450,
    270,
    "Grid.chain → CellChain",
    ["pot »cells«: brez zemljevida, le napad", "na članstvo (Porto; validacija)"],
    "val",
)

edge([(94, 108), (94, 130)])
edge([(236, 108), (236, 130)])
edge([(165, 176), (165, 196)])
edge([(205, 342), (205, 366)])
edge([(70, 256), (70, 366)])
edge([(45, 256), (45, 450)])

# ---------------------------------------------------------------- column 2: protection
group(345, 48, 320, 402, "PERTURBACIJSKI MEHANIZMI · ena izdana pot na vhodno")
node(360, 76, 290, "none", ["kontrola brez zaščite"], "meas")
node(360, 132, 290, "geo_indistinguishability", ["S4 · planarni Laplaceov šum · ε"], "meas")
node(360, 188, 290, "ZM-2 · point_ldp", ["naključni odziv nad celico 20×20 · ε"], "meas")
group(352, 246, 306, 192, "ZM-3 · NAIVNI OSNOVNI")
node(360, 270, 290, "spatial_rounding", ["zaokroževanje na središče celice · cell_m"], "meas")
node(360, 326, 290, "temporal_downsampling", ["ena točka na časovni interval · interval_s"], "meas")
node(360, 382, 290, "gaussian_noise", ["normalni šum na vsako os · sigma_m"], "meas")

group(345, 470, 320, 268, "SINTETIČNI GENERATORJI · nove poti, naučeni na train")
node(360, 498, 290, "markov", ["nezasebni osnovni (Markov 1. reda)"], "meas")
node(360, 554, 290, "ZM-1 · ldptrace", ["ε-LDP na pot · celice 12×12"], "val")
node(360, 610, 290, "ZM-4 · privtrace", ["centralni DP · prilagodljiva mreža"], "val")
node(
    360,
    666,
    290,
    "rn_ldp_synth",
    ["lastni prototip v1 · ε-LDP na pot,", "omejen na cestno omrežje"],
    "meas",
)

# column 1 -> column 2
edge(
    [(300, 396), (322, 396), (322, 250), (345, 250)],
    "MatchedTrajectory",
    lx=318,
    ly=270,
    anchor="end",
)
edge([(300, 420), (330, 420), (330, 600), (345, 600)])
add(t(318, 545, "fit na split train", "elbl-v", "middle", ' transform="rotate(-90 318 545)"'))
edge([(300, 480), (338, 480), (338, 577), (345, 577)], "celice", lx=320, ly=472, anchor="middle")

# ---------------------------------------------------------------- column 3: attacks
group(705, 48, 310, 160, "")
add(t(717, 70, "reidentification", "ttl-mono"))
add(t(717, 86, "napadalec pozna k ∈ {3, 5, 10} točk tarče · obseg raw + protected", "sub"))
add(t(717, 120, "galerija:", "sub"))
pill(790, 105, "rematched", "meas", 96)
pill(896, 105, "release", "prep", 96)
add(t(717, 152, "razdalja:", "sub"))
pill(790, 137, "dtw", "meas", 96)
pill(896, 137, "dtw_norm", "prep", 96)
add(t(717, 182, "rematched: izdaja znova pripeta na omrežje (map-matching)", "sub"))
add(t(717, 196, "release: surove izdane točke, brez map-matchinga", "sub"))

node(
    705,
    248,
    310,
    "membership_inference",
    ["LiRA-lite · 16 senčnih generatorjev", "člani = train, nečlani = test · obseg synthetic"],
    "meas",
)
node(
    705,
    330,
    310,
    "reconstruction",
    ["Whittakerjev glajevalnik brez zemljevida", "obseg protected (roke geo-ind)"],
    "meas",
)
node(705, 400, 310, "A3 · rekonstrukcija z omejitvijo cestnega omrežja", status="open", mono=False)
node(705, 444, 310, "A4 · delno predznanje (k sidrnih točk tarče)", status="open", mono=False)
node(
    705,
    500,
    310,
    "poi_inference",
    ["točke postanka → dom (noč) / služba (dan)", "obseg protected (+ synthetic, le formalno)"],
    "meas",
)
node(705, 570, 310, "M2 · top-k točnost POI + pogled as_poi_visits()", status="open", mono=False)

# column 2 -> column 3
# perturbative trunk at x=692
add(
    '<path d="M 665,250 L 695,250 L 695,660 L 705,660" class="edge ed-flow" marker-end="url(#arr)"/>'
)
edge([(695, 113), (705, 113)])
edge([(695, 360), (705, 360)])
edge([(695, 530), (705, 530)])
add('<path d="M 695,250 L 695,113" class="edge ed-flow"/>')
add(t(686, 200, "ProtectedTrajectory", "elbl-v", "middle", ' transform="rotate(-90 686 200)"'))
# synthetic
edge([(665, 604), (676, 604), (676, 278), (705, 278)])
add(t(686, 560, "SyntheticTrajectory", "elbl-v", "middle", ' transform="rotate(-90 686 560)"'))

# ---------------------------------------------------------------- column 4: metrics
node(
    1055,
    83,
    255,
    "Zasebnost · reidentifikacija",
    ["top1_acc · topk_acc (k = 5)", "linkage_rate"],
    "meas",
    mono=False,
)
node(
    1055,
    160,
    255,
    "Pragovi zadostne zaščite",
    ["poročilo §8.2 · čaka potrditev mentorice"],
    "open",
    mono=False,
)
node(
    1055,
    248,
    255,
    "Zasebnost · napad na članstvo",
    ["auc · tpr@fpr ∈ {0.001, 0.01, 0.1}", "razpon čez semena, brez bootstrapa"],
    "meas",
    mono=False,
)
node(
    1055,
    330,
    255,
    "Zasebnost · rekonstrukcija",
    ["hausdorff_m · dtw_m", "mean_spatial_error_m"],
    "meas",
    mono=False,
)
node(
    1055,
    500,
    255,
    "Zasebnost · točke interesa",
    ["home_error_m · work_error_m", "home_localised · work_localised"],
    "meas",
    mono=False,
)

group(705, 630, 605, 104, "")
add(t(717, 652, "Uporabnost izdaje · UTILITY_METRICS", "ttl"))
add(t(717, 668, "surovo proti izdaji, parni bootstrap · le za perturbacijske mehanizme", "sub"))
pill(717, 680, "cell_js_divergence", "meas")
pill(870, 680, "length_dist_error", "meas")
pill(717, 706, "duration_dist_error", "prep")
pill(870, 706, "speed_dist_error", "prep")
add(t(1010, 721, "← M3: v kodi, izmerjeno šele pri 50/182", "sub"))

edge([(1015, 113), (1055, 113)])
edge([(1015, 278), (1055, 278)])
edge([(1015, 360), (1055, 360)])
edge([(1015, 530), (1055, 530)])
edge([(1182, 143), (1182, 160)], status="open")

# ---------------------------------------------------------------- band: experiments
group(
    20,
    770,
    1300,
    300,
    "5 · EKSPERIMENTI IN STANJE · konfiguracije v config/experiments, "
    "stopnje = število uporabnikov Geolife",
)
add(t(1308, 786, "izhod: results/*.csv → trajguard report → reports/", "sub", "end"))
edge(
    [(1007, 734), (1007, 770)],
    "results.csv (stolpca distance, gallery)",
    lx=1015,
    ly=757,
    anchor="start",
)

cols = {"u20": 350, "u50": 570, "u182": 790, "porto": 1010}
for key, label in (
    ("u20", "20 uporabnikov"),
    ("u50", "50 uporabnikov"),
    ("u182", "182 uporabnikov"),
    ("porto", "Porto · validacija proti kodi avtorjev"),
):
    cx = cols[key] + (150 if key == "porto" else 100)
    add(t(cx, 812, label, "col-sub", "middle"))

rows = [
    (
        "S4 · reidentifikacija, geo_indistinguishability",
        "geolife_geoind_reid*",
        [
            ("meas", "izmerjeno (5 semen)"),
            ("meas", "izmerjeno (5 semen)"),
            ("meas", "izmerjeno · poročevalski pogon"),
            None,
        ],
    ),
    (
        "S4 · napad na članstvo, markov + rn_ldp_synth",
        "geolife_synth_mia*",
        [
            ("meas", "izmerjeno (3 semena)"),
            ("meas", "izmerjeno (3 semena)"),
            ("meas", "izmerjeno (3 semena)"),
            None,
        ],
    ),
    (
        "Mehanizmi · reidentifikacija",
        "geolife_mech_reid_u*",
        [
            ("meas", "izmerjeno · release še ne"),
            ("prep", "pripravljeno · naslednji korak"),
            ("prep", "pripravljeno · po stopnji 50"),
            ("val", "privtrace_validation: port ≈ izvirnik"),
        ],
    ),
    (
        "Mehanizmi · napad na članstvo",
        "geolife_mech_mia_u*",
        [
            ("meas", "izmerjeno (3 semena)"),
            ("prep", "pripravljeno · naslednji korak"),
            ("prep", "pripravljeno · po stopnji 50"),
            ("val", "porto_cells_mia + ldptrace_validation"),
        ],
    ),
]
y = 826
for label, cfg, cells in rows:
    add(t(30, y + 15, label, "ttl", "start"))
    add(t(30, y + 30, cfg, "sub-mono"))
    for (key, x), cell in zip(cols.items(), cells, strict=True):
        w = 300 if key == "porto" else 200
        if cell is None:
            add(t(x + w / 2, y + 22, "—", "sub", "middle"))
            continue
        st, txt = cell
        add(f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="7" class="node st-{st}"/>')
        add(t(x + w / 2, y + 22, txt, "cell-txt", "middle"))
    y += 46

add(t(30, y + 22, "Odprto / načrtovano", "ttl"))
node(
    350,
    y + 4,
    420,
    "Primerjalni zvezek notebooks/04 · nad stopnjama 50 in 182",
    status="open",
    mono=False,
)
node(
    790,
    y + 4,
    520,
    "Val 5 · horizont B: nalagalnika T-Drive/Porto, fmm, PostGIS, MLflow, difuzija",
    status="open",
    mono=False,
)

# ---------------------------------------------------------------- legend (standalone only)
legend_y = 1092
legend = [
    ("meas", "izmerjeno"),
    ("val", "validirano proti kodi avtorjev (in izmerjeno)"),
    ("prep", "pripravljeno, a neizmerjeno"),
    ("open", "odprto / načrtovano (črtkano)"),
]
legend_parts: list[str] = []
lx = 30
for st, txt in legend:
    legend_parts.append(
        f'<rect x="{lx}" y="{legend_y}" width="26" height="16" rx="4" class="node st-{st}"/>'
    )
    legend_parts.append(t(lx + 34, legend_y + 12, txt, "sub"))
    lx += 34 + len(txt) * 6.1 + 24
legend_parts.append(
    f'<path d="M {lx},{legend_y + 8} L {lx + 40},{legend_y + 8}" class="edge ed-flow" '
    'marker-end="url(#arr)"/>'
)
legend_parts.append(t(lx + 48, legend_y + 12, "puščica = tok podatkov", "sub"))

DEFS = (
    '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
    'markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" '
    'class="arrhead"/></marker></defs>'
)

BODY = "\n".join(parts)
LEGEND = "\n".join(legend_parts)

# CSS shared by both outputs; colours come from custom properties.
SVG_CSS = f"""
.node{{stroke-width:1.5}}
.st-meas{{fill:var(--f-meas);stroke:var(--c-meas)}}
.st-val{{fill:var(--f-val);stroke:var(--c-val)}}
.st-prep{{fill:var(--f-prep);stroke:var(--c-prep)}}
.st-open{{fill:var(--f-open);stroke:var(--c-open);stroke-dasharray:5 4}}
.pill{{stroke-width:1.3}}
.grp{{fill:var(--grp-fill);stroke:var(--grp-stroke);stroke-width:1}}
.grp-dashed{{stroke-dasharray:5 4}}
.edge{{fill:none;stroke:var(--edge);stroke-width:1.4}}
.ed-open{{stroke-dasharray:5 4}}
.arrhead{{fill:var(--edge)}}
text{{font-family:{SANS};fill:var(--ink)}}
.ttl{{font-size:12.5px;font-weight:600}}
.ttl-mono{{font-family:{MONO};font-size:12px;font-weight:600}}
.sub{{font-size:11px;fill:var(--muted)}}
.sub-mono{{font-family:{MONO};font-size:10.5px;fill:var(--muted)}}
.pill-txt{{font-family:{MONO};font-size:11px;font-weight:600}}
.cell-txt{{font-size:11.5px;font-weight:600}}
.col-ttl{{font-size:12px;font-weight:700;letter-spacing:.08em;fill:var(--muted)}}
.col-sub{{font-size:11.5px;font-weight:700;letter-spacing:.04em;fill:var(--muted)}}
.grp-ttl{{font-size:10.5px;font-weight:700;letter-spacing:.07em;fill:var(--muted)}}
.elbl{{font-size:10.5px;fill:var(--muted);paint-order:stroke;stroke:var(--bg);stroke-width:4px;stroke-linejoin:round}}
.elbl-v{{font-size:10.5px;fill:var(--muted)}}
"""

LIGHT = """
--bg:#f6f7f5;--surface:#ffffff;--ink:#1f2429;--muted:#58606a;--edge:#6b727b;
--grp-fill:#fbfbfa;--grp-stroke:#c6ccd3;
--c-meas:#277a52;--f-meas:#e1f2e8;
--c-val:#2b5fa6;--f-val:#e2ebf9;
--c-prep:#a86d14;--f-prep:#fbefd6;
--c-open:#7a8189;--f-open:#f1f2f4;
"""
DARK = """
--bg:#15181c;--surface:#1c2025;--ink:#e7e9ec;--muted:#a3a9b1;--edge:#8e959e;
--grp-fill:#191d22;--grp-stroke:#3b424b;
--c-meas:#5fcd8f;--f-meas:#1a3326;
--c-val:#80b3ff;--f-val:#1b2b47;
--c-prep:#e9b85c;--f-prep:#3c2e13;
--c-open:#9aa1aa;--f-open:#24282e;
"""

ARIA = (
    "Pregled rešitve trajguard: viri in priprava podatkov, zaščitni mehanizmi, "
    "napadi, metrike ter stanje eksperimentov po stopnjah 20, 50 in 182 uporabnikov."
)

# ---------------------------------------------------------------- standalone SVG
svg_standalone = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(ARIA)}">
<title>trajguard – pregled rešitve (5. oktober 2026)</title>
<style>
svg{{{LIGHT}}}
{SVG_CSS}
</style>
{DEFS}
<rect x="0" y="0" width="{W}" height="{H}" fill="var(--bg)"/>
{BODY}
{LEGEND}
</svg>
"""
(OUT / "trajguard_pregled.svg").write_text(svg_standalone, encoding="utf-8")

# ---------------------------------------------------------------- HTML page
svg_inline = f"""<svg viewBox="0 0 {W} {H - 40}" role="img" aria-label="{escape(ARIA)}" class="dia">
{DEFS}
{BODY}
</svg>"""

html = f"""<title>trajguard pregled</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@500;600&display=swap">
<style>
/* Layout: one wide figure that scrolls sideways on narrow screens, legend and a short reading guide below. */
:root{{{LIGHT}}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{{DARK}color-scheme:dark}}}}
:root[data-theme="dark"]{{{DARK}color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font-family:{SANS};margin:0;padding-block:28px 48px;padding-inline:16px;line-height:1.5}}
.wrap{{max-width:1340px;margin:0 auto}}
h1{{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.01em;text-wrap:balance}}
.lede{{color:var(--muted);margin:0 0 20px;font-size:.95rem}}
figure{{margin:0}}
.scroller{{overflow-x:auto;border:1px solid var(--grp-stroke);border-radius:12px;background:var(--surface);padding:12px}}
.dia{{display:block;min-width:1180px;width:100%;height:auto}}
figcaption{{font-size:.85rem;color:var(--muted);margin-top:8px}}
.legend{{display:flex;flex-wrap:wrap;gap:10px 22px;margin:18px 0 6px;padding:0;list-style:none;font-size:.9rem}}
.legend li{{display:flex;align-items:center;gap:8px}}
.sw{{width:26px;height:16px;border-radius:4px;border:1.5px solid;flex:none}}
.sw-meas{{background:var(--f-meas);border-color:var(--c-meas)}}
.sw-val{{background:var(--f-val);border-color:var(--c-val)}}
.sw-prep{{background:var(--f-prep);border-color:var(--c-prep)}}
.sw-open{{background:var(--f-open);border-color:var(--c-open);border-style:dashed}}
.sw-arrow{{width:34px;height:0;border-top:1.5px solid var(--edge);position:relative;flex:none}}
.sw-arrow::after{{content:"";position:absolute;right:-1px;top:-4px;border:4px solid transparent;border-left:6px solid var(--edge)}}
.prose{{max-width:68ch;font-size:1rem}}
.prose p{{margin:0 0 10px}}
code{{font-family:{MONO};font-size:.86em;background:var(--f-open);padding:1px 5px;border-radius:4px}}
.note{{font-size:.85rem;color:var(--muted);max-width:68ch}}
{SVG_CSS}
</style>
<div class="wrap">
<h1>trajguard — potek celotne rešitve</h1>
<p class="lede">Stanje repozitorija na dan 5. oktober 2026 (veja <code>main</code>, po združitvi PR #51–#53). Brez izmerjenih številk; te so v <code>docs/HANDOFF.md</code>.</p>
<figure>
<div class="scroller">{svg_inline}</div>
<figcaption>Podatki tečejo od leve proti desni: viri → zaščita → napadi → metrike; spodnji pas pove, kaj je pri kateri stopnji izmerjeno. Na ozkem zaslonu diagram pomaknite vodoravno.</figcaption>
</figure>
<ul class="legend">
<li><span class="sw sw-meas"></span>izmerjeno</li>
<li><span class="sw sw-val"></span>validirano proti kodi avtorjev (in izmerjeno)</li>
<li><span class="sw sw-prep"></span>pripravljeno, a neizmerjeno</li>
<li><span class="sw sw-open"></span>odprto / načrtovano (črtkano)</li>
<li><span class="sw-arrow"></span>tok podatkov</li>
</ul>
<div class="prose">
<p>Vhod so surove poti Geolife (Peking), ki jih ogrodje očisti, enkrat razdeli po uporabnikih na štiri dele (train, test, shadow, attack) in pripne na cestno omrežje OpenStreetMap; Porto pride v igro samo brez zemljevida, kot celična veriga za validacijo LDPTrace.</p>
<p>Zaščita je dveh vrst. Perturbacijski mehanizmi vsako pot zašumijo in vrnejo eno izdano pot na vhodno (kontrola <code>none</code>, geo-nerazločljivost iz kampanje S4, ZM-2 <code>point_ldp</code> in trojica naivnih osnov ZM-3). Sintetični generatorji se naučijo na delu train in izdajo povsem nove poti (nezasebni <code>markov</code>, ZM-1 <code>ldptrace</code>, ZM-4 <code>privtrace</code> in lastni prototip <code>rn_ldp_synth</code>).</p>
<p>Na izdano gradivo tečejo štirje napadi: reidentifikacija z dvema galerijama in dvema razdaljama ter rekonstrukcija in sklepanje o točkah interesa nad perturbiranimi izdajami, napad na članstvo pa nad sintetičnimi. Vsak napad vrne svoje zasebnostne metrike, perturbacijske izdaje pa dobijo še metrike uporabnosti (surovo proti izdanemu).</p>
<p>Kampanja S4 je izmerjena pri vseh treh stopnjah; primerjava mehanizmov je izmerjena pri 20 uporabnikih, pri 50 in 182 je pripravljena in čaka na avtorjev pogon (najprej stopnja 50). ZM-1 in ZM-4 sta validirana proti izvirni kodi avtorjev na Portu. Črtkano so odprte postavke: razširitvi rekonstrukcije A3 in A4, metrika M2, pragovi iz poročila §8.2, primerjalni zvezek in horizont B (val 5).</p>
</div>
<p class="note">Vir: koda v <code>src/trajguard</code> (registrska imena), <code>config/experiments</code>, <code>docs/HANDOFF.md</code> §1–§2 in <code>docs/NACRT_MEHANIZMI.md</code> §1.6. Kjer se koda in dokumenti razhajajo, velja koda.</p>
</div>
"""
print("written", OUT / "trajguard_pregled.svg")
if HTML_DIR is not None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    (HTML_DIR / "trajguard_pregled.html").write_text(html, encoding="utf-8")
    print("written", HTML_DIR / "trajguard_pregled.html")
