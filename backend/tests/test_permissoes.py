"""Quem pode o quê: login em toda rota de dados e perfil nas duas que guardam algo sensível."""

from collections.abc import Callable
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence

from venergy_api.agente import get_agente
from venergy_api.auth import Perfil
from venergy_api.database import Base
from venergy_api.usuarios import criar_usuarios_demo

SENHA = "senha-de-demonstracao"

LOGIN_DO_PERFIL = {
    Perfil.DIRETORIA: "henrique",
    Perfil.ATENDIMENTO: "camila",
    Perfil.PERDAS: "rafael",
    Perfil.OPERACAO: "beatriz",
    Perfil.TI: "patricia",
}

# As únicas rotas que respondem sem login: a saúde, para o orquestrador, e a porta de entrada.
ROTAS_PUBLICAS = {"/health", "/auth/login", "/auth/logout"}

NAO_AUTORIZADO = (401, 403)


@pytest.fixture
def api(engine: Engine, client_for: Callable[..., TestClient]) -> TestClient:
    # Tabelas vazias bastam: o que se testa é a barreira, não o conteúdo das respostas.
    Base.metadata.create_all(engine)
    criar_usuarios_demo(engine, SENHA)
    return client_for(engine, sem_login=True)


def _entrar_como(api: TestClient, perfil: Perfil) -> TestClient:
    resposta = api.post("/auth/login", json={"login": LOGIN_DO_PERFIL[perfil], "senha": SENHA})
    assert resposta.status_code == 200
    return api


def _rotas_de_dados(api: TestClient) -> list[tuple[str, str]]:
    # Pelo OpenAPI, e não por app.routes: o contrato é o que o portal enxerga, e vale para
    # qualquer router incluído.
    caminhos = api.app.openapi()["paths"]
    return [
        (metodo.upper(), caminho)
        for caminho, operacoes in caminhos.items()
        if caminho not in ROTAS_PUBLICAS
        for metodo in operacoes
    ]


def test_toda_rota_fora_da_lista_publica_exige_login(api: TestClient):
    rotas = _rotas_de_dados(api)
    assert len(rotas) > 15

    sem_login = [
        (metodo, caminho)
        for metodo, caminho in rotas
        if api.request(metodo, caminho.replace("{", "").replace("}", "")).status_code != 401
    ]

    # Lista as rotas que escaparam: um router novo sem login aparece aqui pelo nome.
    assert sem_login == []


def test_a_saude_continua_publica(api: TestClient):
    assert api.get("/health").status_code == 200


@pytest.mark.parametrize("perfil", [p for p in Perfil if p is not Perfil.PERDAS])
def test_so_perdas_gera_e_atualiza_ordens_de_inspecao(api: TestClient, perfil: Perfil):
    _entrar_como(api, perfil)

    gerar = api.post("/ordens-inspecao", json={"cod_ucs": ["UC0001"]})
    atualizar = api.patch("/ordens-inspecao/1", json={"status": "EM_CAMPO"})

    planilha = api.post(
        "/ordens-inspecao/planilha", files={"arquivo": ("campo.xlsx", b"x", "application/xlsx")}
    )

    assert gerar.status_code == 403
    assert atualizar.status_code == 403
    assert planilha.status_code == 403


def test_perdas_chega_nas_ordens_de_inspecao(api: TestClient):
    _entrar_como(api, Perfil.PERDAS)

    # Sem a Gold carregada a UC não existe (404) e a ordem também (404): o que importa é
    # que a barreira de perfil deixou passar.
    assert api.post("/ordens-inspecao", json={"cod_ucs": ["UC0001"]}).status_code == 404
    assert api.patch("/ordens-inspecao/1", json={"status": "EM_CAMPO"}).status_code == 404


@pytest.mark.parametrize("perfil", [p for p in Perfil if p is not Perfil.TI])
def test_so_ti_le_a_auditoria_do_agente(api: TestClient, perfil: Perfil):
    _entrar_como(api, perfil)

    assert api.get("/ai/audit/1").status_code == 403


def test_ti_chega_na_auditoria_do_agente(api: TestClient):
    _entrar_como(api, Perfil.TI)

    assert api.get("/ai/audit/1").status_code == 404


class AgenteDeTeste:
    """Responde sem chamar o modelo: o que se testa aqui é a barreira de acesso."""

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        return AgentAnswer(
            answer="Não sei responder com os dados disponíveis.",
            status=AnswerStatus.UNKNOWN,
            sql=None,
            rows=(),
            row_count=0,
            truncated=False,
            confidence=Confidence.UNKNOWN,
            sources=(),
            assumptions=(),
            clarification=None,
            refused_reason="Sem dados para responder.",
            request_id="req-teste",
            model="teste",
            prompt_version="v2",
            latency_ms=1,
        )


@pytest.mark.parametrize("perfil", list(Perfil))
def test_todo_perfil_le_os_dados_e_pergunta_ao_agente(api: TestClient, perfil: Perfil):
    _entrar_como(api, perfil)
    api.app.dependency_overrides[get_agente] = lambda: AgenteDeTeste()

    leitura = api.get("/indicadores/janelas")
    pergunta = api.post("/ai/ask", json={"question": "Qual a receita?", "session_id": str(uuid4())})

    assert leitura.status_code not in NAO_AUTORIZADO
    assert pergunta.status_code == 200
