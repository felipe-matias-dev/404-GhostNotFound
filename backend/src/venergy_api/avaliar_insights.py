"""Rodada fixa dos insights da Receita: `make eval-insights` (DEC-066).

Escolhe na Gold carregada um recorte para cada caso que a regra de leitura distingue, soma dois
casos sintéticos que a base pode não ter e chama o modelo em todos. O relatório vai para
`ai-agent/eval/runs_gold/`, fora do Git, porque traz números da Gold. Termina com erro se algum
caso esperado não sair com texto do modelo.
"""

import asyncio
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from venergy_agent.bootstrap import build_insight_writer
from venergy_agent.config import AgentSettings

from venergy_api.config import get_settings
from venergy_api.database import create_db_engine
from venergy_api.insight_receita import filtro_acima, metricas_da_receita, texto_aceito
from venergy_api.models import ReceitaDecomposicao
from venergy_api.routers.receita import consultar_decomposicao
from venergy_api.schemas import DecomposicaoFiltroSchema, DecomposicaoLinhaSchema

Metricas = dict[str, object]
Candidato = tuple[DecomposicaoFiltroSchema, Metricas]

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


async def _narrar(redator, caso: str, recorte: str, metricas: Metricas) -> dict[str, object]:
    insight = await redator.narrate("receita", metricas)
    aceito = insight is not None and texto_aceito(insight.text, metricas)
    return {
        "caso": caso,
        "recorte": recorte,
        "leitura": metricas["leitura_principal"],
        "origem": "ia" if aceito else "regra",
        "regra": metricas["leitura_texto"],
        "texto": insight.text if insight else None,
    }


async def rodar() -> int:
    engine = create_db_engine(get_settings().database_url)
    redator = build_insight_writer(AgentSettings())
    resultados: list[dict[str, object]] = []
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
        escolhidos = escolher_recortes(_candidatos(session, par[0], par[1]))
    for caso, candidato in escolhidos.items():
        if candidato is None:
            sem_recorte.append(caso)
            continue
        resultados.append(await _narrar(redator, caso, str(candidato[1]["recorte"]), candidato[1]))
    for caso, metricas in casos_sinteticos().items():
        resultados.append(await _narrar(redator, caso, "sintético", metricas))

    RELATORIOS.mkdir(parents=True, exist_ok=True)
    instante = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    relatorio = RELATORIOS / f"insights-{instante}.json"
    conteudo = {"resultados": resultados, "sem_recorte": sem_recorte}
    relatorio.write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")

    recusados = [item for item in resultados if item["origem"] != "ia"]
    for item in resultados:
        print(f"[{item['origem']}] {item['caso']} · {item['recorte']}\n  {item['texto']}")
    print(f"\n{len(resultados) - len(recusados)} de {len(resultados)} com texto do modelo.")
    print(f"Sem recorte na base: {', '.join(sem_recorte) or 'nenhum'}.")
    print(f"Relatório: {relatorio}")
    return 1 if recusados else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(rodar()))
