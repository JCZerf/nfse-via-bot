from nfse_via_bot.invoice import parse
from tests.fakes import KEY, invoice_body


def test_the_invoice_is_read_from_the_via_answer():
    invoice = parse(invoice_body())

    assert invoice.number == "1234567890123"
    assert invoice.status_code == "100"
    assert invoice.issuer.cnpj == "00000000000191"
    assert invoice.trip.plate == "ABC1D23"
    assert invoice.trip.toll_plaza_km == 642.85
    assert invoice.amounts.service == 13.6
    assert invoice.amounts.total == 13.1
    assert invoice.amounts.taxes.issqn == 0.64
    assert invoice.amounts.taxes.cbs == 0.12
    assert invoice.protocol.access_key == KEY


def test_a_missing_part_leaves_its_fields_empty():
    invoice = parse({"sucesso": True, "dados": {"nfseViaProc": {}}})

    assert invoice.number is None
    assert invoice.trip.plate is None
    assert invoice.amounts.taxes.issqn is None
