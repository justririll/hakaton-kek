#!/usr/bin/env python3
"""Проверка раскладки колоды: не вылез ли текст за поля.

Сборщик считает переносы по таблице ширин, но опечатка в тексте или новый
абзац могут вытолкнуть блок за нижнюю границу полосы — на глаз это заметно не
всегда, особенно если налезает подвал. Скрипт берёт PDF, отрендеренный
LibreOffice (tools/preview.sh), достаёт координаты каждого слова и сверяет их
с той же сеткой, по которой собиралась колода.

    ./tools/preview.sh && uv run python tools/check_layout.py

Возвращает ненулевой код, если что-то вышло за поля, — годится для проверки
перед коммитом.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# Та же сетка, что в build_pptx.py, в дюймах.
SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN = 0.62
BODY_BOT = 6.60
RULE_Y = 6.80        # линейка хода выступления
FOOT_BAND = (6.88, 7.24)   # полоса подвала: там текст и должен быть
TOP = 0.46
TOLERANCE = 0.04     # дюйма: округления рендера и выносные элементы


def words(pdf: Path):
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    page = 0
    scale = None
    for line in out.splitlines():
        m = re.search(r'<page width="([\d.]+)" height="([\d.]+)"', line)
        if m:
            page += 1
            scale = SLIDE_W / float(m.group(1))
            continue
        m = re.search(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', line)
        if m and scale:
            x0, y0, x1, y1 = (float(m.group(i)) * scale for i in range(1, 5))
            yield page, x0, y0, x1, y1, m.group(5)


def main() -> int:
    pdf = next((HERE / ".preview" / "out").glob("*.pdf"), None)
    if pdf is None:
        print("нет отрендеренного PDF — сначала ./tools/preview.sh", file=sys.stderr)
        return 2

    problems: list[str] = []
    for page, x0, y0, x1, y1, word in words(pdf):
        footer = y0 >= FOOT_BAND[0] and y1 <= FOOT_BAND[1]
        if not footer:
            if y1 > RULE_Y - TOLERANCE:
                problems.append(f"слайд {page}: «{word}» заходит на подвал (низ {y1:.2f})")
            elif y1 > BODY_BOT + 0.26:
                problems.append(f"слайд {page}: «{word}» ниже полосы (низ {y1:.2f} при {BODY_BOT})")
        if x0 < MARGIN - TOLERANCE:
            problems.append(f"слайд {page}: «{word}» левее поля (лево {x0:.2f})")
        if x1 > SLIDE_W - MARGIN + TOLERANCE:
            problems.append(f"слайд {page}: «{word}» правее поля (право {x1:.2f})")
        if y0 < TOP - TOLERANCE:
            problems.append(f"слайд {page}: «{word}» выше полосы (верх {y0:.2f})")

    if problems:
        print(f"{pdf.name}: нарушений {len(problems)}")
        for line in problems[:40]:
            print(" ", line)
        if len(problems) > 40:
            print(f"  … и ещё {len(problems) - 40}")
        return 1
    print(f"{pdf.name}: текст внутри полей на всех слайдах")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
