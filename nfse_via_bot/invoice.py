from pydantic import BaseModel, Field


class Issuer(BaseModel):
    cnpj: str | None = Field(default=None, description="CNPJ da concessionária")
    name: str | None = Field(default=None, description="Razão social")
    municipality_code: str | None = Field(default=None, description="Código IBGE do município")


class Trip(BaseModel):
    plate: str | None = Field(default=None, description="Placa do veículo")
    vehicle_category: str | None = Field(default=None, description="Categoria do veículo")
    direction: str | None = Field(default=None, description="Sentido da passagem")
    toll_plaza: str | None = Field(default=None, description="Praça de pedágio")
    toll_plaza_km: float | None = Field(default=None, description="Quilômetro da praça")
    operation_place: str | None = Field(default=None, description="Local da operação")
    issue_place: str | None = Field(default=None, description="Local da emissão")
    access_code: str | None = Field(default=None, description="Código de acesso do pedágio")
    passage_mode: str | None = Field(default=None, description="Modo da passagem")
    contract_code: str | None = Field(default=None, description="Código do contrato")


class Taxes(BaseModel):
    issqn_base: float | None = None
    issqn_rate: float | None = None
    issqn: float | None = None
    pis: float | None = None
    cofins: float | None = None
    ibs: float | None = None
    cbs: float | None = None


class Amounts(BaseModel):
    service: float | None = Field(default=None, description="Valor do serviço")
    unconditional_discount: float | None = None
    conditional_discount: float | None = None
    total: float | None = Field(default=None, description="Total da nota com IBS e CBS")
    payment_mode: str | None = None
    taxes: Taxes = Field(default_factory=Taxes)


class Protocol(BaseModel):
    number: str | None = None
    received_at: str | None = None
    access_key: str | None = None


class Invoice(BaseModel):
    number: str | None = Field(default=None, description="Número da NFS-e Via")
    series: str | None = None
    issued_at: str | None = Field(default=None, description="Data e hora da emissão")
    competence: str | None = None
    status_code: str | None = Field(default=None, description="cStat; 100 é autorizada")
    national_tax_code: str | None = None
    nbs: str | None = None
    issuer: Issuer = Field(default_factory=Issuer)
    trip: Trip = Field(default_factory=Trip)
    amounts: Amounts = Field(default_factory=Amounts)
    protocol: Protocol = Field(default_factory=Protocol)


def _get(data: dict, *path: str):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse(body: dict) -> Invoice:
    proc = _get(body, "dados", "nfseViaProc") or {}
    info = _get(proc, "NFSeVia", "infNFSeVia") or {}
    service = info.get("serv") or {}
    trip = service.get("explVia") or {}
    values = info.get("valores") or {}
    trib = values.get("trib") or {}
    return Invoice(
        number=service.get("nNFSeVia"),
        series=service.get("serie"),
        issued_at=info.get("dhEmi"),
        competence=info.get("dhCompet"),
        status_code=info.get("cStat"),
        national_tax_code=service.get("cTribNac"),
        nbs=service.get("cNBS"),
        issuer=Issuer(
            cnpj=_get(info, "fornec", "CNPJ"),
            name=_get(info, "fornec", "xNome"),
            municipality_code=_get(info, "fornec", "cMun"),
        ),
        trip=Trip(
            plate=trip.get("placa"),
            vehicle_category=trip.get("categVeic"),
            direction=trip.get("sentido"),
            toll_plaza=service.get("xPracaEmi"),
            toll_plaza_km=_number(service.get("kmPracaEmi")),
            operation_place=service.get("xLocOper"),
            issue_place=service.get("xLocEmi"),
            access_code=trip.get("codAcessoPed"),
            passage_mode=trip.get("modPassagem"),
            contract_code=trip.get("codContrato"),
        ),
        amounts=Amounts(
            service=_number(values.get("vServ")),
            unconditional_discount=_number(_get(values, "vDescCondIncond", "vDescIncond")),
            conditional_discount=_number(_get(values, "vDescCondIncond", "vDescCond")),
            total=_number(_get(trib, "ibscbs", "vTotNF")),
            payment_mode=values.get("modPagamento"),
            taxes=Taxes(
                issqn_base=_number(_get(trib, "issqn", "vBC")),
                issqn_rate=_number(_get(trib, "issqn", "pAliq")),
                issqn=_number(_get(trib, "issqn", "vISSQN")),
                pis=_number(_get(trib, "tribFed", "piscofins", "vPis")),
                cofins=_number(_get(trib, "tribFed", "piscofins", "vCofins")),
                ibs=_number(_get(trib, "ibscbs", "gIBS", "vIBSTot")),
                cbs=_number(_get(trib, "ibscbs", "gCBS", "vCBS")),
            ),
        ),
        protocol=Protocol(
            number=_get(proc, "protNFSeVia", "infProt", "nProt"),
            received_at=_get(proc, "protNFSeVia", "infProt", "dhRecbto"),
            access_key=_get(proc, "protNFSeVia", "infProt", "chNFSeVia"),
        ),
    )
