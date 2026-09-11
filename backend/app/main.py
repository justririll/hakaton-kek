"""HTTP-слой платформы «Культурный пульс».

Приложение отдаёт результат аналитического конвейера. Модели считаются один
раз на старте и живут в памяти процесса: исходных данных двадцать отчётов,
полный пересчёт занимает секунды, поэтому отдельное хранилище не нужно.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.ingest.schema import BY_KEY, CHANNELS
from app.ml.pipeline import Analytics, build_analytics, overview

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("culture-pulse")

DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "DATASET"
SOURCE_DIR = Path(os.getenv("CULTURE_PULSE_DATA", DEFAULT_SOURCE))

_state: dict[str, Analytics] = {}


def analytics() -> Analytics:
    """Текущий результат конвейера; 503, пока он не собран."""
    if "analytics" not in _state:
        raise HTTPException(status_code=503, detail="аналитика ещё не готова")
    return _state["analytics"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("источник данных: %s", SOURCE_DIR)
    _state["analytics"] = build_analytics(SOURCE_DIR)
    log.info("конвейер собран за %.2f с", _state["analytics"].build_seconds)
    yield
    _state.clear()


app = FastAPI(
    title="Культурный пульс",
    description=(
        "Аналитика сети центров прототипирования и творческих инкубаторов вузов культуры: "
        "динамика, кластеризация аудиторных моделей, рекомендации по программированию."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # витрина открытая, персональных данных нет
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# --- сериализация ---------------------------------------------------------------


def clean(value: Any) -> Any:
    """Приводит значения pandas/numpy к типам, которые умеет JSON.

    NaN и бесконечности превращаются в None: JSON их не поддерживает, а
    молчаливая подстановка нуля исказила бы показатель.
    """
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if not np.isfinite(number) else number
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NaT or (value is not None and pd.api.types.is_scalar(value) and pd.isna(value)):
        return None
    return value


def records(frame: pd.DataFrame, index_name: str | None = None) -> list[dict]:
    """DataFrame → список записей с индексом в виде поля."""
    table = frame.reset_index() if index_name else frame
    if index_name:
        table = table.rename(columns={table.columns[0]: index_name})
    return [clean(row) for row in table.to_dict(orient="records")]


# --- метаданные -----------------------------------------------------------------


@api.get("/health", summary="Состояние сервиса")
def health() -> dict:
    ready = "analytics" in _state
    return {
        "status": "ok" if ready else "starting",
        "source": str(SOURCE_DIR),
        "organizations": len(_state["analytics"].dataset.facts) if ready else 0,
        "build_seconds": _state["analytics"].build_seconds if ready else None,
    }


@api.get("/meta", summary="Справочники: показатели, каналы, типы рекомендаций")
def meta() -> dict:
    return {
        "indicators": [
            {
                "key": indicator.key,
                "title": indicator.title,
                "unit": indicator.unit,
                "group": indicator.group,
                "form": indicator.form,
                "code": indicator.code,
            }
            for indicator in BY_KEY.values()
        ],
        "channels": [
            {"key": key, "label": label, "audience_key": audience, "product_key": product}
            for key, label, audience, product in CHANNELS
        ],
        "recommendation_types": {
            "fix_format": "Поднять наполняемость существующего формата",
            "expand_format": "Нарастить работающий формат",
            "launch_format": "Запустить отсутствующий формат",
            "raise_conversion": "Поднять выход творческих продуктов",
            "monetize": "Ввести платный сегмент",
            "amplify_visibility": "Усилить медийное сопровождение",
            "plan_risk": "Закрыть риск по годовому плану",
        },
    }


# --- сводка ---------------------------------------------------------------------


@api.get("/overview", summary="Сводка по сети")
def get_overview() -> dict:
    return clean(overview(analytics()))


@api.get("/quality", summary="Отчёт контроля качества исходных данных")
def get_quality() -> dict:
    return clean(analytics().dataset.quality_report())


# --- организации ----------------------------------------------------------------


@api.get("/organizations", summary="Список организаций с профилем")
def get_organizations() -> list[dict]:
    state = analytics()
    table = (
        state.dataset.organizations.join(state.profile)
        .join(state.clustering.labels)
        .join(state.plan[["completion", "status", "run_rate_forecast", "target_2026"]])
        .join(state.clustering.silhouette_per_object)
    )
    return records(table, index_name="org_id")


@api.get("/organizations/{org_id}", summary="Карточка организации")
def get_organization(org_id: str) -> dict:
    state = analytics()
    if org_id not in state.dataset.facts.index:
        raise HTTPException(status_code=404, detail=f"организация {org_id!r} не найдена")

    cluster_id = state.cluster_of(org_id)
    profile = state.clustering.profiles[cluster_id]
    recommendations = state.recommendations[state.recommendations["org_id"] == org_id]
    anomalies = state.anomalies[state.anomalies["org_id"] == org_id] if not state.anomalies.empty else state.anomalies

    return clean(
        {
            "org_id": org_id,
            "passport": state.dataset.organizations.loc[org_id].to_dict(),
            "facts": state.dataset.facts.loc[org_id].to_dict(),
            "profile": state.profile.loc[org_id].to_dict(),
            "plan": state.plan.loc[org_id].to_dict(),
            "cluster": {
                "id": cluster_id,
                "name": profile.name,
                "summary": profile.summary,
                "size": profile.size,
                "peers": [m for m in profile.members if m != org_id],
                "membership_confidence": state.validation.membership_confidence.get(org_id),
                "silhouette": float(state.clustering.silhouette_per_object.loc[org_id]),
            },
            "recommendations": records(recommendations),
            "anomalies": records(anomalies),
        }
    )


# --- кластеризация ---------------------------------------------------------------


@api.get("/clusters", summary="Кластеры аудиторных моделей")
def get_clusters() -> dict:
    state = analytics()
    result = state.clustering
    names = state.names

    embedding = result.embedding.copy()
    embedding["cluster"] = result.labels
    embedding["silhouette"] = result.silhouette_per_object
    embedding["name"] = names
    embedding["audience_total"] = state.profile["audience_total"]

    return clean(
        {
            "k": result.k,
            "algorithm": result.algorithm,
            "profiles": [
                {
                    "cluster_id": p.cluster_id,
                    "name": p.name,
                    "summary": p.summary,
                    "size": p.size,
                    "members": p.members,
                    "member_names": [names[m] for m in p.members],
                    "distinctive": p.distinctive,
                    "mean_silhouette": p.mean_silhouette,
                    "centroid": p.centroid,
                }
                for p in result.profiles
            ],
            "embedding": records(embedding, index_name="org_id"),
            "explained_variance": result.explained_variance,
            "components": result.embedding.shape[1],
            "loadings": records(result.loadings, index_name="feature"),
            "agreement": result.agreement,
            "candidates": [c.__dict__ for c in result.candidates],
            "dendrogram": result.dendrogram,
            "feature_descriptions": state.features.descriptions,
            "feature_blocks": state.features.blocks,
        }
    )


@api.get("/clusters/validation", summary="Проверка значимости и устойчивости разбиения")
def get_validation() -> dict:
    state = analytics()
    return clean(
        {
            "clustering": state.validation.as_dict(),
            "recommendations": state.recommendation_stability,
            "co_assignment": records(state.co_assignment, index_name="org_id"),
        }
    )


# --- рекомендации ----------------------------------------------------------------


@api.get("/recommendations", summary="Рекомендации по программированию")
def get_recommendations(
    org_id: str | None = Query(None, description="фильтр по организации"),
    rec_type: str | None = Query(None, description="фильтр по типу рекомендации"),
    min_priority: int = Query(0, ge=0, le=100, description="минимальный приоритет"),
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    state = analytics()
    table = state.recommendations

    if org_id:
        table = table[table["org_id"] == org_id]
    if rec_type:
        table = table[table["rec_type"] == rec_type]
    table = table[table["priority"] >= min_priority]
    table = table.sort_values("priority", ascending=False).head(limit)

    names = state.names
    rows = records(table)
    for row in rows:
        row["org_name"] = str(names.get(row["org_id"], row["org_id"]))
    return {"total": len(rows), "items": rows}


@api.get("/plan", summary="План, факт и прогноз исполнения года")
def get_plan() -> list[dict]:
    state = analytics()
    table = state.plan.join(state.dataset.organizations["short_name"])
    return records(table, index_name="org_id")


@api.get("/anomalies", summary="Аномалии и противоречия в отчётности")
def get_anomalies(severity: str | None = Query(None, description="error | warning | info")) -> dict:
    state = analytics()
    table = state.anomalies
    if severity and not table.empty:
        table = table[table["severity"] == severity]

    names = state.names
    rows = records(table)
    for row in rows:
        row["org_name"] = str(names.get(row["org_id"], row["org_id"]))
    return {"total": len(rows), "items": rows}


@api.get("/benchmark/{metric}", summary="Распределение показателя по сети и кластерам")
def get_benchmark(metric: str) -> dict:
    state = analytics()
    if metric not in state.profile.columns:
        raise HTTPException(
            status_code=404,
            detail=f"показатель {metric!r} не рассчитывается; доступные: {list(state.profile.columns)}",
        )

    values = state.profile[metric]
    table = pd.DataFrame(
        {
            "value": values,
            "cluster": state.clustering.labels,
            "name": state.names,
        }
    )

    by_cluster = {}
    for cluster_id, group in table.groupby("cluster"):
        by_cluster[int(cluster_id)] = {
            "median": float(group["value"].median()),
            "p25": float(group["value"].quantile(0.25)),
            "p75": float(group["value"].quantile(0.75)),
            "count": int(len(group)),
        }

    return clean(
        {
            "metric": metric,
            "network": {
                "median": float(values.median()),
                "p25": float(values.quantile(0.25)),
                "p75": float(values.quantile(0.75)),
                "min": float(values.min()),
                "max": float(values.max()),
            },
            "by_cluster": by_cluster,
            "items": records(table, index_name="org_id"),
        }
    )


@api.post("/reload", summary="Пересобрать аналитику из исходных файлов")
def reload_analytics() -> dict:
    _state["analytics"] = build_analytics(SOURCE_DIR)
    return {"status": "ok", "build_seconds": _state["analytics"].build_seconds}


from app.ai import get_network_ai_summary, get_org_ai_summary, GEMINI_MODEL


@api.get("/ai/status", summary="Статус модуля генеративного ИИ Gemini")
def get_ai_status() -> dict:
    return {
        "enabled": True,
        "model": GEMINI_MODEL,
        "provider": "Google Gemini",
    }


@api.get("/ai/summary", summary="Исполнительское резюме всей сети (Gemini AI)")
def get_ai_summary(refresh: bool = Query(False, description="Принудительный пересчет")) -> dict:
    state = analytics()
    return get_network_ai_summary(state, force_refresh=refresh)


@api.get("/ai/org/{org_id}", summary="Персональный разбор центра культуры (Gemini AI)")
def get_ai_org_summary(org_id: str, refresh: bool = Query(False, description="Принудительный пересчет")) -> dict:
    state = analytics()
    return get_org_ai_summary(org_id, state, force_refresh=refresh)


app.include_router(api)
