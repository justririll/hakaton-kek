#!/usr/bin/env python3
"""Сборка колоды защиты в PowerPoint.

HTML-версия (`index.html`) остаётся основной: она показывается с таймером и
заметками. Этот файл собирает из того же содержания нативный .pptx — на случай,
когда организаторы принимают только его.

Ключевое отличие от печати в PDF: слайды здесь настоящие, с текстовыми блоками,
которые можно править, и с заметками докладчика в области notes. Гарнитуры взяты
те, что есть на любой машине с PowerPoint (Georgia, Calibri, Consolas), — фирменные
Literata и Inter пришлось бы внедрять в файл, а это работает не везде.

Запуск:  python build_pptx.py [--out vitdashboard-7min.pptx]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# ── палитра витрины ───────────────────────────────────────────────────────────

PAPER = RGBColor(0xF2, 0xEF, 0xE8)
PANEL = RGBColor(0xFC, 0xFA, 0xF6)
PANEL3 = RGBColor(0xED, 0xE9, 0xDF)
INK = RGBColor(0x1B, 0x1A, 0x17)
INK2 = RGBColor(0x56, 0x53, 0x4A)
INK3 = RGBColor(0x84, 0x80, 0x6F)
RULE = RGBColor(0xE3, 0xDE, 0xD3)
RULE2 = RGBColor(0xD3, 0xCC, 0xBC)

C0 = RGBColor(0x2B, 0x64, 0xA8)  # индиго
C1 = RGBColor(0xA7, 0x6C, 0xB5)  # слива
C2 = RGBColor(0xAA, 0x51, 0x31)  # терракота
C3 = RGBColor(0x9E, 0x96, 0x2A)  # олива
C4 = RGBColor(0x07, 0x8E, 0x7D)  # морская зелень
WARN = RGBColor(0xA8, 0x76, 0x0A)

SERIF = "Georgia"
SANS = "Calibri"
MONO = "Consolas"

# ── геометрия ─────────────────────────────────────────────────────────────────

W, H = 13.333, 7.5
M = 0.62               # боковое поле
TOP = 0.5
CONTENT_W = W - 2 * M
FOOT_Y = 6.98

# HTML-колода показывает те же снимки в webp — он легче, но PowerPoint его
# понимает не везде, поэтому для pptx рядом лежат png.
PNG = Path(__file__).with_name("shots") / "pptx"


def px(value: float) -> float:
    """Пиксель макета 1280×720 в дюймах слайда 13,333×7,5."""
    return value * W / 1280


# ── примитивы ─────────────────────────────────────────────────────────────────


def set_face(font, name: str) -> None:
    """Гарнитура для латиницы, кириллицы и восточных наборов сразу.

    python-pptx пишет только `a:latin`; без `a:cs` и `a:ea` PowerPoint на части
    систем подставляет под кириллицу свой шрифт по умолчанию.
    """
    font.name = name
    rPr = font._element
    for tag in ("a:ea", "a:cs"):
        existing = rPr.find(qn(tag))
        if existing is not None:
            rPr.remove(existing)
        node = rPr.makeelement(qn(tag), {"typeface": name})
        rPr.append(node)


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


def run(p, text, *, size=13.5, color=INK2, bold=False, face=SANS, spacing=None, caps=False):
    r = p.add_run()
    r.text = text.upper() if caps else text
    set_face(r.font, face)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    if spacing is not None:
        r.font._element.set("spc", str(int(spacing * 100)))
    return r


def rich(frame, chunks, *, first=False, size=13.5, color=INK2, line=1.35, space_after=0, face=SANS):
    """Абзац из кусков: строка — обычный текст, кортеж — (текст, жирный/цвет)."""
    p = para(frame, first=first, space_after=space_after, line=line)
    for chunk in chunks:
        if isinstance(chunk, tuple):
            text, bold = chunk[0], True
            tone = chunk[1] if len(chunk) > 1 and isinstance(chunk[1], RGBColor) else INK
            run(p, text, size=size, color=tone, bold=bold, face=face)
        else:
            run(p, chunk, size=size, color=color, face=face)
    return p


def no_shadow(shape) -> None:
    """Снимает тень с фигуры.

    Мало пустого `a:effectLst`: автофигура несёт ещё и `p:style` со ссылками на
    эффекты темы, и часть просмотрщиков (в том числе LibreOffice) читает именно
    её. Заливку и обводку мы всё равно задаём явно, поэтому ссылку на стиль
    можно убрать целиком.
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


def rect(slide, x, y, w, h, *, fill=PANEL, line=RULE, width=0.75, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.035):
    box = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    no_shadow(box)
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


def hline(slide, x, y, w, *, color=RULE, width=0.75):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Emu(6350))
    no_shadow(line)
    line.fill.solid()
    line.fill.fore_color.rgb = color
    line.line.fill.background()
    return line


def dot(slide, x, y, d, color):
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    no_shadow(circle)
    circle.fill.solid()
    circle.fill.fore_color.rgb = color
    circle.line.fill.background()
    return circle


def picture(slide, name, x, y, w, h, *, anchor="topleft"):
    """Снимок в рамку с обрезкой, как object-fit: cover.

    Обрезается от левого верхнего угла: у снимков витрины смысловая часть —
    заголовок панели и первые строки, срезать их по центру нельзя.
    """
    pic = slide.shapes.add_picture(str(PNG / name), Inches(x), Inches(y), Inches(w), Inches(h))
    native_w, native_h = pic.image.size
    want = w / h
    have = native_w / native_h
    if have > want:                      # шире рамки — режем справа
        cut = 1 - want / have
        if anchor == "topleft":
            pic.crop_right = cut
        else:
            pic.crop_left = pic.crop_right = cut / 2
    elif have < want:                    # выше рамки — режем снизу
        pic.crop_bottom = 1 - have / want
    pic.line.color.rgb = RULE2
    pic.line.width = Pt(0.75)
    no_shadow(pic)
    return pic


# ── блоки слайда ──────────────────────────────────────────────────────────────


def new_slide(prs, note=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = PAPER
    if note:
        slide.notes_slide.notes_text_frame.text = note
    return slide


def head(slide, eyebrow, title, *, title_size=30, y=TOP, rule=True):
    frame = textbox(slide, M, y, CONTENT_W, 0.24)
    p = para(frame, first=True, line=1.0)
    run(p, eyebrow, size=9, color=INK3, face=MONO, spacing=1.2, caps=True)

    frame = textbox(slide, M, y + 0.3, CONTENT_W, 1.0)
    p = para(frame, first=True, line=1.08)
    run(p, title, size=title_size, color=INK, bold=True, face=SERIF, spacing=-0.6)

    lines = 2 if len(title) > 58 else 1
    bottom = y + 0.3 + lines * px(title_size / 0.75 * 1.08) + px(16)
    if rule:
        hline(slide, M, bottom, CONTENT_W)
    return bottom + px(26)


def foot(slide, left, right):
    frame = textbox(slide, M, FOOT_Y, CONTENT_W, 0.22)
    p = para(frame, first=True, line=1.0)
    run(p, left, size=8.25, color=INK3, face=MONO, spacing=0.8, caps=True)
    frame = textbox(slide, M, FOOT_Y, CONTENT_W, 0.22)
    p = para(frame, first=True, line=1.0, align=PP_ALIGN.RIGHT)
    run(p, right, size=8.25, color=INK3, face=MONO, spacing=0.8, caps=True)


def stat(slide, x, y, w, label, value, *, unit=None, note=None, size=30):
    frame = textbox(slide, x, y, w, 0.3)
    p = para(frame, first=True, line=1.2)
    run(p, label, size=9.75, color=INK2)

    frame = textbox(slide, x, y + 0.24, w, px(size / 0.75 * 1.1))
    p = para(frame, first=True, line=1.0)
    run(p, value, size=size, color=INK, bold=True, face=SANS, spacing=-1.2)
    if unit:
        run(p, " " + unit, size=11.25, color=INK3)

    if note:
        frame = textbox(slide, x, y + 0.28 + px(size / 0.75 * 1.05), w, 0.5)
        p = para(frame, first=True, line=1.25)
        run(p, note, size=9.0, color=INK3)


def bullets(slide, x, y, w, items, *, markers=None, size=12.75, gap=13, marker_w=0.22):
    """Список с моноширинным маркером слева и висячим отступом."""
    cursor = y
    for index, chunks in enumerate(items):
        mark = markers[index] if markers else "→"
        frame = textbox(slide, x, cursor + px(2), marker_w, 0.25)
        p = para(frame, first=True, line=1.0)
        run(p, mark, size=8.5, color=INK3, face=MONO, spacing=0.4)

        frame = textbox(slide, x + marker_w + px(6), cursor, w - marker_w - px(6), 0.4)
        rich(frame, chunks, first=True, size=size, line=1.32)
        lines = max(1, estimate_lines(chunks, w - marker_w - px(6), size))
        cursor += lines * px(size / 0.75 * 1.32) + px(gap)
    return cursor


# Символов на дюйм при кегле 1 pt: Georgia шире Calibri, полужирный ещё шире.
DENSITY = {SANS: 128, SERIF: 104, MONO: 108}


def estimate_lines(chunks, width_in, size_pt, face=SANS):
    """Оценка числа строк — нужна, чтобы развести блоки по вертикали.

    Метрик шрифта у нас нет, поэтому берём эмпирическую плотность символов и
    сознательно округляем вверх: лишний зазор безопаснее наложения.
    """
    text = "".join(c[0] if isinstance(c, tuple) else c for c in chunks)
    per_line = max(8, int(width_in * DENSITY.get(face, 128) / size_pt))
    return max(1, -(-len(text) // per_line))


def kv(slide, x, y, w, rows, *, size=11.25, gap=0.245):
    """Пары «подпись — значение» с волосяной линейкой между строками."""
    cursor = y
    for index, (key, value) in enumerate(rows):
        frame = textbox(slide, x, cursor, w, 0.24)
        p = para(frame, first=True, line=1.15)
        run(p, key, size=size, color=INK2)
        frame = textbox(slide, x, cursor, w, 0.24)
        p = para(frame, first=True, line=1.15, align=PP_ALIGN.RIGHT)
        run(p, value, size=size, color=INK, bold=True)
        cursor += gap
        if index < len(rows) - 1:
            hline(slide, x, cursor - px(6), w)
    return cursor


def panel_head(slide, x, y, w, *, eyebrow=None, title=None, body=None, body_size=11.25):
    cursor = y
    if eyebrow:
        frame = textbox(slide, x, cursor, w, 0.22)
        p = para(frame, first=True, line=1.0)
        run(p, eyebrow, size=9, color=INK3, face=MONO, spacing=1.2, caps=True)
        cursor += 0.24
    if title:
        frame = textbox(slide, x, cursor, w, 0.9)
        p = para(frame, first=True, line=1.15)
        run(p, title, size=16.5, color=INK, bold=True, face=SERIF, spacing=-0.3)
        cursor += px(22 / 0.75 * 1.15) * estimate_lines([title], w, 16.5, SERIF) + px(8)
    if body:
        frame = textbox(slide, x, cursor, w, 1.2)
        rich(frame, body, first=True, size=body_size, line=1.4)
        cursor += estimate_lines(body, w, body_size) * px(body_size / 0.75 * 1.4) + px(8)
    return cursor


# ── слайды ────────────────────────────────────────────────────────────────────


def slide_title(prs):
    slide = new_slide(prs, "Не начинаем отсчёт: слайд стоит на экране, пока нас представляют. "
                           "Открыть демо в соседней вкладке заранее.")
    frame = textbox(slide, M, TOP, CONTENT_W, 0.24)
    p = para(frame, first=True, line=1.0)
    run(p, "Vitaliy Software Solutions · хакатон", size=9, color=INK3, face=MONO, spacing=1.2, caps=True)

    frame = textbox(slide, M, TOP + 0.36, CONTENT_W, 1.0)
    p = para(frame, first=True, line=1.02)
    run(p, "ВитДашборд", size=43.5, color=INK, bold=True, face=SERIF, spacing=-1.1)

    frame = textbox(slide, M, TOP + 1.34, px(800), 1.7)
    rich(frame, ["Аналитическая платформа сети центров прототипирования и творческих инкубаторов "
                 "при вузах культуры: динамика показателей, кластеризация аудиторных моделей "
                 "и адресные рекомендации по программированию."], first=True, size=15.75, line=1.45)

    hline(slide, M, 4.74, CONTENT_W)
    frame = textbox(slide, M, 4.9, CONTENT_W, 0.3)
    p = para(frame, first=True, line=1.0)
    for index, part in enumerate(["DATASET · 20 книг Excel", "разбор Форм 1 и 2", "11 признаков",
                                  "5 моделей", "50 действий"]):
        if index:
            run(p, "   →   ", size=9.75, color=INK3, face=MONO)
        run(p, part, size=9.75, color=INK2, face=MONO, spacing=0.5)
    hline(slide, M, 5.28, CONTENT_W)

    column = CONTENT_W / 4
    for index, (label, value, unit) in enumerate([
        ("Центров в сети", "20", None),
        ("Аудиторных моделей", "5", None),
        ("Адресных мер", "50", None),
        ("Резерв выручки", "9,7", "млн ₽"),
    ]):
        stat(slide, M + index * column, 5.62, column - 0.2, label, value, unit=unit)

    foot(slide, "vitaliysoftware.duckdns.org", "защита · 7 минут")


def slide_problem(prs):
    slide = new_slide(prs, "Блок A1. Заход. Утверждение: отчётность есть, управления по ней нет. "
                           "Не торопиться — это рамка всего выступления. Закончить фразой "
                           "«мы превращаем эту отчётность в действия».")
    y = head(slide, "Проблема · 0:00–0:25", "Отчётность сдают. Решений по ней не принимают.")

    cards = [
        ("Двадцать шаблонов",
         "Каждый центр заполняет формы по-своему: где-то тысячи рублей подписаны рублями, "
         "где-то итог не сходится с подпунктами. Свести их вручную — работа на неделю."),
        ("Сравнивать не с чем",
         "Консерватория и центр цифрового контента работают с разной аудиторией. Сравнение "
         "«всех со всеми» даёт рейтинг, а не управленческий вывод."),
        ("Видно только постфактум",
         "К декабрю выясняется, что часть центров не вышла на план. В сентябре это уже видно "
         "в цифрах — но никто их не сводит."),
    ]
    gap = 0.3
    card_w = (CONTENT_W - 2 * gap) / 3
    for index, (title, body) in enumerate(cards):
        x = M + index * (card_w + gap)
        rect(slide, x, y, card_w, 2.05)
        panel_head(slide, x + 0.22, y + 0.2, card_w - 0.44, title=title, body=[body])

    hline(slide, M, y + 2.45, CONTENT_W)
    frame = textbox(slide, M, y + 2.68, px(880), 0.9)
    rich(frame, [("Мы сделали платформу, которая превращает эту отчётность в конкретные "
                  "управленческие действия.",), " Она развёрнута, работает и открыта по ссылке."],
         first=True, size=15.75, line=1.42)

    foot(slide, "ВитДашборд", "критерий 2 · актуальность")


def slide_dataset(prs):
    slide = new_slide(prs, "Блок A2. Проблема доказывается самим датасетом. Назвать три числа: "
                           "26 правок, 17 противоречий, 13 центров с пометками. Ключевая фраза: "
                           "«мы не чинили данные молча — каждая правка записана».")
    y = head(slide, "Актуальность · 0:25–1:10", "Проблема видна в самом датасете")

    left_w = px(690)
    column = left_w / 3
    for index, (label, value, unit, note) in enumerate([
        ("Правок при разборе", "26", None, "единицы, пустые строки, расхождения итогов"),
        ("Противоречий", "17", None, "показатели не сходятся между формами"),
        ("Центров с пометками", "13", "из 20", "у четырёх вклад в резерв не засчитан"),
    ]):
        stat(slide, M + index * column, y, column - 0.16, label, value, unit=unit, note=note)

    box_y = y + 1.5
    rect(slide, M, box_y, left_w, 2.65)
    inner = panel_head(slide, M + 0.24, box_y + 0.22, left_w - 0.48, title="Три примера из журнала")
    bullets(slide, M + 0.24, inner, left_w - 0.48, [
        ["Строка подписана «тыс. рублей», но перевод даёт величину ", ("в 475 раз выше медианы сети",),
         " — подпись признана ошибочной, значение оставлено в рублях."],
        ["Разработано ", ("69 форматов при 21 обученном",), ": меньше одного участника на мероприятие "
         "— вероятна ошибка в строках 3.1–3.4 Формы 2."],
        ["Резидентов ", ("131 при 58 обученных",), " — показатели ведутся по разным контурам, "
         "сравнение по ним недостоверно."],
    ], markers=["01", "02", "03"], size=11.25, gap=11, marker_w=0.26)

    picture(slide, "quality.png", M + left_w + 0.3, y, CONTENT_W - left_w - 0.3, 4.15)
    foot(slide, "раздел «Качество данных»", "критерий 2 · актуальность")


def slide_solution(prs):
    slide = new_slide(prs, "Короткий переход. Показать обзор. Одна мысль: двадцать книг Excel "
                           "сведены в один экран, и каждое число кликабельно до исходной строки отчёта.")
    y = head(slide, "Решение", "Двадцать книг Excel — один экран")

    shot_w = px(700)
    picture(slide, "overview.png", M, y, shot_w, 3.95)

    x = M + shot_w + 0.36
    w = CONTENT_W - shot_w - 0.36
    cursor = bullets(slide, x, y + 0.1, w, [
        [("4 193 участника",), " за девять отчётных месяцев, 307 мероприятий, "
         "2 074 готовые работы, 25,0 млн ₽ платных услуг."],
        [("7 центров",), " при текущем темпе не выходят на годовую цель — это видно в сентябре, "
         "а не в декабре."],
        ["Любое число раскрывается до карточки центра, исходного файла и строки формы."],
    ], size=12.75, gap=20)

    hline(slide, x, cursor + 0.14, w)
    frame = textbox(slide, x, cursor + 0.34, w, 0.8)
    rich(frame, ["Семь разделов: обзор, динамика, вовлечённость, кластеры, организации, "
                 "рекомендации, качество данных."], first=True, size=11.25, line=1.4)

    foot(slide, "раздел «Обзор»", "критерий 1 · проработка")


def slide_why_clusters(prs):
    slide = new_slide(prs, "Блок B1, первая половина. Главная мысль: кластеризуем не посетителей — "
                           "их персональных данных нет и быть не должно, — а аудиторные модели центров. "
                           "Сравнивать можно только с равными.")
    y = head(slide, "Кластеризация · 1:10–2:10", "Сравнивать можно только с равными")

    half = (CONTENT_W - 0.34) / 2
    frame = textbox(slide, M, y, half, 1.2)
    rich(frame, ["Персональных данных посетителей в отчётности нет и быть не должно. Зато у каждого "
                 "центра есть ", ("профиль аудитории",), " — и его можно кластеризовать."],
         first=True, size=15.75, line=1.45)

    hline(slide, M, y + 1.28, half)
    blocks = [("Состав", "Доли четырёх каналов обучения"),
              ("Масштаб", "Размер аудитории и линейки форматов"),
              ("Глубина", "Наполняемость и доля резидентов"),
              ("Отдача", "Продукты, выручка, публичность")]
    col_w = (half - 0.26) / 2
    for index, (name, body) in enumerate(blocks):
        x = M + (index % 2) * (col_w + 0.26)
        row_y = y + 1.5 + (index // 2) * 0.86
        frame = textbox(slide, x, row_y, col_w, 0.22)
        p = para(frame, first=True, line=1.0)
        run(p, name, size=9, color=INK3, face=MONO, spacing=1.2, caps=True)
        frame = textbox(slide, x, row_y + 0.24, col_w, 0.5)
        rich(frame, [body], first=True, size=11.25, line=1.35)

    x = M + half + 0.34
    rect(slide, x, y, half, 3.55)
    cursor = panel_head(slide, x + 0.24, y + 0.24, half - 0.48,
                        title="Одна техническая деталь",
                        body=["Доли каналов — ", ("композиционные данные",), ": они лежат на симплексе, "
                              "сумма всегда равна единице. Признаки линейно зависимы, и обычная "
                              "стандартизация для них некорректна — евклидово расстояние искажает близость."])
    frame = textbox(slide, x + 0.24, cursor + 0.06, half - 0.48, 0.9)
    rich(frame, ["Применено ", ("центрированное логарифмическое преобразование",), " с мультипликативной "
                 "заменой нулей — стандартная практика для составов."], first=True, size=11.25, line=1.4)
    hline(slide, x + 0.24, cursor + 0.96, half - 0.48)
    kv(slide, x + 0.24, cursor + 1.12, half - 0.48,
       [("Признаков", "11"), ("Наблюдений", "20"), ("Компонент после сжатия", "5 · 90 % разброса")])

    foot(slide, "признаковое пространство", "критерий 1 · проработка")


def slide_models(prs):
    slide = new_slide(prs, "Блок B1, вторая половина. Назвать модели вслух, показать карту. "
                           "Подчеркнуть: имена не придуманы вручную — они собираются из признаков, "
                           "наиболее отличающих группу.")
    y = head(slide, "Пять аудиторных моделей", "Что сеть делает на самом деле")

    shot_w = px(690)
    picture(slide, "clusters.png", M, y, shot_w, 3.95)

    x = M + shot_w + 0.32
    w = CONTENT_W - shot_w - 0.32
    models = [
        (C0, "Массовые просветители · 8", "Массовый охват и широкая линейка форматов"),
        (C1, "Медийные площадки · 5", "Заметность в медиа при камерном формате"),
        (C2, "Продуктовые мастерские · 3", "Сильное ядро резидентов, высокая отдача в продуктах"),
        (C3, "Открытые бесплатные площадки · 2", "Бесплатная модель, крупные потоки, узкая линейка"),
        (C4, "Профессиональные академии · 2", "Ставка на повышение квалификации и мастер-классы"),
    ]
    card_h = 0.75
    for index, (color, name, body) in enumerate(models):
        row_y = y + index * (card_h + 0.1)
        rect(slide, x, row_y, w, card_h)
        dot(slide, x + 0.2, row_y + 0.19, 0.1, color)
        frame = textbox(slide, x + 0.38, row_y + 0.13, w - 0.58, 0.24)
        p = para(frame, first=True, line=1.0)
        run(p, name, size=11.25, color=INK, bold=True)
        frame = textbox(slide, x + 0.2, row_y + 0.4, w - 0.4, 0.3)
        rich(frame, [body], first=True, size=10.5, line=1.3)

    foot(slide, "раздел «Кластеры»", "критерий 1 · проработка")


def slide_proof(prs):
    slide = new_slide(prs, "Блок B2. Самый сильный слайд по критерию 1. Логика: на двадцати "
                           "наблюдениях кластеры можно получить всегда — поэтому мы проверили, "
                           "что они не случайны. Назвать p = 0,0005 и ARI 0,982. Если горит время — "
                           "оставить только p-value.")
    y = head(slide, "Доказательство · 2:10–3:10",
             "На двадцати наблюдениях кластеры получаются всегда. Мы проверили, что эти — настоящие.",
             title_size=27)

    cards = [
        ("Перестановочный тест", "Структура не случайна",
         "Признаки перемешиваются внутри столбцов, кластеризация повторяется — так получается, "
         "какой силуэт даёт чистый шум.",
         [("Наблюдаемый силуэт", "0,326"), ("p-значение", "0,0005"), ("Размер эффекта", "9,4 σ")]),
        ("Исключение по одному", "Разбиение не держится на одном центре",
         "Каждый центр по очереди убирается, модель пересобирается, результат сравнивается "
         "по индексу Рэнда.",
         [("Средний ARI", "0,982"), ("Худший прогон", "0,849"), ("Сменили кластер", "0 центров")]),
        ("Согласие алгоритмов", "Три метода дают одно и то же",
         "Разные семейства сходятся на близком разбиении — значит, дело в данных, а не в выбранном методе.",
         [("k-средние ~ Уорд", "1,000"), ("GMM ~ k-средние", "0,757"), ("Устойчивость мер", "96 %")]),
    ]
    gap = 0.28
    card_w = (CONTENT_W - 2 * gap) / 3
    for index, (eyebrow, title, body, rows) in enumerate(cards):
        x = M + index * (card_w + gap)
        rect(slide, x, y, card_w, 3.02)
        cursor = panel_head(slide, x + 0.22, y + 0.22, card_w - 0.44,
                            eyebrow=eyebrow, title=title, body=[body], body_size=10.5)
        hline(slide, x + 0.22, cursor + 0.04, card_w - 0.44)
        kv(slide, x + 0.22, cursor + 0.18, card_w - 0.44, rows, size=10.5, gap=0.235)

    hline(slide, M, y + 3.25, CONTENT_W)
    frame = textbox(slide, M, y + 3.44, CONTENT_W, 0.7)
    rich(frame, ["Число кластеров тоже не назначено рукой: перебор k от 2 до 5 по четырём метрикам "
                 "сразу — силуэт, стабильность на бутстрапе, баланс размеров и индекс Дэвиса—Болдина. "
                 "Сводный балл у ", ("k = 5",), " — 0,976 против 0,592 у ближайшего."],
         first=True, size=11.25, line=1.45)

    foot(slide, "раздел «Кластеры» → проверки", "критерий 1 · проработка")


def slide_rec_logic(prs):
    slide = new_slide(prs, "Блок C, первая половина. Показать, что рекомендация — не «совет вообще», "
                           "а разрыв с медианой сопоставимых центров, переведённый в натуральную величину.")
    y = head(slide, "Рекомендации · 3:10–4:10", "Не совет, а посчитанный разрыв")

    left_w = px(660)
    bullets(slide, M, y + 0.08, left_w, [
        ["Центр сравнивается с ", ("медианой своей аудиторной модели",), ". Если в модели меньше пяти "
         "центров — со всей сетью; круг сравнения указан в каждой мере."],
        ["Разрыв переводится в натуральную величину: участники, работы, рубли, публикации."],
        ["Приоритет складывается из размера разрыва, доли затронутой аудитории и ",
         ("надёжности исходных данных",), "."],
        ["Мера пересобирается на возмущённых данных — ", ("20 прогонов",), ", чтобы отсеять артефакты "
         "одной выборки."],
    ], markers=["01", "02", "03", "04"], size=12.75, gap=18, marker_w=0.26)

    x = M + left_w + 0.34
    w = CONTENT_W - left_w - 0.34
    rect(slide, x, y, w, 3.92)
    cursor = panel_head(slide, x + 0.24, y + 0.24, w - 0.48,
                        eyebrow="Пример меры", title="Поднять наполняемость «Мастер-классы»",
                        body=["На «Мастер-классы» приходит ", ("0,3 чел.",), " на мероприятие при медиане ",
                              ("13,8",), " в своей модели — это нижний квартиль. Мероприятия уже проводятся "
                              "(68 шт.), значит резерв закрывается работой с набором, а не новой программой."])
    hline(slide, x + 0.24, cursor + 0.04, w - 0.48)
    cursor = kv(slide, x + 0.24, cursor + 0.18, w - 0.48,
                [("Приоритет", "100 из 100"), ("Оценка эффекта", "+914 чел."), ("Лучший в группе", "ОГИК · 130,2")])

    tag = rect(slide, x + 0.24, cursor + 0.1, 1.85, 0.26,
               fill=RGBColor(0xF7, 0xF1, 0xE4), line=RGBColor(0xDC, 0xCB, 0xA6), radius=0.16)
    frame = tag.text_frame
    frame.margin_left = frame.margin_right = Inches(0.06)
    frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = para(frame, first=True, line=1.0, align=PP_ALIGN.CENTER)
    run(p, "данные под вопросом", size=9.0, color=WARN)

    foot(slide, "раздел «Рекомендации»", "критерий 3 · востребованность")


def slide_rec_screen(prs):
    slide = new_slide(prs, "Блок C, вторая половина. Показать очередь мер на экране. Одна фраза: "
                           "«пятьдесят адресных действий, у каждого — обоснование, эффект и уровень доверия».")
    y = head(slide, "Пятьдесят адресных действий", "Очередь мер с доказательной базой")

    shot_w = px(700)
    picture(slide, "recs.png", M, y, shot_w, 3.95)

    x = M + shot_w + 0.36
    w = CONTENT_W - shot_w - 0.36
    for index, (label, value, unit, note) in enumerate([
        ("Мер в очереди", "50", None, "по семи типам, средний приоритет 51"),
        ("Устойчивы к возмущению данных", "96", "%", "20 прогонов, средняя выживаемость 98 %"),
        ("Центров охвачено", "20", "из 20", "у каждого — своя очередь действий"),
    ]):
        stat(slide, x, y + 0.3 + index * 1.24, w, label, value, unit=unit, note=note)

    foot(slide, "раздел «Рекомендации»", "критерий 3 · востребованность")


def slide_economy(prs):
    slide = new_slide(prs, "Блок D. Ключевой слайд по критерию 4. Обязательно проговорить: резерв "
                           "считается при НЕИЗМЕННОМ числе мероприятий — это не «дайте денег», "
                           "а «используйте то, что уже есть». И назвать разницу полного и "
                           "подтверждённого резерва: мы сами вычли шесть мер по четырём центрам.")
    y = head(slide, "Экономика · 4:10–5:10", "Резерв закрывается без роста бюджета")

    column = CONTENT_W / 5
    for index, (label, value, unit, note) in enumerate([
        ("Платные услуги", "+9,7", "млн ₽", "9 центров"),
        ("Творческие работы", "+1 411", None, "8 центров"),
        ("Участники", "+753", None, "13 центров"),
        ("Публикации", "+317", None, "8 центров"),
        ("Мероприятия", "+81", None, "6 центров"),
    ]):
        stat(slide, M + index * column, y + 0.3, column - 0.22, label, value, unit=unit, note=note, size=38)

    hline(slide, M, y + 2.2, CONTENT_W)

    half = (CONTENT_W - 0.5) / 2
    cursor = panel_head(slide, M, y + 2.45, half, title="Откуда берётся",
                        body=["Это разрыв между центром и медианой ", ("сопоставимых",), " центров — "
                              "при неизменном числе мероприятий и неизменном бюджете. Не «дайте денег», "
                              "а «используйте то, что уже проводится»."])
    panel_head(slide, M + half + 0.5, y + 2.45, half, title="Почему числу можно верить",
               body=["Показан ", ("подтверждённый",), " резерв. Полный — 9,67 млн ₽ выручки и "
                     "1 690 участников; из него ", ("вычтены шесть мер по четырём центрам",),
                     ", у которых показатели внутри отчёта противоречат друг другу. Мы сами уменьшили "
                     "свою цифру, а не защищаем максимальную."])
    del cursor

    foot(slide, "раздел «Рекомендации» → совокупный резерв", "критерий 4 · экономика")


def slide_honesty(prs):
    slide = new_slide(prs, "Блок E. Отличает нас от типового дашборда. Сказать прямо: в задании была "
                           "обратная связь, в датасете её нет, синтетику мы рисовать не стали. "
                           "Показать панель «Чего в данных нет».")
    y = head(slide, "Честность данных · 5:10–6:10", "Мы не рисуем то, чего нет")

    left_w = px(660)
    frame = textbox(slide, M, y, left_w, 1.5)
    rich(frame, ["В задании была обратная связь. В датасете её нет — ни одной строки об "
                 "удовлетворённости, ни одного отзыва. ",
                 ("Синтетический NPS генерируется за час, но дашборд из выдуманных метрик "
                  "не годится для решений.",)], first=True, size=15.75, line=1.42)

    box_y = y + 1.68
    rect(slide, M, box_y, left_w, 2.3)
    inner = panel_head(slide, M + 0.24, box_y + 0.22, left_w - 0.48, title="Что сделано вместо")
    bullets(slide, M + 0.24, inner, left_w - 0.48, [
        ["Наблюдаемые заменители: ", ("конверсия в готовую работу",), ", доля закрепившихся резидентов, "
         "внешняя заметность результата."],
        ["Отдельная панель ", ("«Чего в данных нет»",), ": перечень недостающих источников и что каждый "
         "из них дал бы."],
        ["Показатель без базы 2025 года не получает ни прироста, ни нуля — он помечен как несравнимый."],
    ], size=11.25, gap=12)

    picture(slide, "eng.png", M + left_w + 0.32, y, CONTENT_W - left_w - 0.32, 3.9)
    foot(slide, "раздел «Вовлечённость»", "критерий 1 · проработка")


def slide_tech(prs):
    slide = new_slide(prs, "Быстрый слайд. Не зачитывать таблицу — назвать два факта: конвейер "
                           "целиком пересчитывается за 6,3 секунды и всё воспроизводится "
                           "с фиксированным сидом.")
    y = head(slide, "Как это устроено", "Конвейер целиком — 6,3 секунды")

    cards = [
        ("Данные", "Устойчивый разбор 20 разнородных книг Excel, приведение единиц, журнал каждой правки"),
        ("Модели", "CLR-признаки, PCA, k-средние / Уорд / GMM, перестановочный тест, leave-one-out"),
        ("API", "FastAPI, 14 эндпоинтов, результат конвейера держится в памяти процесса"),
        ("Витрина", "React 19 + TypeScript, графики собственные на SVG, палитра проверена машинно"),
    ]
    gap = 0.26
    card_w = (CONTENT_W - 3 * gap) / 4
    for index, (name, body) in enumerate(cards):
        x = M + index * (card_w + gap)
        rect(slide, x, y + 0.2, card_w, 1.55)
        frame = textbox(slide, x + 0.22, y + 0.42, card_w - 0.44, 0.22)
        p = para(frame, first=True, line=1.0)
        run(p, name, size=9, color=INK3, face=MONO, spacing=1.2, caps=True)
        frame = textbox(slide, x + 0.22, y + 0.7, card_w - 0.44, 1.0)
        rich(frame, [body], first=True, size=11.25, line=1.4)

    hline(slide, M, y + 2.1, CONTENT_W)
    column = CONTENT_W / 3
    for index, (label, value, unit, note) in enumerate([
        ("Сборка конвейера", "6,3", "с", "от Excel до рекомендаций"),
        ("Воспроизводимость", "100", "%", "фиксированный сид во всех случайных процессах"),
        ("Развёрнуто", "Docker", None, "HTTPS, автопродление сертификата"),
    ]):
        stat(slide, M + index * column, y + 2.35, column - 0.3, label, value, unit=unit, note=note)

    foot(slide, "архитектура", "критерий 1 · проработка")


def slide_final(prs):
    slide = new_slide(prs, "Блок F. Закрыть кругом: начали с «решений по отчётности не принимают» — "
                           "заканчиваем «вот пятьдесят решений». Назвать ссылку и остановиться. "
                           "Не добавлять новых фактов.")
    y = head(slide, "Финал · 6:10–7:00", "Готово к внедрению сегодня")

    # Левая колонка: вывод, затем — как платформа живёт дальше.
    left_w = px(690)
    frame = textbox(slide, M, y, left_w, 1.4)
    rich(frame, ["Мы начали с того, что отчётность собирают, а решений по ней не принимают. ",
                 ("Вот пятьдесят решений",), " — с обоснованием, оценкой эффекта и честной пометкой "
                 "там, где данным нельзя доверять."], first=True, size=15.75, line=1.45)

    hline(slide, M, y + 1.52, left_w)

    half = (left_w - 0.36) / 2
    for index, (label, value, face, note) in enumerate([
        ("Новый отчётный период", "POST /reload", MONO, "положить файлы в каталог — модели пересоберутся"),
        ("Новый показатель", "одна запись", SANS, "в схеме показателей — и он в конвейере"),
    ]):
        x = M + index * (half + 0.36)
        frame = textbox(slide, x, y + 1.78, half, 0.28)
        p = para(frame, first=True, line=1.2)
        run(p, label, size=9.75, color=INK2)
        frame = textbox(slide, x, y + 2.08, half, 0.36)
        p = para(frame, first=True, line=1.1)
        run(p, value, size=17.5, color=INK, bold=True, face=face, spacing=-0.3)
        frame = textbox(slide, x, y + 2.52, half, 0.6)
        rich(frame, [note], first=True, size=9.75, line=1.35)

    picture(slide, "orgs.png", M + left_w + 0.4, y, CONTENT_W - left_w - 0.4, 3.02)

    # Нижняя полоса — единственное, что остаётся на экране в конце речи.
    band_y = 5.24
    rect(slide, M, band_y, CONTENT_W, 1.18, fill=PANEL, line=RULE2)
    frame = textbox(slide, M + 0.34, band_y + 0.26, 4.6, 0.24)
    p = para(frame, first=True, line=1.0)
    run(p, "Демо · открыто прямо сейчас", size=9, color=INK3, face=MONO, spacing=1.2, caps=True)
    frame = textbox(slide, M + 0.34, band_y + 0.56, 6.4, 0.4)
    p = para(frame, first=True, line=1.0)
    run(p, "vitaliysoftware.duckdns.org", size=20, color=INK, face=MONO, spacing=-0.2)

    frame = textbox(slide, M + 7.4, band_y + 0.36, CONTENT_W - 7.74, 0.7, anchor=MSO_ANCHOR.MIDDLE)
    rich(frame, ["Можно открыть с телефона, пока мы говорим. Развёрнуто в Docker, работает по HTTPS."],
         first=True, size=11.25, line=1.4, color=INK2)

    foot(slide, "Vitaliy Software Solutions", "критерий 5 · презентация")


# ── сборка ────────────────────────────────────────────────────────────────────

BUILDERS = [
    slide_title, slide_problem, slide_dataset, slide_solution, slide_why_clusters,
    slide_models, slide_proof, slide_rec_logic, slide_rec_screen, slide_economy,
    slide_honesty, slide_tech, slide_final,
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="vitdashboard-7min.pptx")
    args = parser.parse_args()

    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    for build in BUILDERS:
        build(prs)

    out = Path(__file__).with_name(args.out) if not Path(args.out).is_absolute() else Path(args.out)
    prs.save(out)
    print(f"{out} · {len(prs.slides.__iter__.__self__._sldIdLst)} слайдов · {out.stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
