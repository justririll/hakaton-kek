"""Кластеризация аудиторных моделей центров.

Двадцать наблюдений — это мало, и честный ответ на вопрос «сколько кластеров»
здесь нельзя получить одним силуэтом: на малой выборке он шумит и почти всегда
поощряет k=2. Поэтому число кластеров выбирается по трём согласованным
критериям, а результат проверяется на устойчивость к составу выборки.

Пайплайн:
    1. стандартизация признаков;
    2. PCA до числа компонент, объясняющих заданную долю дисперсии;
    3. три алгоритма (KMeans, Ward, GMM) на одном и том же пространстве;
    4. выбор k по совокупности силуэта, Calinski–Harabasz, Davies–Bouldin
       и устойчивости (средний ARI на бутстрэп-подвыборках);
    5. автоматическое именование кластеров по профилю центроида.

Устойчивость здесь — не украшение: на n=20 разбиение, которое рассыпается при
удалении двух наблюдений, нельзя показывать как «сегменты аудитории».
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from app.ml.features import FeatureSpace

RANDOM_STATE = 42
PCA_VARIANCE_TARGET = 0.85
BOOTSTRAP_ROUNDS = 200
BOOTSTRAP_FRACTION = 0.8
BOOTSTRAP_N_INIT = 3  # перезапусков на одно разбиение внутри бутстрэпа

# Ограничения на разбиение. Силуэт и Calinski–Harabasz на малой выборке растут
# почти монотонно по k, поэтому без этих ограничений выбор упирается в верхнюю
# границу диапазона и порождает кластеры из одного объекта.
MIN_CLUSTER_SIZE = 2  # кластер из одного центра — это выброс, а не сегмент
MIN_OBJECTS_PER_CLUSTER = 4  # k <= n / 4: иначе сегменты нечем наполнить
# Правило парсимонии: среди разбиений, отстающих от лучшего не более чем на
# этот зазор, выбирается наименьшее k — простое решение предпочтительнее.
PARSIMONY_TOLERANCE = 0.05


def k_range(n_samples: int) -> range:
    """Рабочий диапазон числа кластеров для выборки размера n."""
    upper = max(2, min(6, n_samples // MIN_OBJECTS_PER_CLUSTER))
    return range(2, upper + 1)


@dataclass
class KCandidate:
    """Диагностика одного значения k."""

    k: int
    silhouette: float
    calinski_harabasz: float
    davies_bouldin: float
    stability: float  # средний ARI на бутстрэпе, 1.0 — идеально устойчиво
    balance: float  # отношение размеров наименьшего и наибольшего кластеров
    score: float  # сводная оценка, по которой выбирается k
    sizes: list[int]


@dataclass
class ClusterProfile:
    """Портрет одного кластера."""

    cluster_id: int
    name: str
    summary: str
    size: int
    members: list[str]
    centroid: dict[str, float]  # средние значения признаков (в z-шкале)
    distinctive: list[dict[str, object]]  # чем кластер отличается от сети
    mean_silhouette: float


@dataclass
class ClusteringResult:
    """Полный результат кластеризации — то, что отдаётся в API и в отчёт."""

    labels: pd.Series
    k: int
    algorithm: str
    candidates: list[KCandidate]
    profiles: list[ClusterProfile]
    embedding: pd.DataFrame  # координаты PCA для визуализации
    explained_variance: list[float]
    loadings: pd.DataFrame  # вклад признаков в компоненты
    agreement: dict[str, float]  # согласие алгоритмов между собой (ARI)
    silhouette_per_object: pd.Series
    dendrogram: dict[str, object]
    feature_z: pd.DataFrame = field(repr=False)  # z-шкала признаков


# --- подготовка пространства ---------------------------------------------------

def _prepare(features: FeatureSpace) -> tuple[pd.DataFrame, pd.DataFrame, PCA, np.ndarray]:
    """Стандартизует признаки и понижает размерность до PCA-пространства."""
    scaler = StandardScaler()
    scaled = pd.DataFrame(
        scaler.fit_transform(features.matrix),
        index=features.matrix.index,
        columns=features.matrix.columns,
    )

    full = PCA(random_state=RANDOM_STATE).fit(scaled)
    cumulative = np.cumsum(full.explained_variance_ratio_)
    n_components = int(np.searchsorted(cumulative, PCA_VARIANCE_TARGET) + 1)
    n_components = max(2, min(n_components, scaled.shape[1], scaled.shape[0] - 1))

    pca = PCA(n_components=n_components, random_state=RANDOM_STATE).fit(scaled)
    embedding = pd.DataFrame(
        pca.transform(scaled),
        index=scaled.index,
        columns=[f"pc{i + 1}" for i in range(n_components)],
    )
    return scaled, embedding, pca, full.explained_variance_ratio_


# --- алгоритмы ------------------------------------------------------------------

def _fit_labels(
    algorithm: str, data: np.ndarray, k: int, seed: int = RANDOM_STATE, n_init: int | None = None
) -> np.ndarray:
    """Разбиение на k кластеров выбранным алгоритмом.

    `n_init` понижается на бутстрэпе: там считаются тысячи разбиений, и полный
    набор перезапусков превращает диагностику в самый долгий шаг конвейера,
    не меняя результата — на двух десятках точек решение находится сразу.
    """
    if algorithm == "kmeans":
        return KMeans(n_clusters=k, n_init=n_init or 25, random_state=seed).fit_predict(data)
    if algorithm == "ward":
        return AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(data)
    if algorithm == "gmm":
        return GaussianMixture(
            n_components=k, covariance_type="diag", n_init=n_init or 10, random_state=seed
        ).fit_predict(data)
    raise ValueError(f"неизвестный алгоритм: {algorithm}")


def _stability(data: np.ndarray, k: int, algorithm: str, rng: np.random.Generator) -> float:
    """Устойчивость разбиения к составу выборки.

    На каждом раунде берутся две пересекающиеся подвыборки; кластеризация
    выполняется независимо, а согласие измеряется ARI на их пересечении.
    Так проверяется именно воспроизводимость структуры, а не совпадение
    подвыборки с полным решением.
    """
    n_samples = data.shape[0]
    size = max(k + 1, int(round(n_samples * BOOTSTRAP_FRACTION)))
    scores: list[float] = []

    for _ in range(BOOTSTRAP_ROUNDS):
        first = rng.choice(n_samples, size=size, replace=False)
        second = rng.choice(n_samples, size=size, replace=False)
        shared = np.intersect1d(first, second)
        if shared.size < k + 1:
            continue
        try:
            labels_first = _fit_labels(algorithm, data[first], k, n_init=BOOTSTRAP_N_INIT)
            labels_second = _fit_labels(algorithm, data[second], k, n_init=BOOTSTRAP_N_INIT)
        except ValueError:
            continue
        index_first = {idx: pos for pos, idx in enumerate(first)}
        index_second = {idx: pos for pos, idx in enumerate(second)}
        scores.append(
            adjusted_rand_score(
                [labels_first[index_first[i]] for i in shared],
                [labels_second[index_second[i]] for i in shared],
            )
        )
    return float(np.mean(scores)) if scores else 0.0


def _normalize(values: np.ndarray, higher_is_better: bool = True) -> np.ndarray:
    """Приводит метрику к шкале 0–1 внутри набора кандидатов."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.zeros_like(values)
    low, high = float(finite.min()), float(finite.max())
    if high - low < 1e-12:
        return np.ones_like(values) * 0.5
    scaled = (values - low) / (high - low)
    return scaled if higher_is_better else 1.0 - scaled


def evaluate_k(data: np.ndarray, algorithm: str = "kmeans") -> list[KCandidate]:
    """Считает диагностику для каждого k из рабочего диапазона."""
    rng = np.random.default_rng(RANDOM_STATE)
    rows = []
    for k in k_range(data.shape[0]):
        if k >= data.shape[0]:
            continue
        labels = _fit_labels(algorithm, data, k)
        if len(set(labels)) < 2:
            continue
        sizes = np.bincount(labels)
        if sizes.min() < MIN_CLUSTER_SIZE:
            # Разбиение выродилось: часть кластеров описывает единичные выбросы.
            continue
        rows.append(
            {
                "k": k,
                "silhouette": float(silhouette_score(data, labels)),
                "calinski_harabasz": float(calinski_harabasz_score(data, labels)),
                "davies_bouldin": float(davies_bouldin_score(data, labels)),
                "stability": _stability(data, k, algorithm, rng),
                "balance": float(sizes.min() / sizes.max()),
                "sizes": sorted(sizes.tolist(), reverse=True),
            }
        )

    if not rows:
        raise ValueError("не удалось построить ни одного разбиения")

    silhouettes = np.array([r["silhouette"] for r in rows])
    calinski = np.array([r["calinski_harabasz"] for r in rows])
    davies = np.array([r["davies_bouldin"] for r in rows])
    stability = np.array([r["stability"] for r in rows])
    balance = np.array([r["balance"] for r in rows])

    # Веса: силуэт и устойчивость важнее — первый отвечает за разделимость,
    # вторая за воспроизводимость. CH и DB добавлены как независимый контроль,
    # баланс — как защита от разбиений «один большой кластер и крошки».
    combined = (
        0.30 * _normalize(silhouettes)
        + 0.30 * _normalize(stability)
        + 0.15 * _normalize(calinski)
        + 0.15 * _normalize(davies, higher_is_better=False)
        + 0.10 * _normalize(balance)
    )

    return [
        KCandidate(
            k=row["k"],
            silhouette=round(row["silhouette"], 4),
            calinski_harabasz=round(row["calinski_harabasz"], 3),
            davies_bouldin=round(row["davies_bouldin"], 4),
            stability=round(row["stability"], 4),
            balance=round(row["balance"], 4),
            score=round(float(score), 4),
            sizes=row["sizes"],
        )
        for row, score in zip(rows, combined)
    ]


def select_k(candidates: list[KCandidate]) -> int:
    """Выбирает число кластеров по сводной оценке с поправкой на простоту.

    Берётся наименьшее k, отстающее от лучшего не более чем на
    `PARSIMONY_TOLERANCE`: если дробление сети на шесть сегментов почти не
    выигрывает у четырёх, показывать нужно четыре.
    """
    best = max(candidates, key=lambda c: c.score)
    threshold = best.score - PARSIMONY_TOLERANCE
    return min((c.k for c in candidates if c.score >= threshold), default=best.k)


# --- именование кластеров -------------------------------------------------------

# Словарь ярлыков: признак → как назвать кластер, если он по нему выделяется.
_LABELS: dict[str, tuple[str, str]] = {
    # признак: (высокое значение, низкое значение)
    "log_audience": ("массовый охват", "камерный формат"),
    "log_supply": ("широкая линейка форматов", "узкая линейка форматов"),
    "audience_per_format": ("крупные потоки", "штучная работа"),
    "product_rate": ("высокая отдача в продуктах", "низкая отдача в продуктах"),
    "resident_rate": ("сильное ядро резидентов", "слабое ядро резидентов"),
    "revenue_per_participant": ("платные услуги", "бесплатная модель"),
    "publicity_per_format": ("заметность в медиа", "тихая работа"),
    "clr_modules": ("ставка на образовательные модули", "без образовательных модулей"),
    "clr_masterclasses": ("ставка на мастер-классы", "без мастер-классов"),
    "clr_cpd": ("ставка на повышение квалификации", "без программ ПК"),
    "clr_retraining": ("ставка на переподготовку", "без переподготовки"),
}

# Готовые имена архетипов по доминирующей паре характеристик.
_ARCHETYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Массовые просветители", ("массовый охват", "крупные потоки")),
    ("Продуктовые мастерские", ("высокая отдача в продуктах", "сильное ядро резидентов")),
    ("Коммерческие студии", ("платные услуги", "высокая отдача в продуктах")),
    ("Медийные площадки", ("заметность в медиа",)),
    ("Профессиональные академии", ("ставка на повышение квалификации", "ставка на переподготовку")),
    ("Камерные лаборатории", ("камерный формат", "штучная работа")),
    ("Открытые бесплатные площадки", ("бесплатная модель",)),
    ("Широкопрофильные центры", ("широкая линейка форматов",)),
    ("Нишевые студии", ("узкая линейка форматов", "без мастер-классов")),
)


def _name_cluster(
    distinctive: list[dict[str, object]], fallback: int, taken: set[str]
) -> tuple[str, str]:
    """Подбирает уникальное имя и описание кластера по его отличиям от сети.

    Архетип выбирается по сильнейшей характеристике, ещё не занятой другим
    кластером: два сегмента с одинаковым названием ничего не объясняют.
    """
    traits = [str(d["label"]) for d in distinctive]
    summary = "; ".join(traits[:3]).capitalize() if traits else "—"

    ranked = sorted(
        (
            (position, name)
            for name, required in _ARCHETYPES
            if name not in taken
            for position, trait in enumerate(traits)
            if trait in required
        )
    )
    if ranked:
        return ranked[0][1], summary
    return f"Кластер {fallback + 1}", summary


def _describe(
    feature_z: pd.DataFrame, labels: pd.Series, descriptions: dict[str, str], top: int = 3
) -> list[ClusterProfile]:
    """Строит портрет каждого кластера: чем он отличается от остальной сети."""
    profiles: list[ClusterProfile] = []
    taken: set[str] = set()
    for cluster_id in sorted(labels.unique()):
        members = labels.index[labels == cluster_id]
        centroid = feature_z.loc[members].mean()

        # Отличие = насколько центроид кластера отстоит от центра всей сети.
        # Признаки уже в z-шкале, поэтому центр сети — ноль.
        ranked = centroid.reindex(centroid.abs().sort_values(ascending=False).index)
        distinctive = []
        for feature, value in ranked.head(top).items():
            high, low = _LABELS.get(str(feature), (str(feature), f"низкий {feature}"))
            distinctive.append(
                {
                    "feature": feature,
                    "description": descriptions.get(str(feature), str(feature)),
                    "z": round(float(value), 3),
                    "label": high if value >= 0 else low,
                }
            )

        name, summary = _name_cluster(distinctive, int(cluster_id), taken)
        taken.add(name)
        profiles.append(
            ClusterProfile(
                cluster_id=int(cluster_id),
                name=name,
                summary=summary,
                size=int(len(members)),
                members=list(members),
                centroid={k: round(float(v), 3) for k, v in centroid.items()},
                distinctive=distinctive,
                mean_silhouette=0.0,  # заполняется в `run_clustering`
            )
        )
    return profiles


def _dendrogram_payload(data: np.ndarray, labels: list[str]) -> dict[str, object]:
    """Данные дендрограммы Ward для отрисовки на фронтенде."""
    matrix = linkage(data, method="ward")
    tree = dendrogram(matrix, no_plot=True, labels=labels)
    return {
        "icoord": tree["icoord"],
        "dcoord": tree["dcoord"],
        "ivl": tree["ivl"],
        "merge_heights": [round(float(row[2]), 4) for row in matrix],
    }


# --- главный вход ---------------------------------------------------------------

def run_clustering(
    features: FeatureSpace, algorithm: str = "kmeans", k: int | None = None
) -> ClusteringResult:
    """Выполняет весь пайплайн кластеризации и собирает результат."""
    feature_z, embedding, pca, full_variance = _prepare(features)
    data = embedding.to_numpy()

    candidates = evaluate_k(data, algorithm=algorithm)
    chosen_k = k if k is not None else select_k(candidates)

    labels_array = _fit_labels(algorithm, data, chosen_k)
    labels = pd.Series(labels_array, index=features.matrix.index, name="cluster")

    # Кластеры нумеруются по убыванию размера — так «нулевой» всегда самый
    # крупный, и нумерация не скачет между запусками алгоритмов.
    order = labels.value_counts().index.tolist()
    remap = {old: new for new, old in enumerate(order)}
    labels = labels.map(remap)

    per_object = pd.Series(
        silhouette_samples(data, labels.to_numpy()), index=labels.index, name="silhouette"
    )

    profiles = _describe(feature_z, labels, features.descriptions)
    for profile in profiles:
        profile.mean_silhouette = round(float(per_object.loc[profile.members].mean()), 4)

    # Согласие алгоритмов: если три метода дают близкие разбиения, структура
    # в данных есть, а не выдумана конкретным методом.
    agreement = {}
    partitions = {name: _fit_labels(name, data, chosen_k) for name in ("kmeans", "ward", "gmm")}
    for left in partitions:
        for right in partitions:
            if left < right:
                agreement[f"{left}~{right}"] = round(
                    float(adjusted_rand_score(partitions[left], partitions[right])), 4
                )

    loadings = pd.DataFrame(
        pca.components_.T,
        index=features.matrix.columns,
        columns=[f"pc{i + 1}" for i in range(pca.n_components_)],
    )

    return ClusteringResult(
        labels=labels,
        k=chosen_k,
        algorithm=algorithm,
        candidates=candidates,
        profiles=profiles,
        embedding=embedding,
        explained_variance=[round(float(v), 4) for v in full_variance],
        loadings=loadings.round(4),
        agreement=agreement,
        silhouette_per_object=per_object.round(4),
        dendrogram=_dendrogram_payload(data, list(features.matrix.index)),
        feature_z=feature_z,
    )
