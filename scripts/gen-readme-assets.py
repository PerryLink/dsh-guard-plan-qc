#!/usr/bin/env python3
"""README visuals for dsh-guard-plan-qc — drawn from this plugin's real checker.

Two figures, both read off the shipped material and source, not off a template:

  hero 1440x576 (Pillow, 4 files: zh/en x light/dark)
      The document the plugin reads, plus the one cell it zooms into. Row 1 of
      the configuration table states its quantity as "若干" — a quantity cell the
      parser cannot turn into a number. The zoomed cell, the numberOf() steps
      (full-width / thousands normalisation, unit stripping, regex), the GP-002
      finding with its row + column locator, and the skipped[] note all come
      from tests/fixtures/GP-002/GP-002-unsafe.json, the README's documented
      GP-002 example, and samples/quickstart/expected/result.json (skipped 5).

  flow 1100x660 (hand-written SVG, 2 files: light/dark)
      Grammar: a TWO-SIDED RECONCILIATION, not a row of nodes. The left panel is
      the expectation side (header declarations + the rule parameters, where
      factors[] and requiredCategories[] ship empty); the right panel is the
      actual side (rows[] with its five field lines). The six rules sit in the
      gutter as rule plates, each attached to the lines it compares:
        GP-001  requiredFields  -> each row's 品名 / 规格型号 / 配置数量 (bracket)
        GP-002  quantity cell, row-internal (no left operand)
        GP-003  headcount x factors -> quantity, gated: factors empty (dashed)
        GP-004  periodFrom/periodTo -> 发放日期
        GP-005  发放日期 -> 有效截止日期, row-internal (bracket)
        GP-006  requiredCategories -> 品名 / 规格型号, gated: list empty (dashed)
      Every rule ends in one of two outlets: issues[] (row + column + found /
      expected / fix) or skipped[] (reason). Config keys and severity caps are
      printed as commands/tokens, so one light/dark pair serves all five READMEs.

Text values come from the repository's own fixtures:
  tests/fixtures/GP-002/GP-002-unsafe.json   (安全帽 / V 型 黄色 / 若干 /
      2026-03-05, no 有效截止日期)
  README.md "材料格式" example               (绝缘手套 / 12kV / 40 / 2026-03-05 /
      2028-03-04; headcount 20; 2026-03-01..2026-03-31)
  rules/guard-plan-qc.yaml                   (GP-001..GP-006, kinds, severities)
  src/model.ts COLUMNS                       (column aliases; quantity units)
  src/check.ts                               (skip reasons, locators, outputs)
  samples/quickstart/expected/result.json    (issueCount 1, skippedCount 5)

Run once:  python scripts/gen-readme-assets.py
Requires:  Pillow + Windows fonts msyh.ttc / msyhbd.ttc / consola.ttf.
"""
from __future__ import annotations

import math
import os
from html import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "assets")

FONT_CJK = r"C:\Windows\Fonts\msyh.ttc"
FONT_CJK_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"
FONT_MONO_BOLD = r"C:\Windows\Fonts\consolab.ttf"
for _p in (FONT_CJK, FONT_CJK_BOLD, FONT_MONO, FONT_MONO_BOLD):
    if not os.path.exists(_p):
        raise SystemExit(f"FATAL: font missing: {_p}")

RADIUS = 22
SHADOW = 26

SKIN = {
    "light": dict(
        bg_from="#f9f6fd", bg_to="#e4eaf8",
        card="#ffffff", card_edge="#e6e2ef",
        text="#141419", sub="#4d5261", faint="#8f94a4",
        accent="#4B67B4", accent2="#16a34a",
        pill="#ece7f9", band="#f5f2fb", grid="#e7e4f0",
        mark="#b45309", mark_bg="#fdf3e9",
        shadow=(32, 26, 64), glow2="#7a68c9",
    ),
    "dark": dict(
        bg_from="#131a2a", bg_to="#0c1016",
        card="#1b2231", card_edge="#2e374b",
        text="#f0f3f9", sub="#a8b1c4", faint="#737b8d",
        accent="#8496f5", accent2="#3fb950",
        pill="#242d42", band="#202839", grid="#262f42",
        mark="#d9a441", mark_bg="#2a2216",
        shadow=(0, 0, 0), glow2="#8496f5",
    ),
}

FONT_FILES = {"cjk": FONT_CJK, "cjk_bold": FONT_CJK_BOLD,
              "mono": FONT_MONO, "mono_bold": FONT_MONO_BOLD}


def font(size: int, kind: str = "cjk_bold") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_FILES[kind], size)


def hx(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w: int, h: int, c1: str, c2: str) -> Image.Image:
    base = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(base)
    a, b = hx(c1), hx(c2)
    for y in range(h):
        t = 0.15 * (y / h) + 0.85 * (y / h) ** 1.35
        d.line([(0, y), (w, y)],
               fill=tuple(int(p + (q - p) * t) for p, q in zip(a, b)))
    return base


def glow(img: Image.Image, cx: int, cy: int, r: int, color: tuple,
         alpha: int = 40) -> Image.Image:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(9, 0, -1):
        rr = r * i / 9
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  fill=color + (int(alpha * (1 - i / 10)),))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def card(img: Image.Image, box: tuple, s: dict, radius: int = RADIUS,
         shadow: int = SHADOW, fill: str | None = None,
         edge: str | None = None) -> Image.Image:
    """A soft-shadowed rounded card on the gradient background."""
    x0, y0, x1, y1 = box
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for i in range(shadow, 0, -3):
        sd.rounded_rectangle([x0 - i // 5, y0 + i // 2, x1 + i // 5, y1 + i],
                             radius=radius + i // 5,
                             fill=s["shadow"] + (int(9 * (1 - i / shadow)),))
    base = Image.alpha_composite(img.convert("RGBA"),
                                 sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(box, radius=radius, fill=hx(fill or s["card"]),
                        outline=hx(edge or s["card_edge"]), width=2)
    return base.convert("RGB")


_SCRATCH = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def measure(text: str, size: int, kind: str) -> float:
    return _SCRATCH.textlength(text, font=font(size, kind))


def require_w(text: str, size: int, kind: str, max_w: float, what: str) -> None:
    """Fail loudly instead of shipping a clipped label."""
    w = measure(text, size, kind)
    if w > max_w + 0.4:
        raise SystemExit(
            f"FATAL: {what} overflows: {text!r} needs {w:.1f}px > {max_w}px")


def fit(text: str, kind: str, max_w: float, start: int, minimum: int) -> int:
    size = start
    while size > minimum:
        if measure(text, size, kind) <= max_w:
            return size
        size -= 1
    raise SystemExit(f"FATAL: text does not fit {max_w}px at >= {minimum}px: {text!r}")


def fit_lines(lines: list[str], kind: str, max_w: float, start: int,
              minimum: int) -> int:
    return min(fit(t, kind, max_w, start, minimum) for t in lines)


def wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
         maxw: float) -> list[str]:
    if " " in text:
        words, lines, cur = text.split(" "), [], ""
        for wd in words:
            cand = (cur + " " + wd) if cur else wd
            if d.textlength(cand, font=f) <= maxw or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) <= maxw or not cur:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def pill(img: Image.Image, xy: tuple[int, int], text: str, s: dict,
         size: int = 16, fg: str | None = None, bg: str | None = None,
         kind: str = "cjk_bold") -> tuple[int, int]:
    d = ImageDraw.Draw(img)
    f = font(size, kind)
    w = d.textlength(text, font=f)
    x, y = xy
    h = size + 20
    d.rounded_rectangle([x, y, x + w + 30, y + h], radius=h // 2,
                        fill=hx(bg or s["pill"]))
    d.text((x + 15, y + h / 2), text, font=f, fill=hx(fg or s["accent"]),
           anchor="lm")
    return int(x + w + 30), int(y + h)


def chip(img: Image.Image, xy: tuple[int, int], text: str, fg: str, bg: str,
         size: int = 11, kind: str = "cjk_bold", padx: int = 9,
         height: int = 20) -> int:
    d = ImageDraw.Draw(img)
    f = font(size, kind)
    w = d.textlength(text, font=f)
    x, y = xy
    d.rounded_rectangle([x, y, x + w + padx * 2, y + height],
                        radius=height // 2, fill=hx(bg))
    d.text((x + padx, y + height / 2), text, font=f, fill=hx(fg), anchor="lm")
    return int(w + padx * 2)


def dash_rect(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int],
              color: str, width: int = 2, dash: int = 7, gap: int = 5) -> None:
    x0, y0, x1, y1 = box
    for a, b in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
                 ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        n = int(dist // (dash + gap)) + 1
        for i in range(n):
            t0 = i * (dash + gap) / dist
            t1 = min((i * (dash + gap) + dash) / dist, 1.0)
            if t0 >= 1:
                break
            d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                    (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)],
                   fill=hx(color), width=width)


# ===========================================================================
# hero: 1440x576, the document + one zoomed cell + the finding it produces
# ===========================================================================
HERO = {
    "zh": dict(
        kicker="DeepSeek Harness 插件 · 核查器",
        value=["一份配置表，逐行逐栏核对", "差异落到行号与栏名"],
        sub=["只核对表格自身的齐备：填没填、数量是不是数字、",
             "日期在不在期间内——合规结论留给审核人。"],
        meta="GP-001..GP-006 · 规则包即数据 · skipped 逐条说明",
        foot="Apache-2.0 · PerryLink DSH plugin family",
        reg_title="配置表 · 某某厂房工程",
        reg_chip="只读材料",
        reg_meta="headcount 20 · 2026-03-01 → 2026-03-31 · 2 行",
        headers=["#", "品名", "规格型号", "配置数量"],
        widths=[28, 128, 172, 122],
        rows=[["1", "安全帽", "V 型 黄色", "若干"],
              ["2", "绝缘手套", "12kV", "40"]],
        zoom_label="配置数量 · 第 1 行",
        zoom_note="不是数字",
        parse_title="解析配置数量 · numberOf()",
        parse_steps=["① 全角 / 千分位归一", "② 剥离尾部单位", "③ 正则判定"],
        parse_result="「若干」→ undefined：不是数字（与数量 0 分开报）",
        issue_rule="GP-002", issue_sev="warn", issue_chip="issues[] 1",
        issue_where="第 1 行 · 配置数量",
        issue_found="发现：「若干」不是数字；应填：数字（可带单位，如 2双）",
        issue_fix="建议：改用数字填写，例如 2 或 2双",
        skip_note="skipped[] 5 · GP-003 / GP-006 清单未配置 · 未执行与无差异逐条写明",
        verdict="结论留给审核人",
    ),
    "en": dict(
        kicker="DeepSeek Harness plugin · checker",
        value=["One plan, checked row by row", "each finding: row + column"],
        sub=["Only the table's own completeness: fill-ins, numbers, dates.",
             "No compliance verdict — that stays with the reviewer."],
        meta="GP-001..GP-006 · the pack is data · every skip explained",
        foot="Apache-2.0 · PerryLink DSH plugin family",
        reg_title="PPE plan · Some Plant Project",
        reg_chip="read-only",
        reg_meta="headcount 20 · 2026-03-01 → 2026-03-31 · 2 rows",
        headers=["#", "Product", "Specification", "Qty"],
        widths=[28, 132, 168, 122],
        rows=[["1", "Safety helmet", "Type V yellow", "several"],
              ["2", "Insulating gloves", "12 kV", "40"]],
        zoom_label="Qty · row 1",
        zoom_note="not a number",
        parse_title="Parse the quantity · numberOf()",
        parse_steps=["① full-width / thousands", "② strip unit", "③ regex"],
        parse_result="「several」→ undefined: not a number (reported apart from 0)",
        issue_rule="GP-002", issue_sev="warn", issue_chip="issues[] 1",
        issue_where="row 1 · Qty",
        issue_found="Found: 「several」 is not a number · expected: a number, units allowed",
        issue_fix="Fix: write it as a number, e.g. 2 or 2 pairs",
        skip_note="skipped[] 5 · GP-003 / GP-006 lists empty · each entry carries its reason",
        verdict="verdict: the reviewer's",
    ),
}


def hero(lang: str, skin: str) -> None:
    s = SKIN[skin]
    H = HERO[lang]
    W, HT = 1440, 576
    img = gradient(W, HT, s["bg_from"], s["bg_to"])
    img = glow(img, 1180, 24, 430, hx(s["accent"]),
               24 if skin == "light" else 38)
    img = glow(img, 80, 580, 300, hx(s["glow2"]),
               10 if skin == "light" else 16)

    m = 64
    col_w = 600

    # ---- left column: kicker / title / value / sub / meta / footer -----------
    pill(img, (m, 52), H["kicker"], s, size=17)
    d = ImageDraw.Draw(img)

    title_size = fit("dsh-guard-plan-qc", "mono_bold", col_w, 58, 48)
    d.text((m - 2, 112), "dsh-guard-plan-qc",
           font=font(title_size, "mono_bold"), fill=hx(s["text"]))

    vf = fit_lines(H["value"], "cjk_bold", col_w, 42, 34)
    for i, line in enumerate(H["value"]):
        require_w(line, vf, "cjk_bold", col_w, "hero value")
        d.text((m, 214 + i * 54), line, font=font(vf, "cjk_bold"),
               fill=hx(s["text"]))

    sf = fit_lines(H["sub"], "cjk", col_w, 22, 19)
    for i, line in enumerate(H["sub"]):
        require_w(line, sf, "cjk", col_w, "hero sub")
        d.text((m + 1, 344 + i * 32), line, font=font(sf, "cjk"),
               fill=hx(s["sub"]))

    require_w(H["meta"], 19, "cjk", col_w, "hero meta")
    require_w(H["foot"], 16, "cjk", col_w, "hero footer")
    d.text((m + 1, 424), H["meta"], font=font(19, "cjk"), fill=hx(s["faint"]))
    d.line([m + 1, 470, m + col_w - 4, 470], fill=hx(s["grid"]), width=2)
    d.text((m + 1, 486), H["foot"], font=font(16, "cjk"), fill=hx(s["faint"]))

    # ---- right: the material card -------------------------------------------
    img = card(img, (688, 40, 1376, 520), s, radius=RADIUS, shadow=SHADOW)
    d = ImageDraw.Draw(img)
    d.text((712, 60), H["reg_title"], font=font(17, "cjk_bold"),
           fill=hx(s["accent"]))
    cw = measure(H["reg_chip"], 11, "cjk")
    chip(img, (1352 - int(cw) - 18, 54), H["reg_chip"], s["accent"],
         s["pill"], size=11)
    d = ImageDraw.Draw(img)
    require_w(H["reg_meta"], 13, "cjk", 620, "register meta")
    d.text((712, 88), H["reg_meta"], font=font(13, "cjk"), fill=hx(s["sub"]))
    d.line([712, 112, 1352, 112], fill=hx(s["grid"]), width=1)

    # mini table: # / 品名 / 规格型号 / 配置数量
    x0, top = 712, 124
    xs, acc = [], x0
    for w in H["widths"]:
        xs.append(acc)
        acc += w
    x_end = acc
    d.rounded_rectangle([x0 - 8, top, x_end + 8, top + 32], radius=9,
                        fill=hx(s["band"]))
    for i, head in enumerate(H["headers"]):
        hs = 12 if lang == "zh" else 11.5
        require_w(head, hs, "cjk_bold", H["widths"][i] - 14, "hero header")
        d.text((xs[i] + 8, top + 9), head, font=font(hs, "cjk_bold"),
               fill=hx(s["sub"]))
    # the zoomed cell: row 1 quantity "若干" — amber, dashed, corner ticks.
    # Drawn before the cell text so the value stays on top of the highlight.
    row_h = 44
    cell = (xs[3] - 4, top + 32 + 3, xs[3] + H["widths"][3] - 6,
            top + 32 + row_h - 3)
    d.rounded_rectangle(cell, radius=9, fill=hx(s["mark_bg"]))
    dash_rect(d, cell, s["mark"], width=2, dash=6, gap=4)
    for (cx, cy, dx, dy) in ((cell[0], cell[1], 7, 7),
                             (cell[2], cell[1], -7, 7),
                             (cell[0], cell[3], 7, -7),
                             (cell[2], cell[3], -7, -7)):
        d.line([(cx, cy), (cx + dx, cy)], fill=hx(s["mark"]), width=2)
        d.line([(cx, cy), (cx, cy + dy)], fill=hx(s["mark"]), width=2)

    for r, row in enumerate(H["rows"]):
        ry = top + 32 + r * row_h
        for i, value in enumerate(row):
            f = font(13, "cjk") if i == 0 else font(14, "cjk")
            fill = s["mark"] if (r == 0 and i == 3) else s["text"]
            require_w(value, 13 if i == 0 else 14, "cjk",
                      H["widths"][i] - 16, "hero cell")
            d.text((xs[i] + 8, ry + 13), value, font=f, fill=hx(fill))
        if r < len(H["rows"]) - 1:
            d.line([x0, ry + row_h, x_end, ry + row_h], fill=hx(s["grid"]),
                   width=1)

    # zoom tile
    img = card(img, (1180, 124, 1352, 244), s, radius=18, shadow=18)
    d = ImageDraw.Draw(img)
    require_w(H["zoom_label"], 11, "cjk", 150, "zoom label")
    d.text((1198, 140), H["zoom_label"], font=font(11, "cjk"), fill=hx(s["faint"]))
    zf = fit(H["rows"][0][3], "cjk_bold", 112, 36, 24)
    d.text((1266, 190), H["rows"][0][3], font=font(zf, "cjk_bold"),
           fill=hx(s["mark"]), anchor="mm")
    require_w(H["zoom_note"], 11, "cjk", 150, "zoom note")
    d.text((1198, 228), H["zoom_note"], font=font(11, "cjk"), fill=hx(s["mark"]))
    # dashed leader from the cell to the tile
    for px in range(x_end + 2, 1180, 10):
        d.line([(px, 178), (min(px + 5, 1180), 178)], fill=hx(s["mark"]), width=2)

    # parse strip
    img = card(img, (712, 260, 1352, 360), s, radius=18, shadow=20)
    d = ImageDraw.Draw(img)
    d.text((730, 278), H["parse_title"], font=font(12.5, "cjk_bold"),
           fill=hx(s["text"]))
    px = 730
    for i, step in enumerate(H["parse_steps"]):
        tw = chip(img, (px, 296), step, s["sub"], s["band"], size=11,
                  height=24, padx=10)
        d = ImageDraw.Draw(img)
        px += tw + 10
        if i < len(H["parse_steps"]) - 1:
            d.text((px, 308), "→", font=font(12, "cjk"), fill=hx(s["faint"]),
                   anchor="lm")
            px += 20
    require_w(H["parse_result"], 12.5, "cjk", 610, "parse result")
    d.text((730, 336), H["parse_result"], font=font(12.5, "cjk"),
           fill=hx(s["mark"]))

    # issue strip
    img = card(img, (712, 376, 1352, 452), s, radius=18, shadow=20)
    d = ImageDraw.Draw(img)
    d.text((730, 392), H["issue_rule"], font=font(13.5, "mono_bold"),
           fill=hx(s["accent"]))
    w = measure(H["issue_rule"], 13.5, "mono_bold")
    chip(img, (730 + int(w) + 8, 390), H["issue_sev"], s["mark"], s["mark_bg"],
         size=10.5, height=18)
    d = ImageDraw.Draw(img)
    require_w(H["issue_where"], 12, "cjk", 160, "issue locator")
    d.text((730 + int(w) + 62, 392), H["issue_where"], font=font(12, "cjk"),
           fill=hx(s["sub"]))
    # events count chip on the right of the issue strip
    cw = measure(H["issue_chip"], 10.5, "cjk")
    chip(img, (1334 - int(cw) - 18, 388), H["issue_chip"], s["accent"],
         s["pill"], size=10.5, height=20)
    d = ImageDraw.Draw(img)
    require_w(H["issue_found"], 12.5, "cjk", 610, "issue found")
    require_w(H["issue_fix"], 11.5, "cjk", 610, "issue fix")
    d.text((730, 414), H["issue_found"], font=font(12.5, "cjk"),
           fill=hx(s["sub"]))
    d.text((730, 434), H["issue_fix"], font=font(11.5, "cjk"),
           fill=hx(s["faint"]))

    # skipped / verdict strip
    d.rounded_rectangle([712, 468, 1352, 504], radius=18, fill=hx(s["band"]))
    require_w(H["skip_note"], 11.5, "cjk", 470, "skip note")
    d.text((730, 486), H["skip_note"], font=font(11.5, "cjk"),
           fill=hx(s["sub"]), anchor="lm")
    require_w(H["verdict"], 12, "cjk", 220, "verdict")
    d.text((1334, 486), H["verdict"], font=font(12, "cjk_bold"),
           fill=hx(s["accent2"]), anchor="rm")

    name = f"dsh-guard-plan-qc-hero-{lang}-{skin}.webp"
    img.save(os.path.join(OUT, name), "WEBP", quality=92, method=6)
    print(f"wrote {name} ({W}x{HT})")


# ===========================================================================
# flow: 1100x660, two-sided reconciliation
# ===========================================================================
FONT_CSS_CJK = ("'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',"
                "'Source Han Sans SC',sans-serif")
FONT_CSS_MONO = "'Consolas','SFMono-Regular','Menlo',ui-monospace,monospace"

FLOW_SKIN = {
    "light": dict(
        bg_from="#f9f6fd", bg_to="#e4eaf8",
        panel="#ffffff", edge="#e6e2ef", band="#f5f2fb", band_alt="#faf8fe",
        text="#141419", sub="#4d5261", faint="#8f94a4",
        accent="#4B67B4", accent2="#16a34a", rule="#dcd8ea",
        mark="#b45309", mark_bg="#fdf3e9",
        shadow="0.10",
    ),
    "dark": dict(
        bg_from="#131a2a", bg_to="#0c1016",
        panel="#1b2231", edge="#2e374b", band="#202839", band_alt="#1e2534",
        text="#f0f3f9", sub="#a8b1c4", faint="#737b8d",
        accent="#8496f5", accent2="#3fb950", rule="#2b3348",
        mark="#d9a441", mark_bg="#2a2216",
        shadow="0.45",
    ),
}

# rule id, severity cap chip, relation line, side, left anchor y, right anchor y
# Anchors are the field-line baselines in the two panels (see the drawing code):
#   left  193 subject · 217 headcount · 241 period · 326 requiredFields
#         374 factors · 418 requiredCategories
#   right (transposed table) 230 品名 · 256 规格型号 · 282 配置数量
#         308 发放日期 · 334 有效截止日期
RULES = [
    ("GP-001", "≤ info", "每行三栏是否填齐", "both", 326, (230, 282)),
    ("GP-002", "≤ warn", "配置数量须为正数", "right", None, 282),
    ("GP-003", "≤ info", "人数 × 基数（清单空）", "left", 374, None),
    ("GP-004", "≤ warn", "发放日期落在期间内", "both", 241, 308),
    ("GP-005", "≤ warn", "截止日期晚于发放日", "right", None, (308, 334)),
    ("GP-006", "≤ info", "覆盖类别（清单空）", "left", 418, None),
]


class Svg:
    """Tiny SVG writer that measures every label before it is emitted."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.overflows: list[str] = []

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def text(self, x: float, y: float, content: str, size: float, fill: str, *,
             anchor: str = "start", weight: int | None = None,
             mono: bool = False, max_w: float | None = None,
             opacity: float | None = None, tracking: float | None = None) -> None:
        kind = ("mono" if mono else "cjk") + ("_bold" if weight else "")
        if mono and weight:
            kind = "mono_bold"
        if max_w is not None:
            w = measure(content, size, kind)
            if tracking:
                w += tracking * max(len(content) - 1, 0)
            if w > max_w + 0.4:
                self.overflows.append(
                    f"{content!r} needs {w:.1f}px > {max_w}px")
        family = FONT_CSS_MONO if mono else FONT_CSS_CJK
        attrs = [f'x="{x}"', f'y="{y}"', f'fill="{fill}"',
                 f'font-family="{family}"', f'font-size="{size}"']
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity}"')
        if tracking:
            attrs.append(f'letter-spacing="{tracking}"')
        self.add(f'<text {" ".join(attrs)}>{escape(content)}</text>')

    def rect(self, x: float, y: float, w: float, h: float, *, fill: str,
             rx: float = 0, stroke: str | None = None, sw: float = 1.5,
             shadow: bool = False, dash: str | None = None,
             opacity: float | None = None) -> None:
        attrs = [f'x="{x}"', f'y="{y}"', f'width="{w}"', f'height="{h}"']
        if rx:
            attrs.append(f'rx="{rx}"')
        attrs.append(f'fill="{fill}"')
        if stroke:
            attrs.append(f'stroke="{stroke}"')
            attrs.append(f'stroke-width="{sw}"')
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity}"')
        if shadow:
            attrs.append('filter="url(#soft)"')
        self.add(f'<rect {" ".join(attrs)}/>')

    def line(self, x1: float, y1: float, x2: float, y2: float, *, stroke: str,
             sw: float = 1.5, dash: str | None = None,
             marker: str | None = None, opacity: float | None = None) -> None:
        attrs = [f'x1="{x1}"', f'y1="{y1}"', f'x2="{x2}"', f'y2="{y2}"',
                 f'stroke="{stroke}"', f'stroke-width="{sw}"',
                 'stroke-linecap="round"']
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if marker:
            attrs.append(f'marker-end="url(#{marker})"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity}"')
        self.add(f'<line {" ".join(attrs)}/>')

    def path(self, d: str, *, stroke: str, sw: float = 1.5,
             marker: str | None = None, dash: str | None = None,
             fill: str = "none", opacity: float | None = None) -> None:
        attrs = [f'd="{d}"', f'fill="{fill}"', f'stroke="{stroke}"',
                 f'stroke-width="{sw}"', 'stroke-linecap="round"',
                 'stroke-linejoin="round"']
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if marker:
            attrs.append(f'marker-end="url(#{marker})"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity}"')
        self.add(f'<path {" ".join(attrs)}/>')

    def circle(self, cx: float, cy: float, r: float, *, fill: str,
               stroke: str | None = None, sw: float = 1.5) -> None:
        attrs = [f'cx="{cx}"', f'cy="{cy}"', f'r="{r}"', f'fill="{fill}"']
        if stroke:
            attrs.append(f'stroke="{stroke}"')
            attrs.append(f'stroke-width="{sw}"')
        self.add(f'<circle {" ".join(attrs)}/>')

    def chip(self, x_right: float, y: float, label: str, fg: str, bg: str,
             *, size: float = 11, pad: float = 9, height: float = 20,
             mono: bool = False, weight: int | None = None) -> float:
        """A pill anchored on its right edge; returns its left edge."""
        kind = "mono" if mono else "cjk"
        if weight:
            kind += "_bold"
        w = measure(label, size, kind) + pad * 2
        x = x_right - w
        self.rect(x, y, w, height, fill=bg, rx=height / 2)
        self.text(x + pad, y + height / 2 + size * 0.34, label, size, fg,
                  anchor="start", weight=weight, mono=mono)
        return x

    def svg(self, w: int, h: int, label: str) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
                f'height="{h}" viewBox="0 0 {w} {h}" role="img" '
                f'aria-label="{escape(label)}">'
                f'<title>{escape(label)}</title>')
        return "\n".join([head, *self.parts, "</svg>"]) + "\n"


def flow_svg(skin: str) -> str:
    s = FLOW_SKIN[skin]
    W, H = 1100, 660
    v = Svg()

    v.add("<defs>")
    v.add(f'<linearGradient id="bg" x1="0" y1="0" x2="0.3" y2="1">'
          f'<stop offset="0" stop-color="{s["bg_from"]}"/>'
          f'<stop offset="1" stop-color="{s["bg_to"]}"/></linearGradient>')
    v.add(f'<filter id="soft" x="-30%" y="-30%" width="160%" height="170%">'
          f'<feDropShadow dx="0" dy="7" stdDeviation="9" '
          f'flood-color="#16122c" flood-opacity="{s["shadow"]}"/></filter>')
    v.add('</defs>')
    v.add(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    # ---- header -------------------------------------------------------------
    v.text(44, 54, "dsh-guard-plan-qc", 27, s["text"], weight=700, mono=True,
           max_w=520)
    v.chip(1056, 32, "rules/guard-plan-qc.yaml · v2026.1 · 6 条",
           s["accent"], s["panel"], size=11.5, pad=12, height=26)
    v.text(44, 82,
           "六条规则把「表头声明 + 规则参数」与「行内容」按栏目比对；差异只回到行号与栏名，"
           "未配置的清单让规则停在 skipped。",
           13.5, s["sub"], max_w=840)

    # ---- panels -------------------------------------------------------------
    LP = (44, 128, 344, 492)
    RP = (744, 128, 1056, 492)
    v.rect(LP[0], LP[1], LP[2] - LP[0], LP[3] - LP[1], fill=s["panel"], rx=20,
           stroke=s["edge"], sw=1.5, shadow=True)
    v.rect(RP[0], RP[1], RP[2] - RP[0], RP[3] - RP[1], fill=s["panel"], rx=20,
           stroke=s["edge"], sw=1.5, shadow=True)

    # left panel: expectation side
    v.text(62, 155, "期望侧 · 表头与规则参数", 13, s["text"], weight=700,
           max_w=210)
    v.chip(326, 138, "随包 / 本机构", s["accent"], s["band"], size=10.5,
           pad=8, height=18)
    v.line(62, 168, 326, 168, stroke=s["rule"], sw=1)

    left_rows = [
        ("subject", "某某厂房工程", 193, "cjk"),
        ("headcount", "20", 217, "mono"),
        ("period", "2026-03-01 → 2026-03-31", 241, "mono"),
    ]
    for key, value, y, kind in left_rows:
        v.text(62, y, key, 11, s["faint"], mono=True, max_w=120)
        if kind == "mono":
            v.text(326, y, value, 11.5, s["text"], anchor="end", mono=True,
                   max_w=320 - (62 + measure(key, 11, "mono") + 8))
        else:
            v.text(326, y, value, 12.5, s["text"], anchor="end",
                   max_w=320 - (62 + measure(key, 11, "mono") + 8))

    v.line(62, 262, 326, 262, stroke=s["rule"], sw=1)
    v.text(62, 286, "规则参数 · 默认 / 本机构配置", 11.5, s["faint"],
           weight=700, max_w=250)

    v.text(62, 308, "requiredFields", 11, s["faint"], mono=True, max_w=120)
    v.text(62, 326, "[品名 · 规格型号 · 配置数量]", 11.5, s["sub"],
           max_w=264)
    v.text(62, 356, "factors", 11, s["faint"], mono=True, max_w=120)
    v.text(62, 374, "[] · 未配置", 11.5, s["mark"], max_w=150)
    v.text(62, 400, "requiredCategories", 11, s["faint"], mono=True, max_w=130)
    v.text(62, 418, "[] · 未配置", 11.5, s["mark"], max_w=150)
    v.text(62, 446, "两条清单出厂为空：未配置即 skipped，", 11, s["faint"],
           max_w=264)
    v.text(62, 460, "绝不静默通过；requiredFields 可换成本机构表式。", 11,
           s["faint"], max_w=280)

    # right panel: the actual side, drawn as the table transposed —
    # field names down the left, one column per material row.
    v.text(762, 155, "实际侧 · 行内容 rows[]", 13, s["text"], weight=700,
           max_w=220)
    v.chip(1038, 138, "只读", s["accent"], s["band"], size=10.5, pad=8, height=18)
    v.line(762, 168, 1038, 168, stroke=s["rule"], sw=1)

    COL_F, COL_R1, COL_R2 = 762, 866, 966
    RIGHT_X = 1040
    v.rect(752, 180, 296, 26, fill=s["band"], rx=8)
    v.text(COL_F, 197, "栏目", 11, s["faint"], max_w=96)
    v.text(COL_R1 + 50, 197, "第 1 行", 11.5, s["accent"], weight=700,
           anchor="middle", max_w=94)
    v.text(COL_R2 + 40, 197, "第 2 行", 11.5, s["accent"], weight=700,
           anchor="middle", max_w=72)
    rows = [
        ("品名", "安全帽", "绝缘手套", "cjk", "cjk"),
        ("规格型号", "V 型 黄色", "12kV", "cjk", "cjk"),
        ("配置数量", "若干", "40", "mark", "mono"),
        ("发放日期", "2026-03-05", "2026-03-05", "mono", "mono"),
        ("有效截止日期", "（未填）", "2028-03-04", "faint", "mono"),
    ]
    for i, (key, r1, r2, t1, t2) in enumerate(rows):
        y = 230 + i * 26
        if i % 2 == 1:
            v.rect(752, y - 18, 296, 26, fill=s["band_alt"])
        v.text(COL_F, y, key, 11.5, s["faint"], max_w=100)
        fill1 = (s["mark"] if t1 == "mark" else
                 s["faint"] if t1 == "faint" else s["text"])
        fill2 = s["text"]
        v.text(958, y, r1, 12, fill1, anchor="end",
               mono=(t1 == "mono"))
        v.text(RIGHT_X, y, r2, 12, fill2, anchor="end",
               mono=(t2 == "mono"))
    v.line(762, 348, 1038, 348, stroke=s["rule"], sw=1)
    v.text(762, 372, "只读材料：原件永不修改", 11, s["faint"], max_w=270)
    v.text(762, 390, "行 = 一种用品；列名按别名归一", 11, s["faint"],
           max_w=270)
    v.text(762, 408, "名称 · 数量 · 领用日期 · 有效期至", 11, s["faint"],
           max_w=270)
    v.text(762, 436, "每条差异回到 行号 + 栏名", 11.5, s["accent"],
           max_w=270)

    # ---- connectors (under the plates) --------------------------------------
    LX0, LX1 = LP[0], LP[2]
    RX0, RX1 = RP[0], RP[2]
    LBUS, RBUS = 372, 716
    PX0, PW, PH = 452, 196, 46
    PITCH, PY0 = 55, 148

    def left_anchor(y: float, dashed: bool) -> None:
        dash = "5 4" if dashed else None
        v.line(LX1, y, LBUS, y, stroke=s["accent"], sw=1.5, dash=dash,
               opacity=0.85)
        if dashed:
            v.circle(LX1, y, 3.2, fill=s["panel"], stroke=s["accent"], sw=1.5)
        else:
            v.circle(LX1, y, 3.2, fill=s["accent"])

    def right_anchor(y: float, dashed: bool = False) -> None:
        dash = "5 4" if dashed else None
        v.line(RBUS, y, RX0, y, stroke=s["accent"], sw=1.5, dash=dash,
               opacity=0.85)
        if dashed:
            v.circle(RX0, y, 3.2, fill=s["panel"], stroke=s["accent"], sw=1.5)
        else:
            v.circle(RX0, y, 3.2, fill=s["accent"])

    def bracket(edge_x: float, ys: tuple[float, float], inward: int) -> None:
        """A vertical bracket outside a panel edge, ticks pointing inward."""
        y1, y2 = ys
        v.line(edge_x, y1 - 6, edge_x, y2 + 6, stroke=s["accent"], sw=1.5,
               opacity=0.8)
        v.line(edge_x, y1, edge_x + inward, y1, stroke=s["accent"], sw=1.5,
               opacity=0.8)
        v.line(edge_x, y2, edge_x + inward, y2, stroke=s["accent"], sw=1.5,
               opacity=0.8)

    # left-row connectors: panel edge -> bus -> plate
    left_specs = []
    for i, (rid, cap, rel, side, ly, ry) in enumerate(RULES):
        if side in ("left", "both"):
            left_specs.append((ly, i, side == "left"))
    for y, i, dashed in left_specs:
        left_anchor(y, dashed)
    # vertical bus segments + stubs into every plate that has a left operand
    for i, (rid, cap, rel, side, ly, ry) in enumerate(RULES):
        if side not in ("left", "both"):
            continue
        mid = PY0 + i * PITCH + PH / 2
        v.line(LBUS, ly, LBUS, mid, stroke=s["accent"], sw=1.5,
               dash="5 4" if side == "left" else None, opacity=0.65)
        v.line(LBUS, mid, PX0, mid, stroke=s["accent"], sw=1.5,
               dash="5 4" if side == "left" else None, opacity=0.85)

    # right-row connectors: bracket or single anchor on the row panel
    for i, (rid, cap, rel, side, ly, ry) in enumerate(RULES):
        if side not in ("right", "both"):
            continue
        mid = PY0 + i * PITCH + PH / 2
        if isinstance(ry, tuple):
            bracket(RX0 - 8, ry, 8)
            anchor_y = (ry[0] + ry[1]) / 2
            v.line(RBUS, anchor_y, RX0 - 8, anchor_y, stroke=s["accent"],
                   sw=1.5, opacity=0.85)
        else:
            anchor_y = ry
            right_anchor(ry)
        v.line(RBUS, anchor_y, RBUS, mid, stroke=s["accent"], sw=1.5,
               opacity=0.65)
        v.line(PX0 + PW, mid, RBUS, mid, stroke=s["accent"], sw=1.5,
               opacity=0.85)

    # ---- rule plates --------------------------------------------------------
    for i, (rid, cap, rel, side, ly, ry) in enumerate(RULES):
        y = PY0 + i * PITCH
        gated = side == "left" and rid in ("GP-003", "GP-006")
        v.rect(PX0, y, PW, PH, fill=s["panel"], rx=14, stroke=s["accent"],
               sw=1.5, shadow=True, dash="5 4" if gated else None)
        v.text(PX0 + 14, y + 19, rid, 13.5, s["text"], weight=700, mono=True,
               max_w=90)
        v.chip(PX0 + PW - 12, y + 6, cap,
               s["mark"] if "warn" in cap else s["accent"], s["band"],
               size=10.5, pad=7, height=18, weight=700)
        v.text(PX0 + 14, y + 38, rel, 13, s["sub"], max_w=PW - 28)

    # ---- legend -------------------------------------------------------------
    v.text(544, 485,
           "实线 = 读到的两侧；虚线 = 清单空 → skipped；括号 = 同组栏目",
           11, s["faint"], anchor="middle", max_w=400)

    # ---- outputs ------------------------------------------------------------
    v.rect(44, 508, 484, 92, fill=s["panel"], rx=18, stroke=s["edge"],
           sw=1.5, shadow=True)
    v.text(62, 532, "issues[]", 14, s["accent"], weight=700, mono=True)
    v.chip(510, 518, "行号 + 栏名", s["accent"], s["band"], size=10.5, pad=8,
           height=18)
    v.text(62, 556, "GP-002 · 第 1 行 · 配置数量「若干」不是数字", 11.5,
           s["text"], max_w=450)
    v.text(62, 576, "应填：数字（可带单位，如 2双）；建议：改成 2 或 2双", 11,
           s["sub"], max_w=450)
    v.text(62, 592, "issue 还带 id · ruleId · severity · locator · basis",
           11, s["faint"], max_w=450)

    v.rect(548, 508, 364, 92, fill=s["panel"], rx=18, stroke=s["edge"],
           sw=1.5, shadow=True)
    v.text(566, 532, "skipped[]", 14, s["sub"], weight=700, mono=True)
    v.chip(894, 518, "逐条原因", s["sub"], s["band"], size=10.5, pad=8, height=18)
    v.text(566, 556, "GP-003 · factors 未配置（清单出厂为空）", 11,
           s["sub"], max_w=330)
    v.text(566, 574, "GP-006 · requiredCategories 未配置", 11, s["sub"],
           max_w=330)
    v.text(566, 592, "未执行 ≠ 通过；无差异同样记录在案", 11, s["faint"],
           max_w=330)

    v.rect(932, 508, 124, 92, fill=s["panel"], rx=18, stroke=s["accent"],
           sw=1.6, shadow=True)
    v.text(950, 532, "审核人", 13, s["text"], weight=700, max_w=90)
    v.text(950, 556, "结论不在", 11, s["sub"], max_w=90)
    v.text(950, 572, "报告里", 11, s["sub"], max_w=90)
    v.text(950, 590, "只列差异", 11, s["faint"], max_w=90)

    # ---- footer -------------------------------------------------------------
    v.line(44, 614, 1056, 614, stroke=s["rule"], sw=1)
    v.text(44, 632,
           "严重级跟着证据走：derived-from-principle ≤ warn · "
           "institutional-configuration ≤ info；excerpt 写明条文本次未取得，绝不伪造引文",
           11.2, s["sub"], max_w=1012)
    v.text(44, 650,
           "config：rulesFile · disabledRules · onlyRules · skipNotes · timeoutMs ｜ "
           "列名别名归一（名称 · 数量 · 领用日期 · 有效期至）· 只读材料 · 无网络",
           11, s["faint"], max_w=1012)

    if v.overflows:
        raise SystemExit("FATAL: SVG label overflow:\n  " + "\n  ".join(v.overflows))
    return v.svg(
        W, H,
        "dsh-guard-plan-qc 结构图：左侧是表头声明与规则参数（requiredFields、factors、"
        "requiredCategories），右侧是行内容 rows[] 的逐栏字段；中间六块规则牌以跨栏线相连，"
        "GP-001、GP-004 跨两侧读取，GP-002、GP-005 在行内自洽，GP-003、GP-006 因清单出厂为空"
        "停在 skipped；出口为 issues[] 与 skipped[]，结论留给审核人")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for skin in ("light", "dark"):
        for lang in ("zh", "en"):
            hero(lang, skin)
        name = f"dsh-guard-plan-qc-flow-v5-{skin}.svg"
        with open(os.path.join(OUT, name), "w", encoding="utf-8",
                  newline="\n") as fh:
            fh.write(flow_svg(skin))
        print(f"wrote {name} (1100x660)")


if __name__ == "__main__":
    main()
