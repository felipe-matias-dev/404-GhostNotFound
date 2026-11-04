"""Rodada fixa dos insights das quatro telas: `make eval-insights` (DEC-066, DEC-077).

Para cada tela, escolhe na Gold carregada um recorte para cada caso que as leituras distinguem
e chama o modelo em todos; na Receita, soma dois casos sintéticos que a base pode não ter. Cada
texto passa pela mesma conferência da rota. `make eval-insights TELAS=rede,receita` roda só
essas telas. O relatório vai para `ai-agent/eval/runs_gold/`, fora do Git, porque traz números
da Gold. Termina com erro se algum caso não sair com texto do modelo.
"""

import asyncio
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from venergy_agent.bootstrap import build_insight_writer
from venergy_agent.config import AgentSettings

from venergy_api import insight_continuidade, insight_indicadores, insight_receita, insight_uc
from venergy_api.agente import configurar_logs_do_agente
from venergy_api.config import get_settings
from venergy_api.database import create_db_engine
from venergy_api.insight_receita import filtro_acima, metricas_da_receita
from venergy_api.models import DimUc, FatoFaturamentoMensal, ReceitaDecomposicao
from venergy_api.routers.continuidade import get_ranking_alimentadores
from venergy_api.routers.indicadores import get_comparacao
from venergy_api.routers.receita import consultar_decomposicao
from venergy_api.routers.unidades import consultar_metricas_da_uc
from venergy_api.schemas import (
    DecomposicaoFiltroSchema,
    DecomposicaoLinhaSchema,
    IndicadoresComparacaoFiltroSchema,
    RankingFiltroSchema,
)

Metricas = dict[str, object]
Candidato = tuple[DecomposicaoFiltroSchema, Metricas]
# Um caso de uma tela: o nome, o recorte em palavras e as métricas que vão ao modelo.
Caso = tuple[str, str, Metricas]
Aceito = Callable[[str, Metricas, Sequence[str]], bool]

ACEITOS: dict[str, Aceito] = {
    "receita": insight_receita.texto_aceito,
    "visao_geral": insight_indicadores.texto_aceito,
    "rede": insight_continuidade.texto_aceito,
    "unidade_consumidora": insight_uc.texto_aceito,
}
# UCs lidas para achar um caso de cada leitura: o bastante para a base real, sem ler todas.
AMOSTRA_DE_UCS = 400

RELATORIOS = Path(__file__).parents[3] / "ai-agent" / "eval" / "runs_gold"

CASOS: dict[str, Callable[[DecomposicaoFiltroSchema, Metricas], bool]] = {
    "empresa": lambda f, m: not (f.municipio or f.classe),
    "classe": lambda f, m: bool(f.classe) and not f.municipio,
    "municipio": lambda f, m: bool(f.municipio) and not f.bairro,
    "bairro": lambda f, m: bool(f.bairro),
    "receita_em_queda": lambda f, m: m["variacao_receita"] < 0,
    "quantidade_em_alta": lambda f, m: m["efeito_volume"] > 0 and m["variacao_receita"] > 0,
    "sem_quedas": lambda f, m: m["n_segmentos_em_queda"] == 0 and bool(f.municipio),
    "um_segmento": lambda f, m: m["n_segmentos"] == 1,
    **{
        leitura: lambda f, m, leitura=leitura: m["leitura_principal"] == leitura
        for leitura in (
            "unico_em_queda",
            "alta_depende_do_preco",
            "bandeira_pesa",
            "quantidade_geral",
            "quedas_concentradas",
            "comparacao_acima",
        )
    },
}


def _linha_sintetica(base: str, volume: str, mix: str) -> DecomposicaoLinhaSchema:
    variacao = Decimal(volume) + Decimal(mix)
    return DecomposicaoLinhaSchema(
        nivel="municipio",
        segmento="Sintético",
        periodo_base="2024-01/2024-12",
        periodo_atual="2025-01/2025-12",
        receita_base=Decimal(base),
        receita_atual=Decimal(base) + variacao,
        variacao_receita=variacao,
        efeito_preco=Decimal(0),
        efeito_tarifa=Decimal(0),
        efeito_bandeira=Decimal(0),
        efeito_volume=Decimal(volume),
        efeito_mix=Decimal(mix),
    )


def casos_sinteticos() -> dict[str, Metricas]:
    """O que a Gold real pode não ter: com uma só linha, sem nada acima para comparar."""
    filtro = DecomposicaoFiltroSchema(
        periodo_base="2024-01/2024-12", periodo_atual="2025-01/2025-12"
    )
    linhas = {"perfil_maior_fator": ("0", "1", "9"), "sem_receita_base": ("0", "5", "0")}
    return {
        caso: metricas_da_receita(filtro, [_linha_sintetica(*valores)])
        for caso, valores in linhas.items()
    }


def escolher_recortes(candidatos: Sequence[Candidato]) -> dict[str, Candidato | None]:
    """O primeiro candidato de cada caso, ou None se a base não tem o caso."""
    return {
        caso: next(((f, m) for f, m in candidatos if regra(f, m)), None)
        for caso, regra in CASOS.items()
    }


def ids_das_candidatas(metricas: Metricas) -> set[str]:
    return {str(candidata["id"]) for candidata in metricas["candidatas"]}


def casos_por_leitura(
    recortes: Sequence[tuple[str, Metricas]], leituras: Sequence[str]
) -> list[Caso]:
    """Para cada leitura, o primeiro recorte que a tem entre as candidatas, se houver.

    Com as candidatas (DEC-077), o caso garante que a IA tenha a leitura para escolher.
    """
    casos = []
    for leitura in leituras:
        achado = next((r for r in recortes if leitura in ids_das_candidatas(r[1])), None)
        if achado:
            casos.append((leitura, *achado))
    return casos


def _pares(par: tuple[str, str]) -> tuple[list[str], list[str]]:
    return par[0].split("/"), par[1].split("/")


def _municipios(session: Session) -> list[str]:
    return sorted(session.scalars(select(DimUc.municipio).distinct()).all())


def casos_da_visao_geral(session: Session, par: tuple[str, str]) -> list[Caso]:
    (base_inicio, base_fim), (atual_inicio, atual_fim) = _pares(par)
    recortes: list[dict[str, str]] = [{}, {"classe": "B1"}, {"classe": "B3"}]
    recortes += [{"municipio": municipio} for municipio in _municipios(session)]
    lidos = []
    for recorte in recortes:
        filtro = IndicadoresComparacaoFiltroSchema(
            base_inicio=base_inicio,
            base_fim=base_fim,
            atual_inicio=atual_inicio,
            atual_fim=atual_fim,
            **recorte,
        )
        metricas = insight_indicadores.metricas_dos_indicadores(
            filtro, get_comparacao(filtro, session)
        )
        if metricas:
            lidos.append((str(metricas["recorte"]), metricas))
    leituras = (
        "base_cresce_consumo_cai",
        "receita_sem_consumo",
        "preco_acima_do_consumo",
        "receita_e_energia",
        "maior_piora",
        "sem_piora",
    )
    return [("empresa", *lidos[0]), *casos_por_leitura(lidos[1:], leituras)] if lidos else []


def casos_da_rede(session: Session, par: tuple[str, str]) -> list[Caso]:
    (base_inicio, base_fim), (inicio, fim) = _pares(par)
    base = {"base_inicio": base_inicio, "base_fim": base_fim}
    recortes: list[tuple[str, dict[str, str]]] = [
        ("empresa_dec", {"criterio": "dec", **base}),
        ("empresa_fec", {"criterio": "fec", **base}),
        ("empresa_sem_base", {"criterio": "dec"}),
    ]
    recortes += [
        (municipio, {"municipio": municipio, **base}) for municipio in _municipios(session)
    ]
    lidos = []
    for nome, recorte in recortes:
        filtro = RankingFiltroSchema(inicio=inicio, fim=fim, **recorte)
        metricas = insight_continuidade.metricas_da_continuidade(
            filtro, get_ranking_alimentadores(filtro, session)
        )
        if metricas:
            lidos.append((nome, metricas))
    fixos = [(nome, nome, metricas) for nome, metricas in lidos[:3]]
    leituras = ("concentracao", "pior_alimentador", "alimentadores_em_alta", "maior_alta")
    return fixos + casos_por_leitura(lidos[3:], leituras)


def casos_da_uc(session: Session) -> list[Caso]:
    """Uma UC de cada leitura, entre as que faturaram no último mês da Gold."""
    fato = FatoFaturamentoMensal
    referencia = session.scalar(select(func.max(fato.competencia)))
    ucs = session.scalars(
        select(fato.cod_uc)
        .where(fato.competencia == referencia)
        .order_by(fato.cod_uc)
        .limit(AMOSTRA_DE_UCS)
    ).all()
    lidos = [(cod_uc, m) for cod_uc in ucs if (m := consultar_metricas_da_uc(session, cod_uc))]
    leituras = (
        "conta_sem_consumo",
        "conta_com_consumo",
        "mes_fora_do_padrao",
        "tendencia",
        "consumo_do_mes_e_do_ano",
        "consumo_do_ano",
        "leitura_estimada",
    )
    # O relatório não leva o código da UC: só o caso e as métricas, como o modelo recebe.
    return [(caso, "uma UC", metricas) for caso, _, metricas in casos_por_leitura(lidos, leituras)]


def casos_da_receita(session: Session, par: tuple[str, str]) -> tuple[list[Caso], list[str]]:
    escolhidos = escolher_recortes(_candidatos(session, *par))
    casos = [
        (caso, str(candidato[1]["recorte"]), candidato[1])
        for caso, candidato in escolhidos.items()
        if candidato is not None
    ]
    casos += [(caso, "sintético", m) for caso, m in casos_sinteticos().items()]
    return casos, [caso for caso, candidato in escolhidos.items() if candidato is None]


def _candidatos(session: Session, base: str, atual: str) -> list[Candidato]:
    decomposicao = ReceitaDecomposicao
    pares = session.execute(
        select(decomposicao.municipio, decomposicao.bairro)
        .where(decomposicao.periodo_base == base, decomposicao.periodo_atual == atual)
        .distinct()
    ).all()
    classes = session.scalars(select(decomposicao.classe).distinct()).all()
    recortes: list[dict[str, str]] = [{}]
    recortes += [{"classe": classe} for classe in sorted(classes)]
    recortes += [{"municipio": municipio} for municipio in sorted({par[0] for par in pares})]
    recortes += [{"municipio": par[0], "bairro": par[1]} for par in pares]

    candidatos = []
    for recorte in recortes:
        filtro = DecomposicaoFiltroSchema(periodo_base=base, periodo_atual=atual, **recorte)
        acima = filtro_acima(filtro)
        metricas = metricas_da_receita(
            filtro,
            consultar_decomposicao(filtro, session),
            consultar_decomposicao(acima, session) if acima else [],
        )
        if metricas:
            candidatos.append((filtro, metricas))
    return candidatos


async def _narrar(redator, tela: str, caso: Caso) -> dict[str, object]:
    nome, recorte, metricas = caso
    insight = await redator.narrate(tela, metricas)
    aceito = insight is not None and ACEITOS[tela](insight.text, metricas, insight.readings)
    return {
        "tela": tela,
        "caso": nome,
        "recorte": recorte,
        "candidatas": sorted(ids_das_candidatas(metricas)),
        "escolhidas": list(insight.readings) if insight else [],
        "origem": "ia" if aceito else "regra",
        "regra": metricas["leitura_texto"],
        "texto": insight.text if insight else None,
    }


async def rodar(telas: Sequence[str]) -> int:
    # O motivo de cada texto descartado pelo agente (erro do provedor, número sem suporte) é log.
    configurar_logs_do_agente()
    engine = create_db_engine(get_settings().database_url)
    redator = build_insight_writer(AgentSettings())
    casos: dict[str, list[Caso]] = {}
    sem_recorte: list[str] = []
    with Session(engine) as session:
        par = session.execute(
            select(ReceitaDecomposicao.periodo_base, ReceitaDecomposicao.periodo_atual)
            .distinct()
            .order_by(ReceitaDecomposicao.periodo_base, ReceitaDecomposicao.periodo_atual.desc())
        ).first()
        if par is None:
            print("A Gold não tem decomposição de receita.")
            return 1
        par = (par[0], par[1])
        if "receita" in telas:
            casos["receita"], sem_recorte = casos_da_receita(session, par)
        if "visao_geral" in telas:
            casos["visao_geral"] = casos_da_visao_geral(session, par)
        if "rede" in telas:
            casos["rede"] = casos_da_rede(session, par)
        if "unidade_consumidora" in telas:
            casos["unidade_consumidora"] = casos_da_uc(session)

    resultados = [
        await _narrar(redator, tela, caso) for tela, da_tela in casos.items() for caso in da_tela
    ]
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    instante = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    relatorio = RELATORIOS / f"insights-{instante}.json"
    conteudo = {"par": par, "resultados": resultados, "sem_recorte_receita": sem_recorte}
    relatorio.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")

    for item in resultados:
        escolhidas = ", ".join(item["escolhidas"]) or "nenhuma"
        print(f"[{item['origem']}] {item['tela']} · {item['caso']} · {item['recorte']}")
        print(f"  escolhidas: {escolhidas}\n  {item['texto']}")
    print()
    for tela in casos:
        da_tela = [item for item in resultados if item["tela"] == tela]
        aceitos = sum(1 for item in da_tela if item["origem"] == "ia")
        print(f"{tela}: {aceitos} de {len(da_tela)} com texto do modelo.")
    print(f"Sem recorte na base (Receita): {', '.join(sem_recorte) or 'nenhum'}.")
    print(f"Relatório: {relatorio}")
    return 1 if any(item["origem"] != "ia" for item in resultados) else 0


if __name__ == "__main__":
    pedidas = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] else list(ACEITOS)
    desconhecidas = set(pedidas) - set(ACEITOS)
    if desconhecidas:
        sys.exit(
            f"Telas desconhecidas: {', '.join(sorted(desconhecidas))}. Use {', '.join(ACEITOS)}."
        )
    sys.exit(asyncio.run(rodar(pedidas)))
