"""O agente de IA dentro da API: montado uma vez na subida e entregue às rotas por dependência."""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from pydantic import ValidationError
from venergy_agent.application.ports import TextToSqlAgent
from venergy_agent.bootstrap import build_agent
from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure.semantic_source import SemanticLayerError

logger = logging.getLogger(__name__)


async def montar_agente(
    carregar_config: Callable[[], AgentSettings] = AgentSettings,
) -> TextToSqlAgent | None:
    """Monta o agente, ou devolve None se a configuração ou a camada semântica forem inválidas."""
    # None, e não uma exceção: sem a chave do Gemini só o /ai fica de fora. Se a subida
    # falhasse, o /health e todas as telas cairiam junto por causa de um recurso opcional.
    try:
        settings = carregar_config()
    except ValidationError as error:
        # Só o campo e o motivo: include_input=False deixa de fora o valor digitado, que pode
        # ser uma chave de API, e nenhuma chave vai para o log.
        problemas = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'configuração'}: {e['msg']}"
            for e in error.errors(include_input=False, include_url=False)
        )
        logger.warning("Agente de IA desativado, o /ai responde 503. %s", problemas)
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


AgenteDep = Annotated[TextToSqlAgent, Depends(get_agente)]
