#!/usr/bin/env python3
"""Таблица ширин символов для раскладки колоды.

Сборщик .pptx должен знать, сколько строк займёт абзац, — иначе блоки под ним
встают наугад. Метрик PowerPoint-овских гарнитур у нас нет и быть не может, но
для каждой есть свободный заменитель:

    Calibri  → Carlito       метрически совпадает, ширины точные
    Georgia  → Noto Serif    чуть шире оригинала
    Consolas → моноширинный  0,6 em против 0,55 em у Consolas

Оба заменителя шире оригинала, поэтому оценка строк консервативна: на реальном
PowerPoint текст займёт столько же или меньше. Ими же подменяются гарнитуры при
предпросмотре в LibreOffice, так что предпросмотр показывает худший случай.

Таблица кладётся в metrics.json рядом со сборщиком и коммитится — сборка не
требует ни интернета, ни установленных шрифтов.

Запуск:  uv run --with fonttools python tools/make_metrics.py <каталог-со-шрифтами>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

# Достаточно кириллицы, латиницы, цифр и той пунктуации, что встречается в колоде.
ALPHABET = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "".join(chr(c) for c in range(0x410, 0x450))
    + "ЁёЄєІіЇїҐґ"
    + "«»—–…·№₽°±×÷→←↑↓✓≈≤≥§¶©®™"
    + "   ‐‑–−"
)

FACES = {
    "sans": {"regular": "Carlito-Regular.ttf", "bold": "Carlito-Bold.ttf"},
    "serif": {"regular": "NotoSerif-Regular.ttf", "bold": "NotoSerif-Bold.ttf"},
    "mono": {"regular": "NotoSansMono-Regular.ttf", "bold": "NotoSansMono-Bold.ttf"},
}


def line_factor(font: TTFont) -> float:
    """Высота строки при одинарном интервале, в долях кегля.

    И PowerPoint, и LibreOffice берут её из таблицы hhea: восходящая плюс
    нисходящая плюс межстрочный зазор. Множитель line_spacing домножает уже её,
    а не кегль, — без этого блоки под абзацем встают примерно на 20 % выше, чем
    нужно, и налезают на текст.
    """
    hhea = font["hhea"]
    upem = font["head"].unitsPerEm
    return round((hhea.ascender - hhea.descender + hhea.lineGap) / upem, 4)


def widths(path: Path) -> dict[str, float]:
    font = TTFont(path)
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    table: dict[str, float] = {}
    for ch in ALPHABET:
        glyph = cmap.get(ord(ch))
        if glyph is None:
            continue
        table[ch] = round(hmtx[glyph][0] / upem, 5)
    return table


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    system = Path("/usr/share/fonts/noto")

    out: dict[str, object] = {
        "note": "ширины символов и высота строки в долях кегля (em)",
        "fallback": 0.62,
        "faces": {},
        "line": {},
    }
    for face, styles in FACES.items():
        out["faces"][face] = {}
        for style, name in styles.items():
            path = src / name
            if not path.exists():
                path = system / name
            if not path.exists():
                raise SystemExit(f"нет файла шрифта: {name}")
            font = TTFont(path)
            out["faces"][face][style] = widths(path)
            if style == "regular":
                out["line"][face] = line_factor(font)
            print(f"{face}/{style}: {len(out['faces'][face][style])} символов из {path}")
    print("высота строки:", out["line"])

    target = Path(__file__).resolve().parent.parent / "metrics.json"
    target.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{target} · {target.stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
