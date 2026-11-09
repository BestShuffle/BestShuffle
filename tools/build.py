"""Matrix / Mr Robot cards for the BestShuffle profile README: green phosphor, katakana rain, terminals, red glitches.

    python tools/build.py --static assets                      # banner, whoami, htop, farm (content from profile.json, no token)
    python tools/build.py --live dist --user BestShuffle       # signal + grid (needs GITHUB_TOKEN)
    python tools/build.py --theme robot --static assets        # Mr Robot variant: banner, whoami, recon, farm

Standard library only. Fonts (Share Tech Mono, M PLUS 1 Code, SIL OFL) are subset from Google Fonts and embedded,
because GitHub shows README SVGs as images, which cannot load anything external.
Every animation starts from the final picture: with prefers-reduced-motion, the cards render still and complete.
"""
import argparse, base64, datetime as dt, functools, json, math, os, random, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------------------------------------ themes
W = 1200
KANA = "".join(chr(c) for c in range(0xFF66, 0xFF9E))
RAIN = KANA + "0123456789Z:.=*+-"
ASCII = "".join(chr(c) for c in range(32, 127))
EXTRA = "·—•…“”’éèàç"
BOX = "┌┐└┘─│├┤█▓▒░▌▐■●"

# G is the theme's main ink (phosphor green / paper white); RED is the accent in both.
THEMES = {
    "matrix": dict(
        BG="#010503", PANEL="#03120a", EDGE="#0f3d22", G="#00ff41", G2="#00c837", G3="#0d7a31", G4="#0a3a1a",
        HEAD="#eafff0", TEXT="#b9f4c9", DIM="#4f8a62", RED="#ff2a4a",
        MONO="'Share Tech Mono',Consolas,'DejaVu Sans Mono',monospace", CW=0.54,  # Share Tech Mono advance, in em
        FONT=("Share Tech Mono", "Share+Tech+Mono"), GLYPH_FONT=("M PLUS 1 Code", "M+PLUS+1+Code:wght@500"),
        KANA_FAM="'M PLUS 1 Code','MS Gothic','Noto Sans Mono CJK JP',monospace",
        SCRAMBLE=KANA, HIST=KANA, LEVELS=None, GRID=("#08170d", "#0b4a20", "#0e8a34", "#00d23a", "#ff2a4a")),
    "robot": dict(
        BG="#000000", PANEL="#0a0a0a", EDGE="#262626", G="#f2f2f2", G2="#bcbcbc", G3="#7c7c7c", G4="#1c1c1c",
        HEAD="#ffffff", TEXT="#d4d4d4", DIM="#6c6c6c", RED="#e3122d",
        MONO="'JetBrains Mono',Consolas,'DejaVu Sans Mono',monospace", CW=0.6,  # JetBrains Mono advance, in em
        FONT=("JetBrains Mono", "JetBrains+Mono:wght@400"), GLYPH_FONT=None,
        KANA_FAM="'JetBrains Mono',Consolas,monospace",
        SCRAMBLE="0123456789abcdef", HIST="█", LEVELS="·░▒▓█", GRID=("#141414", "#7c7c7c", "#bcbcbc", "#f2f2f2", "#e3122d")),
}
THEME = "matrix"


def use_theme(name):
    global THEME
    THEME = name
    globals().update(THEMES[name])


use_theme("matrix")

# ------------------------------------------------------------------------------------------------ fonts
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def http(url, headers=None, data=None, tries=3):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    for attempt in range(tries):  # transient TLS / network failures are common enough to retry
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


@functools.lru_cache(None)
def font_face(family, spec, text):
    try:
        css = http(f"https://fonts.googleapis.com/css2?family={spec}&text={urllib.parse.quote(text)}").decode()
        out = []
        for weight, url in re.findall(r"font-weight:\s*(\d+);.*?src:\s*url\((.*?)\)", css, re.S):
            b64 = base64.b64encode(http(url)).decode()
            out.append(f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        return "".join(out)
    except Exception as e:  # system monospace fonts take over
        print(f"font {family}: {e}", file=sys.stderr)
        return ""


def fonts(kana):
    css = font_face(*FONT, "".join(sorted(set(ASCII + EXTRA + BOX))))
    if kana and GLYPH_FONT:
        css += font_face(*GLYPH_FONT, "".join(sorted(set(RAIN))))
    return css


# ------------------------------------------------------------------------------------------------ svg helpers
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cw(size):
    return size * CW


BASE_DEFS = (
    '<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".32"/></pattern>'
    '<radialGradient id="vig" cx=".5" cy=".5" r=".8"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
    '<stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>'
    '<filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="4" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    '<filter id="soft" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="2" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
)

BASE_CSS = (
    "text{white-space:pre}"
    ".show{animation:show .01s linear both}@keyframes show{from{opacity:0}to{opacity:1}}"
    ".type{transform-box:fill-box;transform-origin:0 0;animation-name:type;animation-fill-mode:both}"
    "@keyframes type{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    ".cur{opacity:0}"
    ".blink{opacity:0;animation:blink 1.06s step-end infinite}@keyframes blink{0%{opacity:1}50%{opacity:0}}"
    ".beam{animation:beam 7s linear infinite}"
)


def document(w, h, body, css="", label="", kana=False, defs="", faces=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}">'
        f"<title>{esc(label)}</title><defs>{BASE_DEFS}{defs}</defs>"
        f"<style>{fonts(kana)}{faces}text{{font-family:{MONO}}}.k{{font-family:{KANA_FAM};font-weight:500}}{BASE_CSS}"
        f"@keyframes beam{{from{{transform:translateY(-8px)}}to{{transform:translateY({h}px)}}}}{css}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>"
        f'<rect width="{w}" height="{h}" rx="8" fill="{BG}"/>{body}'
        f'<rect class="beam" width="{w}" height="3" fill="{G}" opacity=".06"/>'
        f'<rect width="{w}" height="{h}" rx="8" fill="url(#scan)"/><rect width="{w}" height="{h}" rx="8" fill="url(#vig)"/>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="8" fill="none" stroke="{EDGE}"/></svg>'
    )


def mono(x, y, s, size=14, fill=DIM, ls=0, anchor="start", extra=""):
    spacing = f' letter-spacing="{ls}"' if ls else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{spacing}{extra}>{esc(s)}</text>'


def titlebar(w, title, right=""):
    return (
        f'<path d="M1 34V9a8 8 0 0 1 8-8h{w - 18}a8 8 0 0 1 8 8v25z" fill="{PANEL}"/><path d="M1 34.5H{w - 1}" stroke="{EDGE}"/>'
        f'<rect x="18" y="12" width="10" height="10" fill="{RED}"/>{mono(36, 22, "tty1", 13, DIM, 1)}'
        f'{mono(w / 2, 22, title, 13, DIM, 2, "middle")}{mono(w - 18, 22, right, 13, G3, 2, "end")}'
    )


class Tape:
    """Timeline of a terminal session: typed lines, lines that appear, a cursor that follows."""

    def __init__(self, t0=0.5, cps=24):
        self.t, self.cps, self.n = t0, cps, 0
        self.defs, self.css = [], []

    def typed(self, x, y, parts, size, pause=0.3, cps=None):
        text = "".join(s for s, _ in parts)
        n, width = len(text), len(text) * cw(size)
        dur = max(n / (cps or self.cps), 0.12)  # steps(n, jump-start): float timing can stop at 0.9999, the last glyph still lands
        cid = f"tp{self.n}"
        self.n += 1
        self.defs.append(
            f'<clipPath id="{cid}"><rect class="type" x="{x}" y="{y - size * 1.05:.1f}" width="{width + 1:.1f}" height="{size * 1.4:.1f}" '
            f'style="animation-duration:{dur:.2f}s;animation-delay:{self.t:.2f}s;animation-timing-function:steps({n},jump-start)"/></clipPath>')
        self.css.append(f"@keyframes {cid}c{{from{{opacity:1;transform:translateX(0)}}to{{opacity:1;transform:translateX({width:.1f}px)}}}}")
        spans = "".join(f'<tspan fill="{f}">{esc(s)}</tspan>' for s, f in parts)
        el = (f'<text x="{x}" y="{y}" font-size="{size}" textLength="{width:.1f}" lengthAdjust="spacing" clip-path="url(#{cid})">{spans}</text>'
              f'<rect class="cur" x="{x}" y="{y - size * 0.8:.1f}" width="{cw(size):.1f}" height="{size:.1f}" fill="{G}" '
              f'style="animation:{cid}c {dur:.2f}s steps({n},jump-start) {self.t:.2f}s"/>')
        self.t += dur + pause
        return el

    def appear(self, el, gap=0.07):
        out = f'<g class="show" style="animation-delay:{self.t:.2f}s">{el}</g>'
        self.t += gap
        return out

    def cursor(self, x, y, size):
        return (f'<rect class="blink" x="{x:.1f}" y="{y - size * 0.8:.1f}" width="{cw(size):.1f}" height="{size:.1f}" fill="{G}" '
                f'style="animation-delay:{self.t:.2f}s"/>')


def rain(w, h, rnd, layers):
    """Katakana rain: one falling strip per column, brightest glyph at the head."""
    out = []
    for step, size, alpha, x0, speed in layers:
        lead = size * 1.1
        for x in range(x0, w, step):
            n = rnd.randint(7, 24)
            spans = []
            for j in range(n):
                ch = esc(rnd.choice(RAIN))
                if j == n - 1:
                    spans.append(f'<tspan x="{x}" y="{j * lead:.0f}" fill="{HEAD}">{ch}</tspan>')
                else:
                    spans.append(f'<tspan x="{x}" y="{j * lead:.0f}" fill-opacity="{0.05 + 0.8 * (j / (n - 1)) ** 1.7:.2f}">{ch}</tspan>')
            d = rnd.uniform(*speed)
            out.append(f'<g class="r" style="animation-duration:{d:.1f}s;animation-delay:-{rnd.uniform(0, d):.1f}s" opacity="{alpha}">'
                       f'<text class="k" font-size="{size}" fill="{G}">{"".join(spans)}</text></g>')
    css = f".r{{animation:fall linear infinite}}@keyframes fall{{from{{transform:translateY(-{int(26 * 20)}px)}}to{{transform:translateY({h + 20}px)}}}}"
    return "".join(out), css


# ------------------------------------------------------------------------------------------------ banner
def banner():
    w, h = W, 420
    rnd = random.Random(1337)
    drops, css_rain = rain(w, h, rnd, [(23, 13, 0.4, 5, (9, 16)), (21, 18, 1, 12, (5, 11))])
    tape = Tape(0.6, 28)
    x = 60
    first, last = P["name"]

    tag = tape.typed(x, 82, [(P["tagline"], G3)], 15, 0.25, 40)

    def name(fill, extra=""):
        return (f'<text x="{x - 4}" y="178" font-size="96" fill="{fill}" letter-spacing="2"{extra}>{esc(first)}</text>'
                f'<text x="{x - 4}" y="268" font-size="96" fill="{fill}" letter-spacing="2"{extra}>{esc(last)}</text>')

    t_name = tape.t
    tape.t += 0.5
    role = tape.typed(x, 318, [("> ", RED), (P["role"], TEXT)], 22)
    org = tape.typed(x, 352, [("> ", RED), (P["org"], TEXT)], 22, 0)
    cur = tape.cursor(x + (len(P["org"]) + 2) * cw(22) + 4, 352, 22)

    bands = lambda rows: "".join(f'<rect x="0" y="{y}" width="{w}" height="{hh}"/>' for y, hh in rows)
    defs = (f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{BG}" stop-opacity=".95"/>'
            f'<stop offset=".5" stop-color="{BG}" stop-opacity=".88"/><stop offset=".72" stop-color="{BG}" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="b1">{bands([(100, 24), (148, 18), (196, 30), (246, 14)])}</clipPath>'
            f'<clipPath id="b2">{bands([(122, 14), (170, 20), (226, 16), (258, 12)])}</clipPath>'
            f'<clipPath id="clk"><rect x="0" y="382" width="{w}" height="22"/></clipPath>' + "".join(tape.defs))

    # target dossier, top right
    dx, dy = 892, 44
    rows = [("ID", P["login"]), ("CLASS", "architect"), ("SINCE", str(P["since"])), ("NODE", P["location"].lower())]
    dossier = (f'<rect x="{dx}" y="{dy}" width="270" height="172" fill="{BG}" fill-opacity=".86" stroke="{EDGE}"/>'
               f'<path d="M{dx - 6} {dy + 14}V{dy - 6}H{dx + 14}M{dx + 256} {dy - 6}H{dx + 276}V{dy + 14}'
               f'M{dx + 276} {dy + 158}V{dy + 178}H{dx + 256}M{dx + 14} {dy + 178}H{dx - 6}V{dy + 158}" fill="none" stroke="{G}" stroke-width="2"/>'
               f'{mono(dx + 16, dy + 26, "TARGET // PROFILE", 12, G3, 3)}<path d="M{dx + 16} {dy + 36}H{dx + 254}" stroke="{EDGE}"/>')
    for i, (k, v) in enumerate(rows):
        dossier += mono(dx + 16, dy + 60 + i * 22, k, 13, DIM, 2) + mono(dx + 100, dy + 60 + i * 22, v, 15, TEXT)
    dossier += (f'{mono(dx + 16, dy + 60 + 4 * 22, "STATUS", 13, DIM, 2)}'
                f'<circle class="blink" cx="{dx + 106}" cy="{dy + 60 + 4 * 22 - 5}" r="5" fill="{RED}" style="animation-delay:0s"/>'
                f'{mono(dx + 118, dy + 60 + 4 * 22, "ACTIVE", 15, RED, 1)}')
    dossier = f'<g class="show" style="animation-delay:{t_name + 0.2:.2f}s">{dossier}</g>'

    # session clock (mm:ss counting since the image loaded)
    def strip(cx, n, period, cls):
        digits = "".join(f'<tspan x="{cx}" y="{399 + i * 22}">{i}</tspan>' for i in range(n + 1))
        return f'<g clip-path="url(#clk)"><g class="{cls}"><text font-size="15" fill="{G}">{digits}</text></g></g>'

    cx = 1078
    clock = (mono(cx - 92, 399, "SESSION", 13, DIM, 2) + strip(cx, 6, 3600, "m1") + strip(cx + 9, 10, 600, "m2")
             + mono(cx + 18, 399, ":", 15, G) + strip(cx + 26, 6, 60, "s1") + strip(cx + 35, 10, 10, "s2"))
    css_clock = "".join(f".{c}{{animation:{c} {p}s steps({n}) infinite}}@keyframes {c}{{to{{transform:translateY(-{n * 22}px)}}}}"
                        for c, n, p in [("m1", 6, 3600), ("m2", 10, 600), ("s1", 6, 60), ("s2", 10, 10)])

    status = (f'<rect x="1" y="376" width="{w - 2}" height="32" fill="{PANEL}" fill-opacity=".92"/><path d="M1 376H{w - 1}" stroke="{EDGE}"/>'
              f'{mono(24, 397, "[", 13, DIM)}{mono(34, 397, "ONLINE", 13, G, 2)}{mono(96, 397, "]", 13, DIM)}'
              f'{mono(124, 397, "UPLINK  github.com/" + P["login"], 13, DIM, 2)}'
              f'{mono(w / 2 + 40, 397, "ENCRYPTION  AES-256  //  TRACE  BLOCKED", 13, G3, 2, "middle")}'
              f'<circle class="blink" cx="{cx - 116}" cy="392" r="5" fill="{RED}" style="animation-delay:0s"/>{clock}')

    glitch = ("@keyframes gm{0%,88%,100%{transform:none}89%{transform:translate(4px,0)}90.5%{transform:translate(-3px,1px)}"
              "92%{transform:none}95%{transform:skewX(-6deg)}96%{transform:none}}"
              "@keyframes g1{0%,88%,100%{opacity:0;transform:none}89%{opacity:.9;transform:translate(-9px,0)}"
              "90.5%{opacity:.9;transform:translate(6px,-2px)}92%{opacity:0}95%{opacity:.8;transform:translate(-4px,0)}96%{opacity:0}}"
              "@keyframes g2{0%,88%,100%{opacity:0;transform:none}89.5%{opacity:.8;transform:translate(8px,1px)}"
              "91%{opacity:.8;transform:translate(-5px,0)}92%{opacity:0}95.5%{opacity:.7;transform:translate(5px,0)}96.5%{opacity:0}}"
              ".gm,.g1,.g2{transform-box:fill-box;transform-origin:50% 50%;animation-duration:6.5s;animation-iteration-count:infinite;"
              "animation-timing-function:steps(1,end);animation-delay:2.5s}"
              ".gm{animation-name:gm}.g1{opacity:0;animation-name:g1}.g2{opacity:0;animation-name:g2}"
              ".boot{animation:boot .9s steps(1,end) both}"
              "@keyframes boot{0%{opacity:0}20%{opacity:.7}30%{opacity:0}45%{opacity:1}55%{opacity:.2}65%{opacity:1}}")

    body = (f'{drops}<rect width="{w}" height="{h}" fill="url(#fade)"/>{tag}'
            f'<g class="boot" style="animation-delay:{t_name:.2f}s"><g filter="url(#glow)"><g class="gm">{name(G)}</g></g>'
            f'<g class="g1" clip-path="url(#b1)">{name(RED)}</g><g class="g2" clip-path="url(#b2)">{name(HEAD)}</g></g>'
            f'<path d="M{x} 290H{x + 520}" stroke="{G3}" stroke-dasharray="2 6"/>{role}{org}{cur}{dossier}{status}')
    label = f"{P['full_name']}: {P['role']}, {P['org']}. Matrix-style code rain behind a glitching name."
    return document(w, h, body, css_rain + glitch + css_clock + "".join(tape.css), label, kana=True, defs=defs)


# ------------------------------------------------------------------------------------------------ whoami terminal
def whoami():
    size, lead, x = 17, 27, 30
    lines = []
    for item in P["terminal"]:
        if "kv" in item:
            lines += [("kv", k, v) for k, v in item["kv"]]
        elif "cmd" in item:
            lines.append(("cmd", item["cmd"], None))
        else:
            lines.append(("out", item["out"], G if item.get("hl") else TEXT))
    lines.append(("prompt", "", None))
    h = 34 + 26 + len(lines) * lead + 14
    tape = Tape(0.6, 22)
    body, y = [], 34 + 30 + size
    prompt = [(f"{P['user']}@{P['host']}", G), (":", DIM), ("~", G2), ("$ ", DIM)]
    plen = sum(len(s) for s, _ in prompt) * cw(size)
    for kind, a, b in lines:
        if kind == "cmd":
            body.append(tape.appear(f'<text x="{x}" y="{y}" font-size="{size}">' + "".join(f'<tspan fill="{f}">{esc(s)}</tspan>' for s, f in prompt) + "</text>", 0.25))
            body.append(tape.typed(x + plen, y, [(a, HEAD)], size, 0.35))
        elif kind == "out":
            body.append(tape.appear(mono(x, y, a, size, b)))
        elif kind == "kv":
            body.append(tape.appear(mono(x + 24, y, a, size, G3, 2) + mono(x + 24 + 9 * cw(size) + 18, y, b, size, TEXT), 0.12))
        else:
            body.append(tape.appear(f'<text x="{x}" y="{y}" font-size="{size}">' + "".join(f'<tspan fill="{f}">{esc(s)}</tspan>' for s, f in prompt) + "</text>", 0))
            body.append(tape.cursor(x + plen + 2, y, size))
        y += lead
    label = f"Terminal session. whoami: {P['full_name']}. " + " ".join(f"{k}: {v}." for item in P["terminal"] if "kv" in item for k, v in item["kv"])
    return document(W, h, titlebar(W, f"{P['user']}@{P['host']}: ~  -  bash", "pts/0") + "".join(body), "".join(tape.css), label, defs="".join(tape.defs))


# ------------------------------------------------------------------------------------------------ robot theme
def spans(x, y, size, parts, extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}"{extra}>' + "".join(f'<tspan fill="{f}">{esc(s)}</tspan>' for s, f in parts) + "</text>"


def kali(tape, x, y, size, lead, steps):
    """Kali-style session: two-line prompt, typed commands, outputs and aligned table rows."""
    out = []
    top = [("┌──(", RED), (f"{P['user']}@{P['host']}", HEAD), (")-[", RED), ("~", TEXT), ("]", RED)]
    low = [("└─", RED), ("$ ", HEAD)]
    for st in steps:
        kind = st[0]
        if kind in ("cmd", "end"):
            out.append(tape.appear(spans(x, y, size, top), 0.15))
            y += lead
            out.append(tape.appear(spans(x, y, size, low), 0.1))
            if kind == "cmd":
                out.append(tape.typed(x + 4 * cw(size), y, [(st[1], HEAD)], size, 0.35))
            else:
                out.append(tape.cursor(x + 4 * cw(size) + 2, y, size))
            y += lead
        elif kind == "out":
            out.append(tape.appear(mono(x, y, st[1], size, st[2] if len(st) > 2 else TEXT)))
            y += lead
        elif kind == "row":  # cells: (column in characters, text, colour, anchor)
            out.append(tape.appear("".join(mono(x + c * cw(size), y, t, size, f, 0, a) for c, t, f, a in st[1]), 0.09))
            y += lead
        elif kind == "blank":
            y += lead * 0.5
    return out, y


def strip_clock(x, y, size, fill, prefix):
    """mm:ss counting from the moment the image loads: four digit strips stepping through a clipped window."""
    lead, w = size * 1.3, cw(size)
    cid = f"{prefix}clip"
    defs = f'<clipPath id="{cid}"><rect x="{x - 2}" y="{y - size}" width="{6 * w + 4:.1f}" height="{size * 1.25:.1f}"/></clipPath>'
    parts, css = [], []
    for k, (n, period) in enumerate([(6, 3600), (10, 600), (None, None), (6, 60), (10, 10)]):
        cx = x + k * w
        if n is None:
            parts.append(mono(cx, y, ":", size, fill))
            continue
        cls = f"{prefix}{k}"
        digits = "".join(f'<tspan x="{cx:.1f}" y="{y + i * lead:.1f}">{i % 10}</tspan>' for i in range(n + 1))
        parts.append(f'<g clip-path="url(#{cid})"><g class="{cls}"><text font-size="{size}" fill="{fill}">{digits}</text></g></g>')
        css.append(f".{cls}{{animation:{cls} {period}s steps({n}) infinite}}@keyframes {cls}{{to{{transform:translateY(-{n * lead:.1f}px)}}}}")
    return "".join(parts), "".join(css), defs


def hexdump(x, y0, rows, size, rnd, messages):
    """xxd-style dump; a few rows carry a message in their ASCII column, picked out in red."""
    lines, msg_rows = [], {}
    slots = rnd.sample(range(2, rows - 1), len(messages))
    for r, m in zip(slots, messages):
        msg_rows[r] = m
    for r in range(rows):
        if r in msg_rows:
            data = msg_rows[r].encode()[:16].ljust(16, b".")
        else:
            data = bytes(rnd.randrange(256) for _ in range(16))
        hx = " ".join(data[i:i + 2].hex() for i in range(0, 16, 2))
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
        lines.append((f"{0x7f3a2c00 + r * 16:08x}: {hx}  ", asc, r in msg_rows))
    lead = size * 1.5
    out = []
    for r, (left, asc, hot) in enumerate(lines):
        yy = y0 + r * lead
        out.append(f'<text x="{x}" y="{yy:.1f}" font-size="{size}"><tspan fill="{G4 if not hot else G3}">{esc(left)}</tspan>'
                   f'<tspan fill="{RED if hot else G4}">{esc(asc)}</tspan></text>')
    return "".join(out), rows * lead


def banner_robot():
    w, h = W, 420
    R = P["robot"]
    rnd = random.Random(1986)
    tape = Tape(0.8, 16)
    x = 60

    # background: a memory dump scrolling upward, twice the height so the loop is seamless
    rows = 26
    dump, dump_h = hexdump(712, 0, rows, 11.5, rnd, R["hexdump"])
    scroll = (f'<g class="hex">{dump}<g transform="translate(0 {dump_h:.1f})">{dump}</g></g>')
    css = [f".hex{{animation:hex 70s linear infinite}}@keyframes hex{{to{{transform:translateY(-{dump_h:.1f}px)}}}}"]

    clock, clock_css, clock_defs = strip_clock(x + 70, 58, 15, TEXT, "rc")
    rec = (f'<circle class="blink" cx="{x + 6}" cy="53" r="6" fill="{RED}" style="animation-delay:0s"/>'
           f'{mono(x + 20, 58, "REC", 15, RED, 2)}{clock}{mono(x + 160, 58, R["status"], 13, DIM, 2)}')
    css.append(clock_css)

    hello = tape.typed(x, 146, [(R["hello"], HEAD)], 34, 0.6, 9)
    t_name = tape.t
    tape.t += 0.6
    full = P["full_name"].lower()

    def name(fill, extra=""):
        return f'<text x="{x - 3}" y="244" font-size="74" font-weight="800" fill="{fill}"{extra}>{esc(full)}</text>'

    lines = []
    for i, line in enumerate(R["lines"]):
        lines.append(tape.typed(x, 298 + i * 32, [(line, TEXT if i == 0 else G2)], 19, 0.4, 30))
    last = R["lines"][-1]
    cur = (f'<rect class="blink" x="{x + len(last) * cw(19) + 6:.1f}" y="{298 + (len(R["lines"]) - 1) * 32 - 15}" width="{cw(19):.1f}" '
           f'height="19" fill="{RED}" style="animation-delay:{tape.t:.2f}s"/>')

    bands = lambda rr: "".join(f'<rect x="0" y="{y}" width="{w}" height="{hh}"/>' for y, hh in rr)
    defs = (f'<linearGradient id="fade" x1="0" x2="1"><stop offset=".5" stop-color="{BG}"/>'
            f'<stop offset=".64" stop-color="{BG}" stop-opacity=".55"/><stop offset=".8" stop-color="{BG}" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="b1">{bands([(186, 16), (212, 10), (230, 20)])}</clipPath>'
            f'<clipPath id="b2">{bands([(196, 12), (220, 8), (238, 14)])}</clipPath>' + clock_defs + "".join(tape.defs))

    css.append(
        "@keyframes gm{0%,86%,100%{transform:none}87%{transform:translate(6px,0)}88%{transform:translate(-4px,0)}89%{transform:none}"
        "94%{transform:translate(0,-2px) skewX(10deg)}95%{transform:none}}"
        "@keyframes g1{0%,86%,100%{opacity:0;transform:none}87%{opacity:1;transform:translate(-14px,0)}88.5%{opacity:1;transform:translate(9px,0)}"
        "89.5%{opacity:0}94%{opacity:1;transform:translate(-6px,0)}95%{opacity:0}}"
        "@keyframes g2{0%,86%,100%{opacity:0;transform:none}87.5%{opacity:.9;transform:translate(12px,0)}89%{opacity:0}"
        "94.5%{opacity:.8;transform:translate(7px,0)}95.5%{opacity:0}}"
        ".gm,.g1,.g2{transform-box:fill-box;transform-origin:50% 50%;animation-duration:5.5s;animation-iteration-count:infinite;"
        "animation-timing-function:steps(1,end);animation-delay:3s}"
        ".gm{animation-name:gm}.g1{opacity:0;animation-name:g1}.g2{opacity:0;animation-name:g2}"
        ".boot{animation:boot 1.1s steps(1,end) both}"
        "@keyframes boot{0%{opacity:0}15%{opacity:1}22%{opacity:0}40%{opacity:1}48%{opacity:.15}60%{opacity:1}}"
        # a pale tear band that jumps around the frame now and then
        ".tear{opacity:0;animation:tear 4.3s steps(1,end) 2s infinite}"
        "@keyframes tear{0%,70%,100%{opacity:0}71%{opacity:1;transform:translateY(60px)}73%{opacity:1;transform:translateY(212px)}"
        "75%{opacity:0}90%{opacity:1;transform:translateY(300px)}91.5%{opacity:0}}")

    status = (f'<rect x="1" y="376" width="{w - 2}" height="32" fill="{PANEL}"/><path d="M1 376H{w - 1}" stroke="{EDGE}"/>'
              f'{mono(24, 397, R["id"], 13, DIM, 1)}'
              f'<circle class="blink" cx="{w - 158}" cy="392" r="4" fill="{RED}" style="animation-delay:.5s"/>'
              f'{mono(w - 24, 397, "ESTABLISHED", 13, RED, 3, "end")}')

    body = (f'{scroll}<rect width="{w}" height="{h}" fill="url(#fade)"/>{rec}{hello}'
            f'<g class="boot" style="animation-delay:{t_name:.2f}s"><g class="gm">{name(HEAD)}</g>'
            f'<g class="g1" clip-path="url(#b1)">{name(RED)}</g><g class="g2" clip-path="url(#b2)">{name(G3)}</g></g>'
            f'<rect x="{x}" y="262" width="56" height="4" fill="{RED}"/>'
            f'{"".join(lines)}{cur}<rect class="tear" width="{w}" height="7" fill="{HEAD}" opacity=".08"/>{status}')
    label = f"{R['hello']} {P['full_name']}: {P['role']}, {P['org']}. Black terminal, red glitches, a memory dump scrolling behind."
    bold = font_face("JetBrains Mono", "JetBrains+Mono:wght@800", "".join(sorted(set(full))))  # only the name is heavy
    return document(w, h, body, "".join(css + tape.css), label, defs=defs, faces=bold)


def whoami_robot():
    size, lead, x = 17, 27, 30
    steps = []
    for item in P["terminal"]:
        if "cmd" in item:
            steps.append(("cmd", item["cmd"]))
        elif "kv" in item:
            steps += [("row", [(2, k.lower(), RED, "start"), (12, v, TEXT, "start")]) for k, v in item["kv"]]
        else:
            steps.append(("out", item["out"], HEAD if item.get("hl") else TEXT))
    steps.append(("end",))
    tape = Tape(0.6, 22)
    body, y = kali(tape, x, 34 + 30 + size, size, lead, steps)
    h = int(y - lead + 26)
    label = f"Terminal session. whoami: {P['full_name']}. " + " ".join(f"{k}: {v}." for item in P["terminal"] if "kv" in item for k, v in item["kv"])
    return document(W, h, titlebar(W, f"{P['user']}@{P['host']}: ~  -  zsh", "pts/0") + "".join(body), "".join(tape.css), label,
                    defs="".join(tape.defs))


def recon():
    size, lead, x = 16, 25, 30
    R = P["robot"]
    steps = [("cmd", f"nmap -sV {P['host']}"),
             ("out", "Starting Nmap 7.95", DIM),
             ("out", f"Nmap scan report for {P['host']} ({P['location'].lower()})", TEXT),
             ("out", "Host is up (0.0013s latency).", TEXT),
             ("row", [(0, "PORT", G3, "start"), (11, "STATE", G3, "start"), (18, "SERVICE", G3, "start"), (32, "VERSION", G3, "start")])]
    for port, svc, version in R["services"]:
        steps.append(("row", [(0, port, TEXT, "start"), (11, "open", RED, "start"), (18, svc, HEAD, "start"), (32, version, G2, "start")]))
    steps += [("out", f"Service detection performed. {len(R['services'])} services up.", DIM), ("blank",),
              ("cmd", f"ps -u {P['user']} -o pid,stat,%cpu,comm"),
              ("row", [(5, "PID", G3, "end"), (7, "STAT", G3, "start"), (17, "%CPU", G3, "end"), (19, "COMMAND", G3, "start")])]
    for p in P["processes"]:
        steps.append(("row", [(5, str(p["pid"]), TEXT, "end"), (7, "Rl", G2, "start"), (17, f"{p['cpu']:.1f}", RED if p["cpu"] > 90 else TEXT, "end"),
                              (19, p["cmd"], HEAD, "start"), (35, "# " + p["desc"], DIM, "start")]))
    steps.append(("end",))
    tape = Tape(0.6, 26)
    body, y = kali(tape, x, 34 + 30 + size, size, lead, steps)
    h = int(y - lead + 26)
    label = ("nmap scan of the stack: " + " ".join(f"{p} {s}: {v}." for p, s, v in R["services"]) + " Running processes: "
             + " ".join(f"{p['cmd']}, {p['desc']}." for p in P["processes"]))
    return document(W, h, titlebar(W, f"recon  -  {P['user']}@{P['host']}", "scan complete") + "".join(body), "".join(tape.css), label,
                    defs="".join(tape.defs))


# ------------------------------------------------------------------------------------------------ dev farm
def farm():
    """How BSD Soft ships: me -> orchestrator -> sub-agents -> production, all reading and writing one Obsidian brain."""
    F = P["farm"]
    w, h = W, 436
    body = [titlebar(w, "dev-farm  -  topology", "running 24/7")]
    css = (".flow{stroke-dasharray:3 9;animation:flow 1.1s linear infinite}@keyframes flow{to{stroke-dashoffset:-12}}"
           ".pulse{animation:pulse 2.4s ease-in-out infinite}@keyframes pulse{0%,100%{opacity:.25}50%{opacity:1}}"
           f".lot{{animation:lot 4.2s steps(1,end) infinite}}@keyframes lot{{0%,100%{{fill:{G4}}}8%,30%{{fill:{G}}}}}")

    def box(x, y, bw, bh, accent=G3):
        return (f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{PANEL}" stroke="{EDGE}"/>'
                f'<rect x="{x}" y="{y}" width="3" height="{bh}" fill="{accent}"/>')

    def node(delay, inner):
        return f'<g class="show" style="animation-delay:{delay:.2f}s">{inner}</g>'

    def link(d, delay, color=G3, flow=True):
        cls = ' class="flow"' if flow else ""
        return node(delay, f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{cls}/>')

    # operator
    ux, uy, uw, uh = 30, 150, 170, 74
    you, you_sub = F["you"]
    body.append(node(0.3, box(ux, uy, uw, uh, RED) + mono(ux + 18, uy + 30, you, 20, HEAD) + mono(ux + 18, uy + 54, you_sub, 12, DIM, 1)))

    # orchestrator with its queue of lots
    ox, oy, ow, oh = 240, 136, 256, 102
    title, sub = F["orchestrator"]
    lots = "".join(f'<rect class="lot" x="{ox + 18 + i * 22}" y="{oy + 72}" width="16" height="12" fill="{G4}" '
                   f'style="animation-delay:{i * 0.6:.1f}s"/>' for i in range(9))
    body.append(node(0.6, box(ox, oy, ow, oh) + f'<g filter="url(#soft)">{mono(ox + 18, oy + 32, title, 18, G, 2)}</g>'
                     + mono(ox + 18, oy + 54, sub, 12, DIM, 1) + lots))
    body.append(link(f"M{ux + uw} {uy + uh / 2}H{ox}", 0.5))

    # sub-agents
    ax, aw, ah = 550, 320, 40
    ays = [58 + i * 50 for i in range(len(F["agents"]))]
    sx, sy, sw, sh = 920, 150, 250, 74
    for i, ((name, role), ay) in enumerate(zip(F["agents"], ays)):
        d = 0.9 + i * 0.15
        cy = ay + ah / 2
        body.append(link(f"M{ox + ow} {oy + oh / 2}C{ox + ow + 44} {oy + oh / 2} {ax - 44} {cy} {ax} {cy}", d - 0.05))
        body.append(link(f"M{ax + aw} {cy}C{ax + aw + 44} {cy} {sx - 44} {sy + sh / 2} {sx} {sy + sh / 2}", d + 0.6))
        body.append(node(d, box(ax, ay, aw, ah) + f'<circle class="pulse" cx="{ax + 18}" cy="{cy}" r="4" fill="{G}" style="animation-delay:{i * 0.45:.2f}s"/>'
                         + mono(ax + 32, cy + 5, name, 16, G) + mono(ax + aw - 14, cy + 5, role, 12, DIM, 1, "end")))

    # production
    title, sub = F["ship"]
    body.append(node(1.7, box(sx, sy, sw, sh, G) + mono(sx + 18, sy + 30, title, 18, G, 2) + mono(sx + 18, sy + 54, sub, 12, DIM, 1)
                     + f'<circle class="blink" cx="{sx + sw - 20}" cy="{sy + 24}" r="5" fill="{RED}" style="animation-delay:0s"/>'))

    # the brain, under everything: read before a task, written after
    bx, by, bw, bh = 250, 334, 920, 80
    title, line1, line2 = F["brain"]
    body.append(node(2.0, box(bx, by, bw, bh, G) + f'<g filter="url(#glow)">{mono(bx + 18, by + 28, title, 17, G, 2)}</g>'
                     + mono(bx + 18, by + 50, line1, 14, TEXT) + mono(bx + 18, by + 70, line2, 13, DIM)))
    for cx, top in [(ox + ow / 2, oy + oh), (ax + aw / 2, ays[-1] + ah)]:
        body.append(link(f"M{cx - 5} {by}V{top}", 2.1, G2))       # read: flows up out of the brain
        body.append(link(f"M{cx + 5} {top}V{by}", 2.1, G3))       # write: flows back down into it
        body.append(node(2.1, mono(cx - 12, (top + by) / 2 + 4, "read", 11, G2, 1, "end") + mono(cx + 12, (top + by) / 2 + 4, "write", 11, G3, 1)))
    label = (f"Development farm: {you} gives specs and reviews; an orchestrator queues lots and dispatches them to sub-agents ("
             + ", ".join(f"{n}: {r}" for n, r in F["agents"]) + f"); results ship to production. {title}: {line1}. {line2}.")
    return document(w, h, "".join(body), css, label)


# ------------------------------------------------------------------------------------------------ htop
def htop():
    size, x = 16, 30
    meters, procs = P["meters"], P["processes"]
    top = 34 + 22
    rh = 60  # each process gets two lines: name + stack, then what it is
    h = top + len(meters) * 26 + 30 + 28 + len(procs) * rh + 14 + 30 + 10
    tape = Tape(0.5, 60)
    body = [titlebar(W, f"htop  -  {P['user']}@{P['host']}", "modules loaded")]
    nbar = 40
    css = []
    for i, (lab, lvl, items) in enumerate(meters):
        y = top + 18 + i * 26
        filled = round(nbar * lvl)
        bx = x + 7 * cw(size)
        bar_hi, bar_mid = filled - max(2, filled // 6), max(2, filled // 6)
        bar = [("|" * bar_hi, G), ("|" * bar_mid, RED), (" " * (nbar - filled), G)]
        pct = f"{lvl * 100:.1f}%"
        body.append(mono(x, y, lab, size, G2, 1))
        body.append(mono(bx, y, "[", size, DIM))
        tape.t = 0.4 + i * 0.25
        body.append(tape.typed(bx + cw(size), y, bar, size, 0, 70))
        body.append(mono(bx + (nbar + 1) * cw(size), y, "]", size, DIM))
        body.append(mono(bx + (nbar + 8) * cw(size), y, pct, size, G3, 0, "end"))
        body.append(mono(bx + (nbar + 10) * cw(size), y, items, size, TEXT))

    years = dt.date.today().year - P["since"]
    rx = 900
    info = [("Tasks: ", f"{len(procs)}, 0 thr; {len(procs)} running"), ("Load average: ", "0.97 1.12 1.31"),
            ("Uptime: ", f"{years} years (since {P['since']})")]
    for i, (k, v) in enumerate(info):
        body.append(f'<text x="{rx}" y="{top + 18 + i * 26}" font-size="{size}"><tspan fill="{G3}">{esc(k)}</tspan><tspan fill="{TEXT}">{esc(v)}</tspan></text>')

    ty = top + len(meters) * 26 + 24
    # column anchors in characters: right-aligned numbers end at their anchor
    cols = [("PID", 5, "end"), ("USER", 7, "start"), ("PRI", 18, "end"), ("S", 20, "start"), ("CPU%", 27, "end"), ("COMMAND", 29, "start")]
    body.append(mono(W - 30, ty + 17, "STACK", size, BG, 0, "end"))
    def colx(c):
        return x + c * cw(size)
    body.append(f'<rect x="1" y="{ty}" width="{W - 2}" height="24" fill="{G2}"/>')
    for name, c, anc in cols:
        body.append(mono(colx(c), ty + 17, name, size, BG, 0, anc))
    rows_y0 = ty + 24
    for i, p in enumerate(procs):
        y = rows_y0 + 26 + i * rh
        body.append(mono(colx(5), y, p["pid"], size, TEXT, 0, "end"))
        body.append(mono(colx(7), y, P["user"], size, TEXT))
        body.append(mono(colx(18), y, 20, size, DIM, 0, "end"))
        body.append(mono(colx(20), y, "R", size, G))
        body.append(mono(colx(27), y, f"{p['cpu']:.1f}", size, RED if p["cpu"] > 90 else TEXT, 0, "end"))
        body.append(f'<g class="show" style="animation-delay:{1.2 + i * 0.15:.2f}s">'
                    + mono(colx(29), y + 1, p["cmd"], 24, G, 1, "start", ' filter="url(#glow)"')
                    + mono(W - 30, y, p.get("stack", ""), 14, G3, 0, "end")
                    + mono(colx(29), y + 24, p["desc"], size, TEXT) + "</g>")
        if i < len(procs) - 1:
            body.append(f'<path d="M{colx(29):.0f} {y + 36}H{W - 30}" stroke="{EDGE}" stroke-dasharray="2 5"/>')
    # selection bar walking down the process list
    n = len(procs)
    css.append(f".sel{{animation:sel {n * 2.2:.1f}s steps(1,end) 2s infinite}}@keyframes sel{{"
               + "".join(f"{i * 100 / n:.2f}%{{transform:translateY({i * rh}px)}}" for i in range(n)) + "}")
    body.insert(1, f'<rect class="sel" x="1" y="{rows_y0 + 2}" width="6" height="{rh - 4}" fill="{RED}"/>'
                   f'<rect class="sel" x="7" y="{rows_y0 + 2}" width="{W - 8}" height="{rh - 4}" fill="{G4}" opacity=".55"/>')

    fy = h - 30
    keys = [("F1", "Hire"), ("F2", "Collab"), ("F3", "Search"), ("F5", "Tree"), ("F6", "SortBy"), ("F9", "Kill"), ("F10", "Quit")]
    fx = x
    for k, v in keys:
        body.append(mono(fx, fy + 19, k, 14, TEXT))
        kx = fx + len(k) * cw(14) + 2
        body.append(f'<rect x="{kx:.1f}" y="{fy + 4}" width="{len(v) * cw(14) + 22:.1f}" height="20" fill="{G4}"/>')
        body.append(mono(kx + 4, fy + 19, v, 14, G))
        fx = kx + len(v) * cw(14) + 34
    label = "htop: tech stack meters. " + " ".join(f"{a}: {c}." for a, _, c in meters) + " Running processes: " + \
            " ".join(f"{p['cmd']}, {p['desc']}." for p in procs)
    return document(W, h, "".join(body), "".join(css + tape.css), label, defs="".join(tape.defs))


# ------------------------------------------------------------------------------------------------ live data
def gql(query, token):
    body = json.dumps({"query": query}).encode()
    res = json.loads(http("https://api.github.com/graphql", {"Authorization": f"bearer {token}", "Content-Type": "application/json"}, body))
    if res.get("errors"):
        raise SystemExit(f"GraphQL: {res['errors']}")
    return res["data"]


def fetch(user, token):
    d = gql(f"""{{ user(login:"{user}") {{ createdAt followers {{ totalCount }}
      repositories(ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC) {{ totalCount }}
      contributionsCollection {{ contributionYears contributionCalendar {{ totalContributions
        weeks {{ contributionDays {{ date contributionCount contributionLevel }} }} }} }} }} }}""", token)["user"]
    years = d["contributionsCollection"]["contributionYears"]
    parts = " ".join(f'y{y}: contributionsCollection(from:"{y}-01-01T00:00:00Z", to:"{y}-12-31T23:59:59Z")'
                     f"{{ contributionCalendar {{ totalContributions }} }}" for y in years)
    yd = gql(f'{{ user(login:"{user}") {{ {parts} }} }}', token)["user"]
    d["all_time"] = sum(v["contributionCalendar"]["totalContributions"] for v in yd.values())
    return d


LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def summarize(d):
    cal = d["contributionsCollection"]["contributionCalendar"]
    weeks = [[(x["date"], x["contributionCount"], LEVEL.get(x["contributionLevel"], 0)) for x in w["contributionDays"]] for w in cal["weeks"]]
    days = [x for w in weeks for x in w]
    counts = [c for _, c, _ in days]
    i, cur = len(days) - 1, 0
    if counts and counts[-1] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur, i = cur + 1, i - 1
    best = run = 0
    for c in counts:
        run = run + 1 if c else 0
        best = max(best, run)
    peak = max(days, key=lambda x: x[1]) if days else ("", 0, 0)
    return {"total": cal["totalContributions"], "all_time": d["all_time"], "weeks": weeks, "current": cur, "longest": best,
            "active": sum(1 for c in counts if c), "ndays": len(days), "peak": peak,
            "since": int(d["createdAt"][:4]), "repos": d["repositories"]["totalCount"], "followers": d["followers"]["totalCount"],
            "today": days[-1][0] if days else dt.date.today().isoformat()}


def num(n):
    return f"{n:,}"


def signal(s):
    w, h = W, 390
    rnd = random.Random(s["total"])
    body = [titlebar(w, "netstat  -  signal trace  //  last 365 days", f"updated {s['today']}")]
    x = 30
    big = num(s["total"])
    body.append(mono(x, 78, "CONTRIBUTIONS  //  LAST 365 DAYS", 13, G3, 3))
    # decode effect: scrambled readings flash over the real number, which lands last
    scr = []
    for k in range(4):
        fake = "".join(rnd.choice(SCRAMBLE) if ch.isdigit() else ch for ch in big)
        scr.append(f'<text class="k dec" x="{x}" y="150" font-size="64" fill="{G2}" style="animation-delay:{0.3 + k * 0.18:.2f}s">{esc(fake)}</text>')
    body.append("".join(scr))
    body.append(f'<g class="show" style="animation-delay:1.05s"><g filter="url(#glow)">{mono(x - 2, 150, big, 76, G)}</g></g>')
    peak_d, peak_c, _ = s["peak"]
    body.append(f'<text x="{x}" y="182" font-size="14"><tspan fill="{DIM}">ALL TIME </tspan><tspan fill="{TEXT}">{num(s["all_time"])}</tspan>'
                f'<tspan fill="{DIM}">   PEAK </tspan><tspan fill="{TEXT}">{num(peak_c)}</tspan><tspan fill="{DIM}"> ON {esc(peak_d)}</tspan></text>')

    tiles = [("CURRENT STREAK", s["current"], "days"), ("LONGEST STREAK", s["longest"], "days"), ("ACTIVE DAYS", s["active"], f"/ {s['ndays']}"),
             ("YEARS ONLINE", dt.date.today().year - s["since"], f"since {s['since']}"), ("PUBLIC REPOS", s["repos"], ""),
             ("FOLLOWERS", s["followers"], "")]
    tx0, tw, th = 560, 196, 62
    for i, (lab, v, unit) in enumerate(tiles):
        tx, ty = tx0 + (i % 3) * (tw + 10), 54 + (i // 3) * (th + 10)
        body.append(f'<g class="show" style="animation-delay:{0.4 + i * 0.1:.2f}s"><rect x="{tx}" y="{ty}" width="{tw}" height="{th}" fill="{PANEL}" stroke="{EDGE}"/>'
                    f'<rect x="{tx}" y="{ty}" width="3" height="{th}" fill="{RED if i == 0 else G3}"/>'
                    f'{mono(tx + 14, ty + 20, lab, 11, DIM, 2)}'
                    f'<text x="{tx + 14}" y="{ty + 50}"><tspan font-size="28" fill="{G}">{esc(num(v))}</tspan>'
                    f'<tspan font-size="12" fill="{DIM}"> {esc(unit)}</tspan></text></g>')

    # weekly histogram drawn as glyph stacks, dropping in like rain
    weeks = [sum(c for _, c, _ in wk) for wk in s["weeks"]]
    mx = max(weeks) or 1
    gx0, base, pitch, gs, rows = 30, h - 22, (w - 60) / max(len(weeks), 1), 13, 9
    cols = []
    for i, v in enumerate(weeks):
        n = 0 if v == 0 else max(1, round(rows * math.log1p(v) / math.log1p(mx)))  # log scale: quiet weeks stay visible
        cx = gx0 + i * pitch
        spans = "".join(
            f'<tspan x="{cx:.1f}" y="{base - j * (gs + 1)}" fill="{HEAD if j == n - 1 else G}" fill-opacity="{1 if j == n - 1 else 0.25 + 0.6 * j / max(n - 1, 1):.2f}">{esc(rnd.choice(HIST))}</tspan>'
            for j in range(n))
        if not n:
            spans = f'<tspan x="{cx:.1f}" y="{base}" fill="{G4}">·</tspan>'
        cols.append(f'<g class="drop" style="animation-delay:{0.6 + i * 0.03:.2f}s"><text class="k" font-size="{gs}">{spans}</text></g>')
    body.append(f'<path d="M30 {base - rows * (gs + 1) - 16}H{w - 30}" stroke="{EDGE}" stroke-dasharray="2 5"/>')
    body.append(mono(30, base - rows * (gs + 1) - 24, "WEEKLY THROUGHPUT", 11, DIM, 3))
    body.append(mono(w - 30, base - rows * (gs + 1) - 24, f"MAX {num(mx)} / WEEK", 11, DIM, 3, "end"))
    body.append("".join(cols))
    css = (".dec{opacity:0;animation:dec .18s steps(1,end) forwards}@keyframes dec{0%{opacity:1}99%{opacity:1}100%{opacity:0}}"
           ".drop{animation:drop .6s cubic-bezier(.3,0,.7,1) both}@keyframes drop{from{transform:translateY(-240px);opacity:0}30%{opacity:1}}")
    label = (f"Signal trace: {num(s['total'])} contributions in the last 365 days, {num(s['all_time'])} all time. Current streak {s['current']} days, "
             f"longest {s['longest']} days, active {s['active']} of {s['ndays']} days.")
    return document(w, h, "".join(body), css, label, kana=True)


def grid(s):
    weeks = s["weeks"]
    pitch, gs = 20, 15
    x0, y0 = 78, 34 + 52
    w = W
    h = y0 + 7 * pitch + 46
    rnd = random.Random(len(weeks) * 7 + s["total"])
    body = [titlebar(w, "contrib.log  -  53 weeks", P["login"])]
    months, last = [], None
    for i, wk in enumerate(weeks):
        m = wk[0][0][:7]
        if m != last and (not months or i - months[-1][0] >= 3):
            months.append((i, dt.date.fromisoformat(wk[0][0]).strftime("%b").upper()))
        last = m
    for i, mname in months:
        body.append(mono(x0 + i * pitch, y0 - 16, mname, 11, DIM, 2))
    for r, lab in [(1, "MON"), (3, "WED"), (5, "FRI")]:
        body.append(mono(x0 - 14, y0 + r * pitch + 5, lab, 11, DIM, 2, "end"))
    rows = []
    today = None
    for i, wk in enumerate(weeks):
        for date, c, lv in wk:  # square cells, the hottest days in red
            r = dt.date.fromisoformat(date).isoweekday() % 7
            cx, cy = x0 + i * pitch, y0 + r * pitch + 5
            rows.append(f'<rect x="{cx - 2}" y="{cy - 14}" width="15" height="15" fill="{GRID[lv]}"/>')
            today = (cx, cy)
    body.append("".join(rows))
    if today:
        body.append(f'<rect class="blink" x="{today[0] - 4}" y="{today[1] - 15}" width="{pitch - 1}" height="{pitch - 1}" fill="none" '
                    f'stroke="{RED}" stroke-width="1.5" style="animation-delay:0s"/>')
    sweep_w = len(weeks) * pitch
    body.append(f'<rect class="sweep" x="{x0 - 6}" y="{y0 - 8}" width="{pitch}" height="{7 * pitch + 4}" fill="{G}" opacity=".09"/>')
    ly = h - 18
    lx = w - 30 - 10 * 22
    body.append(mono(lx - 12, ly, "LESS", 11, DIM, 2, "end"))
    for k, fill in enumerate(GRID):
        body.append(f'<rect x="{lx + k * 22 - 2}" y="{ly - 11}" width="13" height="13" fill="{fill}"/>')
    body.append(mono(lx + 5 * 22 + 4, ly, "MORE", 11, DIM, 2))
    body.append(mono(30, ly, f"{num(s['total'])} CONTRIBUTIONS  //  {s['active']} ACTIVE DAYS", 11, G3, 2))
    css = f".sweep{{animation:sweep 9s linear infinite}}@keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({sweep_w}px)}}}}"
    label = f"Contribution grid for the last year: {num(s['total'])} contributions, {s['active']} active days."
    return document(w, h, "".join(body), css, label)


# ------------------------------------------------------------------------------------------------ main
def write(out, name, svg):
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(svg, encoding="utf-8")
    print(f"{out / name}  {len(svg) // 1024} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", type=Path, help="write banner, whoami and htop here")
    ap.add_argument("--live", type=Path, help="write signal and grid here (needs GITHUB_TOKEN)")
    ap.add_argument("--user", default=P["login"])
    ap.add_argument("--theme", choices=sorted(THEMES), default=P.get("theme", "matrix"))
    a = ap.parse_args()
    use_theme(a.theme)
    if not (a.static or a.live):
        ap.error("nothing to do: pass --static and/or --live")
    if a.static:
        cards = ([("banner.svg", banner_robot), ("whoami.svg", whoami_robot), ("recon.svg", recon)] if THEME == "robot"
                 else [("banner.svg", banner), ("whoami.svg", whoami), ("htop.svg", htop)]) + [("farm.svg", farm)]
        for name, make in cards:
            write(a.static, name, make())
    if a.live:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required for --live")
        s = summarize(fetch(a.user, token))
        write(a.live, "signal.svg", signal(s))
        write(a.live, "grid.svg", grid(s))


if __name__ == "__main__":
    main()
