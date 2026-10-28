from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import Insight

from venergy_api.agente import get_redator_insights
from venergy_api.database import Base
from venergy_api.models import ReceitaDecomposicao

BASE = "2024-01/2024-12"
ATUAL = "2025-01/2025-12"
FILTRO = {"periodo_base": BASE, "periodo_atual": ATUAL}
TEXTO = "A receita caiu no período."


class RedatorFalso:
    """Devolve os textos combinados, em ordem, sem chamar o Gemini, e guarda o que recebeu."""

    def __init__(self, *textos: str | None) -> None:
        self.textos = list(textos) or [TEXTO]
        self.chamadas: list[tuple[str, dict]] = []

    async def narrate(self, screen: str, metrics: dict) -> Insight | None:
        self.chamadas.append((screen, metrics))
        texto = self.textos[min(len(self.chamadas), len(self.textos)) - 1]
        return None if texto is None else Insight(text=texto, metrics_used=tuple(metrics))


def decomposition_line(
    municipio: str, bairro: str, classe: str, base: str, atual: str, volume: str
) -> ReceitaDecomposicao:
    return ReceitaDecomposicao(
        periodo_base=BASE,
        periodo_atual=ATUAL,
        municipio=municipio,
        bairro=bairro,
        classe=classe,
        possui_gd=False,
        receita_base=Decimal(base),
        receita_atual=Decimal(atual),
        efeito_preco=Decimal("0"),
        efeito_tarifa=Decimal("0"),
        efeito_bandeira=Decimal("0"),
        efeito_volume=Decimal(volume),
        efeito_mix=Decimal("0"),
    )


@pytest.fixture
def add_lines(engine: Engine) -> Callable[..., None]:
    Base.metadata.create_all(engine)

    def add(*lines: ReceitaDecomposicao) -> None:
        with Session(engine) as session, session.begin():
            session.add_all(lines)

    return add


@pytest.fixture
def bridge(add_lines: Callable[..., None]) -> None:
    add_lines(
        decomposition_line("Recife", "Boa Viagem", "B1", "100", "90", "-10"),
        decomposition_line("Recife", "Casa Forte", "B1", "50", "55", "5"),
        decomposition_line("Olinda", "Carmo", "B1", "80", "60", "-20"),
    )


@pytest.fixture
def client_with_writer(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> Callable[..., tuple[TestClient, RedatorFalso]]:
    def build(*textos: str | None) -> tuple[TestClient, RedatorFalso]:
        client = client_for(engine)
        redator = RedatorFalso(*textos)
        client.app.dependency_overrides[get_redator_insights] = lambda: redator
        return client, redator

    return build


@pytest.mark.usefixtures("bridge")
def test_returns_the_text_and_the_metrics_that_sustain_it(client_with_writer) -> None:
    client, redator = client_with_writer()

    response = client.get("/receita/insight", params=FILTRO)

    assert response.status_code == 200, response.text
    corpo = response.json()
    assert corpo["texto"] == TEXTO
    assert corpo["metricas"]["receita_base"] == 230.0
    assert corpo["metricas"]["variacao_receita"] == -25.0
    assert corpo["metricas"]["nivel_das_linhas"] == "municipio"
    assert redator.chamadas == [("receita", corpo["metricas"])]


@pytest.mark.usefixtures("bridge")
def test_metrics_match_the_bridge_the_screen_shows_for_the_same_filter(client_with_writer) -> None:
    client, _ = client_with_writer()

    linhas = client.get("/receita/decomposicao", params=FILTRO).json()
    metricas = client.get("/receita/insight", params=FILTRO).json()["metricas"]

    assert metricas["receita_base"] == sum(linha["receita_base"] for linha in linhas)
    assert metricas["efeito_volume"] == sum(linha["efeito_volume"] for linha in linhas)
    assert metricas["n_segmentos"] == len(linhas)
    assert metricas["maiores_quedas"][0]["segmento"] == linhas[0]["segmento"]


@pytest.mark.usefixtures("bridge")
def test_respects_the_cut_chosen_on_the_screen(client_with_writer) -> None:
    client, _ = client_with_writer()

    resposta = client.get("/receita/insight", params={**FILTRO, "municipio": "Recife"})
    metricas = resposta.json()["metricas"]

    assert metricas["recorte"] == "Recife"
    assert metricas["nivel_das_linhas"] == "bairro"
    assert metricas["receita_base"] == 150.0


@pytest.mark.usefixtures("bridge")
def test_text_is_null_when_the_writer_rejects_it(client_with_writer) -> None:
    client, _ = client_with_writer(None)

    response = client.get("/receita/insight", params=FILTRO)

    assert response.status_code == 200
    assert response.json()["texto"] is None
    assert response.json()["metricas"]["receita_base"] == 230.0


@pytest.mark.usefixtures("bridge")
def test_same_cut_is_narrated_once(client_with_writer) -> None:
    client, redator = client_with_writer()

    first = client.get("/receita/insight", params=FILTRO).json()
    second = client.get("/receita/insight", params=FILTRO).json()

    assert first == second
    assert len(redator.chamadas) == 1


@pytest.mark.usefixtures("bridge")
def test_a_reloaded_gold_is_narrated_again(
    client_with_writer, add_lines: Callable[..., None]
) -> None:
    # O cache é pelo conteúdo das métricas: se a Gold muda, a chave muda e o insight é refeito.
    client, redator = client_with_writer("Primeiro.", "Segundo.")

    first = client.get("/receita/insight", params=FILTRO).json()
    add_lines(decomposition_line("Jaboatão", "Piedade", "B1", "40", "20", "-20"))
    second = client.get("/receita/insight", params=FILTRO).json()

    assert (first["texto"], second["texto"]) == ("Primeiro.", "Segundo.")
    assert len(redator.chamadas) == 2


@pytest.mark.usefixtures("bridge")
def test_a_failed_narration_is_not_cached(client_with_writer) -> None:
    client, redator = client_with_writer(None, "Agora deu certo.")

    first = client.get("/receita/insight", params=FILTRO).json()
    second = client.get("/receita/insight", params=FILTRO).json()

    assert first["texto"] is None
    assert second["texto"] == "Agora deu certo."
    assert len(redator.chamadas) == 2


@pytest.mark.usefixtures("bridge")
def test_cut_without_rows_returns_nothing_and_does_not_call_the_model(client_with_writer) -> None:
    client, redator = client_with_writer()

    response = client.get("/receita/insight", params={**FILTRO, "municipio": "Gotham"})

    assert response.status_code == 200
    assert response.json() == {"texto": None, "metricas": None}
    assert redator.chamadas == []


@pytest.mark.usefixtures("bridge")
def test_answers_503_without_the_writer(client: TestClient) -> None:
    response = client.get("/receita/insight", params=FILTRO)

    assert response.status_code == 503
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in response.json()["detail"]


@pytest.mark.usefixtures("bridge")
def test_validates_the_filter_like_the_decomposition(client_with_writer) -> None:
    client, redator = client_with_writer()

    sem_par = client.get("/receita/insight")
    bairro_sem_municipio = client.get("/receita/insight", params={**FILTRO, "bairro": "Carmo"})

    assert sem_par.status_code == 422
    assert bairro_sem_municipio.status_code == 422
    assert redator.chamadas == []
