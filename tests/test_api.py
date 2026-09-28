import pytest
from fastapi.testclient import TestClient

from nfse_via_bot import main
from nfse_via_bot.config import Settings
from nfse_via_bot.service import Result
from tests.fakes import KEY


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        main, "settings", Settings(_env_file=None, SOLVER_URL="http://solver", SOLVER_API_KEY="k")
    )

    async def fake(access_key, settings):
        return Result(status="refused", access_key=access_key, elapsed_seconds=1.0, attempts=[])

    monkeypatch.setattr(main, "fetch_invoice", fake)
    return TestClient(main.app)


@pytest.mark.parametrize("path", ["/", "/api/docs"])
def test_the_root_goes_to_the_docs(client, path):
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_the_page_is_served(client):
    response = client.get("/consulta")

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
        main,
        "settings",
        Settings(_env_file=None, SOLVER_URL="http://solver", SOLVER_API_KEY="k", ACCESS_TOKEN="s"),
    )

    assert client.post("/api/invoices", json={"access_key": KEY}).status_code == 401
    ok = client.post("/api/invoices", json={"access_key": KEY}, headers={"X-Access-Token": "s"})
    assert ok.status_code == 200


def test_an_unconfigured_solver_answers_503(client, monkeypatch):
    monkeypatch.setattr(
        main, "settings", Settings(_env_file=None, SOLVER_URL="", SOLVER_API_KEY="")
    )

    assert client.post("/api/invoices", json={"access_key": KEY}).status_code == 503


def test_the_docs_describe_every_field_and_the_examples_are_valid():
    from nfse_via_bot.docs import LOOKUP_EXAMPLES, RESULT_EXAMPLES

    schemas = main.app.openapi()["components"]["schemas"]
    for name in (
        "Result",
        "Attempt",
        "Invoice",
        "Issuer",
        "Trip",
        "Amounts",
        "Taxes",
        "Protocol",
        "Lookup",
        "Health",
    ):
        for field, prop in schemas[name]["properties"].items():
            assert prop.get("description"), f"{name}.{field}"
    for example in LOOKUP_EXAMPLES.values():
        main.Lookup.model_validate(example["value"])
    for example in RESULT_EXAMPLES.values():
        Result.model_validate(example["value"])
