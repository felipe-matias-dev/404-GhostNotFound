from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from venergy_agent.domain.numbers import unsupported_numbers

from venergy_api.database import Base
from venergy_api.insight_continuidade import metricas_da_continuidade, texto_aceito
from venergy_api.models import ContinuidadeAlimentadorMensal
from venergy_api.schemas import (
    RankingAlimentadorSchema,
    RankingContinuidadeSchema,
    RankingFiltroSchema,
    VariacaoContinuidadeSchema,
)


def filtro(**changes: str) -> RankingFiltroSchema:
    return RankingFiltroSchema(inicio="2025-01", fim="2025-12", **changes)


def alimentador(
    cod: str, horas: float, n_uc: float = 100, variacao: float | None = None
) -> RankingAlimentadorSchema:
    return RankingAlimentadorSchema(
        cod_alimentador=cod,
        dec=horas / n_uc,
        fec=horas / n_uc,
        horas_interrompidas=horas,
        n_interrupcoes=int(horas),
        n_uc_medio=n_uc,
        variacao_pct=None
        if variacao is None
        else VariacaoContinuidadeSchema(
            dec=variacao, fec=variacao, horas_interrompidas=None, n_interrupcoes=None
        ),
    )


def ranking(*linhas: RankingAlimentadorSchema, criterio: str = "dec") -> RankingContinuidadeSchema:
    ordenadas = sorted(linhas, key=lambda linha: -linha.dec)
    return RankingContinuidadeSchema(
        inicio="2025-01", fim="2025-12", criterio=criterio, n_meses=12, alimentadores=ordenadas
    )


TEN = [
    alimentador(f"AL-{i:02d}", horas) for i, horas in enumerate([60, 20, 4, 4, 4, 2, 2, 2, 1, 1])
]


def ids(metricas: dict) -> list[str]:
    return [candidata["id"] for candidata in metricas["candidatas"]]


def test_nothing_to_narrate_without_feeders() -> None:
    assert metricas_da_continuidade(filtro(), ranking()) is None


def test_concentration_is_the_share_of_the_worst_tenth() -> None:
    metricas = metricas_da_continuidade(filtro(), ranking(*TEN))

    assert metricas["leitura_principal"] == "concentracao"
    assert metricas["leitura_texto"] == (
        "O alimentador de pior DEC na empresa concentra 60,0% "
        "das horas de interrupção, entre 10 alimentadores."
    )


def test_worst_feeder_is_compared_with_the_index_of_the_whole_place() -> None:
    metricas = metricas_da_continuidade(filtro(municipio="Olinda"), ranking(*TEN))

    assert metricas["vezes_o_indice_do_lugar"] == 6.0
    assert "O AL-00 tem o pior DEC em Olinda: 6,0 vezes o DEC do conjunto." in [
        candidata["texto"] for candidata in metricas["candidatas"]
    ]


def test_few_feeders_have_no_concentration_reading() -> None:
    metricas = metricas_da_continuidade(filtro(), ranking(*TEN[:3]))

    assert ids(metricas) == ["pior_alimentador"]


def test_with_a_base_it_counts_where_the_index_rose_and_names_the_biggest_rise() -> None:
    linhas = [
        alimentador("AL-A", 50, variacao=10.0),
        alimentador("AL-B", 30, variacao=-5.0),
        alimentador("AL-C", 20, variacao=42.26),
        alimentador("AL-D", 10),
    ]

    metricas = metricas_da_continuidade(filtro(), ranking(*linhas))

    textos = {candidata["id"]: candidata["texto"] for candidata in metricas["candidatas"]}
    assert textos["alimentadores_em_alta"] == (
        "O DEC subiu em 2 dos 3 alimentadores com comparação contra o período base."
    )
    assert textos["maior_alta"] == (
        "Onde o DEC mais subiu foi no AL-C: cresceu 42,3% contra o período base."
    )


def test_fec_ranking_speaks_of_interruptions() -> None:
    metricas = metricas_da_continuidade(filtro(), ranking(*TEN, criterio="fec"))

    assert "das interrupções, entre 10 alimentadores." in metricas["leitura_texto"]


def test_every_candidate_passes_the_agents_number_check() -> None:
    linhas = [*TEN[:9], alimentador("AL-09", 1, variacao=7.77)]
    metricas = metricas_da_continuidade(filtro(), ranking(*linhas))

    for candidata in metricas["candidatas"]:
        assert unsupported_numbers(candidata["texto"], list(metricas.values())) == ()


def test_model_text_must_keep_the_numbers_of_the_chosen_reading() -> None:
    metricas = metricas_da_continuidade(filtro(), ranking(*TEN))

    assert texto_aceito(
        "O AL-00 tem o pior DEC na empresa, 6,0 vezes o DEC do conjunto.",
        metricas,
        ("pior_alimentador",),
    )
    assert not texto_aceito(
        "O AL-00 tem o pior DEC na empresa, 7,0 vezes o do conjunto.",
        metricas,
        ("pior_alimentador",),
    )


def test_insight_route_narrates_the_ranking_the_screen_shows(
    engine: Engine, client_with_writer
) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all(
            ContinuidadeAlimentadorMensal(
                cod_alimentador=cod,
                competencia="2025-01",
                dec=horas / 100,
                fec=horas / 100,
                n_uc=100,
                n_interrupcoes=int(horas),
                horas_interrompidas=horas,
            )
            for cod, horas in (("AL-A", 30.0), ("AL-B", 10.0))
        )
    client, redator = client_with_writer()
    params = {"inicio": "2025-01", "fim": "2025-01"}

    corpo = client.get("/continuidade/insight", params=params).json()

    assert corpo["origem"] == "ia"
    assert corpo["metricas"]["pior_alimentador"] == "AL-A"
    assert redator.chamadas == [("rede", corpo["metricas"])]


def test_insight_route_without_the_writer_is_the_rule_reading(
    engine: Engine, client: TestClient
) -> None:
    Base.metadata.create_all(engine)

    corpo = client.get("/continuidade/insight", params={"inicio": "2025-01", "fim": "2025-01"})

    assert corpo.json() == {"texto": None, "origem": None, "metricas": None}


def test_concentration_of_several_feeders_is_written_in_the_plural() -> None:
    linhas = [alimentador(f"AL-{i:02d}", 30 - i) for i in range(20)]

    metricas = metricas_da_continuidade(filtro(), ranking(*linhas))

    assert metricas["leitura_texto"].startswith(
        "Os 2 alimentadores de pior DEC na empresa concentram"
    )
