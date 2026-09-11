"""Поиск аномалий в отчётности сети.

Две разные задачи решаются здесь раздельно, потому что и реагировать на них
нужно по-разному.

    Статистические выбросы — центр резко отличается от сети по показателю.
    Это не ошибка: так выглядит и лидер, и провал. Задача — заметить.

    Внутренние противоречия — цифры внутри одного отчёта не согласуются
    между собой (мероприятий больше, чем участников; резидентов больше, чем
    обучено). Это почти всегда дефект заполнения, и он обесценивает любые
    выводы по этому центру, пока не разобран.

Устойчивость к выбросам обязательна: в сети из двадцати наблюдений один
экстремальный отчёт сдвигает среднее и стандартное отклонение так, что метод
перестаёт видеть сам этот выброс. Поэтому используется медиана и MAD.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ml.features import FeatureSpace

RANDOM_STATE = 42

# Порог робастной z-оценки. 3.5 — классический порог Иглвича–Хоаглина для
# модифицированной z-оценки на основе MAD.
ROBUST_Z_THRESHOLD = 3.5
MAD_TO_SIGMA = 0.6745  # множитель, приводящий MAD к масштабу стандартного отклонения

# Показатели, по которым ищутся выбросы, и их человекочитаемые названия.
WATCHED_METRICS: dict[str, str] = {
    "audience_total": "Аудитория",
    "supply_total": "Число форматов",
    "audience_per_format": "Участников на формат",
    "product_rate": "Продуктов на участника",
    "revenue_per_participant": "Выручка на участника",
    "publicity_per_format": "Публикаций на формат",
}


@dataclass
class Anomaly:
    """Одна находка: выброс или противоречие в отчёте."""

    org_id: str
    kind: str  # "outlier" | "inconsistency" | "multivariate"
    metric: str | None
    severity: str  # "info" | "warning" | "error"
    value: float | None
    reference: float | None
    score: float
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


def robust_z(series: pd.Series) -> pd.Series:
    """Модифицированная z-оценка на медиане и MAD.

    Обычная z-оценка здесь не годится: выброс входит и в среднее, и в
    стандартное отклонение, маскируя сам себя. Медиана и MAD от единичного
    экстремума не сдвигаются.
    """
    values = series.astype(float)
    median = values.median()
    mad = (values - median).abs().median()
    if mad <= 0:
        # Вырожденный случай: больше половины значений совпадают. Откатываемся
        # к среднему абсолютному отклонению, иначе оценка обращается в бесконечность.
        mad = (values - median).abs().mean()
    if mad <= 0:
        return pd.Series(0.0, index=values.index)
    return MAD_TO_SIGMA * (values - median) / mad


def find_outliers(profile: pd.DataFrame, names: pd.Series) -> list[Anomaly]:
    """Одномерные выбросы по наблюдаемым показателям."""
    found: list[Anomaly] = []
    for metric, label in WATCHED_METRICS.items():
        if metric not in profile.columns:
            continue
        scores = robust_z(profile[metric])
        median = float(profile[metric].median())
        for org_id, score in scores.items():
            if abs(score) < ROBUST_Z_THRESHOLD:
                continue
            value = float(profile.loc[org_id, metric])
            direction = "выше" if score > 0 else "ниже"
            found.append(
                Anomaly(
                    org_id=str(org_id),
                    kind="outlier",
                    metric=metric,
                    severity="warning" if abs(score) >= 2 * ROBUST_Z_THRESHOLD else "info",
                    value=round(value, 2),
                    reference=round(median, 2),
                    score=round(float(score), 2),
                    message=(
                        f"«{label}» — {value:,.2f} против медианы сети {median:,.2f}: "
                        f"{direction} нормы на {abs(score):.1f} робастных отклонения"
                    ).replace(",", " "),
                )
            )
    return found


def find_inconsistencies(facts: pd.DataFrame, profile: pd.DataFrame) -> list[Anomaly]:
    """Логические противоречия внутри отчёта одной организации."""
    found: list[Anomaly] = []

    for org_id in facts.index:
        audience = float(facts.loc[org_id, "audience_total"])
        supply = float(facts.loc[org_id, "supply_total"])
        residents = float(facts.loc[org_id, "residents_total"])
        products = float(facts.loc[org_id, "products_total"])
        revenue = float(facts.loc[org_id, "revenue_total"])

        # Мероприятий больше, чем участников: формат физически не мог состояться
        # в заявленном виде либо аудитория посчитана не по всем мероприятиям.
        if supply > 0 and audience > 0 and audience < supply:
            found.append(
                Anomaly(
                    org_id=str(org_id),
                    kind="inconsistency",
                    metric="audience_per_format",
                    severity="error",
                    value=round(audience / supply, 3),
                    reference=1.0,
                    score=round(supply / max(audience, 1), 2),
                    message=(
                        f"разработано {supply:,.0f} форматов при {audience:,.0f} обученных: "
                        f"меньше одного участника на формат — вероятна ошибка в строках 3.1–3.4 "
                        f"Формы 2 либо в приложении к Форме 1"
                    ).replace(",", " "),
                )
            )

        # Резидентов больше, чем всех обученных: строка 3 шире суммы 3.1–3.4,
        # но кратный разрыв означает разный контур учёта.
        if audience > 0 and residents > audience * 2:
            found.append(
                Anomaly(
                    org_id=str(org_id),
                    kind="inconsistency",
                    metric="resident_rate",
                    severity="warning",
                    value=round(residents, 0),
                    reference=round(audience, 0),
                    score=round(residents / audience, 2),
                    message=(
                        f"резидентов {residents:,.0f} при {audience:,.0f} обученных "
                        f"(строка 3 против суммы 3.1–3.4): показатели ведутся по разным контурам"
                    ).replace(",", " "),
                )
            )

        # Продукты есть, а обучения нет — результат не привязан к аудитории.
        if products > 0 and audience == 0:
            found.append(
                Anomaly(
                    org_id=str(org_id),
                    kind="inconsistency",
                    metric="product_rate",
                    severity="warning",
                    value=round(products, 0),
                    reference=0.0,
                    score=float(products),
                    message=(
                        f"создано {products:,.0f} творческих продуктов при нулевой обученной "
                        f"аудитории: результат не сводится с охватом"
                    ).replace(",", " "),
                )
            )

        # Выручка без аудитории и без продуктов — услуга оказана вне учёта.
        if revenue > 0 and audience == 0 and products == 0:
            found.append(
                Anomaly(
                    org_id=str(org_id),
                    kind="inconsistency",
                    metric="revenue_total",
                    severity="warning",
                    value=round(revenue, 0),
                    reference=0.0,
                    score=1.0,
                    message=(
                        f"объём услуг {revenue:,.0f} ₽ при нулевой аудитории и нулевом "
                        f"результате: выручка не привязана к мероприятиям"
                    ).replace(",", " "),
                )
            )

    return found


def find_multivariate(features: FeatureSpace, contamination: float = 0.15) -> list[Anomaly]:
    """Многомерные выбросы: нетипичное сочетание показателей.

    Одномерные проверки не видят центр, у которого каждый показатель в норме,
    но их сочетание в сети не встречается. Isolation Forest оценивает именно
    это — насколько легко наблюдение отделяется от остальных.
    """
    model = IsolationForest(
        n_estimators=300, contamination=contamination, random_state=RANDOM_STATE
    )
    matrix = features.matrix.to_numpy()
    model.fit(matrix)
    scores = pd.Series(model.decision_function(matrix), index=features.matrix.index)
    flags = pd.Series(model.predict(matrix), index=features.matrix.index)

    found: list[Anomaly] = []
    for org_id in features.matrix.index:
        if flags.loc[org_id] != -1:
            continue
        found.append(
            Anomaly(
                org_id=str(org_id),
                kind="multivariate",
                metric=None,
                severity="info",
                value=None,
                reference=None,
                score=round(float(scores.loc[org_id]), 4),
                message=(
                    "сочетание показателей не встречается у других центров сети — "
                    "профиль стоит рассмотреть отдельно, автоматические эталоны "
                    "для него менее надёжны"
                ),
            )
        )
    return found


def detect(
    facts: pd.DataFrame, profile: pd.DataFrame, features: FeatureSpace, names: pd.Series
) -> pd.DataFrame:
    """Полный прогон детекторов аномалий."""
    found = find_inconsistencies(facts, profile)
    found += find_outliers(profile, names)
    found += find_multivariate(features)

    if not found:
        return pd.DataFrame(
            columns=["org_id", "kind", "metric", "severity", "value", "reference", "score", "message"]
        )

    order = {"error": 0, "warning": 1, "info": 2}
    table = pd.DataFrame([a.as_dict() for a in found])
    table["_rank"] = table["severity"].map(order)
    return table.sort_values(["_rank", "org_id"]).drop(columns="_rank").reset_index(drop=True)


def flagged_orgs(anomalies: pd.DataFrame) -> set[str]:
    """Организации, чьи данные требуют проверки до принятия решений по ним."""
    if anomalies.empty:
        return set()
    serious = anomalies[anomalies["severity"].isin({"error", "warning"})]
    return set(serious["org_id"].astype(str))
