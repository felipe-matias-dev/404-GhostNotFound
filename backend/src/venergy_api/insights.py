"""Insights de IA das telas: o cache, a conferência do texto e a narração com reserva da regra.

Em toda tela, o backend calcula as leituras candidatas do recorte, cada uma com os seus números,
e a IA escolhe as que mais importam e escreve o insight (DEC-077). O texto só vale se disser o
que as leituras escolhidas dizem; senão, a tela mostra `leitura_texto`, a reserva da regra.
"""

import json
import logging
import re
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, Request
from venergy_agent.application.ports import InsightWriter
from venergy_agent.domain.answer import Insight

from venergy_api.schemas import InsightSchema

# O logger do agente: o mesmo handler mostra o motivo do descarte do agente e o da conferência.
logger = logging.getLogger("venergy_agent.insight")

CAPACIDADE_PADRAO = 256
# Uma ou duas leituras: mais que isso vira a lista que a tela já mostra.
MAX_ESCOLHIDAS = 2
# Folga para o modelo reescrever a leitura, sem espaço para ele acrescentar outra conclusão: ao
# menos 40 caracteres, e 30% do tamanho quando ele junta duas leituras numa frase.
FOLGA_DO_TEXTO = 40
FOLGA_PROPORCIONAL = 0.3
# Sentido de cada afirmação. "Ganho" é alta: "o ganho de receita foi de 14,3%".
_SENTIDO = re.compile(
    r"\b(?:(?P<alta>cresc\w*|sub\w*|alta|aument\w*|ganh\w*)"
    r"|(?P<queda>recu\w*|ca[ií]\w*|qued\w*|perd\w*|redu\w*|derrub\w*))\b",
    re.IGNORECASE,
)
_NUMERO = re.compile(r"\d+(?:\.\d{3})*(?:,\d+)?")
# Variações: um percentual ou um valor em R$. São os números que sobem ou caem.
_VARIACAO = re.compile(r"(?P<reais>R\$\s*)?(?P<numero>\d+(?:\.\d{3})*(?:,\d+)?)(?P<pct>\s*%)?")
_FIM_DA_FRASE = re.compile(r"[.:;!?](?=\s|$)")


def numero_br(valor: object, casas: int = 1) -> str:
    return f"{valor:,.{casas}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def variou(pct: float) -> str:
    if pct == 0:
        return "ficou estável"
    return f"{'cresceu' if pct > 0 else 'recuou'} {numero_br(abs(pct))}%"


def _numeros(texto: str) -> set[Decimal]:
    return {_decimal(numero) for numero in _NUMERO.findall(texto)}


def _decimal(numero: str) -> Decimal:
    return Decimal(numero.replace(".", "").replace(",", "."))


def _sentidos(texto: str) -> set[tuple[Decimal, str]]:
    """Cada variação com o sentido da última alta ou queda dita antes dela, na mesma frase."""
    pares: set[tuple[Decimal, str]] = set()
    for frase in _FIM_DA_FRASE.split(texto):
        for variacao in _VARIACAO.finditer(frase):
            if not (variacao["reais"] or variacao["pct"]):
                continue
            antes = list(_SENTIDO.finditer(frase, 0, variacao.start()))
            if antes:
                pares.add((_decimal(variacao["numero"]), str(antes[-1].lastgroup)))
    return pares


def com_candidatas(
    candidatas: list[tuple[str, str]], metricas: dict[str, object]
) -> dict[str, object]:
    """As métricas com as leituras candidatas e a reserva: a primeira, na ordem da regra."""
    return {
        **metricas,
        "candidatas": [{"id": chave, "texto": texto} for chave, texto in candidatas],
        "leitura_principal": candidatas[0][0],
        "leitura_texto": candidatas[0][1],
    }


def leitura_escolhida(metricas: dict[str, object], escolhidas: Sequence[str]) -> str | None:
    """O texto das leituras que a IA escolheu, na ordem dela, ou None se a escolha não vale.

    Sem escolha (prompt anterior ao v4), a comparação é com a reserva, como antes.
    """
    if not escolhidas:
        return str(metricas["leitura_texto"])
    textos = {candidata["id"]: candidata["texto"] for candidata in metricas["candidatas"]}
    repetida = len(set(escolhidas)) < len(escolhidas)
    if len(escolhidas) > MAX_ESCOLHIDAS or repetida or not set(escolhidas) <= textos.keys():
        return None
    return " ".join(textos[chave] for chave in escolhidas)


def motivo_da_recusa(
    texto: str,
    metricas: dict[str, object],
    escolhidas: Sequence[str],
    proibidos: re.Pattern[str],
) -> str | None:
    """Por que o texto da IA não diz o que as leituras escolhidas dizem, ou None se diz.

    O motivo é escrito para a IA: volta para ela na nova tentativa, sem o texto recusado.
    Cada variação que a leitura diz que subiu ou caiu precisa subir ou cair no texto também,
    em qualquer ordem: juntar duas leituras que repetem um número continua valendo, e trocar
    uma alta por uma queda nunca vale.
    """
    leitura = leitura_escolhida(metricas, escolhidas)
    if leitura is None:
        return f"Escolha uma ou até {MAX_ESCOLHIDAS} leituras diferentes, pelos id de candidatas."
    if termo := proibidos.search(texto):
        return f'Não use "{termo.group(0)}".'
    limite = int(len(leitura) + max(FOLGA_DO_TEXTO, len(leitura) * FOLGA_PROPORCIONAL))
    if len(texto) > limite:
        return (
            f"Escreva no máximo {limite} caracteres e diga só o que as leituras escolhidas "
            "dizem, sem outra conclusão."
        )
    if _numeros(texto) != _numeros(leitura):
        esperados = ", ".join(dict.fromkeys(_NUMERO.findall(leitura)))
        return f"Use estes números, escritos exatamente assim, e nenhum outro: {esperados}."
    if not _sentidos(leitura) <= _sentidos(texto):
        return "Mantenha o sentido de cada número: o que sobe nas leituras sobe no texto."
    return None


def texto_aceito(
    texto: str,
    metricas: dict[str, object],
    escolhidas: Sequence[str],
    proibidos: re.Pattern[str],
) -> bool:
    """Se a escolha da IA vale e o texto diz o que as leituras escolhidas dizem."""
    return motivo_da_recusa(texto, metricas, escolhidas, proibidos) is None


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


async def redigir(
    tela: str,
    metricas: dict[str, object],
    redator: InsightWriter,
    motivo: Callable[[str, tuple[str, ...]], str | None],
) -> Insight | None:
    """O texto da IA que passa na conferência, com uma nova tentativa se o primeiro não passar.

    A nova tentativa leva o motivo da recusa, e não o texto recusado: com o mesmo pedido, a
    temperatura 0 repetiria o texto (DEC-066). Erro do provedor não ganha nova tentativa aqui:
    a cadeia de modelos reserva já tentou os outros.
    """
    insight = await redator.narrate(tela, metricas)
    if insight is None:
        return None
    recusa = motivo(insight.text, insight.readings)
    if recusa is None:
        return insight
    _log(tela, "recusado", recusa)
    insight = await redator.narrate(tela, metricas, feedback=recusa)
    if insight is None:
        return None
    recusa = motivo(insight.text, insight.readings)
    if recusa is None:
        _log(tela, "aceito_na_nova_tentativa")
        return insight
    _log(tela, "recusado_de_novo", recusa)
    return None


def _log(tela: str, status: str, motivo: str | None = None) -> None:
    linha = {"step": "insight_backend", "screen": tela, "status": status}
    if motivo:
        linha["motivo"] = motivo
    logger.info(json.dumps(linha, ensure_ascii=False))


async def narrar(
    tela: str,
    metricas: dict[str, object],
    redator: InsightWriter | None,
    cache: CacheInsights,
    motivo: Callable[[str, tuple[str, ...]], str | None],
) -> InsightSchema:
    """O texto da IA, se a conferência o aceita (`motivo` None), ou a reserva da regra."""
    chave = chave_do_cache(tela, metricas)
    texto = cache.obter(chave)
    if texto is None:
        insight = await redigir(tela, metricas, redator, motivo) if redator else None
        if insight is None:
            # IA desligada, provedor fora ou texto recusado duas vezes: a tela mostra a leitura
            # da regra. Ela não entra no cache, e o próximo pedido tenta o modelo de novo.
            leitura = str(metricas["leitura_texto"])
            return InsightSchema(texto=leitura, origem="regra", metricas=metricas)
        texto = insight.text
        cache.guardar(chave, texto)
    return InsightSchema(texto=texto, origem="ia", metricas=metricas)
