"""Regras de negócio das ordens de inspeção (OIs), separadas do banco e da API.

Ficam aqui, e não no router, para que a máquina de estados seja testada sem banco e
consultada de um lugar só por qualquer endpoint que mude o status de uma OI.
"""

from enum import StrEnum


class StatusOrdem(StrEnum):
    GERADA = "GERADA"
    EM_CAMPO = "EM_CAMPO"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"


class ResultadoOrdem(StrEnum):
    IRREGULAR_CONFIRMADA = "IRREGULAR_CONFIRMADA"
    REGULAR = "REGULAR"
    # A equipe foi, mas não conseguiu vistoriar (imóvel fechado, acesso negado).
    NAO_REALIZADA = "NAO_REALIZADA"


# Para onde cada status pode ir. CONCLUIDA e CANCELADA são finais: reabrir uma OI
# apagaria o registro do que aconteceu em campo; o certo é gerar uma nova. EM_CAMPO ainda
# não tem resultado, então pode voltar para GERADA (envio por engano): a volta fica no
# histórico e a OI segue ativa, ocupando a UC.
TRANSICOES: dict[StatusOrdem, frozenset[StatusOrdem]] = {
    StatusOrdem.GERADA: frozenset({StatusOrdem.EM_CAMPO, StatusOrdem.CANCELADA}),
    StatusOrdem.EM_CAMPO: frozenset(
        {StatusOrdem.GERADA, StatusOrdem.CONCLUIDA, StatusOrdem.CANCELADA}
    ),
    StatusOrdem.CONCLUIDA: frozenset(),
    StatusOrdem.CANCELADA: frozenset(),
}

# Status em que a OI ainda ocupa a UC: enquanto houver uma assim, não se gera outra.
STATUS_ATIVOS: frozenset[StatusOrdem] = frozenset({StatusOrdem.GERADA, StatusOrdem.EM_CAMPO})


class TransicaoInvalidaError(Exception):
    """A OI não pode ir do status atual para o pedido."""

    def __init__(self, atual: StatusOrdem, novo: StatusOrdem) -> None:
        super().__init__(f"Não é possível mudar uma ordem de {atual} para {novo}")
        self.atual = atual
        self.novo = novo


def validar_transicao(atual: StatusOrdem, novo: StatusOrdem) -> None:
    """Levanta TransicaoInvalidaError se a mudança de status não for permitida."""
    if novo not in TRANSICOES[atual]:
        raise TransicaoInvalidaError(atual, novo)
