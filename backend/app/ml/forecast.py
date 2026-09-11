"""Прогноз исполнения года и контроль плановых обязательств.

Отчёт сдаётся нарастающим итогом за девять месяцев, а обязательство Формы 1
задано на год: прирост числа мероприятий на 10 % к предыдущему году. Модуль
отвечает на три вопроса: где центр находится сейчас, куда он придёт при
текущем темпе и что нужно сделать за оставшийся квартал.

Экстраполяция сознательно линейная. Сезонность вузовского года (спад летом,
пик осенью) достоверно оценить не на чем: в данных один срез, а не ряд.
Поэтому линейный прогноз подаётся как консервативная нижняя оценка, а рядом
считается требуемый темп остатка года — величина, не зависящая от гипотез
о сезонности.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from app.ingest.dataset import Dataset

# Отчётный период — январь–сентябрь (ежеквартальная форма, срок 10 сентября).
REPORTED_MONTHS = 9
YEAR_MONTHS = 12


@dataclass
class PlanStatus:
    """Состояние плана по одной организации."""

    org_id: str
    baseline_2025: float  # факт предыдущего года
    target_growth: float  # плановый прирост, доля
    target_2026: float  # цель года в единицах
    fact_ytd: float  # факт за отчётный период
    completion: float  # доля цели, закрытая на сегодня
    run_rate_forecast: float  # прогноз года при текущем темпе
    forecast_gap: float  # разрыв прогноза с целью
    required_remaining: float  # сколько нужно за оставшийся период
    required_monthly_rate: float  # требуемый темп, ед./мес.
    current_monthly_rate: float  # текущий темп, ед./мес.
    status: str  # "опережение" | "в графике" | "риск" | "срыв"

    def as_dict(self) -> dict:
        return asdict(self)


def _status(completion: float, forecast_ratio: float, has_baseline: bool) -> str:
    """Классифицирует положение дел по прогнозу достижения цели."""
    if not has_baseline:
        # Центр запущен в отчётном году: прироста «к предыдущему году» нет,
        # сравнивать не с чем — это не срыв плана, а отсутствие базы.
        return "без базы"
    if forecast_ratio >= 1.10:
        return "опережение"
    if forecast_ratio >= 1.0:
        return "в графике"
    if forecast_ratio >= 0.85:
        return "риск"
    return "срыв"


def build_plan_status(dataset: Dataset) -> pd.DataFrame:
    """Считает план-факт и прогноз года по каждой организации.

    Источник цели — строка 1 Формы 1: значение показателя за 2025 год и
    плановый прирост в процентах. Факт — суммарное число разработанных
    форматов за отчётный период (приложение к Форме 1).
    """
    facts = dataset.facts
    baselines = dataset.baselines

    rows: list[PlanStatus] = []
    for org_id in facts.index:
        baseline = float(baselines.loc[org_id, "events_growth_rate"])
        growth = float(facts.loc[org_id, "events_growth_rate"])  # здесь лежит факт строки 1
        plan_share = _plan_share(dataset, org_id)

        # Факт года берём из приложения: сумма разработанных форматов.
        fact_ytd = float(facts.loc[org_id, "supply_total"])
        baseline_supply = float(baselines.loc[org_id, "supply_total"])
        # Базой считается значение 2025 года; если приложение его не содержит,
        # опираемся на строку 1 Формы 1, где оно продублировано.
        base = baseline_supply if baseline_supply > 0 else baseline
        target = base * (1.0 + plan_share)

        current_rate = fact_ytd / REPORTED_MONTHS
        run_rate = current_rate * YEAR_MONTHS
        required_remaining = max(0.0, target - fact_ytd)
        remaining_months = YEAR_MONTHS - REPORTED_MONTHS
        has_baseline = base > 0
        forecast_ratio = run_rate / target if target > 0 else 0.0
        completion = fact_ytd / target if target > 0 else (1.0 if fact_ytd > 0 else 0.0)

        rows.append(
            PlanStatus(
                org_id=org_id,
                baseline_2025=base,
                target_growth=plan_share,
                target_2026=round(target, 2),
                fact_ytd=fact_ytd,
                completion=round(completion, 4),
                run_rate_forecast=round(run_rate, 2),
                forecast_gap=round(run_rate - target, 2),
                required_remaining=round(required_remaining, 2),
                required_monthly_rate=round(required_remaining / remaining_months, 3),
                current_monthly_rate=round(current_rate, 3),
                status=_status(completion, forecast_ratio, has_baseline),
            )
        )

    return pd.DataFrame([r.as_dict() for r in rows]).set_index("org_id")


def _plan_share(dataset: Dataset, org_id: str) -> float:
    """Плановый прирост из Формы 1 (доля, а не проценты).

    В шаблоне значение записано долей (0.1 = 10 %), но часть организаций
    заполняет колонку целым числом процентов. Значения больше единицы
    трактуются как проценты.
    """
    raw = dataset.plan_shares.get(org_id)
    if raw is None or pd.isna(raw):
        return 0.10  # значение по умолчанию из шаблона госпрограммы
    value = float(raw)
    return value / 100.0 if value > 1.0 else value
