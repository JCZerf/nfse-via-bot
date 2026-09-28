import asyncio

from nfse_via_bot.config import Settings
from nfse_via_bot.service import fetch_invoice
from tests.fakes import KEY, NOT_FOUND, REFUSAL, World, invoice_body

SETTINGS = Settings(
    SOLVER_URL="http://solver",
    SOLVER_API_KEY="k",
    POLL_SECONDS=0,
    MAX_ATTEMPTS=3,
    DEADLINE_SECONDS=270,
)


def run(world: World, settings: Settings = SETTINGS):
    async def scenario():
        async with world.client() as client:
            return await fetch_invoice(KEY, settings, client)

    return asyncio.run(scenario())


def test_an_accepted_token_returns_the_invoice():
    world = World([(200, invoice_body())])

    result = run(world)

    assert result.status == "found"
    assert result.invoice.number == "1234567890123"
    assert [a.outcome for a in result.attempts] == ["accepted"]
    consult = world.consults[0]
    assert consult.headers["x-hcaptcha-token"] == "P1_token"
    assert consult.headers["user-agent"] == "UA/1.0"
    assert consult.url.path.endswith(KEY)


def test_a_refused_token_is_replaced_by_a_new_one():
    world = World([(401, REFUSAL), (200, invoice_body())])

    result = run(world)

    assert result.status == "found"
    assert [(a.outcome, a.score) for a in result.attempts] == [
        ("token_refused", 0.79),
        ("accepted", None),
    ]


def test_every_token_refused_ends_as_refused():
    world = World([(401, REFUSAL)] * 3)

    result = run(world)

    assert result.status == "refused"
    assert len(result.attempts) == 3
    assert result.invoice is None


def test_a_via_error_other_than_the_token_is_not_retried():
    world = World([(404, NOT_FOUND)])

    result = run(world)

    assert result.status == "error"
    assert result.messages == ["Nota não encontrada"]
    assert len(result.attempts) == 1


def test_a_solver_failure_counts_as_an_attempt():
    world = World([(200, invoice_body())], solver_errors=["ERROR_CAPTCHA_UNSOLVABLE"])

    result = run(world)

    assert result.status == "found"
    assert [a.outcome for a in result.attempts] == ["solver_error", "accepted"]


def test_no_new_attempt_starts_without_time_to_finish_it():
    world = World([(401, REFUSAL)] * 3)
    tight = SETTINGS.model_copy(update={"DEADLINE_SECONDS": 30})

    result = run(world, tight)

    assert len(result.attempts) == 1
    assert result.status == "refused"


def test_each_attempt_goes_through_the_next_proxy():
    world = World([(401, REFUSAL), (401, REFUSAL), (200, invoice_body())])
    proxied = SETTINGS.model_copy(
        update={
            "PROXY_URLS": "http://ana:s%40nha@br.proxy.example:10001, http://ana:s%40nha@br.proxy.example:10002"
        }
    )

    result = run(world, proxied)

    assert result.status == "found"
    assert [t["proxyPort"] for t in world.tasks] == [10001, 10002, 10001]
    assert world.tasks[0]["type"] == "HCaptchaTask"
    assert world.tasks[0]["proxyPassword"] == "s@nha"


def test_without_proxies_the_task_is_proxyless():
    world = World([(200, invoice_body())])

    run(world)

    assert world.tasks == [
        {"type": "HCaptchaTaskProxyless", "websiteURL": "https://via.nfse.gov.br/consultapublica/"}
    ]
