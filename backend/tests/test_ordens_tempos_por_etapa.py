from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import DimUc, OrdemEvento, OrdemInspecao
from venergy_api.ordens import StatusOrdem

URL = "/ordens-inspecao/tempos-por-etapa"
INICIO = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)

UC_BASE = {
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "classe_cadastro": "Residencial",
    "cod_alimentador": "AL-01",
    "possui_gd": False,
    "consumo_medio_kwh_12m": 150.0,
    "data_ligacao": date(2018, 6, 1),
}

HORA = 3600
DIA = 24 * HORA


@pytest.fixture(autouse=True)
def stored_ucs(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([DimUc(cod_uc=cod, **UC_BASE) for cod in ("0001", "0002", "0003")])


def store_order(engine: Engine, cod_uc: str, *historico: tuple[StatusOrdem, timedelta]) -> None:
    """Grava uma OI com o histórico dado: cada par é o status em que entrou e quanto depois."""
    with Session(engine) as session, session.begin():
        session.add(
            OrdemInspecao(
                cod_uc=cod_uc,
                status=historico[-1][0],
                eventos=[
                    OrdemEvento(status_novo=status, ocorrido_em=INICIO + depois)
                    for status, depois in historico
                ],
            )
        )


def by_stage(client: TestClient) -> dict[str, dict]:
    response = client.get(URL)
    assert response.status_code == 200, response.text
    return {linha["etapa"]: linha for linha in response.json()}


def test_without_orders_every_stage_comes_with_zero_samples_and_no_percentiles(
    client: TestClient,
) -> None:
    assert client.get(URL).json() == [
        {"etapa": "GERADA", "n": 0, "mediana_segundos": None, "p90_segundos": None},
        {"etapa": "EM_CAMPO", "n": 0, "mediana_segundos": None, "p90_segundos": None},
    ]


def test_median_and_p90_of_the_finished_passes_of_each_stage(
    client: TestClient, engine: Engine
) -> None:
    gerada, em_campo, concluida = (
        StatusOrdem.GERADA,
        StatusOrdem.EM_CAMPO,
        StatusOrdem.CONCLUIDA,
    )
    # A: gerada 1 h, em campo 2 dias, concluída.
    store_order(
        engine,
        "0001",
        (gerada, timedelta(0)),
        (em_campo, timedelta(hours=1)),
        (concluida, timedelta(hours=1, days=2)),
    )
    # B: gerada 3 h, em campo 1 h, voltou para gerada 1 h e foi de novo para o campo (ainda lá).
    store_order(
        engine,
        "0002",
        (gerada, timedelta(0)),
        (em_campo, timedelta(hours=3)),
        (gerada, timedelta(hours=4)),
        (em_campo, timedelta(hours=5)),
    )
    # C: gerada agora, sem passagem encerrada.
    store_order(engine, "0003", (gerada, timedelta(0)))

    etapas = by_stage(client)

    # Gerada: 1 h, 3 h e 1 h. Mediana 1 h; p90 interpola entre 1 h e 3 h: 1 h + 0,8 × 2 h = 9360 s.
    assert etapas["GERADA"]["n"] == 3
    assert etapas["GERADA"]["mediana_segundos"] == pytest.approx(HORA)
    assert etapas["GERADA"]["p90_segundos"] == pytest.approx(2.6 * HORA)
    # Em campo: 2 dias e 1 h (a passagem em curso de B não conta). Mediana é a média das duas;
    # p90 = 1 h + 0,9 × (2 dias - 1 h).
    assert etapas["EM_CAMPO"]["n"] == 2
    assert etapas["EM_CAMPO"]["mediana_segundos"] == pytest.approx((HORA + 2 * DIA) / 2)
    assert etapas["EM_CAMPO"]["p90_segundos"] == pytest.approx(HORA + 0.9 * (2 * DIA - HORA))


def test_a_cancelled_order_closes_the_pass_of_the_stage_it_left(
    client: TestClient, engine: Engine
) -> None:
    store_order(
        engine,
        "0001",
        (StatusOrdem.GERADA, timedelta(0)),
        (StatusOrdem.CANCELADA, timedelta(hours=6)),
    )

    etapas = by_stage(client)

    assert etapas["GERADA"]["n"] == 1
    assert etapas["GERADA"]["mediana_segundos"] == pytest.approx(6 * HORA)
    assert etapas["EM_CAMPO"]["n"] == 0


def test_final_statuses_are_not_stages_of_the_summary(client: TestClient, engine: Engine) -> None:
    store_order(
        engine,
        "0001",
        (StatusOrdem.GERADA, timedelta(0)),
        (StatusOrdem.EM_CAMPO, timedelta(hours=1)),
        (StatusOrdem.CONCLUIDA, timedelta(hours=2)),
    )

    assert [linha["etapa"] for linha in client.get(URL).json()] == ["GERADA", "EM_CAMPO"]
