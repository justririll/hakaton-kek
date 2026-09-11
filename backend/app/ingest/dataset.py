"""Сборка аналитического датасета из разобранных отчётных книг.

Здесь сырые значения превращаются в таблицу, пригодную для моделирования:
приводятся единицы измерения, фиксируются пропуски, проверяется сходимость
агрегатов с подпунктами. Всё, что пришлось поправить, попадает в отчёт о
качестве данных — он часть результата, а не служебный лог.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from app.ingest.excel_parser import ParsedReport, parse_directory
from app.ingest.schema import BY_KEY, INDICATORS

# Короткие имена для интерфейса: в отчётах организации подписаны по-разному
# («ФГБОУ ВО "Орловский государственный институт культуры"»), а на графике
# нужна метка в 6–12 символов.
SHORT_NAMES: dict[str, str] = {
    "АГИК": "АГИК",
    "Андрияки": "Академия Андрияки",
    "ВГИИ": "ВГИИ",
    "ЕГТИ": "ЕГТИ",
    "КГИК": "КГИК",
    "Карандаш": "Карандаш",
    "КемГИК": "КемГИК",
    "МГАХИ": "МГАХИ",
    "МГИК ф1-2": "МГИК",
    "Нижний новогород": "Нижегородская консерватория",
    "Новосиб": "Новосибирская консерватория",
    "ОГИК": "ОГИК",
    "ПГИК": "ПГИК",
    "Саратов": "Саратовская консерватория",
    "СпбКИТ": "СПбГИКиТ",
    "УГИИ": "УГИИ",
    "ЦП ВСГИК ф1 и 2": "ВСГИК",
    "ЧГИК": "ЧГИК",
    "гмп": "ГМПИ им. Ипполитова-Иванова",
    "театриум": "Театриум (ПГХУ)",
}

# Денежная строка, подписанная «тыс. рублей», приводится к рублям. Но если
# после приведения значение выбивается из выборки более чем в N раз от медианы,
# подпись считается ошибочной, а число — уже рублёвым (см. README, «Качество
# данных»). Порог намеренно мягкий: он ловит опечатку в подписи, а не выброс.
THOUSAND_SCALE = 1000.0
IMPLAUSIBLE_RATIO = 50.0

# Показатели-агрегаты и их подпункты — для проверки сходимости.
AGGREGATES: dict[str, tuple[str, ...]] = {
    "products_total": (
        "products_modules",
        "products_masterclasses",
        "products_cpd",
        "products_retraining",
        "products_extra",
    ),
    "ip_total": ("copyrights", "patents"),
    "revenue_total": ("revenue_science", "revenue_education", "revenue_other"),
}

AUDIENCE_PARTS: tuple[str, ...] = (
    "trained_modules",
    "trained_masterclasses",
    "trained_cpd",
    "trained_retraining",
)

SUPPLY_PARTS: tuple[str, ...] = (
    "dev_modules",
    "dev_masterclasses",
    "dev_cpd",
    "dev_retraining",
)


@dataclass
class QualityIssue:
    """Одна находка контроля качества исходных данных."""

    org_id: str
    severity: str  # "info" | "warning" | "error"
    kind: str
    indicator: str | None
    message: str


@dataclass
class Dataset:
    """Готовый к анализу датасет сети центров."""

    organizations: pd.DataFrame  # паспорт организации
    facts: pd.DataFrame  # факт отчётного периода, приведённые единицы
    baselines: pd.DataFrame  # значения предыдущего года (где заявлены)
    plan_shares: pd.Series  # плановый прирост из Формы 1, доля
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def org_ids(self) -> list[str]:
        return list(self.organizations.index)

    def quality_report(self) -> dict:
        """Сводка контроля качества для README и API."""
        by_severity: dict[str, int] = {}
        for issue in self.issues:
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
        filled = self.facts.notna().mean(axis=None)
        return {
            "organizations": int(len(self.organizations)),
            "indicators": int(self.facts.shape[1]),
            "cell_coverage": round(float(filled), 4),
            "issues_total": len(self.issues),
            "issues_by_severity": by_severity,
            "issues": [asdict(i) for i in self.issues],
        }


def _org_id(source_file: str) -> str:
    """Устойчивый идентификатор организации из имени файла."""
    stem = Path(source_file).stem
    slug = re.sub(r"[^0-9a-zA-Zа-яА-ЯёЁ]+", "-", stem).strip("-").lower()
    return slug or stem.lower()


def _short_name(source_file: str) -> str:
    stem = Path(source_file).stem
    return SHORT_NAMES.get(stem, stem)


def _normalize_monetary(
    facts: pd.DataFrame, hints: pd.DataFrame, issues: list[QualityIssue]
) -> pd.DataFrame:
    """Приводит денежные показатели к рублям, отбраковывая неверные подписи."""
    monetary = [i.key for i in INDICATORS if i.monetary]
    result = facts.copy()

    for key in monetary:
        if key not in result.columns:
            continue
        column = result[key]
        flagged = hints[key] == "thousand" if key in hints.columns else pd.Series(False, index=column.index)
        if not flagged.any():
            continue
        # Эталон масштаба — организации, подписавшие строку рублями.
        reference = column[~flagged].replace(0, np.nan).median()
        for org_id in column.index[flagged]:
            value = column.loc[org_id]
            if pd.isna(value) or value == 0:
                continue
            scaled = value * THOUSAND_SCALE
            if pd.notna(reference) and reference > 0 and scaled / reference > IMPLAUSIBLE_RATIO:
                issues.append(
                    QualityIssue(
                        org_id=org_id,
                        severity="warning",
                        kind="unit_label_mismatch",
                        indicator=key,
                        message=(
                            f"строка подписана «тыс. рублей», но при переводе значение "
                            f"{scaled:,.0f} ₽ превышает медиану сети в "
                            f"{scaled / reference:,.0f} раз — подпись признана ошибочной, "
                            f"значение оставлено в рублях"
                        ).replace(",", " "),
                    )
                )
                continue
            result.loc[org_id, key] = scaled
            issues.append(
                QualityIssue(
                    org_id=org_id,
                    severity="info",
                    kind="unit_normalized",
                    indicator=key,
                    message=f"тыс. рублей → рубли: {value:g} → {scaled:,.0f} ₽".replace(",", " "),
                )
            )
    return result


def _check_aggregates(facts: pd.DataFrame, issues: list[QualityIssue]) -> None:
    """Сверяет агрегированные строки с суммой их подпунктов."""
    for parent, children in AGGREGATES.items():
        present = [c for c in children if c in facts.columns]
        if parent not in facts.columns or not present:
            continue
        parts = facts[present].sum(axis=1, skipna=True)
        for org_id in facts.index:
            total = facts.loc[org_id, parent]
            if pd.isna(total):
                continue
            diff = parts.loc[org_id] - total
            # Допуск: 1 единица или 1 % — на округления в рублёвых строках.
            tolerance = max(1.0, abs(total) * 0.01)
            if abs(diff) > tolerance:
                issues.append(
                    QualityIssue(
                        org_id=org_id,
                        severity="warning",
                        kind="aggregate_mismatch",
                        indicator=parent,
                        message=(
                            f"сумма подпунктов {parts.loc[org_id]:,.0f} не сходится "
                            f"с итогом {total:,.0f} (расхождение {diff:+,.0f})"
                        ).replace(",", " "),
                    )
                )


def _impute_missing(facts: pd.DataFrame, issues: list[QualityIssue]) -> pd.DataFrame:
    """Незаполненные счётные строки трактуются как ноль — с явной пометкой.

    В шаблоне пустая ячейка означает «деятельности не было»: организации,
    не ведущие курсы переподготовки, просто не заполняют строку. Подмена на
    ноль корректна для счётных показателей и обязательно логируется.
    """
    result = facts.copy()
    for key in result.columns:
        missing = result[key].isna()
        for org_id in result.index[missing]:
            issues.append(
                QualityIssue(
                    org_id=org_id,
                    severity="info",
                    kind="imputed_zero",
                    indicator=key,
                    message=f"строка «{BY_KEY[key].title}» не заполнена → 0",
                )
            )
        result[key] = result[key].fillna(0.0)
    return result


def build_dataset(source_dir: Path | str) -> Dataset:
    """Разбирает каталог отчётов и собирает аналитический датасет."""
    source_dir = Path(source_dir)
    reports: list[ParsedReport] = parse_directory(source_dir)
    if not reports:
        raise FileNotFoundError(f"в каталоге {source_dir} не найдено книг отчётов")

    keys = [i.key for i in INDICATORS]
    org_rows, fact_rows, base_rows, hint_rows, plan_rows = [], [], [], [], []
    issues: list[QualityIssue] = []

    for report in reports:
        org_id = _org_id(report.source_file)
        org_rows.append(
            {
                "org_id": org_id,
                "short_name": _short_name(report.source_file),
                "full_name": report.organization or _short_name(report.source_file),
                "center": report.center,
                "year": report.year,
                "report_date": report.report_date,
                "source_file": report.source_file,
            }
        )
        fact_rows.append({"org_id": org_id, **{k: report.values[k].fact if k in report.values else None for k in keys}})
        base_rows.append({"org_id": org_id, **{k: report.values[k].baseline if k in report.values else None for k in keys}})
        hint_rows.append({"org_id": org_id, **{k: report.values[k].unit_hint if k in report.values else "unit" for k in keys}})
        growth = report.values.get("events_growth_rate")
        plan_rows.append({"org_id": org_id, "plan_share": growth.plan_pct if growth else None})

        for warning in report.warnings:
            issues.append(
                QualityIssue(org_id=org_id, severity="warning", kind="parse", indicator=None, message=warning)
            )

    organizations = pd.DataFrame(org_rows).set_index("org_id")
    facts = pd.DataFrame(fact_rows).set_index("org_id").astype(float)
    baselines = pd.DataFrame(base_rows).set_index("org_id").astype(float)
    hints = pd.DataFrame(hint_rows).set_index("org_id")
    plan_shares = pd.DataFrame(plan_rows).set_index("org_id")["plan_share"].astype(float)

    facts = _normalize_monetary(facts, hints, issues)
    baselines = _normalize_monetary(baselines, hints, [])  # база: без дублей в отчёте
    _check_aggregates(facts, issues)
    facts = _impute_missing(facts, issues)

    # Производные суммы, на которых держится вся дальнейшая аналитика.
    facts["audience_total"] = facts[list(AUDIENCE_PARTS)].sum(axis=1)
    facts["supply_total"] = facts[list(SUPPLY_PARTS)].sum(axis=1)
    baselines["supply_total"] = baselines[list(SUPPLY_PARTS)].sum(axis=1)

    return Dataset(
        organizations=organizations,
        facts=facts,
        baselines=baselines,
        plan_shares=plan_shares,
        issues=issues,
    )


def export(dataset: Dataset, out_dir: Path) -> dict[str, Path]:
    """Выгружает датасет в CSV/JSON для воспроизводимости и внешних инструментов."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "organizations": out_dir / "organizations.csv",
        "facts": out_dir / "facts.csv",
        "baselines": out_dir / "baselines.csv",
        "quality": out_dir / "quality_report.json",
    }
    dataset.organizations.to_csv(paths["organizations"], encoding="utf-8")
    dataset.facts.to_csv(paths["facts"], encoding="utf-8")
    dataset.baselines.to_csv(paths["baselines"], encoding="utf-8")
    paths["quality"].write_text(
        json.dumps(dataset.quality_report(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return paths
