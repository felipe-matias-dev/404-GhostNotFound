"""O agente de IA dentro da API: montado uma vez na subida e entregue às rotas por dependência."""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from pydantic import ValidationError
from venergy_agent.application.ports import InsightWriter, TextToSqlAgent
from venergy_agent.bootstrap import build_agent, build_insight_writer
from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure.semantic_source import SemanticLayerError

logger = logging.getLogger(__name__)


def _carregar_configuracao(
    carregar_config: Callable[[], AgentSettings], desativado: str
) -> AgentSettings | None:
    # None, e não uma exceção: sem a chave do Gemini só a IA fica de fora. Se a subida
    # falhasse, o /health e todas as telas cairiam junto por causa de um recurso opcional.
    try:
        return carregar_config()
    except ValidationError as error:
        # Só o campo e o motivo: include_input=False deixa de fora o valor digitado, que pode
        # ser uma chave de API, e nenhuma chave vai para o log.
        problemas = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'configuração'}: {e['msg']}"
            for e in error.errors(include_input=False, include_url=False)
        )
        logger.warning("%s. %s", desativado, problemas)
        return None


async def montar_agente(
    carregar_config: Callable[[], AgentSettings] = AgentSettings,
) -> TextToSqlAgent | None:
    """Monta o agente, ou devolve None se a configuração ou a camada semântica forem inválidas."""
    settings = _carregar_configuracao(
        carregar_config, "Agente de IA desativado, o /ai responde 503"
    )
    if settings is None:
        return None
    try:
        return await build_agent(settings)
    except SemanticLayerError as error:
        # Uma mudança no contrato da Gold pode deixar a camada semântica do agente inválida
        # antes de o GenAI regerá-la. É problema do /ai, e não pode derrubar o resto da API.
        # A lista traz só nomes de view e coluna, nada de segredo.
        logger.warning(
            "Agente de IA desativado, o /ai responde 503. Camada semântica inválida:\n%s", error
        )
        return None


async def montar_redator_insights(
    carregar_config: Callable[[], AgentSettings] = AgentSettings,
) -> InsightWriter | None:
    """Monta o redator de insights, ou devolve None se a configuração ou o prompt não servirem."""
    settings = _carregar_configuracao(
        carregar_config, "Insights de IA desativados, as rotas de insight respondem 503"
    )
    if settings is None:
        return None
    try:
        return build_insight_writer(settings)
    except FileNotFoundError:
        # Uma versão de prompt que não existe (VENERGY_AGENT_INSIGHT_PROMPT_VERSION errada)
        # desliga só os insights. O caminho do arquivo não traz segredo, mas a mensagem do
        # sistema operacional não ajuda quem lê: o log diz a versão pedida.
        logger.warning(
            "Insights de IA desativados, as rotas de insight respondem 503. "
            "Prompt de insight %r não encontrado.",
            settings.insight_prompt_version,
        )
        return None


def get_agente(request: Request) -> TextToSqlAgent:
    # getattr: o estado só existe depois do lifespan, e um app montado sem ele (os testes)
    # tem o mesmo efeito de uma configuração inválida.
    agente = getattr(request.app.state, "agente", None)
    if agente is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "O agente de IA está indisponível: configure VENERGY_AGENT_GOOGLE_API_KEY "
                "e reinicie a API."
            ),
        )
    return agente


def get_redator_insights(request: Request) -> InsightWriter:
    redator = getattr(request.app.state, "redator_insights", None)
    if redator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Os insights de IA estão indisponíveis: configure VENERGY_AGENT_GOOGLE_API_KEY "
                "e reinicie a API."
            ),
        )
    return redator


AgenteDep = Annotated[TextToSqlAgent, Depends(get_agente)]
RedatorInsightsDep = Annotated[InsightWriter, Depends(get_redator_insights)]
