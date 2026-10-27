from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.database import Base
from venergy_api.models import (
    AtendimentoUc,
    DimUc,
    FatoFaturamentoMensal,
    InspecaoUc,
    InterrupcaoUc,
    MedidorUc,
)

URL = "/unidades-consumidoras/{cod_uc}/visao-360"


def make_uc(cod_uc: str, **changes: object) -> DimUc:
    values: dict[str, object] = {
        "cod_uc": cod_uc,
        "municipio": "Recife",
        "bairro": "Boa Viagem",
        "classe": "B1",
        "classe_cadastro": "Residencial",
        "cod_alimentador": "AL-01",
        "possui_gd": False,
        "consumo_medio_kwh_12m": Decimal("150"),
        "titular_mascarado": "M. S.",
        "documento_mascarado": "***.***.**1-23",
        "potencia_kwp": None,
        "data_ligacao": date(2018, 6, 1),
        "data_conexao_gd": None,
        "modalidade_gd": None,
        "energia_injetada_kwh_mes": None,
    }
    return DimUc(**{**values, **changes})


def make_meter(cod_uc: str, **changes: object) -> MedidorUc:
    values: dict[str, object] = {
        "cod_uc": cod_uc,
        "cod_medidor": f"MED-{cod_uc}",
        "tipo_medidor": "smart",
        "modelo": "Landis E350",
        "data_instalacao": date(2021, 3, 10),
        "idade_anos": 3.5,
        "n_trocas": 1,
        "data_ultima_troca": date(2021, 3, 10),
    }
    return MedidorUc(**{**values, **changes})


def make_outage(cod_ocorrencia: str, cod_uc: str, abertura: datetime, **changes: object):
    values: dict[str, object] = {
        "cod_ocorrencia": cod_ocorrencia,
        "cod_uc": cod_uc,
        "cod_alimentador": "AL-01",
        "competencia": abertura.strftime("%Y-%m"),
        "data_abertura": abertura,
        "data_encerramento": abertura.replace(hour=abertura.hour + 2),
        "duracao_horas": 2.0,
        "tipo": "nao_programada",
        "causa": "descarga_atmosferica",
    }
    return InterrupcaoUc(**{**values, **changes})


def make_ticket(protocolo: str, cod_uc: str, abertura: datetime, **changes: object):
    values: dict[str, object] = {
        "protocolo": protocolo,
        "cod_uc": cod_uc,
        "competencia": abertura.strftime("%Y-%m"),
        "data_abertura": abertura,
        "data_fechamento": abertura.replace(hour=abertura.hour + 1),
        "canal": "telefone",
        "assunto": "conta_alta",
        "subassunto": None,
        "nota_satisfacao": 4.0,
    }
    return AtendimentoUc(**{**values, **changes})


def make_inspection(cod_inspecao: str, cod_uc: str, data: date, **changes: object):
    values: dict[str, object] = {
        "cod_inspecao": cod_inspecao,
        "cod_uc": cod_uc,
        "data_inspecao": data,
        "competencia": data.strftime("%Y-%m"),
        "resultado": "irregularidade_confirmada",
        "tipo_irregularidade": "desvio_de_energia",
        "kwh_recuperado": Decimal("320"),
    }
    return InspecaoUc(**{**values, **changes})


def make_invoice(cod_uc: str, competencia: str, **changes: object) -> FatoFaturamentoMensal:
    ano, mes = int(competencia[:4]), int(competencia[5:])
    values: dict[str, object] = {
        "cod_uc": cod_uc,
        "competencia": competencia,
        "kwh_faturado": Decimal("100"),
        "kwh_leitura": Decimal("100"),
        "origem_kwh": "leitura",
        "receita_faturada": Decimal("90.00"),
        "receita_energia": Decimal("70.00"),
        "tributos": Decimal("20.00"),
        "receita_arrecadada": Decimal("90.00"),
        "tarifa_media": 0.9,
        "bandeira": "verde",
        "data_vencimento": date(ano + (mes // 12), (mes % 12) + 1, 10),
        "data_pagamento": date(ano + (mes // 12), (mes % 12) + 1, 8),
        "status_pagamento": "paga",
        "dias_em_atraso": None,
        "receita_bandeira": Decimal("0"),
        "tipo_leitura": "real",
        "tipo_medidor": "smart",
        "dias_faturados": 30,
    }
    return FatoFaturamentoMensal(**{**values, **changes})


@pytest.fixture
def seed(engine: Engine):
    """Cria as tabelas e devolve uma função que grava linhas numa transação própria."""
    Base.metadata.create_all(engine)

    def add(*rows: Base) -> None:
        with Session(engine) as session, session.begin():
            session.add_all(rows)

    return add


def test_returns_the_registration_and_the_meter(client: TestClient, seed) -> None:
    seed(make_uc("0001", possui_gd=True, potencia_kwp=3.3), make_meter("0001"))

    response = client.get(URL.format(cod_uc="0001"))

    assert response.status_code == 200
    body = response.json()
    assert body["cadastro"]["cod_uc"] == "0001"
    assert body["cadastro"]["possui_gd"] is True
    assert body["cadastro"]["potencia_kwp"] == 3.3
    assert body["medidor"]["cod_medidor"] == "MED-0001"
    assert body["medidor"]["tipo_medidor"] == "smart"
    assert body["medidor"]["n_trocas"] == 1


def test_unit_without_meter_has_no_meter_block(client: TestClient, seed) -> None:
    # A UC sem medidor instalado não tem linha em gold_medidor_uc: vazio, e não erro.
    seed(make_uc("0002"))

    response = client.get(URL.format(cod_uc="0002"))

    assert response.status_code == 200
    assert response.json()["medidor"] is None


def test_returns_404_when_the_consumer_unit_does_not_exist(client: TestClient, seed) -> None:
    seed(make_uc("0001"))

    response = client.get(URL.format(cod_uc="9999"))

    assert response.status_code == 404
    assert response.json() == {"detail": "Unidade consumidora 9999 não encontrada"}


def test_lists_only_the_history_of_the_requested_unit(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_uc("0002"),
        make_outage("OC-1", "0001", datetime(2025, 3, 5, 10)),
        make_outage("OC-2", "0002", datetime(2025, 3, 5, 10)),
        make_ticket("AT-1", "0001", datetime(2025, 4, 2, 9)),
        make_ticket("AT-2", "0002", datetime(2025, 4, 2, 9)),
        make_inspection("IN-1", "0001", date(2025, 5, 20)),
        make_inspection("IN-2", "0002", date(2025, 5, 20)),
    )

    body = client.get(URL.format(cod_uc="0001")).json()

    assert [item["cod_ocorrencia"] for item in body["interrupcoes"]] == ["OC-1"]
    assert [item["protocolo"] for item in body["atendimentos"]] == ["AT-1"]
    assert [item["cod_inspecao"] for item in body["inspecoes"]] == ["IN-1"]


def test_history_comes_newest_first(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_outage("OC-1", "0001", datetime(2024, 1, 5, 10)),
        make_outage("OC-2", "0001", datetime(2025, 6, 5, 10)),
        make_outage("OC-3", "0001", datetime(2025, 2, 5, 10)),
        make_ticket("AT-1", "0001", datetime(2024, 8, 2, 9)),
        make_ticket("AT-2", "0001", datetime(2025, 8, 2, 9)),
        make_inspection("IN-1", "0001", date(2023, 5, 20)),
        make_inspection("IN-2", "0001", date(2025, 5, 20)),
    )

    body = client.get(URL.format(cod_uc="0001")).json()

    assert [item["cod_ocorrencia"] for item in body["interrupcoes"]] == ["OC-2", "OC-3", "OC-1"]
    assert [item["protocolo"] for item in body["atendimentos"]] == ["AT-2", "AT-1"]
    assert [item["cod_inspecao"] for item in body["inspecoes"]] == ["IN-2", "IN-1"]


def test_unit_without_history_gets_empty_lists(client: TestClient, seed) -> None:
    seed(make_uc("0001"))

    body = client.get(URL.format(cod_uc="0001")).json()

    assert body["interrupcoes"] == []
    assert body["atendimentos"] == []
    assert body["inspecoes"] == []


def test_unrated_ticket_and_unknown_cause_stay_empty(client: TestClient, seed) -> None:
    # Vazio, e não zero nem texto: o cliente não avaliou, e a causa não foi registrada.
    seed(
        make_uc("0001"),
        make_outage("OC-1", "0001", datetime(2025, 3, 5, 10), causa=None),
        make_ticket("AT-1", "0001", datetime(2025, 4, 2, 9), nota_satisfacao=None),
    )

    body = client.get(URL.format(cod_uc="0001")).json()

    assert body["interrupcoes"][0]["causa"] is None
    assert body["atendimentos"][0]["nota_satisfacao"] is None


def test_open_invoices_list_only_unpaid_ones_oldest_first(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2025-01"),
        make_invoice("0001", "2025-02", status_pagamento="paga_com_atraso", dias_em_atraso=4),
        make_invoice(
            "0001",
            "2025-04",
            receita_faturada=Decimal("120.50"),
            data_pagamento=None,
            status_pagamento="em_atraso",
            dias_em_atraso=40,
        ),
        make_invoice(
            "0001",
            "2025-03",
            receita_faturada=Decimal("99.90"),
            data_pagamento=None,
            status_pagamento="em_aberto",
            dias_em_atraso=None,
        ),
    )

    body = client.get(URL.format(cod_uc="0001")).json()["faturas_nao_pagas"]

    assert [item["competencia"] for item in body["itens"]] == ["2025-03", "2025-04"]
    assert [item["status_pagamento"] for item in body["itens"]] == ["em_aberto", "em_atraso"]
    assert body["itens"][1]["dias_em_atraso"] == 40
    assert body["itens"][0]["dias_em_atraso"] is None
    assert body["quantidade"] == 2


def test_open_invoices_total_is_exact(client: TestClient, seed) -> None:
    # 0,10 + 0,20 em float dá 0,30000000000000004: o total sai da soma em Decimal (DEC-010).
    seed(
        make_uc("0001"),
        make_invoice(
            "0001",
            "2025-01",
            receita_faturada=Decimal("0.10"),
            data_pagamento=None,
            status_pagamento="em_atraso",
            dias_em_atraso=10,
        ),
        make_invoice(
            "0001",
            "2025-02",
            receita_faturada=Decimal("0.20"),
            data_pagamento=None,
            status_pagamento="em_atraso",
            dias_em_atraso=5,
        ),
    )

    body = client.get(URL.format(cod_uc="0001")).json()["faturas_nao_pagas"]

    assert body["valor_total"] == 0.3


def test_other_units_invoices_are_not_counted(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_uc("0002"),
        make_invoice(
            "0002", "2025-01", data_pagamento=None, status_pagamento="em_atraso", dias_em_atraso=9
        ),
    )

    body = client.get(URL.format(cod_uc="0001")).json()["faturas_nao_pagas"]

    assert body == {"quantidade": 0, "valor_total": 0, "itens": []}
