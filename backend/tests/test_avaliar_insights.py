from venergy_api.avaliar_insights import casos_por_leitura, casos_sinteticos, escolher_recortes
from venergy_api.schemas import DecomposicaoFiltroSchema


def test_synthetic_cases_reach_the_readings_the_base_may_not_have() -> None:
    casos = casos_sinteticos()

    assert casos["perfil_maior_fator"]["maior_fator"] == "perfil de consumo"
    assert "variacao_receita_pct" not in casos["sem_receita_base"]


def test_each_case_gets_the_first_matching_cut_or_none() -> None:
    filtro = DecomposicaoFiltroSchema(
        periodo_base="2024-01/2024-12", periodo_atual="2025-01/2025-12", municipio="Recife"
    )
    metricas = {
        "variacao_receita": -1.0,
        "efeito_volume": -1.0,
        "n_segmentos_em_queda": 1,
        "n_segmentos": 4,
        "leitura_principal": "quantidade_geral",
    }

    escolhidos = escolher_recortes([(filtro, metricas)])

    assert escolhidos["municipio"] == (filtro, metricas)
    assert escolhidos["quantidade_geral"] == (filtro, metricas)
    assert escolhidos["empresa"] is None
    assert escolhidos["bandeira_pesa"] is None


def test_each_reading_gets_the_first_cut_that_offers_it_as_a_candidate() -> None:
    def metricas(*ids: str) -> dict:
        return {"candidatas": [{"id": i, "texto": i} for i in ids]}

    recortes = [("Olinda", metricas("tendencia")), ("Recife", metricas("tendencia", "maior_alta"))]

    casos = casos_por_leitura(recortes, ("maior_alta", "tendencia", "sem_piora"))

    assert [(caso, recorte) for caso, recorte, _ in casos] == [
        ("maior_alta", "Recife"),
        ("tendencia", "Olinda"),
    ]
