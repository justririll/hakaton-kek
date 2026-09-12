#!/usr/bin/env bash
# Предпросмотр колоды: .pptx → по одному PNG на слайд.
#
# Рендерит LibreOffice с метрически совместимыми заменителями Georgia, Calibri
# и Consolas (tools/make_preview_fonts.py), поэтому картинка совпадает с тем,
# что посчитал сборщик, и с тем, что увидит PowerPoint.
#
#   ./tools/preview.sh [файл.pptx] [dpi]
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="${1:-$here/vitdashboard-7min.pptx}"
dpi="${2:-110}"
work="${PREVIEW_DIR:-$here/.preview}"

fonts="$work/fonts"
if [ ! -f "$fonts/Calibri.ttf" ]; then
  uv run --with fonttools python "$here/tools/make_preview_fonts.py" "$fonts"
fi

mkdir -p "$work/home/.fonts" "$work/cache" "$work/out"
cp -u "$fonts"/*.ttf "$work/home/.fonts/"
cat > "$work/fonts.conf" <<XML
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>$work/home/.fonts</dir>
  <cachedir>$work/cache</cachedir>
</fontconfig>
XML

rm -f "$work/out"/*.png "$work/out"/*.pdf
FONTCONFIG_FILE="$work/fonts.conf" HOME="$work/home" \
  soffice --headless --norestore --convert-to pdf --outdir "$work/out" "$src" >/dev/null
pdftoppm -r "$dpi" -png "$work/out/$(basename "${src%.pptx}").pdf" "$work/out/slide"
ls "$work/out"/slide-*.png | wc -l
echo "$work/out"
