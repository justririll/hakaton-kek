#!/usr/bin/env python3
"""Сборка колоды защиты в PowerPoint.

Слайды здесь настоящие: текстовые блоки правятся, фигуры остаются фигурами,
в области notes лежит текст докладчика. Это не печать HTML-версии в картинки.

Три вещи, на которых такая сборка обычно разваливается, решены явно:

1. «Сколько строк займёт абзац». Без ответа на этот вопрос блок под абзацем
   встаёт наугад — отсюда и налезающий текст, и дыры. Ширины символов и высота
   строки лежат в metrics.json (см. tools/make_metrics.py); все отступы по
   вертикали считаются, а не подбираются.
2. Высота строки при одинарном интервале — это НЕ кегль. И PowerPoint, и
   LibreOffice берут её из hhea (восходящая + нисходящая + зазор), около 1,22
   кегля для Calibri. Множитель line_spacing домножает уже её.
3. Гарнитуры. python-pptx пишет только `a:latin`, и на части систем под
   кириллицу подставляется шрифт по умолчанию; set_face() пишет ещё `a:ea` и
   `a:cs`. Взяты те, что есть на любой машине с PowerPoint: Georgia, Calibri,
   Consolas.

Запуск:  python build_pptx.py [--out vitdashboard-7min.pptx]
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.parts.image import Image
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
PNG = HERE / "shots" / "pptx"

# ── палитра ───────────────────────────────────────────────────────────────────
# Те же значения, что у витрины: бумажный фон, три ступени чернил, две линейки.

PAPER = RGBColor(0xF2, 0xEF, 0xE8)
PANEL = RGBColor(0xFC, 0xFA, 0xF6)
PANEL2 = RGBColor(0xF7, 0xF4, 0xEC)
INK = RGBColor(0x1B, 0x1A, 0x17)
INK2 = RGBColor(0x56, 0x53, 0x4A)
INK3 = RGBColor(0x84, 0x80, 0x6F)
RULE = RGBColor(0xE3, 0xDE, 0xD3)
RULE2 = RGBColor(0xD3, 0xCC, 0xBC)

# Тёмный разворот — один на всю колоду, на слайде про деньги.
D_PAPER = RGBColor(0x1B, 0x1A, 0x17)
D_PANEL = RGBColor(0x26, 0x25, 0x20)
D_INK = RGBColor(0xF2, 0xEF, 0xE8)
D_INK2 = RGBColor(0xB4, 0xB0, 0xA2)
D_INK3 = RGBColor(0x8B, 0x86, 0x77)
D_RULE = RGBColor(0x3B, 0x39, 0x31)
D_RULE2 = RGBColor(0x4C, 0x49, 0x3F)

# Кластерные цвета витрины: проверены на различимость при дальтонизме,
# поэтому и в колоде группы кодируются ими же, а не «какими получится».
C0 = RGBColor(0x2B, 0x64, 0xA8)  # индиго
C1 = RGBColor(0xA7, 0x6C, 0xB5)  # слива
C2 = RGBColor(0xAA, 0x51, 0x31)  # терракота
C3 = RGBColor(0x9E, 0x96, 0x2A)  # олива
C4 = RGBColor(0x07, 0x8E, 0x7D)  # морская зелень
WARN = RGBColor(0xA8, 0x76, 0x0A)
WARN_BG = RGBColor(0xF7, 0xF1, 0xE4)
WARN_LINE = RGBColor(0xDC, 0xCB, 0xA6)

SERIF = "Georgia"
SANS = "Calibri"
MONO = "Consolas"


@dataclass(frozen=True)
class Skin:
    """Цвета одного разворота: светлого или тёмного."""

    paper: RGBColor
    panel: RGBColor
    ink: RGBColor
    ink2: RGBColor
    ink3: RGBColor
    rule: RGBColor
    rule2: RGBColor


LIGHT = Skin(PAPER, PANEL, INK, INK2, INK3, RULE, RULE2)
DARK = Skin(D_PAPER, D_PANEL, D_INK, D_INK2, D_INK3, D_RULE, D_RULE2)
S = LIGHT


@contextmanager
def skin(value: Skin):
    global S
    previous, S = S, value
    try:
        yield value
    finally:
        S = previous


# ── сетка ─────────────────────────────────────────────────────────────────────

W, H = 13.333, 7.5
M = 0.62                 # боковое поле
TOP = 0.52               # верх надзаголовка
CONTENT_W = W - 2 * M
BODY_BOT = 6.60          # ниже этой линии содержимое не опускается
FOOT_Y = 6.98
PROG_Y = 6.80            # линейка хода выступления

GUTTER = 0.36            # колонок между блоками
PAD = 0.24               # внутреннее поле панели

# Кегли: чем меньше ступеней, тем спокойнее колода.
DISPLAY = 50.0
H1 = 30.0
H1_LONG = 26.5
H2 = 16.5
LEDE = 16.5
BODY = 13.0
SMALL = 11.5
NOTE = 10.0
MICRO = 9.0


def px(value: float) -> float:
    """Пиксель макета 1280×720 в дюймах слайда 13,333×7,5."""
    return value * W / 1280


# ── метрики текста ────────────────────────────────────────────────────────────

_METRICS = json.loads((HERE / "metrics.json").read_text(encoding="utf-8"))
_FACE_KEY = {SANS: "sans", SERIF: "serif", MONO: "mono"}


def _table(face: str, bold: bool) -> dict[str, float]:
    return _METRICS["faces"][_FACE_KEY[face]]["bold" if bold else "regular"]


def line_height(size: float, face: str = SANS, line: float = 1.0) -> float:
    """Высота строки в дюймах при заданном множителе интервала."""
    return size * _METRICS["line"][_FACE_KEY[face]] * line / 72


def text_w(text: str, size: float, face: str = SANS, bold: bool = False, spacing: float = 0.0) -> float:
    """Ширина строки в дюймах."""
    table = _table(face, bold)
    fallback = _METRICS["fallback"]
    em = sum(table.get(ch, fallback) for ch in text)
    return em * size / 72 + spacing * len(text) / 72


def _chars(chunks) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for chunk in chunks:
        text, bold = (chunk[0], True) if isinstance(chunk, tuple) else (chunk, False)
        out.extend((ch, bold) for ch in text)
    return out


def count_lines(chunks, width: float, size: float, face: str = SANS, spacing: float = 0.0) -> int:
    """Сколько строк займёт абзац из кусков разного начертания.

    Жадный перенос по словам — ровно то, что делает и PowerPoint. Кернинг не
    учитывается: он сужает строку, то есть ошибка всегда в запас.
    """
    table_r, table_b = _table(face, False), _table(face, True)
    fallback = _METRICS["fallback"]
    scale = size / 72

    def advance(ch: str, bold: bool) -> float:
        table = table_b if bold else table_r
        return (table.get(ch, fallback) + spacing / size) * scale

    tokens: list[list[tuple[str, bool]] | None] = []
    current: list[tuple[str, bool]] = []
    for ch, bold in _chars(chunks):
        if ch in "  ":
            if current:
                tokens.append(current)
                current = []
            tokens.append(None)
        else:
            current.append((ch, bold))
    if current:
        tokens.append(current)

    lines, used, pending_space = 1, 0.0, False
    space = advance(" ", False)
    for token in tokens:
        if token is None:
            pending_space = used > 0
            continue
        word = sum(advance(ch, bold) for ch, bold in token)
        gap = space if pending_space else 0.0
        if used > 0 and used + gap + word > width + 1e-6:
            lines += 1
            used = word
        else:
            used += gap + word
        pending_space = False
    return lines


def block_h(chunks, width: float, size: float, face: str = SANS, line: float = 1.0) -> float:
    """Высота абзаца в дюймах."""
    return count_lines(chunks, width, size, face) * line_height(size, face, line)


# ── примитивы ─────────────────────────────────────────────────────────────────


def set_face(font, name: str) -> None:
    """Гарнитура для латиницы, кириллицы и восточных наборов сразу."""
    font.name = name
    rPr = font._element
    for tag in ("a:ea", "a:cs"):
        existing = rPr.find(qn(tag))
        if existing is not None:
            rPr.remove(existing)
        rPr.append(rPr.makeelement(qn(tag), {"typeface": name}))


def textbox(slide, x, y, w, h, *, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    return frame


def para(frame, *, first=False, space_after=0, line=1.25, align=PP_ALIGN.LEFT, space_before=0):
    p = frame.paragraphs[0] if first else frame.add_paragraph()
    p.line_spacing = line
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    p.alignment = align
    return p


def run(p, text, *, size=BODY, color=None, bold=False, face=SANS, spacing=None, caps=False):
    r = p.add_run()
    r.text = text.upper() if caps else text
    set_face(r.font, face)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = S.ink2 if color is None else color
    if spacing is not None:
        r.font._element.set("spc", str(int(spacing * 100)))
    return r


def rich(frame, chunks, *, first=False, size=BODY, color=None, line=1.4, align=PP_ALIGN.LEFT, face=SANS):
    """Абзац из кусков: строка — обычный текст, кортеж — выделенный.

    Кортеж (текст,) даёт полужирный чернилами, (текст, ЦВЕТ) — полужирный цветом.
    """
    p = para(frame, first=first, line=line, align=align)
    for chunk in chunks:
        if isinstance(chunk, tuple):
            tone = chunk[1] if len(chunk) > 1 and isinstance(chunk[1], RGBColor) else S.ink
            run(p, chunk[0], size=size, color=tone, bold=True, face=face)
        else:
            run(p, chunk, size=size, color=S.ink2 if color is None else color, face=face)
    return p


def text(slide, x, y, w, chunks, *, size=BODY, color=None, line=1.4, face=SANS, align=PP_ALIGN.LEFT):
    """Абзац с возвратом нижней границы — на неё встаёт следующий блок."""
    height = block_h(chunks, w, size, face, line)
    frame = textbox(slide, x, y, w, height + 0.04)
    rich(frame, chunks, first=True, size=size, color=color, line=line, face=face, align=align)
    return y + height


def label(slide, x, y, w, value, *, size=MICRO, color=None, align=PP_ALIGN.LEFT, face=MONO, spacing=1.2, caps=True):
    """Надзаголовок: моноширинный, разрядка, прописные."""
    height = line_height(size, face, 1.0)
    frame = textbox(slide, x, y, w, height + 0.04)
    p = para(frame, first=True, line=1.0, align=align)
    run(p, value, size=size, color=S.ink3 if color is None else color, face=face, spacing=spacing, caps=caps)
    return y + height


def no_shadow(shape) -> None:
    """Снимает тень.

    Пустого `a:effectLst` мало: автофигура несёт ещё `p:style` со ссылками на
    эффекты темы, и часть просмотрщиков читает именно её. Заливку и обводку мы
    задаём явно, поэтому ссылку можно убрать целиком.
    """
    element = shape._element
    spPr = element.spPr
    for tag in ("a:effectLst", "a:effectDag"):
        existing = spPr.find(qn(tag))
        if existing is not None:
            spPr.remove(existing)
    spPr.append(spPr.makeelement(qn("a:effectLst"), {}))
    style = element.find(qn("p:style"))
    if style is not None:
        element.remove(style)


def rect(slide, x, y, w, h, *, fill=-1, line=-1, width=0.75, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.035):
    box = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    no_shadow(box)
    fill = S.panel if fill == -1 else fill
    line = S.rule if line == -1 else line
    if fill is None:
        box.fill.background()
    else:
        box.fill.solid()
        box.fill.fore_color.rgb = fill
    if line is None:
        box.line.fill.background()
    else:
        box.line.color.rgb = line
        box.line.width = Pt(width)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        box.adjustments[0] = radius
    box.text_frame.word_wrap = True
    return box


def hline(slide, x, y, w, *, color=-1, thick=6350):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Emu(thick))
    no_shadow(line)
    line.fill.solid()
    line.fill.fore_color.rgb = S.rule if color == -1 else color
    line.line.fill.background()
    return line


def vline(slide, x, y, h, *, color=-1):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Emu(6350), Inches(h))
    no_shadow(line)
    line.fill.solid()
    line.fill.fore_color.rgb = S.rule if color == -1 else color
    line.line.fill.background()
    return line


def dot(slide, x, y, d, color):
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    no_shadow(circle)
    circle.fill.solid()
    circle.fill.fore_color.rgb = color
    circle.line.fill.background()
    return circle


def picture(slide, name, x, y, max_w, max_h, *, align="left", valign="top"):
    """Снимок целиком, вписанный в рамку без обрезки.

    Кадр подбирается под пропорции самого снимка, а не наоборот: снимки для
    колоды снимаются по границам панели (tools/shoot.mjs), поэтому обрезать их
    нечем — в кадре и так ровно то, что нужно.
    """
    path = PNG / name
    native_w, native_h = Image.from_file(str(path)).size
    scale = min(max_w / native_w, max_h / native_h)
    w, h = native_w * scale, native_h * scale
    if align == "center":
        x += (max_w - w) / 2
    elif align == "right":
        x += max_w - w
    if valign == "middle":
        y += (max_h - h) / 2
    elif valign == "bottom":
        y += max_h - h
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    pic.line.color.rgb = S.rule2
    pic.line.width = Pt(0.75)
    no_shadow(pic)
    return pic


# ── блоки слайда ──────────────────────────────────────────────────────────────


def new_slide(prs, note="", *, tone=LIGHT):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = tone.paper
    if note:
        slide.notes_slide.notes_text_frame.text = note
    return slide


def head(slide, eyebrow, title, *, y=TOP, width=CONTENT_W):
    """Надзаголовок, заголовок и линейка под ним. Возвращает верх содержимого."""
    label(slide, M, y, width, eyebrow)
    size = H1 if count_lines([title], width, H1, SERIF) == 1 else H1_LONG
    lines = count_lines([title], width, size, SERIF)
    height = lines * line_height(size, SERIF, 1.0)

    frame = textbox(slide, M, y + 0.30, width, height + 0.06)
    p = para(frame, first=True, line=1.0)
    run(p, title, size=size, color=S.ink, bold=True, face=SERIF, spacing=-0.6)

    rule_y = y + 0.30 + height + 0.13
    hline(slide, M, rule_y, CONTENT_W)
    return rule_y + 0.30


def foot(slide, left, right, *, index=None, total=14):
    label(slide, M, FOOT_Y, CONTENT_W, left, size=8.25, spacing=0.8)
    if index is not None:
        label(slide, M, FOOT_Y, CONTENT_W, f"{index:02d} / {total}", size=8.25, spacing=0.8,
              align=PP_ALIGN.RIGHT, caps=False)
        label(slide, M, FOOT_Y, CONTENT_W - 0.78, right, size=8.25, spacing=0.8, align=PP_ALIGN.RIGHT)
        # Линейка хода: сколько из семи минут уже позади.
        hline(slide, M, PROG_Y, CONTENT_W)
        hline(slide, M, PROG_Y, CONTENT_W * index / total, color=S.ink3, thick=12700)
    else:
        label(slide, M, FOOT_Y, CONTENT_W, right, size=8.25, spacing=0.8, align=PP_ALIGN.RIGHT)


def stat(slide, x, y, w, caption, value, *, unit=None, note=None, size=30.0, tone=None):
    """Показатель: подпись, крупное число, пояснение. Возвращает низ блока."""
    cursor = text(slide, x, y, w, [caption], size=NOTE, line=1.1)

    value_h = line_height(size, SANS, 1.0)
    frame = textbox(slide, x, cursor + 0.09, w, value_h + 0.06)
    p = para(frame, first=True, line=1.0)
    run(p, value, size=size, color=S.ink if tone is None else tone, bold=True, face=SANS, spacing=-1.0)
    if unit:
        run(p, " " + unit, size=max(10.0, size * 0.30), color=S.ink3)
    cursor += 0.09 + value_h

    if note:
        cursor = text(slide, x, cursor + 0.10, w, [note], size=NOTE, line=1.25, color=S.ink3)
    return cursor


def kv(slide, x, y, w, rows, *, size=SMALL, tone=None):
    """Пары «подпись — значение» с волосяной линейкой между строками."""
    step = line_height(size, SANS, 1.0) + 0.145
    cursor = y
    for index, (key, value) in enumerate(rows):
        h = line_height(size, SANS, 1.0) + 0.05
        frame = textbox(slide, x, cursor, w, h)
        p = para(frame, first=True, line=1.0)
        run(p, key, size=size, color=S.ink2)
        frame = textbox(slide, x, cursor, w, h)
        p = para(frame, first=True, line=1.0, align=PP_ALIGN.RIGHT)
        run(p, value, size=size, color=S.ink if tone is None else tone, bold=True)
        cursor += step
        if index < len(rows) - 1:
            hline(slide, x, cursor - 0.085, w)
    return cursor - 0.145


def kv_height(rows, size=SMALL) -> float:
    step = line_height(size, SANS, 1.0) + 0.145
    return len(rows) * step - 0.145


def bullets(slide, x, y, w, items, *, markers=None, size=BODY, gap=0.20, marker_w=0.28, line=1.4):
    """Список с моноширинным маркером слева и висячим отступом."""
    inner_x = x + marker_w
    inner_w = w - marker_w
    cursor = y
    for index, chunks in enumerate(items):
        mark = markers[index] if markers else "→"
        frame = textbox(slide, x, cursor + 0.035, marker_w, 0.24)
        p = para(frame, first=True, line=1.0)
        run(p, mark, size=size * 0.66, color=S.ink3, face=MONO, spacing=0.4)
        cursor = text(slide, inner_x, cursor, inner_w, chunks, size=size, line=line) + gap
    return cursor - gap


def bullets_h(items, w, *, size=BODY, gap=0.20, marker_w=0.28, line=1.4) -> float:
    total = 0.0
    for chunks in items:
        total += block_h(chunks, w - marker_w, size, SANS, line) + gap
    return total - gap

def panel_text(slide, x, y, w, *, eyebrow=None, title=None, body=None, body_size=SMALL,
               gap=0.13, title_lines=None):
    """Шапка панели: надзаголовок, антиква-заголовок, абзац. Возвращает низ.

    `title_lines` резервирует под заголовок фиксированное число строк. В ряду
    карточек это единственный способ поставить тексты под заголовками на одну
    линию: иначе карточка с коротким заголовком начинает абзац выше соседних.
    """
    cursor = y
    if eyebrow:
        cursor = label(slide, x, cursor, w, eyebrow) + 0.12
    if title:
        lines = title_lines or count_lines([title], w, H2, SERIF)
        height = lines * line_height(H2, SERIF, 1.08)
        frame = textbox(slide, x, cursor, w, height + 0.06)
        p = para(frame, first=True, line=1.08)
        run(p, title, size=H2, color=S.ink, bold=True, face=SERIF, spacing=-0.3)
        cursor += height + gap
    if body:
        cursor = text(slide, x, cursor, w, body, size=body_size, line=1.45)
    return cursor


def panel_text_h(w, *, eyebrow=None, title=None, body=None, body_size=SMALL, gap=0.13,
                 title_lines=None) -> float:
    total = 0.0
    if eyebrow:
        total += line_height(MICRO, MONO, 1.0) + 0.12
    if title:
        total += (title_lines or count_lines([title], w, H2, SERIF)) * line_height(H2, SERIF, 1.08) + gap
    if body:
        total += block_h(body, w, body_size, SANS, 1.45)
    return total


def title_lines_max(titles, w) -> int:
    return max(count_lines([t], w, H2, SERIF) for t in titles)


def bullets_fit(slide, x, y, w, items, bottom, *, markers=None, size=BODY,
                min_gap=0.16, max_gap=0.46, marker_w=0.28, line=1.4):
    """Список, растянутый до нижней границы полосы.

    Зазор между пунктами решается из доступной высоты, а не задаётся числом:
    так список не жмётся к заголовку на пустом слайде и не вылезает за панель
    на плотном.
    """
    natural = bullets_h(items, w, size=size, gap=0.0, marker_w=marker_w, line=line)
    slack = bottom - y - natural
    gap = slack / max(1, len(items) - 1) if len(items) > 1 else 0.0
    gap = min(max_gap, max(min_gap, gap))
    return bullets(slide, x, y, w, items, markers=markers, size=size, gap=gap,
                   marker_w=marker_w, line=line)


def compare_bar(slide, x, y, w, caption, part, whole, *, note=None):
    """Полоса «часть от целого»: сколько из полного резерва подтвердилось."""
    share = 0.0 if whole <= 0 else min(1.0, part / whole)
    text(slide, x, y, w * 0.62, [caption], size=NOTE, line=1.1)
    frame = textbox(slide, x, y, w, line_height(NOTE, SANS, 1.0) + 0.05)
    p = para(frame, first=True, line=1.0, align=PP_ALIGN.RIGHT)
    run(p, note or f"{share:.0%}", size=NOTE, color=S.ink, bold=True, face=MONO)
    track_y = y + line_height(NOTE, SANS, 1.0) + 0.10
    rect(slide, x, track_y, w, 0.085, fill=S.rule2, line=None, shape=MSO_SHAPE.RECTANGLE)
    if share > 0:
        rect(slide, x, track_y, w * share, 0.085, fill=S.ink, line=None, shape=MSO_SHAPE.RECTANGLE)
    return track_y + 0.085


def tag(slide, x, y, chunks_text, *, fill=WARN_BG, line=WARN_LINE, color=WARN, size=NOTE):
    """Небольшая плашка по ширине текста."""
    w = text_w(chunks_text, size) + 0.34
    h = line_height(size, SANS, 1.0) + 0.16
    box = rect(slide, x, y, w, h, fill=fill, line=line, radius=0.5)
    frame = box.text_frame
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = para(frame, first=True, line=1.0, align=PP_ALIGN.CENTER)
    run(p, chunks_text, size=size, color=color)
    return y + h

# ── слайды ────────────────────────────────────────────────────────────────────


# Положение требует показать концепцию, процесс разработки и анализ результатов —
# поэтому у каждой строки маршрута проставлен свой блок: судье видно сразу, что
# ни одна из трёх частей не пропущена.
ROUTE = [
    ("0:00", "Проблема и решение", "концепция"),
    ("0:25", "Что в датасете на самом деле", "данные"),
    ("1:10", "Кластеризация аудиторных моделей", "метод"),
    ("2:10", "Проверка: кластеры не случайны", "результат"),
    ("3:10", "Адресные рекомендации", "результат"),
    ("4:10", "Экономика, рынок, модель", "результат"),
    ("5:10", "Процесс разработки и отказы", "процесс"),
    ("6:10", "Внедрение и демо", "итог"),
]


def slide_title(prs, index, total):
    slide = new_slide(prs, "Не начинаем отсчёт: слайд стоит на экране, пока нас представляют. "
                           "Демо открыть в соседней вкладке заранее.")
    left_w = 6.45
    right_x = M + left_w + 0.55
    right_w = CONTENT_W - left_w - 0.55

    label(slide, M, TOP, left_w, "Vitaliy Software Solutions · хакатон")

    height = line_height(DISPLAY, SERIF, 1.0)
    frame = textbox(slide, M, TOP + 0.34, left_w, height + 0.08)
    p = para(frame, first=True, line=1.0)
    run(p, "ВитДашборд", size=DISPLAY, color=INK, bold=True, face=SERIF, spacing=-1.4)

    cursor = TOP + 0.34 + height + 0.30
    cursor = text(slide, M, cursor, left_w, [
        "Аналитическая платформа сети центров прототипирования и творческих "
        "инкубаторов при вузах культуры: динамика показателей, кластеризация "
        "аудиторных моделей и адресные рекомендации по программированию."],
        size=LEDE, line=1.45)

    # Четыре числа таблицей, а не сеткой: они заполняют колонку до низа полосы
    # и читаются сверху вниз — как оглавление к тому, что будет дальше.
    facts = [
        ("Центров в сети", "20", None),
        ("Аудиторных моделей", "5", None),
        ("Адресных мер", "50", None),
        ("Подтверждённый резерв", "9,7", "млн ₽"),
    ]
    top = cursor + 0.40
    step = (BODY_BOT - top) / len(facts)
    for order, (caption, value, unit) in enumerate(facts):
        row_y = top + order * step
        hline(slide, M, row_y, left_w)
        text(slide, M, row_y + 0.18, left_w * 0.62, [caption], size=SMALL, line=1.1)
        frame = textbox(slide, M, row_y + 0.13, left_w, 0.5)
        p = para(frame, first=True, line=1.0, align=PP_ALIGN.RIGHT)
        run(p, value, size=28.0, color=INK, bold=True, spacing=-0.8)
        if unit:
            run(p, " " + unit, size=NOTE, color=INK3)
    hline(slide, M, BODY_BOT, left_w)

    # Маршрут семи минут: судьи видят структуру доклада до того, как он начался.
    box_h = BODY_BOT - TOP + 0.08
    rect(slide, right_x, TOP - 0.08, right_w, box_h)
    inner_x, inner_w = right_x + PAD + 0.04, right_w - 2 * (PAD + 0.04)
    label(slide, inner_x, TOP + 0.20, inner_w, "Маршрут защиты · 7 минут")
    row_h = line_height(SMALL, SANS, 1.25)
    first_y = TOP + 0.66
    last_y = TOP - 0.08 + box_h - 0.34 - row_h
    step = (last_y - first_y) / (len(ROUTE) - 1)
    row_y = first_y
    for order, (clock, topic, block) in enumerate(ROUTE):
        frame = textbox(slide, inner_x, row_y + 0.015, 0.62, 0.24)
        p = para(frame, first=True, line=1.0)
        run(p, clock, size=NOTE, color=INK3, face=MONO, spacing=0.3)
        text(slide, inner_x + 0.72, row_y, inner_w - 1.62, [topic], size=SMALL, line=1.25, color=INK)
        label(slide, inner_x, row_y + 0.02, inner_w, block, size=8.25, spacing=0.9,
              align=PP_ALIGN.RIGHT)
        if order < len(ROUTE) - 1:
            hline(slide, inner_x, row_y + (row_h + step) / 2, inner_w)
        row_y += step

    foot(slide, "vitaliysoftware.duckdns.org", "защита · 7 минут")


def slide_problem(prs, index, total):
    slide = new_slide(prs, "Блок A1. Заход. Утверждение: отчётность есть, управления по ней нет. "
                           "Не торопиться — это рамка всего выступления. Закончить фразой "
                           "«мы превращаем эту отчётность в действия».")
    y = head(slide, "Проблема · 0:00–0:25", "Отчётность сдают. Решений по ней не принимают.")

    cards = [
        ("01", "Двадцать шаблонов",
         "Каждый центр заполняет формы по-своему: где-то тысячи рублей подписаны рублями, "
         "где-то итог не сходится с подпунктами. Свести их вручную — работа на неделю.",
         "26 правок потребовалось только на разбор"),
        ("02", "Сравнивать не с чем",
         "Консерватория и центр цифрового контента работают с разной аудиторией. Сравнение "
         "«всех со всеми» даёт рейтинг, а не управленческий вывод.",
         "5 аудиторных моделей вместо одного рейтинга"),
        ("03", "Видно только постфактум",
         "К декабрю выясняется, что часть центров не вышла на план. В сентябре это уже видно "
         "в цифрах — но никто их не сводит.",
         "7 центров в зоне риска — видно уже сейчас"),
    ]
    card_w = (CONTENT_W - 2 * GUTTER) / 3
    inner_w = card_w - 2 * PAD
    title_top = PAD + 0.42
    body_h = max(panel_text_h(inner_w, title=t, body=[b], gap=0.16) for _, t, b, _ in cards)
    kicker_h = line_height(SMALL, SANS, 1.3)
    card_h = title_top + body_h + 0.34 + kicker_h + PAD
    for order, (number, title, body, kicker) in enumerate(cards):
        x = M + order * (card_w + GUTTER)
        rect(slide, x, y, card_w, card_h)
        label(slide, x + PAD, y + PAD, inner_w, number, spacing=0.6)
        panel_text(slide, x + PAD, y + title_top, inner_w, title=title, body=[body], gap=0.16,
                   title_lines=1)
        hline(slide, x + PAD, y + title_top + body_h + 0.17, inner_w)
        text(slide, x + PAD, y + title_top + body_h + 0.34, inner_w, [(kicker,)],
             size=SMALL, line=1.3)

    statement = [("Мы сделали платформу, которая превращает эту отчётность в конкретные "
                  "управленческие действия.",), " Она развёрнута, работает и открыта по ссылке."]
    statement_h = block_h(statement, 10.6, 19.0, SANS, 1.38)
    text(slide, M, BODY_BOT - statement_h, 10.6, statement, size=19.0, line=1.38)
    hline(slide, M, BODY_BOT - statement_h - 0.34, CONTENT_W)

    foot(slide, "ВитДашборд", "критерий 2 · актуальность", index=index, total=total)


def slide_dataset(prs, index, total):
    slide = new_slide(prs, "Блок A2. Проблема доказывается самим датасетом. Назвать три числа: "
                           "26 правок, 17 противоречий, 13 центров с пометками. Ключевая фраза: "
                           "«мы не чинили данные молча — каждая правка записана».")
    y = head(slide, "Актуальность · 0:25–1:10", "Проблема видна в самом датасете")

    left_w = 6.55
    right_x = M + left_w + GUTTER
    right_w = CONTENT_W - left_w - GUTTER

    column = (left_w - 0.5) / 3
    stat_bottom = y
    for order, (caption, value, unit, note) in enumerate([
        ("Правок при разборе", "26", None, "единицы, пустые строки, расхождения итогов"),
        ("Противоречий", "17", None, "показатели не сходятся между формами"),
        ("Центров с пометками", "13", "из 20", "у четырёх вклад в резерв не засчитан"),
    ]):
        stat_bottom = max(stat_bottom, stat(
            slide, M + order * (column + 0.25), y, column, caption, value, unit=unit, note=note, size=32))

    box_y = stat_bottom + 0.42
    rect(slide, M, box_y, left_w, BODY_BOT - box_y)
    inner = panel_text(slide, M + PAD, box_y + PAD, left_w - 2 * PAD, title="Три примера из журнала")
    bullets_fit(slide, M + PAD, inner + 0.22, left_w - 2 * PAD, [
        ["Строка подписана «тыс. рублей», но перевод даёт величину ", ("в 475 раз выше медианы сети",),
         " — подпись признана ошибочной, значение оставлено в рублях."],
        ["Разработано ", ("69 форматов при 21 обученном",), ": меньше одного участника на мероприятие "
         "— вероятна ошибка в строках 3.1–3.4 Формы 2."],
        ["Резидентов ", ("131 при 58 обученных",), " — показатели ведутся по разным контурам, "
         "сравнение по ним недостоверно."],
    ], BODY_BOT - PAD, markers=["01", "02", "03"], size=SMALL, marker_w=0.34)

    picture(slide, "quality.png", right_x, y, right_w, BODY_BOT - y)
    foot(slide, "раздел «Качество данных»", "критерий 2 · актуальность", index=index, total=total)


def slide_solution(prs, index, total):
    slide = new_slide(prs, "Короткий переход. Показать обзор. Одна мысль: двадцать книг Excel "
                           "сведены в один экран, и каждое число раскрывается до исходной строки отчёта.")
    y = head(slide, "Решение · 1:10–1:25", "Двадцать книг Excel — один экран")

    shot_w = 5.65
    picture(slide, "overview.png", M, y, shot_w, BODY_BOT - y)

    x = M + shot_w + 0.46
    w = CONTENT_W - shot_w - 0.46

    # Нижние сноски прижаты к низу полосы, список тянется от заголовка к ним.
    foot1 = ["Семь разделов: обзор, динамика, вовлечённость, кластеры, организации, "
             "рекомендации, качество данных."]
    foot2 = ["Источник — только годовые формы отчётности. Ни одного показателя, "
             "которого нет в исходных файлах."]
    h2 = block_h(foot2, w, SMALL, SANS, 1.45)
    h1 = block_h(foot1, w, SMALL, SANS, 1.45)
    y2 = BODY_BOT - h2
    y1 = y2 - 0.34 - h1
    text(slide, x, y2, w, foot2, size=SMALL, line=1.45, color=INK3)
    hline(slide, x, y2 - 0.20, w)
    text(slide, x, y1, w, foot1, size=SMALL, line=1.45)
    hline(slide, x, y1 - 0.34, w)

    bullets_fit(slide, x, y + 0.06, w, [
        [("4 193 участника",), " за девять отчётных месяцев, 307 мероприятий, "
         "2 074 готовые работы, 25,0 млн ₽ платных услуг."],
        [("7 центров",), " при текущем темпе не выходят на годовую цель — это видно в сентябре, "
         "а не в декабре."],
        ["Любое число раскрывается до карточки центра, исходного файла и строки формы."],
    ], y1 - 0.60, size=BODY)

    foot(slide, "раздел «Обзор»", "критерий 1 · проработка", index=index, total=total)


def slide_why_clusters(prs, index, total):
    slide = new_slide(prs, "Блок B1, первая половина. Главная мысль: кластеризуем не посетителей — "
                           "их персональных данных нет и быть не должно, — а аудиторные модели центров. "
                           "Сравнивать можно только с равными.")
    y = head(slide, "Кластеризация · 1:25–1:50", "Сравнивать можно только с равными")

    half = (CONTENT_W - 0.52) / 2
    cursor = text(slide, M, y, half, [
        "Персональных данных посетителей в отчётности нет и быть не должно. Зато у каждого "
        "центра есть ", ("профиль аудитории",), " — и его можно кластеризовать."],
        size=LEDE, line=1.45)

    hline(slide, M, cursor + 0.34, half)
    blocks = [
        ("Состав", "Доли четырёх каналов обучения: модули, мастер-классы, повышение "
                   "квалификации, переподготовка"),
        ("Масштаб", "Размер аудитории и ширина линейки форматов"),
        ("Глубина", "Наполняемость мероприятия и доля закрепившихся резидентов"),
        ("Отдача", "Творческие продукты, платные услуги, публичность результата"),
    ]
    col_w = (half - 0.32) / 2
    row_y = cursor + 0.62
    row_h = (BODY_BOT - row_y + 0.1) / 2
    for order, (name, body) in enumerate(blocks):
        x = M + (order % 2) * (col_w + 0.32)
        top = row_y + (order // 2) * row_h
        label(slide, x, top, col_w, name)
        text(slide, x, top + 0.30, col_w, [body], size=SMALL, line=1.4)

    x = M + half + 0.52
    rect(slide, x, y, half, BODY_BOT - y)
    inner_x, inner_w = x + PAD, half - 2 * PAD
    cursor = panel_text(slide, inner_x, y + PAD + 0.04, inner_w,
                        title="Одна техническая деталь",
                        body=["Доли каналов — ", ("композиционные данные",), ": они лежат на симплексе, "
                              "сумма всегда равна единице. Признаки линейно зависимы, и обычная "
                              "стандартизация для них некорректна — евклидово расстояние искажает близость."])
    text(slide, inner_x, cursor + 0.28, inner_w, [
        "Применено ", ("центрированное логарифмическое преобразование",), " с мультипликативной "
        "заменой нулей — стандартная практика для составов. Дальше — главные компоненты "
        "и кластеризация уже в этом пространстве."], size=SMALL, line=1.45)

    rows = [("Признаков", "11"), ("Наблюдений", "20"), ("Компонент после сжатия", "5"),
            ("Объяснённый разброс", "90 %")]
    kv_top = BODY_BOT - PAD - kv_height(rows)
    hline(slide, inner_x, kv_top - 0.28, inner_w)
    kv(slide, inner_x, kv_top, inner_w, rows)

    foot(slide, "признаковое пространство", "критерий 1 · проработка", index=index, total=total)


def slide_models(prs, index, total):
    slide = new_slide(prs, "Блок B1, вторая половина. Назвать модели вслух, показать карту. "
                           "Подчеркнуть: имена не придуманы вручную — они собираются из признаков, "
                           "наиболее отличающих группу.")
    y = head(slide, "Аудиторные модели · 1:50–2:10", "Что сеть делает на самом деле")

    shot_w = 6.35
    picture(slide, "clusters.png", M, y, shot_w, BODY_BOT - y)

    x = M + shot_w + GUTTER
    w = CONTENT_W - shot_w - GUTTER
    models = [
        (C0, "Массовые просветители", "8", "Массовый охват и широкая линейка форматов"),
        (C1, "Медийные площадки", "5", "Заметность в медиа при камерном формате"),
        (C2, "Продуктовые мастерские", "3", "Сильное ядро резидентов, высокая отдача в продуктах"),
        (C3, "Открытые бесплатные площадки", "2", "Бесплатная модель, крупные потоки, узкая линейка"),
        (C4, "Профессиональные академии", "2", "Ставка на повышение квалификации и мастер-классы"),
    ]
    span = BODY_BOT - y
    card_h = (span - 4 * 0.14) / 5
    for order, (color, name, count, body) in enumerate(models):
        top = y + order * (card_h + 0.14)
        rect(slide, x, top, w, card_h)
        dot(slide, x + PAD, top + 0.235, 0.115, color)
        frame = textbox(slide, x + PAD + 0.24, top + 0.17, w - PAD - 0.6, 0.26)
        p = para(frame, first=True, line=1.0)
        run(p, name, size=SMALL + 0.5, color=INK, bold=True)
        frame = textbox(slide, x + PAD, top + 0.17, w - 2 * PAD, 0.26)
        p = para(frame, first=True, line=1.0, align=PP_ALIGN.RIGHT)
        run(p, count, size=SMALL + 0.5, color=INK3, face=MONO)
        text(slide, x + PAD + 0.24, top + 0.50, w - PAD - 0.48, [body], size=NOTE, line=1.35)

    foot(slide, "раздел «Кластеры»", "критерий 1 · проработка", index=index, total=total)


def slide_proof(prs, index, total):
    slide = new_slide(prs, "Блок B2. Самый сильный слайд по критерию 1 — он же самый дорогой: "
                           "двадцать баллов. Логика: на двадцати наблюдениях кластеры можно "
                           "получить всегда, поэтому мы проверили, что они не случайны. Назвать "
                           "p = 0,0005 и ARI 0,982. Если горит время — оставить только p-значение.")
    y = head(slide, "Доказательство · 2:10–3:10",
             "На двадцати наблюдениях кластеры получаются всегда. Мы проверили, что эти — настоящие.")

    cards = [
        ("Перестановочный тест", "Структура не случайна",
         "Признаки перемешиваются внутри столбцов, кластеризация повторяется — так получается, "
         "какой силуэт даёт чистый шум.",
         [("Наблюдаемый силуэт", "0,326"), ("p-значение", "0,0005"), ("Размер эффекта", "9,4 σ")]),
        ("Исключение по одному", "Разбиение не держится на одном центре",
         "Каждый центр по очереди убирается, модель пересобирается, результат сравнивается "
         "по индексу Рэнда.",
         [("Средний ARI", "0,982"), ("Худший прогон", "0,849"), ("Сменили кластер", "0 центров")]),
        ("Согласие алгоритмов", "Три метода дают одно разбиение",
         "Разные семейства сходятся на близком результате — значит, дело в данных, "
         "а не в выбранном методе.",
         [("k-средние ~ Уорд", "1,000"), ("GMM ~ k-средние", "0,757"), ("Устойчивость мер", "96 %")]),
    ]
    card_w = (CONTENT_W - 2 * GUTTER) / 3
    inner_w = card_w - 2 * PAD

    footnote = ["Число кластеров тоже не назначено рукой: перебор k от 2 до 5 по четырём метрикам "
                "сразу — силуэт, стабильность на бутстрапе, баланс размеров и индекс Дэвиса—Болдина. "
                "Сводный балл у ", ("k = 5",), " — 0,976 против 0,592 у ближайшего."]
    footnote_h = block_h(footnote, 11.2, SMALL, SANS, 1.45)
    footnote_y = BODY_BOT - footnote_h

    # Таблицы в карточках выравниваются по одной линии: разная длина заголовков
    # и пояснений не должна ломать горизонтальный ритм слайда.
    lines = title_lines_max([t for _, t, _, _ in cards], inner_w)
    body_h = max(panel_text_h(inner_w, eyebrow=e, title=t, body=[b], body_size=NOTE + 0.5,
                              title_lines=lines) for e, t, b, _ in cards)
    card_h = PAD + body_h + 0.34 + kv_height(cards[0][3], NOTE + 0.5) + PAD
    for order, (eyebrow, title, card_body, rows) in enumerate(cards):
        x = M + order * (card_w + GUTTER)
        rect(slide, x, y, card_w, card_h)
        panel_text(slide, x + PAD, y + PAD, inner_w, eyebrow=eyebrow, title=title,
                   body=[card_body], body_size=NOTE + 0.5, title_lines=lines)
        hline(slide, x + PAD, y + PAD + body_h + 0.17, inner_w)
        kv(slide, x + PAD, y + PAD + body_h + 0.34, inner_w, rows, size=NOTE + 0.5)

    hline(slide, M, footnote_y - 0.30, CONTENT_W)
    text(slide, M, footnote_y, 11.2, footnote, size=SMALL, line=1.45)

    foot(slide, "раздел «Кластеры» → проверки", "критерий 1 · проработка", index=index, total=total)


def slide_rec_logic(prs, index, total):
    slide = new_slide(prs, "Блок C, первая половина. Показать, что рекомендация — не «совет вообще», "
                           "а разрыв с медианой сопоставимых центров, переведённый в натуральную величину.")
    y = head(slide, "Рекомендации · 3:10–3:40", "Не совет, а посчитанный разрыв")

    left_w = 6.45
    bullets_fit(slide, M, y, left_w, [
        ["Центр сравнивается с ", ("медианой своей аудиторной модели",), ". Если в модели меньше пяти "
         "центров — со всей сетью; круг сравнения указан в каждой мере."],
        ["Разрыв переводится в натуральную величину: участники, работы, рубли, публикации."],
        ["Приоритет складывается из размера разрыва, доли затронутой аудитории и ",
         ("надёжности исходных данных",), "."],
        ["Мера пересобирается на возмущённых данных — ", ("20 прогонов",), ", чтобы отсеять артефакты "
         "одной выборки."],
    ], BODY_BOT, markers=["01", "02", "03", "04"], size=BODY, marker_w=0.34)

    x = M + left_w + 0.5
    w = CONTENT_W - left_w - 0.5
    rect(slide, x, y, w, BODY_BOT - y)
    inner_x, inner_w = x + PAD, w - 2 * PAD
    panel_text(slide, inner_x, y + PAD + 0.04, inner_w,
               eyebrow="Пример меры", title="Поднять наполняемость мастер-классов",
               body=["На «Мастер-классы» приходит ", ("0,3 чел.",), " на мероприятие при медиане ",
                     ("13,8",), " в своей модели — это нижний квартиль. Мероприятия уже проводятся "
                     "(68 шт.), значит резерв закрывается работой с набором, а не новой программой."])

    rows = [("Приоритет", "100 из 100"), ("Оценка эффекта", "+914 чел."), ("Лучший в группе", "ОГИК · 130,2")]
    tag_h = line_height(NOTE, SANS, 1.0) + 0.16
    kv_top = BODY_BOT - PAD - tag_h - 0.26 - kv_height(rows)
    hline(slide, inner_x, kv_top - 0.28, inner_w)
    cursor = kv(slide, inner_x, kv_top, inner_w, rows)
    tag(slide, inner_x, cursor + 0.30, "данные под вопросом")

    foot(slide, "раздел «Рекомендации»", "критерий 3 · востребованность", index=index, total=total)


def slide_rec_screen(prs, index, total):
    slide = new_slide(prs, "Блок C, вторая половина. Показать очередь мер на экране. Одна фраза: "
                           "«пятьдесят адресных действий, у каждого — обоснование, эффект и "
                           "уровень доверия». Обратить внимание на фильтр «только с надёжными данными».")
    y = head(slide, "Очередь мер · 3:40–4:10", "Очередь мер с доказательной базой")

    shot_w = 7.55
    picture(slide, "recs.png", M, y, shot_w, BODY_BOT - y)

    x = M + shot_w + 0.5
    w = CONTENT_W - shot_w - 0.5
    rows = [
        ("Мер в очереди", "50", None, "по семи типам, средний приоритет 51"),
        ("Устойчивы к возмущению данных", "96", "%", "20 прогонов, средняя выживаемость 98 %"),
        ("Центров охвачено", "20", "из 20", "у каждого — своя очередь действий"),
    ]
    step = (BODY_BOT - y) / len(rows)
    for order, (caption, value, unit, note) in enumerate(rows):
        top = y + order * step
        stat(slide, x, top, w, caption, value, unit=unit, note=note, size=34)
        if order < len(rows) - 1:
            hline(slide, x, top + step - 0.30, w)

    foot(slide, "раздел «Рекомендации»", "критерий 3 · востребованность", index=index, total=total)


def slide_economy(prs, index, total):
    """Единственный тёмный разворот: на нём называется главная цифра."""
    with skin(DARK):
        slide = new_slide(prs, "Блок D1. Критерий 4. Обязательно проговорить: резерв считается при "
                               "НЕИЗМЕННОМ числе мероприятий — это не «дайте денег», а «используйте "
                               "то, что уже есть». Показать полосы: мы сами вычли шесть мер по "
                               "четырём центрам, у которых данные противоречивы.",
                          tone=DARK)
        y = head(slide, "Экономика · 4:10–4:40", "Резерв закрывается без роста бюджета")

        column = CONTENT_W / 5
        stat_bottom = y
        for order, (caption, value, unit, note) in enumerate([
            ("Платные услуги", "+9,7", "млн ₽", "9 центров"),
            ("Творческие работы", "+1 411", None, "8 центров"),
            ("Участники", "+753", None, "13 центров"),
            ("Публикации", "+317", None, "8 центров"),
            ("Мероприятия", "+81", None, "6 центров"),
        ]):
            stat_bottom = max(stat_bottom, stat(
                slide, M + order * column, y + 0.14, column - 0.26,
                caption, value, unit=unit, note=note, size=40))

        rule_y = stat_bottom + 0.46
        hline(slide, M, rule_y, CONTENT_W)
        top = rule_y + 0.32

        col = (CONTENT_W - 2 * 0.62) / 3
        panel_text(slide, M, top, col, title="Откуда берётся",
                   body=["Это разрыв между центром и медианой ", ("сопоставимых",), " центров — "
                         "при неизменном числе мероприятий и неизменном бюджете. Не «дайте денег», "
                         "а «используйте то, что уже проводится»."], body_size=SMALL)

        x2 = M + col + 0.62
        panel_text(slide, x2, top, col, title="Почему числу можно верить",
                   body=["Показан ", ("подтверждённый",), " резерв: из полного вычтены шесть мер "
                         "по четырём центрам, у которых показатели внутри отчёта противоречат "
                         "друг другу. Мы сами уменьшили свою цифру."], body_size=SMALL)

        # Полосы «подтверждено из полного»: видно, где мы срезали сами себя.
        x3 = M + 2 * (col + 0.62)
        cursor = label(slide, x3, top, col, "Полный резерв → подтверждённый") + 0.26
        bars = [
            ("Платные услуги", 9.6698, 9.6698),
            ("Творческие работы", 1411, 1411),
            ("Мероприятия", 81.2, 114.5),
            ("Публикации", 317, 550),
            ("Участники", 753.3, 1689.9),
        ]
        step = (BODY_BOT - cursor) / len(bars)
        for caption, part, whole in bars:
            compare_bar(slide, x3, cursor, col, caption, part, whole)
            cursor += step

        foot(slide, "раздел «Рекомендации» → совокупный резерв", "критерий 4 · экономика",
             index=index, total=total)


def slide_market(prs, index, total):
    slide = new_slide(prs, "Блок D2. Критерий 4, вторая половина: рынок и бизнес-модель. Главное "
                           "сказать вслух: единица тиражирования — сеть, а не центр, и стоимость "
                           "обслуживания от числа центров почти не растёт. Объём рынка по открытым "
                           "источникам не выдумываем: называем эффект на одну сеть и множитель. "
                           "Если спросят про объём рынка — ответ именно такой.")
    y = head(slide, "Рынок и модель · 4:40–5:10", "Единица внедрения — сеть, а не центр")

    left_w = 7.45
    right_x = M + left_w + 0.5
    right_w = CONTENT_W - left_w - 0.5

    # Юнит-экономика сверху: это и есть ответ на «экономическую целесообразность».
    column = left_w / 3
    stats_bottom = y
    for order, (caption, value, unit, note) in enumerate([
        ("Резерв на сеть из 20 центров", "9,7", "млн ₽", "в год, подтверждённая часть, только выручка"),
        ("В пересчёте на центр", "≈ 0,48", "млн ₽", "в год, плюс работы, участники, публикации"),
        ("Стоимость эксплуатации", "1", "контейнер", "без внешних лицензий и платных сервисов"),
    ]):
        stats_bottom = max(stats_bottom, stat(
            slide, M + order * column, y, column - 0.34, caption, value, unit=unit,
            note=note, size=32))

    rows = [
        ("Кому", "Тому, кто сводит отчётность нескольких учреждений: учредителю сети, "
                 "региональному органу управления культурой, вузу-держателю центров. Признак "
                 "применимости один — те же формы 1 и 2."),
        ("Что продаётся", "Не экран с графиками, а сокращение цикла «отчёт → решение». Внедрение — "
                          "разовая настройка на форматы отчётности и развёртывание; дальше "
                          "подписка на пересчёт, поддержку и новые показатели."),
        ("Почему тиражируется", "Конвейер читает формы, а не конкретные файлы. Новый центр — "
                                "ещё один файл в каталоге, а не новая интеграция: стоимость "
                                "обслуживания сети почти не растёт с числом центров."),
    ]
    top = stats_bottom + 0.46
    heights = [0.30 + block_h([b], left_w, SMALL, SANS, 1.45) for _, b in rows]
    gap = min(0.50, max(0.24, (BODY_BOT - top - sum(heights)) / (len(rows) - 1)))
    cursor = top
    for order, ((name, body), height) in enumerate(zip(rows, heights)):
        # Линейка ставится посередине зазора, а не на фиксированном отступе:
        # иначе на плотном слайде она садится на выносные элементы абзаца.
        hline(slide, M, cursor - (0.26 if order == 0 else gap / 2), left_w)
        label(slide, M, cursor, left_w, name)
        text(slide, M, cursor + 0.30, left_w, [body], size=SMALL, line=1.45)
        cursor += height + gap

    rect(slide, right_x, y, right_w, BODY_BOT - y)
    inner_x, inner_w = right_x + PAD, right_w - 2 * PAD
    cursor = panel_text(slide, inner_x, y + PAD + 0.04, inner_w,
                        eyebrow="Честно про рынок",
                        body=["Объём рынка по открытым источникам мы не считали: в датасете его "
                              "нет, а выдуманная цифра в семиминутной защите проверяется за "
                              "полминуты."])
    text(slide, inner_x, cursor + 0.28, inner_w, [
        "Считаем проверяемое: эффект на сеть, с которой работаем, и стоимость её обслуживания. "
        "Эффект линеен по числу ", ("сетей",), ", а не центров — вторая такая же сеть даёт ещё "
        "9,7 млн ₽ при той же стоимости разработки. Сколько таких сетей, знает заказчик; "
        "умножается одна и та же величина."], size=SMALL, line=1.45)

    kv_rows = [("Сетей в расчёте", "1"), ("Центров в сети", "20"), ("Годовой резерв", "9,7 млн ₽")]
    kv_top = BODY_BOT - PAD - kv_height(kv_rows)
    hline(slide, inner_x, kv_top - 0.30, inner_w)
    kv(slide, inner_x, kv_top, inner_w, kv_rows)

    foot(slide, "экономика внедрения", "критерий 4 · бизнес-модель", index=index, total=total)


def slide_honesty(prs, index, total):
    slide = new_slide(prs, "Блок E. Отличает нас от типового дашборда. Сказать прямо: в задании была "
                           "обратная связь, в датасете её нет, синтетику мы рисовать не стали. "
                           "Показать панель «Чего в данных нет».")
    y = head(slide, "Честность данных · 5:35–6:10", "Мы не рисуем то, чего нет")

    cursor = text(slide, M, y, 11.4, [
        "В задании была обратная связь. В датасете её нет — ни одной строки об "
        "удовлетворённости. ",
        ("Синтетический NPS генерируется за час, но решать по выдуманным метрикам нельзя.",)],
        size=19.0, line=1.38)

    hline(slide, M, cursor + 0.34, CONTENT_W)

    top = cursor + 0.66
    left_w = 6.35
    rect(slide, M, top, left_w, BODY_BOT - top)
    inner = panel_text(slide, M + PAD, top + PAD, left_w - 2 * PAD, title="Что сделано вместо")
    bullets_fit(slide, M + PAD, inner + 0.26, left_w - 2 * PAD, [
        ["Наблюдаемые заменители: ", ("конверсия в готовую работу",), ", доля закрепившихся резидентов, "
         "внешняя заметность результата."],
        ["Отдельная панель ", ("«Чего в данных нет»",), ": перечень недостающих источников и что каждый "
         "из них дал бы."],
        ["Показатель без базы 2025 года не получает ни прироста, ни нуля — он помечен как несравнимый."],
    ], BODY_BOT - PAD, size=SMALL)

    picture(slide, "gaps.png", M + left_w + GUTTER, top, CONTENT_W - left_w - GUTTER,
            BODY_BOT - top, align="center", valign="middle")
    foot(slide, "раздел «Вовлечённость»", "критерий 1 · проработка", index=index, total=total)


def slide_process(prs, index, total):
    slide = new_slide(prs, "Блок E1. Положение требует показать процесс разработки. Логика "
                           "рассказа: на каждом этапе было решение, и у каждого решения была "
                           "цена. Сильнее всего звучит правая колонка — что мы выбросили. "
                           "Назвать вслух хотя бы синтетический NPS и симулятор.")
    y = head(slide, "Процесс · 5:10–5:35", "Четыре решения, которые определили продукт")

    left_w = 6.9
    stages = [
        ("Разбор", "Сначала журнал, потом цифры",
         "Двадцать книг с разными шаблонами. Решили: ни одной правки молча — каждая попадает "
         "в журнал и видна рядом с числом."),
        ("Признаки", "Не сравнивать несравнимое",
         "Доли каналов — состав, а не обычные числа. Решили: CLR-преобразование вместо сырых "
         "долей, иначе расстояния считаются неверно."),
        ("Модели", "Сначала проверка, потом вывод",
         "На двадцати наблюдениях кластеры выходят всегда. Решили: k по четырём метрикам, "
         "разбиение принимается после теста значимости."),
        ("Витрина", "Только то, что пришло из API",
         "Первый интерфейс на Vue показывал числа, зашитые в код. Решили: переписать с нуля "
         "и удалить всё, чего нет в ответах сервиса."),
    ]
    col_w = (left_w - 0.4) / 2
    body_w = col_w - 0.42
    # Заголовки занимают одинаковое число строк, иначе абзацы в соседних
    # ячейках начинаются на разной высоте и сетка разваливается.
    head_lines = title_lines_max([t for _, t, _ in stages], body_w)
    head_h = head_lines * line_height(H2, SERIF, 1.08)
    cell_h = (0.30 + head_h + 0.14
              + max(block_h([b], body_w, SMALL, SANS, 1.45) for _, _, b in stages))
    row_gap = max(0.30, BODY_BOT - y - 2 * cell_h)
    for order, (name, title, body) in enumerate(stages):
        x = M + (order % 2) * (col_w + 0.4)
        top = y + (order // 2) * (cell_h + row_gap)
        hline(slide, x, top - (0.24 if order < 2 else row_gap / 2), col_w)
        frame = textbox(slide, x, top + 0.02, 0.42, 0.24)
        p = para(frame, first=True, line=1.0)
        run(p, f"0{order + 1}", size=MICRO, color=INK3, face=MONO, spacing=0.6)
        label(slide, x + 0.42, top, col_w - 0.42, name)
        frame = textbox(slide, x + 0.42, top + 0.28, body_w, head_h + 0.06)
        p = para(frame, first=True, line=1.08)
        run(p, title, size=H2, color=INK, bold=True, face=SERIF, spacing=-0.3)
        text(slide, x + 0.42, top + 0.30 + head_h + 0.14, body_w, [body], size=SMALL, line=1.45)

    x = M + left_w + 0.5
    w = CONTENT_W - left_w - 0.5
    rect(slide, x, y, w, BODY_BOT - y)
    inner_x, inner_w = x + PAD, w - 2 * PAD
    inner = panel_text(slide, inner_x, y + PAD + 0.04, inner_w,
                       eyebrow="Что выбросили по дороге",
                       title="Отказ — тоже результат разработки")
    bullets_fit(slide, inner_x, inner + 0.26, inner_w, [
        [("Синтетическая обратная связь и NPS",), " — их нет в отчётности, а решать по "
         "выдуманному числу нельзя."],
        [("Симулятор с ползунками",), " — умножал уже посчитанные оценки на коэффициенты "
         "и выдавал это за эксперимент."],
        [("Квартальные ряды",), " — были записаны прямо в коде интерфейса, в формах их нет."],
        [("Радар «средней нормы сети»",), " — 50 баллов по каждой оси были условным ориентиром, "
         "а не расчётом."],
    ], BODY_BOT - PAD, size=SMALL)

    foot(slide, "процесс разработки", "критерий 1 · проработка", index=index, total=total)


PIPELINE = [
    ("01", "Excel", "20 книг"),
    ("02", "Разбор", "единицы, журнал"),
    ("03", "Признаки", "11 на центр"),
    ("04", "CLR + PCA", "5 компонент"),
    ("05", "Кластеры", "k = 5"),
    ("06", "Проверки", "перестановки, LOO"),
    ("07", "Меры", "50 действий"),
]


def slide_tech(prs, index, total):
    slide = new_slide(prs, "Быстрый слайд. Не зачитывать таблицу — назвать два факта: конвейер "
                           "целиком пересчитывается за 9,6 секунды и всё воспроизводится "
                           "с фиксированным сидом.")
    y = head(slide, "Архитектура · 6:10–6:30", "Конвейер целиком — 9,6 секунды")

    cards = [
        ("Данные", "Устойчивый разбор 20 разнородных книг Excel, приведение единиц, "
                   "журнал каждой правки"),
        ("Модели", "CLR-признаки, PCA, k-средние / Уорд / GMM, перестановочный тест, leave-one-out"),
        ("API", "FastAPI, 14 эндпоинтов, результат конвейера держится в памяти процесса"),
        ("Витрина", "React 19 + TypeScript, графики собственные на SVG, палитра проверена машинно"),
    ]
    card_w = (CONTENT_W - 3 * 0.3) / 4
    inner_w = card_w - 2 * PAD
    label_h = line_height(MICRO, MONO, 1.0)
    card_h = PAD + label_h + 0.20 + max(
        block_h([body], inner_w, SMALL, SANS, 1.45) for _, body in cards) + PAD
    for order, (name, body) in enumerate(cards):
        x = M + order * (card_w + 0.3)
        rect(slide, x, y, card_w, card_h)
        label(slide, x + PAD, y + PAD, inner_w, name)
        text(slide, x + PAD, y + PAD + label_h + 0.20, inner_w, [body], size=SMALL, line=1.45)

    rows = [
        ("Сборка конвейера", "9,6", "с", "от книги Excel до готовой меры, на сервере демо"),
        ("Воспроизводимость", "100", "%", "фиксированный сид во всех случайных процессах"),
        ("Развёрнуто", "Docker", None, "HTTPS, автопродление сертификата"),
    ]
    stat_h = (line_height(NOTE, SANS, 1.1) + 0.09 + line_height(30, SANS, 1.0) + 0.10
              + line_height(NOTE, SANS, 1.25))
    stats_y = BODY_BOT - stat_h
    column = CONTENT_W / 3
    for order, (caption, value, unit, note) in enumerate(rows):
        stat(slide, M + order * column, stats_y, column - 0.4, caption, value, unit=unit,
             note=note, size=30)
    hline(slide, M, stats_y - 0.36, CONTENT_W)

    # Конвейер одной строкой: от книги Excel до конкретной меры.
    chain_y = y + card_h + 0.50
    hline(slide, M, chain_y + 0.17, CONTENT_W, color=RULE)
    step = CONTENT_W / len(PIPELINE)
    for order, (number, name, note) in enumerate(PIPELINE):
        x = M + order * step
        dot(slide, x, chain_y + 0.115, 0.11, INK if order == 0 else RULE2)
        frame = textbox(slide, x, chain_y + 0.40, step - 0.2, 0.26)
        p = para(frame, first=True, line=1.0)
        run(p, number + "  ", size=MICRO, color=INK3, face=MONO, spacing=0.6)
        run(p, name, size=SMALL + 0.5, color=INK, bold=True)
        text(slide, x, chain_y + 0.66, step - 0.2, [note], size=NOTE, line=1.25, color=INK3)

    foot(slide, "архитектура", "критерий 1 · проработка", index=index, total=total)


def slide_final(prs, index, total):
    slide = new_slide(prs, "Блок F. Закрыть кругом: начали с «решений по отчётности не принимают» — "
                           "заканчиваем «вот пятьдесят решений». Назвать ссылку и остановиться. "
                           "Не добавлять новых фактов.")
    y = head(slide, "Финал · 6:30–7:00", "Готово к внедрению сегодня")

    band_h = 1.16
    band_y = BODY_BOT - band_h
    left_w = 6.55

    cursor = text(slide, M, y, left_w, [
        "Мы начали с того, что отчётность собирают, а решений по ней не принимают. ",
        ("Вот пятьдесят решений",), " — с обоснованием, оценкой эффекта и честной пометкой "
        "там, где данным нельзя доверять."], size=LEDE, line=1.45)

    hline(slide, M, cursor + 0.36, left_w)

    half = (left_w - 0.4) / 2
    row_y = cursor + 0.66
    for order, (caption, value, face, note) in enumerate([
        ("Новый отчётный период", "POST /reload", MONO, "положить файлы в каталог — модели пересоберутся"),
        ("Новый показатель", "одна запись", SANS, "в схеме показателей — и он в конвейере"),
    ]):
        x = M + order * (half + 0.4)
        text(slide, x, row_y, half, [caption], size=NOTE, line=1.1)
        frame = textbox(slide, x, row_y + 0.30, half, 0.4)
        p = para(frame, first=True, line=1.0)
        run(p, value, size=17.0, color=INK, bold=True, face=face, spacing=-0.3)
        text(slide, x, row_y + 0.78, half, [note], size=NOTE, line=1.35, color=INK3)

    picture(slide, "pace.png", M + left_w + GUTTER, y, CONTENT_W - left_w - GUTTER,
            band_y - y - 0.42, align="right")

    # Нижняя полоса — единственное, что остаётся на экране в конце речи.
    rect(slide, M, band_y, CONTENT_W, band_h, line=RULE2)
    label(slide, M + 0.38, band_y + 0.24, 4.6, "Демо · открыто прямо сейчас")
    frame = textbox(slide, M + 0.38, band_y + 0.52, 7.0, 0.44)
    p = para(frame, first=True, line=1.0)
    run(p, "vitaliysoftware.duckdns.org", size=21.0, color=INK, face=MONO, spacing=-0.2)

    note = ["Можно открыть с телефона, пока мы говорим. Развёрнуто в Docker, работает по HTTPS."]
    note_x = M + 7.7
    note_w = CONTENT_W - 7.7 - 0.38
    text(slide, note_x, band_y + (band_h - block_h(note, note_w, SMALL, SANS, 1.4)) / 2,
         note_w, note, size=SMALL, line=1.4)

    foot(slide, "Vitaliy Software Solutions", "критерий 5 · презентация", index=index, total=total)


# ── сборка ────────────────────────────────────────────────────────────────────

BUILDERS = [
    slide_title, slide_problem, slide_dataset, slide_solution, slide_why_clusters,
    slide_models, slide_proof, slide_rec_logic, slide_rec_screen, slide_economy,
    slide_market, slide_process, slide_honesty, slide_tech, slide_final,
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="vitdashboard-7min.pptx")
    args = parser.parse_args()

    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    for number, build in enumerate(BUILDERS, start=1):
        build(prs, number, len(BUILDERS))

    out = Path(args.out) if Path(args.out).is_absolute() else HERE / args.out
    prs.save(out)
    print(f"{out} · {len(prs.slides._sldIdLst)} слайдов · {out.stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
