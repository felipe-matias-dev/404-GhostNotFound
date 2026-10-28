"""Cache dos insights de IA: o mesmo recorte não paga o modelo duas vezes."""

import json
from collections import OrderedDict
from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends, Request

CAPACIDADE_PADRAO = 256


def chave_do_cache(tela: str, metricas: Mapping[str, object]) -> str:
    """A chave é o conteúdo das métricas, e não os filtros que levaram a elas.

    Se a Gold for recarregada, as métricas mudam e a chave muda junto: o insight nunca fica
    velho, sem prazo de validade para combinar. A consulta SQL é barata; o caro é o modelo.
    """
    # sort_keys: a mesma métrica em outra ordem tem de dar a mesma chave.
    return f"{tela}:{json.dumps(metricas, sort_keys=True, ensure_ascii=False, default=str)}"


class CacheInsights:
    """Em memória e limitado: perde-se ao reiniciar a API, e o insight só é refeito."""

    def __init__(self, capacidade: int = CAPACIDADE_PADRAO) -> None:
        self._capacidade = capacidade
        self._textos: OrderedDict[str, str] = OrderedDict()

    def obter(self, chave: str) -> str | None:
        texto = self._textos.get(chave)
        if texto is not None:
            self._textos.move_to_end(chave)
        return texto

    def guardar(self, chave: str, texto: str) -> None:
        # Só texto que passou na checagem de números entra aqui. Guardar a falha esconderia o
        # insight depois de um erro passageiro do provedor.
        self._textos[chave] = texto
        self._textos.move_to_end(chave)
        while len(self._textos) > self._capacidade:
            self._textos.popitem(last=False)


def get_cache_insights(request: Request) -> CacheInsights:
    return request.app.state.cache_insights


CacheInsightsDep = Annotated[CacheInsights, Depends(get_cache_insights)]
