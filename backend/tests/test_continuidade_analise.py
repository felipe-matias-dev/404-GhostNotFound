"""Variação contra a base, ranking com recorte, série do recorte e o porquê das ocorrências."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.carga import load_gold
from venergy_api.database import Base
from venergy_api.models import (
    ContinuidadeAlimentadorMensal,
    DimUc,
    InterrupcaoUc,
    KpisSegmentoMensal,
)

RANKING = "/continuidade/alimentadores/ranking"
RECORTES = "/continuidade/recortes"
MENSAL = "/continuidade/mensal"
RESUMO = "/continuidade/ocorrencias/resumo"
UCS = "/continuidade/ocorrencias/ucs"


def store_feeders(engine: Engine, rows: list[tuple[str, str, int, int, float]]) -> None:
    """Linhas (alimentador, competência, n_uc, n_interrupcoes, horas)."""
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            ContinuidadeAlimentadorMensal(
                cod_alimentador=alimentador,
                competencia=competencia,
                dec=0.0,
                fec=0.0,
                n_uc=n_uc,
                n_interrupcoes=n_interrupcoes,
                horas_interrompidas=horas,
            )
            for alimentador, competencia, n_uc, n_interrupcoes, horas in rows
        )


# (competencia, municipio, bairro, classe, alimentador, n_uc, n_interrupcoes, horas). O bairro
# Centro existe nos dois municípios; o AL-01 atende Recife e o AL-02 os dois.
SEGMENTS = [
    ("2025-01", "Recife", "Centro", "B1", "AL-01", 100, 10, 20.0),
    ("2025-02", "Recife", "Centro", "B1", "AL-01", 100, 20, 60.0),
    ("2025-01", "Recife", "Centro", "B3", "AL-02", 100, 0, 0.0),
    ("2025-02", "Recife", "Centro", "B3", "AL-02", 100, 10, 10.0),
    ("2025-01", "Olinda", "Centro", "B1", "AL-02", 50, 5, 5.0),
    ("2025-02", "Olinda", "Centro", "B1", "AL-02", 50, 5, 15.0),
    ("2025-01", "Olinda", "Carmo", "B1", "AL-02", 50, 5, 10.0),
    ("2025-02", "Olinda", "Carmo", "B1", "AL-02", 50, 5, 10.0),
]


def store_segments(engine: Engine, rows: list[tuple] = SEGMENTS) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            KpisSegmentoMensal(
                competencia=competencia,
                municipio=municipio,
                bairro=bairro,
                classe_cadastro="Residencial" if classe == "B1" else "Comercial",
                possui_gd=False,
                cod_alimentador=alimentador,
                tipo_medidor="eletronico",
                classe=classe,
                n_uc=n_uc,
                kwh_faturado=Decimal(0),
                receita_faturada=Decimal(0),
                receita_energia=Decimal(0),
                tributos=Decimal(0),
                receita_arrecadada=None,
                horas_interrompidas=horas,
                n_interrupcoes=n_interrupcoes,
                n_chamados=0,
                soma_notas=None,
                n_notas=0,
                receita_bandeira=Decimal(0),
                n_faturas=0,
                n_faturas_nao_pagas=0,
                valor_nao_pago=Decimal(0),
                n_faturas_pagas_com_atraso=0,
                soma_dias_em_atraso=0,
                n_leituras=0,
                n_leituras_estimadas=0,
            )
            for (
                competencia,
                municipio,
                bairro,
                classe,
                alimentador,
                n_uc,
                n_interrupcoes,
                horas,
            ) in rows
        )


def get(client: TestClient, url: str, **params: object) -> dict:
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# --- Variação contra a base ------------------------------------------------------------------

BASE_AND_CURRENT = [
    ("AL-A", "2025-01", 100, 10, 20.0),
    ("AL-A", "2025-02", 100, 15, 30.0),
    ("AL-B", "2025-01", 100, 0, 0.0),
    ("AL-B", "2025-02", 100, 3, 10.0),
    ("AL-NOVO", "2025-02", 100, 4, 8.0),
]


def test_each_feeder_carries_its_base_and_the_variation(engine: Engine, client: TestClient) -> None:
    store_feeders(engine, BASE_AND_CURRENT)

    result = get(
        client, RANKING, inicio="2025-02", fim="2025-02", base_inicio="2025-01", base_fim="2025-01"
    )

    assert (result["base_inicio"], result["base_fim"], result["n_meses_base"]) == (
        "2025-01",
        "2025-01",
        1,
    )
    linhas = {a["cod_alimentador"]: a for a in result["alimentadores"]}
    # AL-A: DEC de 0,2 para 0,3 h (+50%) e de 10 para 15 interrupções (+50%).
    assert linhas["AL-A"]["base"]["dec"] == pytest.approx(0.2)
    assert linhas["AL-A"]["variacao_pct"] == {
        "dec": pytest.approx(50.0),
        "fec": pytest.approx(50.0),
        "horas_interrompidas": pytest.approx(50.0),
        "n_interrupcoes": pytest.approx(50.0),
    }
    # AL-B: base zero, sem variação.
    assert linhas["AL-B"]["variacao_pct"] == {
        "dec": None,
        "fec": None,
        "horas_interrompidas": None,
        "n_interrupcoes": None,
    }
    # AL-NOVO não existe na base.
    assert linhas["AL-NOVO"]["base"] is None
    assert linhas["AL-NOVO"]["variacao_pct"]["dec"] is None


def test_integer_variation_is_not_truncated(engine: Engine, client: TestClient) -> None:
    store_feeders(engine, [("AL-A", "2025-01", 100, 3, 3.0), ("AL-A", "2025-02", 100, 4, 4.0)])

    result = get(
        client, RANKING, inicio="2025-02", fim="2025-02", base_inicio="2025-01", base_fim="2025-01"
    )

    assert result["alimentadores"][0]["variacao_pct"]["n_interrupcoes"] == pytest.approx(100 / 3)


def test_feeder_only_in_the_base_does_not_enter_the_ranking(
    engine: Engine, client: TestClient
) -> None:
    store_feeders(engine, [*BASE_AND_CURRENT, ("AL-VELHO", "2025-01", 100, 50, 90.0)])

    result = get(
        client, RANKING, inicio="2025-02", fim="2025-02", base_inicio="2025-01", base_fim="2025-01"
    )

    assert "AL-VELHO" not in {a["cod_alimentador"] for a in result["alimentadores"]}


def test_variation_is_null_when_a_month_is_missing_in_either_period(
    engine: Engine, client: TestClient
) -> None:
    store_feeders(engine, BASE_AND_CURRENT)

    # Base de dezembro a janeiro: dezembro não existe na tabela.
    incompleta = get(
        client, RANKING, inicio="2025-02", fim="2025-02", base_inicio="2024-12", base_fim="2025-01"
    )
    # Atual de fevereiro a março: março não existe.
    atual_incompleto = get(
        client, RANKING, inicio="2025-02", fim="2025-03", base_inicio="2025-01", base_fim="2025-01"
    )

    for resultado in (incompleta, atual_incompleto):
        linha = next(a for a in resultado["alimentadores"] if a["cod_alimentador"] == "AL-A")
        assert linha["base"] is not None
        assert set(linha["variacao_pct"].values()) == {None}


def test_without_base_the_rows_have_no_base_nor_variation(
    engine: Engine, client: TestClient
) -> None:
    store_feeders(engine, BASE_AND_CURRENT)

    result = get(client, RANKING, inicio="2025-02", fim="2025-02")

    assert result["n_meses_base"] is None
    assert all(a["base"] is None and a["variacao_pct"] is None for a in result["alimentadores"])


@pytest.mark.parametrize("url", [RANKING, RECORTES])
def test_base_must_end_before_the_current_period_and_come_whole(
    engine: Engine, client: TestClient, url: str
) -> None:
    store_segments(engine)
    store_feeders(engine, BASE_AND_CURRENT)
    periodo = {"inicio": "2025-02", "fim": "2025-02"}

    sobreposta = {**periodo, "base_inicio": "2025-01", "base_fim": "2025-02"}
    sem_fim = {**periodo, "base_inicio": "2025-01"}
    invertida = {
        "inicio": "2025-03",
        "fim": "2025-03",
        "base_inicio": "2025-02",
        "base_fim": "2025-01",
    }

    for params in (sobreposta, sem_fim, invertida):
        assert client.get(url, params=params).status_code == 422


def test_neighborhoods_carry_the_variation_too(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = get(
        client,
        RECORTES,
        inicio="2025-02",
        fim="2025-02",
        municipio="Olinda",
        base_inicio="2025-01",
        base_fim="2025-01",
    )

    linhas = {r["segmento"]: r for r in result["recortes"]}
    # Centro de Olinda: 5 h para 15 h (+200%); Carmo: 10 h nos dois meses (0%).
    assert linhas["Centro"]["variacao_pct"]["horas_interrompidas"] == pytest.approx(200.0)
    assert linhas["Carmo"]["variacao_pct"]["dec"] == pytest.approx(0.0)


# --- Ranking com recorte e ranking plano de bairros ------------------------------------------


def test_ranking_with_a_cut_aggregates_the_segments_by_feeder(
    engine: Engine, client: TestClient
) -> None:
    store_segments(engine)

    recife = get(client, RANKING, inicio="2025-01", fim="2025-02", municipio="Recife")
    b1 = get(client, RANKING, inicio="2025-01", fim="2025-02", classe="B1")

    # Recife: AL-01 com 80 h ÷ (200 UC ÷ 2) = 0,8; AL-02 com 10 h ÷ 100 = 0,1.
    assert [(a["cod_alimentador"], a["dec"]) for a in recife["alimentadores"]] == [
        ("AL-01", pytest.approx(0.8)),
        ("AL-02", pytest.approx(0.1)),
    ]
    # Só B1: o AL-02 fica com Olinda (40 h ÷ 100 UC = 0,4).
    assert [(a["cod_alimentador"], a["dec"]) for a in b1["alimentadores"]] == [
        ("AL-01", pytest.approx(0.8)),
        ("AL-02", pytest.approx(0.4)),
    ]


def test_ranking_rejects_a_neighborhood_without_municipality(
    engine: Engine, client: TestClient
) -> None:
    store_segments(engine)

    response = client.get(
        RANKING, params={"inicio": "2025-01", "fim": "2025-02", "bairro": "Centro"}
    )

    assert response.status_code == 422


def test_flat_neighborhood_ranking_keeps_homonyms_apart(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    result = get(client, RECORTES, inicio="2025-01", fim="2025-02", nivel="bairro")

    # Centro de Recife: 90 h ÷ 200 = 0,45; Centro de Olinda: 20 h ÷ 50 = 0,4; Carmo: 0,4.
    assert result["nivel"] == "bairro"
    assert [(r["segmento"], r["municipio"], r["dec"]) for r in result["recortes"]] == [
        ("Centro", "Recife", pytest.approx(0.45)),
        ("Carmo", "Olinda", pytest.approx(0.4)),
        ("Centro", "Olinda", pytest.approx(0.4)),
    ]


def test_other_levels_have_no_municipality_field(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    municipios = get(client, RECORTES, inicio="2025-01", fim="2025-02")
    alimentadores = get(client, RECORTES, inicio="2025-01", fim="2025-02", nivel="alimentador")

    assert {r["municipio"] for r in municipios["recortes"]} == {None}
    assert {r["segmento"] for r in alimentadores["recortes"]} == {"AL-01", "AL-02"}
    assert {r["municipio"] for r in alimentadores["recortes"]} == {None}


def test_level_above_the_filter_is_rejected(engine: Engine, client: TestClient) -> None:
    store_segments(engine)
    periodo = {"inicio": "2025-01", "fim": "2025-02"}

    acima = {**periodo, "municipio": "Recife", "bairro": "Centro", "nivel": "municipio"}
    abaixo = {**periodo, "municipio": "Recife", "nivel": "alimentador"}

    assert client.get(RECORTES, params=acima).status_code == 422
    assert client.get(RECORTES, params=abaixo).status_code == 200


def test_both_sources_give_the_same_feeder_indexes_on_the_sample(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    periodo = {"inicio": "2025-01", "fim": "2025-12"}

    ranking = get(client, RANKING, **periodo)["alimentadores"]
    segmentos = get(client, RECORTES, nivel="alimentador", **periodo)["recortes"]

    assert [a["cod_alimentador"] for a in ranking] == [s["segmento"] for s in segmentos]
    for alimentador, segmento in zip(ranking, segmentos, strict=True):
        assert alimentador["dec"] == pytest.approx(segmento["dec"])
        assert alimentador["fec"] == pytest.approx(segmento["fec"])


# --- Série mensal do recorte ------------------------------------------------------------------


def test_monthly_series_of_a_cut_leaves_missing_months_null(
    engine: Engine, client: TestClient
) -> None:
    store_segments(
        engine,
        [
            *SEGMENTS,
            ("2025-03", "Recife", "Centro", "B1", "AL-01", 100, 0, 0.0),
        ],
    )

    serie = get(client, MENSAL, inicio="2025-01", fim="2025-03", municipio="Olinda")

    assert [linha["competencia"] for linha in serie] == ["2025-01", "2025-02", "2025-03"]
    # Olinda em janeiro: 15 h ÷ 100 UC; em março, sem linha: tudo nulo, e não zero.
    assert serie[0]["dec"] == pytest.approx(0.15)
    assert serie[0]["n_uc"] == 100
    assert serie[2] == {
        "competencia": "2025-03",
        "dec": None,
        "fec": None,
        "horas_interrompidas": None,
        "n_interrupcoes": None,
        "n_uc": None,
    }


def test_monthly_series_of_a_feeder_inside_a_cut(engine: Engine, client: TestClient) -> None:
    store_segments(engine)

    serie = get(
        client, MENSAL, inicio="2025-02", fim="2025-02", municipio="Olinda", cod_alimentador="AL-02"
    )

    # AL-02 só em Olinda, fevereiro: 25 h ÷ 100 UC.
    assert serie[0]["dec"] == pytest.approx(0.25)
    assert serie[0]["horas_interrompidas"] == pytest.approx(25.0)


def test_monthly_series_matches_the_feeder_series_on_the_sample(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    periodo = {"inicio": "2025-01", "fim": "2025-12"}

    gold = get(client, "/continuidade/alimentadores/mensal", cod_alimentador="AL-06", **periodo)
    serie = get(client, MENSAL, cod_alimentador="AL-06", **periodo)

    assert [g["competencia"] for g in gold] == [s["competencia"] for s in serie]
    for linha_gold, linha in zip(gold, serie, strict=True):
        assert linha["dec"] == pytest.approx(linha_gold["dec"])
        assert linha["fec"] == pytest.approx(linha_gold["fec"])
        assert linha["n_uc"] == linha_gold["n_uc"]


# --- Por que cai: ocorrências -----------------------------------------------------------------


def store_units(engine: Engine, units: list[tuple[str, str, str, str, str]]) -> None:
    """UCs (cod_uc, município, bairro, classe, alimentador)."""
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            DimUc(
                cod_uc=cod_uc,
                municipio=municipio,
                bairro=bairro,
                classe=classe,
                classe_cadastro="Residencial" if classe == "B1" else "Comercial",
                cod_alimentador=alimentador,
                possui_gd=False,
                consumo_medio_kwh_12m=None,
                titular_mascarado="F*** S***",
                documento_mascarado="***.123.***-**",
                potencia_kwp=None,
                data_ligacao=date(2020, 1, 1),
                data_conexao_gd=None,
                modalidade_gd=None,
                energia_injetada_kwh_mes=None,
            )
            for cod_uc, municipio, bairro, classe, alimentador in units
        )


def store_outages(engine: Engine, outages: list[tuple[str, str, float, str, str | None]]) -> None:
    """Ocorrências (cod_uc, competência, duração em horas, tipo, causa)."""
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        alimentador = {uc.cod_uc: uc.cod_alimentador for uc in session.query(DimUc)}
        for numero, (cod_uc, competencia, duracao, tipo, causa) in enumerate(outages):
            abertura = datetime(int(competencia[:4]), int(competencia[5:]), 1, 8)
            session.add(
                InterrupcaoUc(
                    cod_ocorrencia=f"OC-{numero}",
                    cod_uc=cod_uc,
                    cod_alimentador=alimentador[cod_uc],
                    competencia=competencia,
                    data_abertura=abertura,
                    data_encerramento=abertura + timedelta(hours=duracao),
                    duracao_horas=duracao,
                    tipo=tipo,
                    causa=causa,
                )
            )


UNITS = [
    ("UC-1", "Recife", "Centro", "B1", "AL-01"),
    ("UC-2", "Recife", "Centro", "B3", "AL-01"),
    ("UC-3", "Olinda", "Carmo", "B1", "AL-02"),
]
OUTAGES = [
    ("UC-1", "2025-01", 1.0, "FALTA DE ENERGIA", "VEGETACAO"),
    ("UC-1", "2025-01", 2.0, "FALTA DE ENERGIA", None),
    ("UC-1", "2025-02", 4.0, "OSCILACAO", None),
    ("UC-2", "2025-01", 3.0, "FALTA DE ENERGIA", "CLIMATICA"),
    ("UC-2", "2025-02", 3.5, "FALTA DE ENERGIA", "CLIMATICA"),
    ("UC-3", "2025-01", 10.0, "FALTA DE ENERGIA", "CLIMATICA"),
]


def test_summary_groups_by_cause_and_keeps_the_unknown_cause(
    engine: Engine, client: TestClient
) -> None:
    store_units(engine, UNITS)
    store_outages(engine, OUTAGES)

    result = get(client, RESUMO, inicio="2025-01", fim="2025-02", cod_alimentador="AL-01")

    assert result["total"] == {
        "n_interrupcoes": 5,
        "horas_interrompidas": pytest.approx(13.5),
        "ucs_atingidas": 2,
        "ucs_reincidentes": 1,
    }
    assert result["por_causa"] == [
        {"nome": "CLIMATICA", "n_interrupcoes": 2, "horas_interrompidas": pytest.approx(6.5)},
        {"nome": None, "n_interrupcoes": 2, "horas_interrompidas": pytest.approx(6.0)},
        {"nome": "VEGETACAO", "n_interrupcoes": 1, "horas_interrompidas": pytest.approx(1.0)},
    ]
    assert [(t["nome"], t["n_interrupcoes"]) for t in result["por_tipo"]] == [
        ("FALTA DE ENERGIA", 4),
        ("OSCILACAO", 1),
    ]


def test_recurrence_and_long_outages_include_the_threshold(
    engine: Engine, client: TestClient
) -> None:
    store_units(engine, UNITS)
    store_outages(engine, OUTAGES)
    periodo = {"inicio": "2025-01", "fim": "2025-02", "cod_alimentador": "AL-01"}

    padrao = get(client, RESUMO, **periodo)
    exigente = get(client, RESUMO, reincidencia_min=4, longa_h=3.5, **periodo)

    # UC-1 tem exatamente 3 interrupções: reincidente no padrão (>= 3), não com 4.
    assert padrao["reincidencia_min"] == 3
    assert padrao["total"]["ucs_reincidentes"] == 1
    assert exigente["total"]["ucs_reincidentes"] == 0
    # Exatamente 4 h conta como longa no padrão; com 3,5 h, também a de 3,5 h.
    assert padrao["duracao"]["n_longas"] == 1
    assert exigente["duracao"]["n_longas"] == 2
    assert padrao["duracao"]["maxima_h"] == 4.0
    assert padrao["duracao"]["mediana_h"] == pytest.approx(3.0)


def test_summary_cut_comes_from_the_unit_registry(engine: Engine, client: TestClient) -> None:
    store_units(engine, UNITS)
    store_outages(engine, OUTAGES)
    periodo = {"inicio": "2025-01", "fim": "2025-02"}

    b3 = get(client, RESUMO, classe="B3", **periodo)
    olinda = get(client, RESUMO, municipio="Olinda", **periodo)
    vazio = get(client, RESUMO, inicio="2030-01", fim="2030-01")

    assert b3["total"]["horas_interrompidas"] == pytest.approx(6.5)
    assert olinda["total"]["ucs_atingidas"] == 1
    assert vazio["total"]["n_interrupcoes"] == 0
    assert vazio["duracao"] == {"mediana_h": None, "p90_h": None, "maxima_h": None, "n_longas": 0}
    assert vazio["por_causa"] == []


def test_summary_rejects_a_neighborhood_without_municipality(
    engine: Engine, client: TestClient
) -> None:
    store_units(engine, UNITS)

    response = client.get(
        RESUMO, params={"inicio": "2025-01", "fim": "2025-02", "bairro": "Centro"}
    )

    assert response.status_code == 422


def test_most_affected_units_are_paginated_by_hours(engine: Engine, client: TestClient) -> None:
    store_units(engine, UNITS)
    store_outages(engine, OUTAGES)
    periodo = {"inicio": "2025-01", "fim": "2025-02"}

    primeira = get(client, UCS, tamanho=2, **periodo)
    segunda = get(client, UCS, tamanho=2, pagina=2, **periodo)
    alem = get(client, UCS, tamanho=2, pagina=3, **periodo)

    assert primeira["total"] == 3
    assert primeira["ucs"][0] == {
        "cod_uc": "UC-3",
        "municipio": "Olinda",
        "bairro": "Carmo",
        "n_interrupcoes": 1,
        "horas_interrompidas": 10.0,
        "maior_duracao_h": 10.0,
    }
    assert [u["cod_uc"] for u in primeira["ucs"]] == ["UC-3", "UC-1"]
    assert [u["cod_uc"] for u in segunda["ucs"]] == ["UC-2"]
    assert (alem["total"], alem["ucs"]) == (3, [])
    assert client.get(UCS, params={**periodo, "tamanho": 51}).status_code == 422


def test_summary_matches_the_ranking_of_a_feeder_on_the_sample(
    tmp_path: Path, engine: Engine, client: TestClient
) -> None:
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    periodo = {"inicio": "2025-01", "fim": "2025-12"}

    ranking = get(client, RANKING, **periodo)["alimentadores"]
    for alimentador in ranking:
        resumo = get(client, RESUMO, cod_alimentador=alimentador["cod_alimentador"], **periodo)
        assert resumo["total"]["horas_interrompidas"] == pytest.approx(
            alimentador["horas_interrompidas"]
        )
        assert resumo["total"]["n_interrupcoes"] == alimentador["n_interrupcoes"]
        assert (
            sum(c["n_interrupcoes"] for c in resumo["por_causa"]) == alimentador["n_interrupcoes"]
        )
    causas = get(client, RESUMO, **periodo)["por_causa"]
    assert None in {c["nome"] for c in causas}
