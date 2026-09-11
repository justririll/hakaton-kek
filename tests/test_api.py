from fastapi.testclient import TestClient

from app.main import app


def test_api_routes_and_schema() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["docs"] == "/docs"

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard["metrics"]["total_attendees"] == 1420
        assert len(dashboard["clusters"]) == 4
        assert sum(cluster["count"] for cluster in dashboard["clusters"]) == 1420
        assert len(dashboard["scatter_points"]) == 12
        assert len(dashboard["schedule"]) == 4
        assert dashboard["recommendations"][0]["event_id"] == "evt-1"

        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "/health" in response.json()["paths"]
        assert "/api/v1/analytics/dashboard" in response.json()["paths"]
