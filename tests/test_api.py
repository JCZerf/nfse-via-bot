import pytest
from fastapi.testclient import TestClient

from nfse_via_bot import main
from nfse_via_bot.config import Settings
from nfse_via_bot.service import Result
from tests.fakes import KEY


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings(SOLVER_URL="http://solver", SOLVER_API_KEY="k"))

    async def fake(access_key, settings):
        return Result(status="refused", access_key=access_key, elapsed_seconds=1.0, attempts=[])

    monkeypatch.setattr(main, "fetch_invoice", fake)
    return TestClient(main.app)


def test_the_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Consulta NFS-e Via" in response.text


def test_a_key_with_spaces_is_cleaned(client):
    spaced = " ".join(KEY[i : i + 10] for i in range(0, 50, 10)).lower()

    response = client.post("/api/invoices", json={"access_key": spaced})

    assert response.status_code == 200
    assert response.json()["access_key"] == KEY


@pytest.mark.parametrize("key", ["123", "1" * 49 + "-", "1" * 51])
def test_a_malformed_key_is_refused(client, key):
    assert client.post("/api/invoices", json={"access_key": key}).status_code == 422


def test_the_access_token_is_required_when_set(client, monkeypatch):
    monkeypatch.setattr(
        main, "settings", Settings(SOLVER_URL="http://solver", SOLVER_API_KEY="k", ACCESS_TOKEN="s")
    )

    assert client.post("/api/invoices", json={"access_key": KEY}).status_code == 401
    ok = client.post("/api/invoices", json={"access_key": KEY}, headers={"X-Access-Token": "s"})
    assert ok.status_code == 200


def test_an_unconfigured_solver_answers_503(client, monkeypatch):
    monkeypatch.setattr(main, "settings", Settings(SOLVER_URL="", SOLVER_API_KEY=""))

    assert client.post("/api/invoices", json={"access_key": KEY}).status_code == 503
