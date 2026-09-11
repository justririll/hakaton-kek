"""Инженерия признаков для кластеризации аудиторных моделей центров.

Наблюдений мало (20 организаций), поэтому пространство признаков строится
экономно и осмысленно: четыре блока, каждый отвечает на отдельный вопрос
о работе центра с аудиторией.

    состав     — с какой аудиторией работает центр (доли каналов);
    масштаб    — сколько людей проходит через центр;
    глубина    — насколько плотно работают с одним участником;
    отдача     — что аудитория производит на выходе и сколько это стоит.

Доли каналов — композиционные данные: они лежат на симплексе, сумма всегда
равна единице, поэтому обычная стандартизация для них некорректна (признаки
линейно зависимы, а евклидово расстояние искажает близость). Применяется
центрированное логарифмическое преобразование (CLR) с мультипликативной
заменой нулей — стандартная практика для составов.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.ingest.dataset import Dataset
from app.ingest.schema import CHANNELS

# Псевдосчёт для замены нулей в составе перед логарифмированием.
# Нулей много и они содержательны («центр не ведёт переподготовку»), поэтому
# замена берётся малой относительно минимального наблюдаемого веса.
ZERO_REPLACEMENT = 0.5


@dataclass
class FeatureSpace:
    """Матрица признаков вместе с описанием каждого столбца."""

    matrix: pd.DataFrame  # исходные (неотмасштабированные) значения
    descriptions: dict[str, str]
    blocks: dict[str, list[str]]

    @property
    def columns(self) -> list[str]:
        return list(self.matrix.columns)


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Отношение с нулевым знаменателем → 0 (деятельности не было)."""
    result = numerator.astype(float) / denominator.replace(0, np.nan).astype(float)
    return result.fillna(0.0)


def clr_transform(shares: pd.DataFrame) -> pd.DataFrame:
    """CLR-преобразование состава с мультипликативной заменой нулей.

    Нули заменяются малой долей `ZERO_REPLACEMENT / n`, остальные компоненты
    пропорционально ужимаются, чтобы сумма осталась равной единице. Затем
    берётся логарифм отношения к среднему геометрическому строки.
    """
    values = shares.to_numpy(dtype=float)
    n_components = values.shape[1]
    replacement = ZERO_REPLACEMENT / n_components

    adjusted = values.copy()
    for row in range(values.shape[0]):
        zeros = adjusted[row] <= 0
        if zeros.all():
            adjusted[row] = 1.0 / n_components
            continue
        if zeros.any():
            adjusted[row, zeros] = replacement
            positive = ~zeros
            adjusted[row, positive] *= 1.0 - replacement * zeros.sum()
        total = adjusted[row].sum()
        if total > 0:
            adjusted[row] /= total

    log_values = np.log(adjusted)
    centered = log_values - log_values.mean(axis=1, keepdims=True)
    return pd.DataFrame(centered, index=shares.index, columns=[f"clr_{c}" for c in shares.columns])


def build_features(dataset: Dataset) -> FeatureSpace:
    """Собирает признаковое пространство аудиторной модели центра."""
    facts = dataset.facts
    descriptions: dict[str, str] = {}
    parts: list[pd.DataFrame] = []

    # --- блок «состав»: распределение аудитории по форматам -------------------
    audience_cols = [audience for _, _, audience, _ in CHANNELS]
    channel_keys = [key for key, _, _, _ in CHANNELS]
    audience_by_channel = facts[audience_cols].copy()
    audience_by_channel.columns = channel_keys
    totals = audience_by_channel.sum(axis=1)
    shares = audience_by_channel.div(totals.replace(0, np.nan), axis=0).fillna(0.0)

    clr = clr_transform(shares)
    parts.append(clr)
    for key, label, _, _ in CHANNELS:
        descriptions[f"clr_{key}"] = f"Перевес аудитории в сторону «{label}» (CLR)"

    # --- блок «масштаб» --------------------------------------------------------
    scale = pd.DataFrame(index=facts.index)
    scale["log_audience"] = np.log1p(facts["audience_total"])
    scale["log_supply"] = np.log1p(facts["supply_total"])
    parts.append(scale)
    descriptions["log_audience"] = "Размер аудитории, log(1+x)"
    descriptions["log_supply"] = "Число разработанных форматов, log(1+x)"

    # --- блок «глубина» --------------------------------------------------------
    depth = pd.DataFrame(index=facts.index)
    depth["audience_per_format"] = np.log1p(_safe_ratio(facts["audience_total"], facts["supply_total"]))
    depth["resident_rate"] = _safe_ratio(facts["residents_total"], facts["audience_total"]).clip(0, 3)
    parts.append(depth)
    descriptions["audience_per_format"] = "Участников на один формат, log(1+x)"
    descriptions["resident_rate"] = "Доля аудитории, ставшей резидентами"

    # --- блок «отдача» ---------------------------------------------------------
    output = pd.DataFrame(index=facts.index)
    output["product_rate"] = _safe_ratio(facts["products_total"], facts["audience_total"]).clip(0, 5)
    output["revenue_per_participant"] = np.log1p(
        _safe_ratio(facts["revenue_total"], facts["audience_total"])
    )
    output["publicity_per_format"] = np.log1p(
        _safe_ratio(facts["media_publications"] + facts["federal_events"], facts["supply_total"])
    )
    parts.append(output)
    descriptions["product_rate"] = "Творческих продуктов на одного участника"
    descriptions["revenue_per_participant"] = "Выручка на участника, ₽, log(1+x)"
    descriptions["publicity_per_format"] = "Публичность на один формат, log(1+x)"

    matrix = pd.concat(parts, axis=1)
    blocks = {
        "состав": list(clr.columns),
        "масштаб": list(scale.columns),
        "глубина": list(depth.columns),
        "отдача": list(output.columns),
    }
    return FeatureSpace(matrix=matrix, descriptions=descriptions, blocks=blocks)


def build_profile_table(dataset: Dataset) -> pd.DataFrame:
    """Интерпретируемые показатели центра — для карточек и объяснений.

    В отличие от признаков модели, здесь всё в натуральных единицах: эти
    значения показываются пользователю и попадают в обоснование рекомендаций.
    """
    facts = dataset.facts
    table = pd.DataFrame(index=facts.index)

    table["audience_total"] = facts["audience_total"]
    table["supply_total"] = facts["supply_total"]
    table["audience_per_format"] = _safe_ratio(facts["audience_total"], facts["supply_total"])
    table["products_total"] = facts["products_total"]
    table["product_rate"] = _safe_ratio(facts["products_total"], facts["audience_total"])
    table["residents_total"] = facts["residents_total"]
    table["resident_rate"] = _safe_ratio(facts["residents_total"], facts["audience_total"])
    table["revenue_total"] = facts["revenue_total"]
    table["revenue_per_participant"] = _safe_ratio(facts["revenue_total"], facts["audience_total"])
    table["media_publications"] = facts["media_publications"]
    table["federal_events"] = facts["federal_events"]
    table["publicity_per_format"] = _safe_ratio(
        facts["media_publications"] + facts["federal_events"], facts["supply_total"]
    )
    table["ip_total"] = facts["ip_total"]

    for key, _, audience_key, product_key in CHANNELS:
        table[f"audience_{key}"] = facts[audience_key]
        table[f"products_{key}"] = facts[product_key]
        table[f"share_{key}"] = _safe_ratio(facts[audience_key], facts["audience_total"])

    return table
