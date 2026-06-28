"""Smoke-тесты для API (без создания таблиц)."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()
