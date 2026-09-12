#!/usr/bin/env python3
"""Шрифты для предпросмотра колоды в LibreOffice.

Колода набрана гарнитурами, которые есть на любой машине с PowerPoint: Georgia,
Calibri, Consolas. На Linux их нет, и LibreOffice молча подставляет свои — при
проверке это давало расхождение по ширине строки до 14 %, то есть предпросмотр
показывал не ту раскладку, которую увидит жюри.

Здесь берутся свободные заменители и переименовываются в целевые имена: тогда
LibreOffice находит точное совпадение и ничего не подставляет.

    Calibri  → Carlito       метрически совпадает, ширины точные
    Georgia  → Noto Serif    чуть шире оригинала — запас в нашу пользу
    Consolas → Noto Sans Mono  то же самое

Файлы кладутся в каталог предпросмотра и в репозиторий не попадают: это чужие
шрифты под своими лицензиями, переименованные для локальной проверки.

Запуск:  uv run --with fonttools python tools/make_preview_fonts.py <каталог>
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont

CARLITO = "https://github.com/google/fonts/raw/main/ofl/carlito/"
NOTO = Path("/usr/share/fonts/noto")

# (источник, семейство, начертание, вес, индекс подсемейства)
PLAN = [
    ("Carlito-Regular.ttf", "Calibri", "Regular", 400, 0),
    ("Carlito-Bold.ttf", "Calibri", "Bold", 700, 1),
    ("Carlito-Italic.ttf", "Calibri", "Italic", 400, 2),
    ("Carlito-BoldItalic.ttf", "Calibri", "Bold Italic", 700, 3),
    ("NotoSerif-Regular.ttf", "Georgia", "Regular", 400, 0),
    ("NotoSerif-Bold.ttf", "Georgia", "Bold", 700, 1),
    ("NotoSerif-Italic.ttf", "Georgia", "Italic", 400, 2),
    ("NotoSansMono-Regular.ttf", "Consolas", "Regular", 400, 0),
    ("NotoSansMono-Bold.ttf", "Consolas", "Bold", 700, 1),
]

FS_SELECTION = {0: 0b1000000, 1: 0b0100000, 2: 0b0000001, 3: 0b0100001}


def source(name: str, cache: Path) -> Path:
    if (NOTO / name).exists():
        return NOTO / name
    local = cache / name
    if not local.exists():
        cache.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(CARLITO + name, local)
    return local


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "preview-fonts")
    out.mkdir(parents=True, exist_ok=True)
    cache = out / ".src"

    for name, family, style, weight, sub in PLAN:
        font = TTFont(source(name, cache))
        full = family if style == "Regular" else f"{family} {style}"
        postscript = full.replace(" ", "")
        for record in font["name"].names:
            if record.nameID == 1 or record.nameID == 16:
                record.string = family
            elif record.nameID == 2 or record.nameID == 17:
                record.string = style
            elif record.nameID == 4:
                record.string = full
            elif record.nameID == 6:
                record.string = postscript
        font["OS/2"].usWeightClass = weight
        font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b1100001) | FS_SELECTION[sub]
        font["head"].macStyle = sub
        font.save(out / f"{postscript}.ttf")
        print(f"{family} {style}  ←  {name}")


if __name__ == "__main__":
    main()
