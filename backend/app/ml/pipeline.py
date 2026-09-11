"""Сборка всех моделей в единый аналитический слой.

Пайплайн считается один раз при старте приложения и держится в памяти:
исходных данных двадцать строк, полный пересчёт занимает единицы секунд,
поэтому кэш проще и надёжнее инкрементальных обновлений.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import pandas as pd

from app.ingest.dataset import Dataset, build_dataset
from app.ml import anomalies as anomaly_module
from app.ml.clustering import ClusteringResult, run_clustering
from app.ml.features import FeatureSpace, build_features, build_profile_table
from app.ml.forecast import REPORTED_MONTHS, YEAR_MONTHS, build_plan_status
from app.ml.recommender import build_recommendations, network_summary
from app.ml.validation import ValidationReport, validate_clustering, validate_recommendations

log = logging.getLogger(__name__)


@dataclass
class Analytics:
    """Полный результат аналитического слоя."""

    dataset: Dataset
    features: FeatureSpace
    profile: pd.DataFrame
    clustering: ClusteringResult
    validation: ValidationReport
    co_assignment: pd.DataFrame
    plan: pd.DataFrame
    recommendations: pd.DataFrame
    recommendation_stability: dict
    anomalies: pd.DataFrame
    build_seconds: float

    @property
    def names(self) -> pd.Series:
        return self.dataset.organizations["short_name"]

    def cluster_of(self, org_id: str) -> int:
        return int(self.clustering.labels.loc[org_id])

    def cluster_members(self, cluster_id: int) -> list[str]:
        labels = self.clustering.labels
        return labels.index[labels == cluster_id].tolist()


def build_analytics(source_dir: Path, validate: bool = True) -> Analytics:
    """Прогоняет весь конвейер: данные → признаки → модели → выводы."""
    started = time.perf_counter()

    dataset = build_dataset(source_dir)
    features = build_features(dataset)
    profile = build_profile_table(dataset)
    clustering = run_clustering(features)
    plan = build_plan_status(dataset)
    names = dataset.organizations["short_name"]

    # Контроль качества идёт до рекомендаций: организации с расхождениями в
    # отчёте должны быть известны раньше, чем по ним считается резерв сети.
    anomalies = anomaly_module.detect(dataset.facts, profile, features, names)
    flagged = anomaly_module.flagged_orgs(anomalies)

    recommendations = build_recommendations(
        profile, dataset.facts, clustering.labels, plan, names, flagged=flagged
    )

    if validate:
        report, co_assignment = validate_clustering(features, clustering)
        stability = validate_recommendations(
            features,
            clustering,
            partial(
                build_recommendations,
                profile,
                dataset.facts,
                plan=plan,
                names=names,
                flagged=flagged,
            ),
            recommendations,
        )
    else:
        report, co_assignment, stability = _empty_validation(clustering)

    elapsed = time.perf_counter() - started
    log.info("аналитика собрана за %.2f с", elapsed)

    return Analytics(
        dataset=dataset,
        features=features,
        profile=profile,
        clustering=clustering,
        validation=report,
        co_assignment=co_assignment,
        plan=plan,
        recommendations=recommendations,
        recommendation_stability=stability,
        anomalies=anomalies,
        build_seconds=round(elapsed, 3),
    )


def _empty_validation(clustering: ClusteringResult) -> tuple[ValidationReport, pd.DataFrame, dict]:
    """Заглушка валидации для быстрых запусков без проверок."""
    report = ValidationReport(
        observed_silhouette=0.0,
        permutation_mean=0.0,
        permutation_std=0.0,
        permutation_p_value=1.0,
        effect_size=0.0,
        loo_mean_ari=0.0,
        loo_min_ari=0.0,
        membership_confidence={},
        unstable_members=[],
        verdict="валидация отключена",
    )
    index = list(clustering.labels.index)
    return report, pd.DataFrame(0.0, index=index, columns=index), {}


# Показатели, для которых строится динамика «2025 → 9 месяцев 2026 → прогноз года».
# Ключ совпадает с идентификатором переключателя на витрине.
DYNAMIC_METRICS: list[tuple[str, str, str, str]] = [
    ("audience", "Посещаемость", "audience_total", "чел."),
    ("formats", "Мероприятия", "supply_total", "ед."),
    ("products", "Арт-продукты", "products_total", "раб."),
    ("revenue", "Платные услуги", "revenue_total", "₽"),
]


def dynamics(analytics: Analytics) -> list[dict]:
    """Динамика показателей сети по тому, что действительно есть в отчётности.

    База 2025 года заполнена не у всех показателей и не у всех организаций,
    поэтому темп считается только по сопоставимому кругу — центрам, у которых
    база есть. Показатели без базы отдаются с `baseline_2025 = None`: витрина
    обязана показать это как «сравнивать не с чем», а не подставить число.

    Отчётный факт накоплен за девять месяцев, а база — за полный год, поэтому
    отдаются два темпа: прямой (заведомо заниженный, девять месяцев против
    двенадцати) и приведённый к году по текущему темпу.
    """
    facts = analytics.dataset.facts
    baselines = analytics.dataset.baselines
    plan = analytics.plan
    year_factor = YEAR_MONTHS / REPORTED_MONTHS

    rows: list[dict] = []
    for key, label, column, unit in DYNAMIC_METRICS:
        fact_total = float(facts[column].sum())
        run_rate = fact_total * year_factor

        has_base = baselines[column] > 0 if column in baselines.columns else None
        covered = int(has_base.sum()) if has_base is not None else 0

        if covered:
            base_total = float(baselines.loc[has_base, column].sum())
            fact_comparable = float(facts.loc[has_base, column].sum())
            growth_ytd = fact_comparable / base_total - 1.0
            growth_year = fact_comparable * year_factor / base_total - 1.0
        else:
            base_total = None
            fact_comparable = None
            growth_ytd = None
            growth_year = None

        # Цель года есть только там, где её задаёт Форма 1 — прирост числа
        # мероприятий. Для остальных показателей плановой величины не существует.
        target = round(float(plan["target_2026"].sum()), 2) if key == "formats" else None

        rows.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "baseline_2025": round(base_total, 2) if base_total is not None else None,
                "baseline_orgs": covered,
                "baseline_coverage": round(covered / len(facts), 3) if len(facts) else 0.0,
                "fact_comparable": round(fact_comparable, 2) if fact_comparable is not None else None,
                "fact_ytd": round(fact_total, 2),
                "run_rate_year": round(run_rate, 2),
                "growth_ytd": round(growth_ytd, 4) if growth_ytd is not None else None,
                "growth_year": round(growth_year, 4) if growth_year is not None else None,
                "target_2026": target,
                "reported_months": REPORTED_MONTHS,
            }
        )

    return rows


def overview(analytics: Analytics) -> dict:
    """Сводка верхнего уровня по всей сети."""
    facts = analytics.dataset.facts
    plan = analytics.plan

    return {
        "organizations": int(len(facts)),
        "audience_total": int(facts["audience_total"].sum()),
        "formats_total": int(facts["supply_total"].sum()),
        "products_total": int(facts["products_total"].sum()),
        "residents_total": int(facts["residents_total"].sum()),
        "revenue_total": float(facts["revenue_total"].sum()),
        "publications_total": int(facts["media_publications"].sum()),
        "federal_events_total": int(facts["federal_events"].sum()),
        "ip_total": int(facts["ip_total"].sum()),
        "median_audience_per_format": round(float(analytics.profile["audience_per_format"].median()), 2),
        "median_product_rate": round(float(analytics.profile["product_rate"].median()), 3),
        "plan_status": {str(k): int(v) for k, v in plan["status"].value_counts().items()},
        "plan_at_risk": int((plan["status"].isin(["риск", "срыв"])).sum()),
        "clusters": analytics.clustering.k,
        "recommendations": network_summary(analytics.recommendations),
        "anomalies": int(len(analytics.anomalies)),
        "data_quality": analytics.dataset.quality_report()["issues_by_severity"],
        "dynamics": dynamics(analytics),
        "build_seconds": analytics.build_seconds,
    }
