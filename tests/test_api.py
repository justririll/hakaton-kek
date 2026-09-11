"""Проверки витрины: что API отдаёт наблюдаемые данные, а не правдоподобные.

Тесты сторожат именно те свойства, которые легко потерять при правке фронтенда
или промпта: темп к прошлому году не должен появляться там, где базы нет, а
сводный резерв сети не должен включать организации, чьи цифры внутри отчёта
противоречат друг другу.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Конвейер собирается один раз на старте приложения (несколько секунд),
    # поэтому клиент переиспользуется всем модулем.
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_loaded_dataset(client: TestClient) -> None:
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["organizations"] == 20


def test_core_endpoints_answer(client: TestClient) -> None:
    for path in (
        "/api/meta",
        "/api/overview",
        "/api/organizations",
        "/api/clusters",
        "/api/clusters/validation",
        "/api/recommendations",
        "/api/anomalies",
        "/api/quality",
        "/api/plan",
    ):
        assert client.get(path).status_code == 200, path


def test_growth_is_absent_where_baseline_is_absent(client: TestClient) -> None:
    """Темп к 2025 году считается только по показателям с заполненной базой."""
    dynamics = client.get("/api/overview").json()["dynamics"]
    assert dynamics, "динамика должна отдаваться в сводке"

    for row in dynamics:
        if row["baseline_2025"] is None:
            assert row["baseline_orgs"] == 0
            assert row["growth_ytd"] is None
            assert row["growth_year"] is None
        else:
            # База и факт сравниваются по одному кругу организаций.
            assert row["baseline_orgs"] > 0
            assert row["fact_comparable"] is not None
            assert row["growth_year"] is not None


def test_supply_is_the_only_indicator_with_a_baseline(client: TestClient) -> None:
    """В выданной отчётности база 2025 года есть только у числа мероприятий."""
    dynamics = {row["key"]: row for row in client.get("/api/overview").json()["dynamics"]}
    assert dynamics["formats"]["baseline_2025"] is not None
    for key in ("audience", "products", "revenue"):
        assert dynamics[key]["baseline_2025"] is None, key


def test_verified_reserve_excludes_flagged_organizations(client: TestClient) -> None:
    """Сводный резерв сети не опирается на отчёты с внутренними расхождениями."""
    summary = client.get("/api/overview").json()["recommendations"]
    flagged = set(summary["flagged_orgs"])
    assert flagged, "в этом датасете расхождения есть — проверка должна что-то ловить"

    items = client.get("/api/recommendations").json()
    items = items["items"] if isinstance(items, dict) else items

    verified_participants = sum(
        row["impact_value"]
        for row in items
        if row["impact_metric"] == "participants" and not row["data_flag"]
    )
    assert summary["impact_verified"]["participants"]["total"] == pytest.approx(
        verified_participants, abs=0.1
    )
    assert (
        summary["impact_verified"]["participants"]["total"]
        < summary["impact"]["participants"]["total"]
    )


def test_flagged_recommendations_carry_lower_confidence(client: TestClient) -> None:
    """Рекомендация по сомнительным данным не должна выглядеть такой же надёжной."""
    items = client.get("/api/recommendations").json()
    items = items["items"] if isinstance(items, dict) else items

    flagged = [row for row in items if row["data_flag"]]
    clean = [row for row in items if not row["data_flag"]]
    assert flagged and clean

    mean = lambda rows: sum(r["confidence"] for r in rows) / len(rows)  # noqa: E731
    assert mean(flagged) < mean(clean)
