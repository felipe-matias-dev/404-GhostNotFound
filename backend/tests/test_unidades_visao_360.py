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
