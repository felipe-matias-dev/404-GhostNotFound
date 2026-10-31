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


def consumption(client: TestClient, cod_uc: str = "0001") -> dict:
    return client.get(URL.format(cod_uc=cod_uc)).json()["consumo"]


def test_consumption_covers_the_twelve_months_ending_at_the_last_month_of_the_gold(
    client: TestClient, seed
) -> None:
    # A referência é a última competência da Gold, e não o mês de hoje: o dado é uma extração
    # única, e com a data de hoje os 12 meses viriam vazios.
    seed(make_uc("0001"), make_invoice("0001", "2025-12"))

    body = consumption(client)

    assert body["referencia"] == "2025-12"
    assert [mes["competencia"] for mes in body["meses"]] == [
        f"2025-{numero:02d}" for numero in range(1, 13)
    ]


def test_reference_is_the_gold_month_even_if_the_unit_has_no_invoice_in_it(
    client: TestClient, seed
) -> None:
    # A UC parou de faturar em 2025-06, mas a Gold vai até 2025-12 (outra UC): a UC não é
    # tratada como "recente" só porque a última fatura dela é a última que ela tem.
    seed(
        make_uc("0001"),
        make_uc("0002"),
        make_invoice("0001", "2025-06"),
        make_invoice("0002", "2025-12"),
    )

    body = consumption(client)

    assert body["referencia"] == "2025-12"
    assert body["meses"][-1] == {
        "competencia": "2025-12",
        "kwh_faturado": None,
        "kwh_ano_anterior": None,
        "receita_faturada": None,
        "bandeira": None,
        "dias_faturados": None,
    }
    assert body["tendencia"] == "sem_comparacao"


def test_each_month_carries_the_same_month_of_the_previous_year(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-03", kwh_faturado=Decimal("80")),
        make_invoice(
            "0001",
            "2025-03",
            kwh_faturado=Decimal("120.5"),
            receita_faturada=Decimal("140.25"),
            bandeira="amarela",
            dias_faturados=31,
        ),
        make_invoice("0001", "2025-12"),
    )

    march = next(mes for mes in consumption(client)["meses"] if mes["competencia"] == "2025-03")

    assert march == {
        "competencia": "2025-03",
        "kwh_faturado": 120.5,
        "kwh_ano_anterior": 80,
        "receita_faturada": 140.25,
        "bandeira": "amarela",
        "dias_faturados": 31,
    }


def test_month_without_invoice_is_empty_and_not_zero(client: TestClient, seed) -> None:
    seed(make_uc("0001"), make_invoice("0001", "2025-12"))

    january = consumption(client)["meses"][0]

    assert january["kwh_faturado"] is None
    assert january["kwh_ano_anterior"] is None


def test_twelve_month_totals_and_variation(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-11", kwh_faturado=Decimal("100")),
        make_invoice("0001", "2024-12", kwh_faturado=Decimal("100")),
        make_invoice("0001", "2025-11", kwh_faturado=Decimal("150")),
        make_invoice("0001", "2025-12", kwh_faturado=Decimal("150")),
    )

    body = consumption(client)

    assert body["kwh_12m"] == 300
    assert body["kwh_12m_ano_anterior"] == 200
    assert body["variacao_12m_pct"] == 50.0
    assert body["meses_comparados"] == 2


def test_variation_compares_only_the_months_with_an_invoice_in_both_years(
    client: TestClient, seed
) -> None:
    # Unidade ligada em 2024-12: 12 faturas na janela contra 1 no ano anterior. Somar tudo daria
    # +1100%, que mede a falta de fatura e não o consumo; só dezembro tem os dois lados.
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-12"),
        *(make_invoice("0001", f"2025-{mes:02d}") for mes in range(1, 13)),
    )

    body = consumption(client)

    assert body["kwh_12m"] == 1200
    assert body["kwh_12m_ano_anterior"] == 100
    assert body["variacao_12m_pct"] == 0.0
    assert body["meses_comparados"] == 1


def test_variation_is_empty_when_no_month_has_an_invoice_in_both_years(
    client: TestClient, seed
) -> None:
    seed(
        make_uc("0001"),
        make_uc("0002"),
        make_invoice("0001", "2024-12", kwh_faturado=Decimal("100")),
        make_invoice("0001", "2025-11", kwh_faturado=Decimal("150")),
        make_invoice("0002", "2025-12"),
    )

    body = consumption(client)

    assert body["kwh_12m"] == 150
    assert body["kwh_12m_ano_anterior"] == 100
    assert body["variacao_12m_pct"] is None
    assert body["meses_comparados"] == 0


def test_consumption_is_empty_before_the_gold_has_invoices(client: TestClient, seed) -> None:
    seed(make_uc("0001"))

    body = consumption(client)

    assert body["referencia"] is None
    assert body["meses"] == []
    assert body["variacao_12m_pct"] is None
    assert body["meses_comparados"] == 0
    assert body["tendencia"] == "sem_comparacao"


def test_no_previous_year_means_no_percentage(client: TestClient, seed) -> None:
    seed(make_uc("0001"), make_invoice("0001", "2025-12", kwh_faturado=Decimal("150")))

    body = consumption(client)

    assert body["kwh_12m_ano_anterior"] == 0
    assert body["variacao_12m_pct"] is None
    assert body["variacao_ultimo_mes_pct"] is None
    assert body["tendencia"] == "sem_comparacao"


@pytest.mark.parametrize(
    ("last_month_kwh", "expected"),
    [
        ("110.01", "subiu"),
        ("110", "estavel"),  # +10% exato ainda é estável
        ("100", "estavel"),
        ("90", "estavel"),  # -10% exato ainda é estável
        ("89.99", "caiu"),
        ("0", "caiu"),  # painel solar compensando tudo: consumo faturado zero
    ],
)
def test_trend_compares_the_last_month_with_the_same_month_of_the_previous_year(
    client: TestClient, seed, last_month_kwh: str, expected: str
) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-12", kwh_faturado=Decimal("100")),
        make_invoice("0001", "2025-12", kwh_faturado=Decimal(last_month_kwh)),
    )

    assert consumption(client)["tendencia"] == expected


def test_trend_is_unavailable_when_the_previous_year_month_has_zero_kwh(
    client: TestClient, seed
) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-12", kwh_faturado=Decimal("0")),
        make_invoice("0001", "2025-12", kwh_faturado=Decimal("100")),
    )

    body = consumption(client)

    assert body["variacao_ultimo_mes_pct"] is None
    assert body["tendencia"] == "sem_comparacao"


def test_last_month_variation_is_a_percentage(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-12", kwh_faturado=Decimal("200")),
        make_invoice("0001", "2025-12", kwh_faturado=Decimal("250")),
    )

    assert consumption(client)["variacao_ultimo_mes_pct"] == 25.0


def test_year_boundary_pairs_january_with_the_previous_january(client: TestClient, seed) -> None:
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-01", kwh_faturado=Decimal("70")),
        make_invoice("0001", "2025-01", kwh_faturado=Decimal("90")),
        make_invoice("0001", "2025-06", kwh_faturado=Decimal("10")),
    )

    body = consumption(client)

    assert body["referencia"] == "2025-06"
    assert body["meses"][0]["competencia"] == "2024-07"
    assert body["meses"][-1]["competencia"] == "2025-06"
    january = next(mes for mes in body["meses"] if mes["competencia"] == "2025-01")
    assert january["kwh_ano_anterior"] == 70


def test_bill_variation_splits_the_difference_with_the_same_month_of_the_previous_year(
    client: TestClient, seed
) -> None:
    # Mesma energia e mesmos dias nos dois anos: a conta subiu R$ 8,50, sendo R$ 1,90 da
    # bandeira que entrou, R$ 5,60 de reajuste da tarifa e R$ 1,00 de tributos.
    seed(
        make_uc("0001"),
        make_invoice("0001", "2024-12"),
        make_invoice(
            "0001",
            "2025-12",
            receita_bandeira=Decimal("1.90"),
            receita_energia=Decimal("77.50"),
            tributos=Decimal("21.00"),
            receita_faturada=Decimal("98.50"),
        ),
    )

    body = client.get(URL.format(cod_uc="0001")).json()

    assert body["variacao_conta"] == {
        "competencia": "2025-12",
        "competencia_comparada": "2024-12",
        "conta": 98.5,
        "conta_comparada": 90.0,
        "diferenca": 8.5,
        "dias_faturados": 30,
        "dias_faturados_comparada": 30,
        "consumo": 0.0,
        "tarifa": 5.6,
        "bandeira": 1.9,
        "tributos": 1.0,
        "leitura_estimada": False,
    }


def test_bill_variation_is_empty_without_the_bill_of_the_previous_year(
    client: TestClient, seed
) -> None:
    seed(make_uc("0001"), make_invoice("0001", "2025-12"))

    body = client.get(URL.format(cod_uc="0001")).json()

    assert body["variacao_conta"] is None
