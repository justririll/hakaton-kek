"""Проверка того, что модели говорят о данных, а не о самих себе.

Кластеризация без валидации всегда «работает»: алгоритм вернёт k групп на
любых данных, включая шум. Поэтому результат проверяется тремя способами, и
каждый отвечает на свой вопрос.

    Есть ли структура вообще? — перестановочный тест: силуэт реального
    разбиения сравнивается с распределением силуэтов случайных разбиений
    того же размера. Если реальное не выделяется, кластеров нет.

    Воспроизводима ли структура? — leave-one-out: каждый центр по очереди
    исключается, сеть кластеризуется заново, результат сверяется с полным
    решением. Заодно считается, как часто каждая пара центров попадает в
    один кластер — это показывает, у кого принадлежность спорная.

    Устойчивы ли выводы? — доля рекомендаций, которые сохраняются при
    исключении любого одного центра. Рекомендация, живущая только в одном
    конкретном составе сети, не годится для управленческого решения.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_score

from app.ml.clustering import RANDOM_STATE, ClusteringResult, _fit_labels, _prepare
from app.ml.features import FeatureSpace

PERMUTATIONS = 2000


@dataclass
class ValidationReport:
    """Сводка проверок модели кластеризации."""

    observed_silhouette: float
    permutation_mean: float
    permutation_std: float
    permutation_p_value: float
    effect_size: float  # на сколько стандартных отклонений шума выше реальный силуэт
    loo_mean_ari: float
    loo_min_ari: float
    membership_confidence: dict[str, float]
    unstable_members: list[str]
    verdict: str

    def as_dict(self) -> dict:
        return asdict(self)


def permutation_test(data: np.ndarray, labels: np.ndarray, rounds: int = PERMUTATIONS) -> dict:
    """Сравнивает силуэт разбиения со случайными разбиениями того же состава.

    Перемешиваются именно метки, а не данные: так сохраняются размеры
    кластеров, и тест проверяет ровно одно — несёт ли конкретное распределение
    объектов по группам больше информации, чем произвольное.
    """
    observed = float(silhouette_score(data, labels))
    rng = np.random.default_rng(RANDOM_STATE)

    shuffled = labels.copy()
    samples = np.empty(rounds, dtype=float)
    for i in range(rounds):
        rng.shuffle(shuffled)
        samples[i] = silhouette_score(data, shuffled)

    mean = float(samples.mean())
    std = float(samples.std(ddof=1))
    # Поправка на конечность выборки: p не может быть равно нулю.
    p_value = float((np.sum(samples >= observed) + 1) / (rounds + 1))

    return {
        "observed": round(observed, 4),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "p_value": round(p_value, 5),
        "effect_size": round((observed - mean) / std, 2) if std > 0 else 0.0,
    }


def leave_one_out(features: FeatureSpace, k: int, algorithm: str = "kmeans") -> dict:
    """Перекластеризует сеть без каждого центра и сверяет с полным решением."""
    _, embedding, _, _ = _prepare(features)
    index = list(embedding.index)
    full_labels = pd.Series(_fit_labels(algorithm, embedding.to_numpy(), k), index=index)

    ari_scores: list[float] = []
    # Счётчики совместного попадания пар в один кластер по всем прогонам.
    # Матрицы держатся в numpy: при 20 прогонах поэлементный обход через
    # pandas дал бы восемь тысяч обращений по меткам на ровном месте.
    size = len(index)
    position = {org_id: i for i, org_id in enumerate(index)}
    together = np.zeros((size, size))
    seen = np.zeros((size, size))

    for held_out in index:
        kept = [i for i in index if i != held_out]
        labels = _fit_labels(algorithm, embedding.loc[kept].to_numpy(), k)
        ari_scores.append(float(adjusted_rand_score(full_labels.loc[kept], labels)))

        kept_positions = np.array([position[i] for i in kept])
        grid = np.ix_(kept_positions, kept_positions)
        together[grid] += (labels[:, None] == labels[None, :]).astype(float)
        seen[grid] += 1.0

    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.divide(together, seen, out=np.zeros_like(together), where=seen > 0)
    co_assignment = pd.DataFrame(ratio, index=index, columns=index)

    # Уверенность принадлежности: как часто центр оказывается в одной группе
    # со «своими» — теми, с кем он объединён в полном решении.
    confidence: dict[str, float] = {}
    for org_id in index:
        peers = [i for i in index if i != org_id and full_labels.loc[i] == full_labels.loc[org_id]]
        confidence[org_id] = round(float(co_assignment.loc[org_id, peers].mean()), 3) if peers else 0.0

    return {
        "mean_ari": round(float(np.mean(ari_scores)), 4),
        "min_ari": round(float(np.min(ari_scores)), 4),
        "co_assignment": co_assignment.round(3),
        "membership_confidence": confidence,
    }


def _verdict(p_value: float, mean_ari: float) -> str:
    """Итоговая формулировка: можно ли опираться на разбиение."""
    if p_value >= 0.05:
        return "структура неотличима от случайной — кластеры показывать нельзя"
    if mean_ari >= 0.75:
        return "структура значима и устойчива — разбиение пригодно для решений"
    if mean_ari >= 0.5:
        return "структура значима, но границы отдельных кластеров подвижны — выводы по спорным центрам проверять вручную"
    return "структура значима, однако состав кластеров сильно зависит от выборки — использовать только как навигацию"


def validate_clustering(
    features: FeatureSpace, result: ClusteringResult, unstable_threshold: float = 0.6
) -> tuple[ValidationReport, pd.DataFrame]:
    """Полная валидация кластеризации: значимость, устойчивость, спорные центры."""
    _, embedding, _, _ = _prepare(features)
    data = embedding.to_numpy()

    permutation = permutation_test(data, result.labels.to_numpy())
    loo = leave_one_out(features, result.k, result.algorithm)

    unstable = [
        org_id
        for org_id, value in loo["membership_confidence"].items()
        if value < unstable_threshold
    ]

    report = ValidationReport(
        observed_silhouette=permutation["observed"],
        permutation_mean=permutation["mean"],
        permutation_std=permutation["std"],
        permutation_p_value=permutation["p_value"],
        effect_size=permutation["effect_size"],
        loo_mean_ari=loo["mean_ari"],
        loo_min_ari=loo["min_ari"],
        membership_confidence=loo["membership_confidence"],
        unstable_members=unstable,
        verdict=_verdict(permutation["p_value"], loo["mean_ari"]),
    )
    return report, loo["co_assignment"]


def validate_recommendations(
    features: FeatureSpace,
    result: ClusteringResult,
    build_fn,
    baseline: pd.DataFrame,
) -> dict:
    """Доля рекомендаций, переживающих исключение любого одного центра.

    `build_fn(labels)` должна вернуть таблицу рекомендаций для переданного
    разбиения. Устойчивой считается рекомендация, которая воспроизводится
    (та же организация, тот же тип, тот же формат) в подавляющем большинстве
    прогонов — то есть не зависит от того, кто именно попал в эталонную группу.
    """
    _, embedding, _, _ = _prepare(features)
    index = list(embedding.index)

    def key(row) -> tuple:
        return (row["org_id"], row["rec_type"], row["channel"])

    baseline_keys = {key(row) for _, row in baseline.iterrows()}
    if not baseline_keys:
        return {"total": 0, "stable_share": 0.0, "unstable": []}

    survived: dict[tuple, int] = {k: 0 for k in baseline_keys}
    runs = 0

    for held_out in index:
        kept = [i for i in index if i != held_out]
        labels = pd.Series(
            _fit_labels(result.algorithm, embedding.loc[kept].to_numpy(), result.k), index=kept
        )
        table = build_fn(labels)
        produced = {key(row) for _, row in table.iterrows()}
        runs += 1
        for candidate in baseline_keys:
            # Исключённый центр не может подтвердить рекомендацию сам о себе.
            if candidate[0] == held_out:
                survived[candidate] += 1
                continue
            if candidate in produced:
                survived[candidate] += 1

    rates = {k: v / runs for k, v in survived.items()}
    unstable = sorted(
        ({"org_id": k[0], "rec_type": k[1], "channel": k[2], "rate": round(v, 3)} for k, v in rates.items() if v < 0.8),
        key=lambda r: r["rate"],
    )
    return {
        "total": len(baseline_keys),
        "runs": runs,
        "stable_share": round(float(np.mean([v >= 0.8 for v in rates.values()])), 4),
        "mean_survival": round(float(np.mean(list(rates.values()))), 4),
        "unstable": unstable,
    }
