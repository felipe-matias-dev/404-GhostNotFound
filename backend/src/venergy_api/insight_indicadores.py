"""As métricas da Visão Geral que o redator de insights narra.

A tela mostra cada indicador com a sua variação, um ao lado do outro, e diz no título se a receita
cresceu com mais ou menos energia. O que ela não diz é o porquê: se a base cresceu e cada unidade
passou a consumir menos, se o ganho veio do preço e qual indicador de rede e atendimento mais
piorou. São as leituras candidatas; a IA escolhe entre elas (DEC-077).
"""

import re
from collections.abc import Sequence

from venergy_api.insights import com_candidatas, variou
from venergy_api.insights import texto_aceito as conferir
from venergy_api.schemas import ComparacaoIndicadoresSchema, IndicadoresComparacaoFiltroSchema

# Ordem de desempate da maior piora, e como o texto chama cada indicador. O sinal diz o que é
# piorar: DEC, FEC e chamados pioram subindo, a satisfação piora caindo.
_SERVICO = (
    ("dec", "o DEC", 1),
    ("fec", "o FEC", 1),
    ("n_chamados", "o número de chamados", 1),
    ("satisfacao_media", "a satisfação média", -1),
)
_TERMOS_PROIBIDOS = re.compile(
    r"\b(faturamento|simultaneamente|desempenho|segmentos?|efeitos?|mix|volume|recorte|kwh)\b"
    r"|·|_",
    re.IGNORECASE,
)


def _pct(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 1)


def _recorte(filtro: IndicadoresComparacaoFiltroSchema) -> str:
    partes = [filtro.municipio or "todos os municípios"]
    if filtro.bairro:
        partes.append(filtro.bairro)
    if filtro.classe:
        partes.append(f"classe {filtro.classe}")
    return ", ".join(partes)


def _leitura_da_receita(receita: float, energia: float) -> tuple[str, str]:
    if receita > 0 and energia < 0:
        return "receita_sem_consumo", (
            f"A receita {variou(receita)}, mas a energia faturada {variou(energia)}: "
            "o ganho veio do preço, não do consumo."
        )
    if receita > energia > 0:
        return "preco_acima_do_consumo", (
            f"A receita {variou(receita)} e a energia faturada {variou(energia)}: "
            "parte do ganho veio do preço."
        )
    return "receita_e_energia", (
        f"A receita {variou(receita)} e a energia faturada {variou(energia)}."
    )


def _leitura_do_servico(variacoes: dict[str, float]) -> tuple[str, str] | None:
    pioras = [
        (sentido * variacoes[chave], nome, variacoes[chave])
        for chave, nome, sentido in _SERVICO
        if chave in variacoes and sentido * variacoes[chave] > 0
    ]
    if not pioras:
        if not any(chave in variacoes for chave, _, _ in _SERVICO):
            return None
        return "sem_piora", "Nenhum indicador de rede e atendimento piorou."
    _, nome, pct = max(pioras, key=lambda piora: piora[0])
    return "maior_piora", (
        f"Na rede e no atendimento, o que mais piorou foi {nome}, que {variou(pct)}."
    )


def texto_aceito(texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()) -> bool:
    """Se o texto da IA diz as leituras que ela escolheu, sem nomes de chaves."""
    return conferir(texto, metricas, escolhidas, _TERMOS_PROIBIDOS)


def metricas_dos_indicadores(
    filtro: IndicadoresComparacaoFiltroSchema, comparacao: ComparacaoIndicadoresSchema
) -> dict[str, object] | None:
    """O JSON de métricas da comparação, ou None se nenhuma variação existe.

    A variação vem do backend, já nula com mês faltando ou base zero (DEC-054): sem ela, a
    leitura daquele indicador simplesmente não entra.
    """
    origem = comparacao.variacao_pct
    nomes = {
        "receita_faturada": "receita",
        "kwh_faturado": "energia",
        "n_uc_medio": "unidades",
        **{chave: chave for chave, _, _ in _SERVICO},
    }
    variacoes = {chave: pct for chave in nomes if (pct := _pct(getattr(origem, chave))) is not None}

    leituras: list[tuple[str, str]] = []
    unidades, energia = variacoes.get("n_uc_medio"), variacoes.get("kwh_faturado")
    # A pergunta do diretor no case: a base cresceu e a energia vendida caiu. A tela não mostra
    # o número de unidades, e é ele que diz que o consumo de cada uma diminuiu.
    if unidades is not None and energia is not None and unidades > 0 > energia:
        leituras.append(
            (
                "base_cresce_consumo_cai",
                f"O número de unidades consumidoras {variou(unidades)}, mas a energia faturada "
                f"{variou(energia)}: cada unidade passou a consumir menos.",
            )
        )
    if "receita_faturada" in variacoes and energia is not None:
        leituras.append(_leitura_da_receita(variacoes["receita_faturada"], energia))
    servico = _leitura_do_servico(variacoes)
    if servico:
        leituras.append(servico)
    if not leituras:
        return None

    metricas = com_candidatas(
        leituras,
        {
            "periodo_base": f"{filtro.base_inicio}/{filtro.base_fim}",
            "periodo_atual": f"{filtro.atual_inicio}/{filtro.atual_fim}",
            "recorte": _recorte(filtro),
            **{f"variacao_{nomes[chave]}_pct": pct for chave, pct in variacoes.items()},
        },
    )
    # A reserva diz a primeira leitura e a de rede e atendimento: a tela tem os dois blocos.
    reserva = [leituras[0], *([servico] if servico and servico != leituras[0] else [])]
    metricas["leitura_principal"] = "+".join(chave for chave, _ in reserva)
    metricas["leitura_texto"] = " ".join(texto for _, texto in reserva)
    return metricas
