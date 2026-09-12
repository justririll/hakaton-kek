#!/usr/bin/env bash
# Предпросмотр колоды: .pptx → по одному PNG на слайд.
#
# Колода набрана Times New Roman, Arial и Courier New — LibreOffice сам
# подставляет вместо них Liberation Serif, Sans и Mono, метрически совпадающие
# знак в знак. Поэтому рендер показывает ровно ту раскладку, которую увидит
# PowerPoint, и никаких подмен шрифтов настраивать не нужно.
#
#   ./tools/preview.sh [файл.pptx] [dpi]
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="${1:-$here/vitdashboard-7min.pptx}"
dpi="${2:-110}"
work="${PREVIEW_DIR:-$here/.preview}"

mkdir -p "$work/home" "$work/out"
rm -f "$work/out"/*.png "$work/out"/*.pdf
HOME="$work/home" \
  soffice --headless --norestore --convert-to pdf --outdir "$work/out" "$src" >/dev/null
pdftoppm -r "$dpi" -png "$work/out/$(basename "${src%.pptx}").pdf" "$work/out/slide"
ls "$work/out"/slide-*.png | wc -l
echo "$work/out"
