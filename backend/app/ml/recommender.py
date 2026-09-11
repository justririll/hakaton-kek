"""Рекомендации по программированию мероприятий.

Логика опирается на сравнение с равными: центр сопоставляется не со всей
сетью, а со своим кластером — организациями с похожей аудиторной моделью.
Сравнивать камерную лабораторию с массовым просветителем бессмысленно, а
внутри кластера разрыв в показателе означает достижимый резерв, потому что
кто-то из соседей по модели его уже закрыл.

Каждое правило отвечает на вопрос «что делать» и сразу оценивает «сколько это
даст»: эффект считается в натуральных единицах (участники, продукты, рубли,
публикации), а не в абстрактных баллах.

Ключевая деталь: эталон считается методом исключения — сам центр не входит в
выборку, по которой для него же считается норма. Иначе лидер кластера всегда
сравнивался бы сам с собой и не получал бы рекомендаций.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from app.ingest.schema import CHANNEL_SUPPLY, CHANNELS

# Минимальный размер группы сравнения. При одном-двух соседях медиана
# неустойчива, поэтому группа расширяется до всей сети (с понижением доверия).
MIN_PEERS = 3

# Вес типа рекомендации в приоритете: насколько действие управляемо и быстро
# даёт результат. Запуск нового формата дороже, чем донастройка текущего.
TYPE_WEIGHTS: dict[str, float] = {
    "fix_format": 1.00,
    "plan_risk": 0.95,
    "expand_format": 0.90,
    "raise_conversion": 0.85,
    "monetize": 0.70,
    "amplify_visibility": 0.60,
    "launch_format": 0.55,
}

CHANNEL_LABELS: dict[str, str] = {key: label for key, label, _, _ in CHANNELS}


@dataclass
class Recommendation:
    """Одна рекомендация с оценённым эффектом и обоснованием."""

    org_id: str
    rec_type: str
    title: str
    action: str
    channel: str | None
    priority: int  # 1–100, перцентиль резерва по сети
    raw_score: float  # сырая оценка до нормировки
    confidence: float  # 0–1
    impact_metric: str
    impact_value: float
    impact_unit: str
    rationale: str
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


# --- эталоны по группе сравнения ------------------------------------------------


@dataclass
class PeerStat:
    """Распределение метрики в группе сравнения (без самого центра)."""

    median: float
    p25: float
    p75: float
    best: float
    best_org: str | None
    count: int
    scope: str  # "cluster" | "network"

    @property
    def dispersion(self) -> float:
        """Относительный межквартильный размах — мера разброса эталона."""
        if self.median <= 0:
            return 1.0
        return float((self.p75 - self.p25) / self.median)


def peer_stat(
    values: pd.Series, org_id: str, cluster_members: list[str], higher_is_better: bool = True
) -> PeerStat:
    """Статистика метрики по кластеру центра, исключая его самого."""
    peers = [m for m in cluster_members if m != org_id]
    scope = "cluster"
    if len(peers) < MIN_PEERS:
        # Кластер слишком мал для устойчивой медианы — расширяем до сети.
        peers = [m for m in values.index if m != org_id]
        scope = "network"

    sample = values.loc[peers].astype(float)
    if sample.empty:
        return PeerStat(0.0, 0.0, 0.0, 0.0, None, 0, scope)

    best_org = str(sample.idxmax() if higher_is_better else sample.idxmin())
    return PeerStat(
        median=float(sample.median()),
        p25=float(sample.quantile(0.25)),
        p75=float(sample.quantile(0.75)),
        best=float(sample.max() if higher_is_better else sample.min()),
        best_org=best_org,
        count=int(sample.size),
        scope=scope,
    )


def _confidence(stat: PeerStat) -> float:
    """Доверие к рекомендации: чем больше и однороднее группа, тем выше.

    Учитываются три фактора: размер группы сравнения, разброс внутри неё и то,
    пришлось ли расширять группу до всей сети вместо кластера.
    """
    coverage = stat.count / (stat.count + 2.0)
    precision = 1.0 / (1.0 + stat.dispersion)
    scope_penalty = 1.0 if stat.scope == "cluster" else 0.75
    return float(np.clip(coverage * precision * scope_penalty, 0.15, 0.95))


def _score(gain: float, reference: float, confidence: float, rec_type: str) -> float:
    """Сырая оценка резерва: масштаб выигрыша × доверие × управляемость действия.

    Выигрыш нормируется на текущий уровень той же метрики у самого центра:
    «плюс 20 участников» значит разное для центра с аудиторией 30 и 1500.
    """
    base = max(abs(reference), 1e-9)
    normalized = float(np.clip(gain / base, 0.0, 2.0)) / 2.0
    weight = TYPE_WEIGHTS.get(rec_type, 0.5)
    return float(normalized * confidence * weight)


def _fmt(value: float, unit: str) -> str:
    """Число с единицей измерения в человекочитаемом виде."""
    if unit == "₽":
        return f"{value:,.0f} ₽".replace(",", " ")
    text = f"{value:,.0f}" if abs(value - round(value)) < 0.05 else f"{value:,.1f}"
    return f"{text} {unit}".replace(",", "\u00a0").strip()


# --- правила уровня формата -----------------------------------------------------


def _format_rules(
    org_id: str,
    profile: pd.DataFrame,
    facts: pd.DataFrame,
    members: list[str],
    names: pd.Series,
) -> list[Recommendation]:
    """Правила уровня формата: донастроить, нарастить или запустить."""
    out: list[Recommendation] = []
    audience_total = float(facts.loc[org_id, "audience_total"])

    for channel, label, audience_key, _ in CHANNELS:
        supply_key = CHANNEL_SUPPLY[channel]
        own_supply = float(facts.loc[org_id, supply_key])
        own_audience = float(facts.loc[org_id, audience_key])

        # Наполняемость формата: участников на одно проведённое мероприятие.
        fill = (facts[audience_key] / facts[supply_key].replace(0, np.nan)).fillna(0.0)
        own_fill = own_audience / own_supply if own_supply > 0 else np.nan
        stat = peer_stat(fill, org_id, members)

        peers = [m for m in members if m != org_id]
        peer_runs = float((facts.loc[peers, supply_key] > 0).mean()) if peers else 0.0

        # --- формат не ведётся, а у соседей по модели он работает -------------
        if own_supply == 0:
            if peer_runs >= 0.6 and stat.median > 0:
                gain = stat.median  # один пилот на медианной наполняемости
                confidence = _confidence(stat) * 0.8  # запуск с нуля рискованнее
                out.append(
                    Recommendation(
                        org_id=org_id,
                        rec_type="launch_format",
                        title=f"Запустить формат «{label}»",
                        action=f"Поставить в программу один пилот «{label}» до конца года",
                        channel=channel,
                        priority=0,
                        raw_score=_score(gain, audience_total, confidence, "launch_format"),
                        confidence=round(confidence, 3),
                        impact_metric="participants",
                        impact_value=round(gain, 1),
                        impact_unit="чел.",
                        rationale=(
                            f"Формат не представлен в программе, при этом его ведут "
                            f"{peer_runs:.0%} центров вашей модели и собирают в среднем "
                            f"{_fmt(stat.median, 'чел.')} на мероприятие. "
                            f"Один пилот закрывает разрыв без перестройки линейки."
                        ),
                        evidence={
                            "own_supply": own_supply,
                            "peer_median_fill": round(stat.median, 2),
                            "peer_share_running": round(peer_runs, 3),
                            "peers": stat.count,
                            "scope": stat.scope,
                            "best_peer": str(names.get(stat.best_org, stat.best_org)),
                        },
                    )
                )
            continue

        # --- формат ведётся, но наполняемость ниже нижнего квартиля группы ----
        if np.isfinite(own_fill) and stat.p25 > 0 and own_fill < stat.p25:
            gain = (stat.median - own_fill) * own_supply
            if gain > 0.5:
                confidence = _confidence(stat)
                out.append(
                    Recommendation(
                        org_id=org_id,
                        rec_type="fix_format",
                        title=f"Поднять наполняемость «{label}»",
                        action=(
                            f"Не увеличивая число мероприятий, довести набор на «{label}» до "
                            f"{_fmt(stat.median, 'чел.')} — пересобрать анонсирование и каналы записи"
                        ),
                        channel=channel,
                        priority=0,
                        raw_score=_score(gain, audience_total, confidence, "fix_format"),
                        confidence=round(confidence, 3),
                        impact_metric="participants",
                        impact_value=round(gain, 1),
                        impact_unit="чел.",
                        rationale=(
                            f"На «{label}» приходит {_fmt(float(own_fill), 'чел.')} на мероприятие "
                            f"при медиане {_fmt(stat.median, 'чел.')} в вашей модели — это нижний "
                            f"квартиль. Мероприятия уже проводятся ({_fmt(own_supply, 'шт.')}), "
                            f"то есть резерв закрывается работой с набором, а не новой программой."
                        ),
                        evidence={
                            "own_fill": round(float(own_fill), 2),
                            "peer_p25": round(stat.p25, 2),
                            "peer_median": round(stat.median, 2),
                            "peer_best": round(stat.best, 2),
                            "own_supply": own_supply,
                            "peers": stat.count,
                            "scope": stat.scope,
                            "best_peer": str(names.get(stat.best_org, stat.best_org)),
                        },
                    )
                )
            continue

        # --- формат работает лучше эталона, но занимает малую долю линейки ----
        share = float(profile.loc[org_id, f"share_{channel}"])
        share_stat = peer_stat(profile[f"share_{channel}"], org_id, members)
        if np.isfinite(own_fill) and own_fill >= stat.median > 0 and share < share_stat.median:
            extra_events = max(1.0, round(own_supply * 0.25))
            gain = extra_events * float(own_fill)
            confidence = _confidence(share_stat)
            out.append(
                Recommendation(
                    org_id=org_id,
                    rec_type="expand_format",
                    title=f"Нарастить «{label}»",
                    action=f"Добавить {_fmt(extra_events, 'мероприятия')} формата «{label}» в программу",
                    channel=channel,
                    priority=0,
                        raw_score=_score(gain, audience_total, confidence, "expand_format"),
                    confidence=round(confidence, 3),
                    impact_metric="participants",
                    impact_value=round(gain, 1),
                    impact_unit="чел.",
                    rationale=(
                        f"Формат у вас собирает {_fmt(float(own_fill), 'чел.')} на мероприятие — "
                        f"не ниже медианы модели ({_fmt(stat.median, 'чел.')}), но занимает "
                        f"{share:.0%} аудитории против {share_stat.median:.0%} у соседей. "
                        f"Спрос подтверждён, предложение отстаёт."
                    ),
                    evidence={
                        "own_fill": round(float(own_fill), 2),
                        "peer_median_fill": round(stat.median, 2),
                        "own_share": round(share, 3),
                        "peer_median_share": round(share_stat.median, 3),
                        "extra_events": extra_events,
                        "peers": share_stat.count,
                        "scope": share_stat.scope,
                    },
                )
            )

    return out


# --- правила уровня результата --------------------------------------------------


def _outcome_rules(
    org_id: str, profile: pd.DataFrame, members: list[str], names: pd.Series
) -> list[Recommendation]:
    """Правила уровня результата: конверсия, деньги, публичность."""
    out: list[Recommendation] = []
    audience = float(profile.loc[org_id, "audience_total"])
    if audience <= 0:
        return out

    # --- конверсия «участник → творческий продукт» ----------------------------
    own_rate = float(profile.loc[org_id, "product_rate"])
    stat = peer_stat(profile["product_rate"], org_id, members)
    gain = (stat.median - own_rate) * audience
    if gain >= 1:
        confidence = _confidence(stat)
        best_name = str(names.get(stat.best_org, stat.best_org))
        out.append(
            Recommendation(
                org_id=org_id,
                rec_type="raise_conversion",
                title="Поднять выход творческих продуктов",
                action=(
                    "Встроить обязательный проектный результат в программу мероприятий: "
                    "защита работы, выставка, запись — чтобы участие завершалось продуктом"
                ),
                channel=None,
                priority=0,
                        raw_score=_score(
                    gain, float(profile.loc[org_id, "products_total"]), confidence, "raise_conversion"
                ),
                confidence=round(confidence, 3),
                impact_metric="products",
                impact_value=round(gain, 1),
                impact_unit="шт.",
                rationale=(
                    f"На одного участника приходится {own_rate:.2f} продукта при медиане "
                    f"{stat.median:.2f} в вашей модели. При той же аудитории "
                    f"({_fmt(audience, 'чел.')}) выход вырос бы на {_fmt(gain, 'шт.')} "
                    f"Лучший результат в группе — у центра «{best_name}»."
                ),
                evidence={
                    "own_rate": round(own_rate, 3),
                    "peer_median": round(stat.median, 3),
                    "peer_best": round(stat.best, 3),
                    "audience": audience,
                    "peers": stat.count,
                    "scope": stat.scope,
                    "best_peer": best_name,
                },
            )
        )

    # --- выручка на участника --------------------------------------------------
    own_revenue = float(profile.loc[org_id, "revenue_per_participant"])
    revenue_stat = peer_stat(profile["revenue_per_participant"], org_id, members)
    revenue_gain = (revenue_stat.median - own_revenue) * audience
    if revenue_gain >= 10_000:
        confidence = _confidence(revenue_stat)
        out.append(
            Recommendation(
                org_id=org_id,
                rec_type="monetize",
                title="Ввести платный сегмент программы",
                action=(
                    "Выделить часть мероприятий в платный контур (мастер-классы для внешних "
                    "участников, услуги по договорам) при сохранении бесплатного ядра"
                ),
                channel=None,
                priority=0,
                        raw_score=_score(
                    revenue_gain, float(profile.loc[org_id, "revenue_total"]), confidence, "monetize"
                ),
                confidence=round(confidence, 3),
                impact_metric="revenue",
                impact_value=float(round(revenue_gain, -2)),
                impact_unit="₽",
                rationale=(
                    f"Выручка на участника — {_fmt(own_revenue, '₽')} при медиане "
                    f"{_fmt(revenue_stat.median, '₽')} в вашей модели. При текущей аудитории "
                    f"это {_fmt(revenue_gain, '₽')} недополученного объёма услуг."
                ),
                evidence={
                    "own_per_participant": round(own_revenue, 1),
                    "peer_median": round(revenue_stat.median, 1),
                    "audience": audience,
                    "peers": revenue_stat.count,
                    "scope": revenue_stat.scope,
                    "best_peer": str(names.get(revenue_stat.best_org, revenue_stat.best_org)),
                },
            )
        )

    # --- публичность -----------------------------------------------------------
    own_publicity = float(profile.loc[org_id, "publicity_per_format"])
    publicity_stat = peer_stat(profile["publicity_per_format"], org_id, members)
    supply = float(profile.loc[org_id, "supply_total"])
    publicity_gain = (publicity_stat.median - own_publicity) * supply
    if supply > 0 and publicity_gain >= 3:
        confidence = _confidence(publicity_stat)
        out.append(
            Recommendation(
                org_id=org_id,
                rec_type="amplify_visibility",
                title="Усилить медийное сопровождение программы",
                action=(
                    "Закрепить за каждым мероприятием обязательный выход: "
                    "анонс, репортаж, публикация результата"
                ),
                channel=None,
                priority=0,
                        raw_score=_score(
                    publicity_gain,
                    float(profile.loc[org_id, "media_publications"]),
                    confidence,
                    "amplify_visibility",
                ),
                confidence=round(confidence, 3),
                impact_metric="publications",
                impact_value=round(publicity_gain, 0),
                impact_unit="шт.",
                rationale=(
                    f"На одно мероприятие приходится {own_publicity:.2f} публикации при медиане "
                    f"{publicity_stat.median:.2f} в вашей модели. Программа того же объёма могла бы "
                    f"дать ещё {_fmt(publicity_gain, 'шт.')} упоминаний."
                ),
                evidence={
                    "own_per_format": round(own_publicity, 2),
                    "peer_median": round(publicity_stat.median, 2),
                    "supply": supply,
                    "peers": publicity_stat.count,
                    "scope": publicity_stat.scope,
                },
            )
        )

    return out


# --- правило исполнения плана ---------------------------------------------------


def _plan_rules(org_id: str, plan: pd.DataFrame) -> list[Recommendation]:
    """Правило исполнения годового обязательства Формы 1."""
    if org_id not in plan.index:
        return []
    row = plan.loc[org_id]
    if row["status"] not in {"риск", "срыв"}:
        return []

    remaining = float(row["required_remaining"])
    if remaining <= 0:
        return []

    return [
        Recommendation(
            org_id=org_id,
            rec_type="plan_risk",
            title="План года под угрозой",
            action=(
                f"Поставить в программу IV квартала {_fmt(remaining, 'мероприятий')} — это "
                f"{_fmt(float(row['required_monthly_rate']), 'ед./мес.')} против текущих "
                f"{_fmt(float(row['current_monthly_rate']), 'ед./мес.')}"
            ),
            channel=None,
            priority=0,
                        raw_score=_score(remaining, float(row["target_2026"]), 0.9, "plan_risk"),
            confidence=0.9,
            impact_metric="formats",
            impact_value=round(remaining, 1),
            impact_unit="шт.",
            rationale=(
                f"За девять месяцев закрыто {float(row['completion']):.0%} годовой цели: "
                f"{_fmt(float(row['fact_ytd']), 'из')} {_fmt(float(row['target_2026']), 'ед')}. "
                f"При текущем темпе год закроется на {_fmt(float(row['run_rate_forecast']), 'ед.')} — "
                f"это {_fmt(abs(float(row['forecast_gap'])), 'ед.')} ниже обязательства."
            ),
            evidence={
                "completion": round(float(row["completion"]), 3),
                "target": float(row["target_2026"]),
                "fact_ytd": float(row["fact_ytd"]),
                "run_rate_forecast": float(row["run_rate_forecast"]),
                "required_monthly_rate": float(row["required_monthly_rate"]),
                "current_monthly_rate": float(row["current_monthly_rate"]),
            },
        )
    ]


# --- сборка ---------------------------------------------------------------------

RECOMMENDATION_COLUMNS: tuple[str, ...] = (
    "org_id",
    "rec_type",
    "title",
    "action",
    "channel",
    "priority",
    "confidence",
    "impact_metric",
    "impact_value",
    "impact_unit",
    "rationale",
    "evidence",
)


def build_recommendations(
    profile: pd.DataFrame,
    facts: pd.DataFrame,
    labels: pd.Series,
    plan: pd.DataFrame,
    names: pd.Series,
    top_per_org: int | None = None,
) -> pd.DataFrame:
    """Строит рекомендации для всех организаций сети."""
    clusters = {int(c): labels.index[labels == c].tolist() for c in labels.unique()}
    rows: list[dict] = []

    # Перебираются организации с назначенным кластером: при проверке
    # устойчивости методом исключения разбиение покрывает не всю сеть.
    for org_id in labels.index:
        members = clusters[int(labels.loc[org_id])]
        found: list[Recommendation] = []
        found += _plan_rules(org_id, plan)
        found += _format_rules(org_id, profile, facts, members, names)
        found += _outcome_rules(org_id, profile, members, names)
        rows.extend(r.as_dict() for r in found)

    if not rows:
        return pd.DataFrame(columns=list(RECOMMENDATION_COLUMNS))

    table = pd.DataFrame(rows)
    # Приоритет — перцентиль сырой оценки по всей сети. Абсолютное значение
    # оценки ничего не сообщает руководителю, а место в очереди резервов —
    # сообщает: приоритет 90 означает «верхние 10 % резервов сети».
    table["priority"] = (table["raw_score"].rank(pct=True) * 100).round().astype(int).clip(1, 100)

    table = table.sort_values(["org_id", "priority"], ascending=[True, False])
    if top_per_org is not None:
        table = table.groupby("org_id", group_keys=False).head(top_per_org)
    return table


def network_summary(recommendations: pd.DataFrame) -> dict:
    """Сводка по сети: где сосредоточен управленческий резерв."""
    if recommendations.empty:
        return {"total": 0, "by_type": {}, "impact": {}}

    impact: dict[str, dict] = {}
    for metric, group in recommendations.groupby("impact_metric"):
        impact[str(metric)] = {
            "total": round(float(group["impact_value"].sum()), 1),
            "unit": str(group["impact_unit"].iloc[0]),
            "count": int(len(group)),
        }

    return {
        "total": int(len(recommendations)),
        "by_type": {str(k): int(v) for k, v in recommendations["rec_type"].value_counts().items()},
        "impact": impact,
        "mean_priority": round(float(recommendations["priority"].mean()), 1),
        "mean_confidence": round(float(recommendations["confidence"].mean()), 3),
    }
