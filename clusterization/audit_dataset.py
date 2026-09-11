"""Проверка исходных Excel-форм. Не создаёт людей из сводных чисел."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REQUIRED = {"visitor_id", "event_id", "event_date", "institution_id", "event_type"}


def audit_dataset(directory: str | Path) -> dict:
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Нет папки: {directory}")
    files = sorted(p for p in directory.iterdir() if p.suffix.lower() in {".xlsx", ".xls"})
    if not files:
        raise ValueError("В папке нет Excel-файлов.")
    books = []
    for path in files:
        sheets = pd.read_excel(path, sheet_name=None, header=None)
        audience_rows, headers, inventory = [], [], []
        for name, frame in sheets.items():
            inventory.append({"name": name, "rows": len(frame), "columns": len(frame.columns)})
            for index, row in frame.iterrows():
                values = {str(value).strip().lower() for value in row if pd.notna(value)}
                if REQUIRED.issubset(values):
                    headers.append({"sheet": name, "row": index + 1})
                if re.sub(r"\s+", "", name).casefold() != "форма2" or len(row) < 3:
                    continue
                label = str(row.iloc[1]).strip()
                code = re.match(r"^(3\.[1-4])(?:\D|$)", label)
                if not code:
                    code = re.match(r"^(3\.[1-4])(?:\D|$)", str(row.iloc[0]).strip())
                if code:
                    value = row.iloc[2]
                    value = None if pd.isna(value) else str(value)
                    audience_rows.append({"indicator_code": code.group(1),
                                          "sheet": name, "cell": f"C{index + 1}",
                                          "label": label, "raw_value": value})
        codes = {row["indicator_code"] for row in audience_rows}
        aggregate = codes == {"3.1", "3.2", "3.3", "3.4"}
        books.append({"file": path.name, "sheets": inventory,
                      "kind": "aggregate_report" if aggregate and not headers else "needs_review",
                      "visit_table_header_candidates": headers, "audience_indicators": audience_rows})
    all_aggregate = all(book["kind"] == "aggregate_report" for book in books)
    return {
        "workbooks": len(books), "sheets": sum(len(b["sheets"]) for b in books),
        "status": "aggregate_reports_only" if all_aggregate else "needs_review",
        "can_cluster_individual_visitors": False if all_aggregate else None,
        "reason": "Строки 3.1–3.4 Формы 2 содержат численность обучившихся по форматам. "
                  "Они не задают связи «посетитель — посещение» и пересечения аудиторий. "
                  "Распознавание относится к этому шаблону, а не ко всем возможным Excel-файлам.",
        "required_visit_columns": sorted(REQUIRED), "files": books,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=HERE.parent / "DATASET")
    parser.add_argument("--output", type=Path, default=HERE / "output_audit" / "dataset_audit.json")
    args = parser.parse_args()
    try:
        report = audit_dataset(args.dataset)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"Ошибка: {exc}\n")
    print(f"Проверено файлов: {report['workbooks']}; листов: {report['sheets']}.")
    print(f"Статус: {report['status']}.")
    print(report["reason"])
    print(f"Отчёт: {args.output}")


if __name__ == "__main__":
    main()
