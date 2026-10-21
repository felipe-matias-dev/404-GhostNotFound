"""Gera uma amostra sintética da Gold para trabalhar sem o dataset confidencial.

Os valores são inventados (nenhum vem do dataset da V-Energy), mas seguem o contrato de
schemas.py e percorrem o mesmo caminho da Gold real: CSV → carga → banco.

Uso: uv run python -m venergy_api.amostra [--force]
"""

import argparse
import csv
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel

from venergy_api.carga import ARRAY_SEPARATOR, GOLD_TABLES
from venergy_api.config import get_settings
from venergy_api.database import Base
from venergy_api.models import (
    ContinuidadeAlimentadorMensal,
    DimUc,
    FatoFaturamentoMensal,
    FilaSuspeita,
    KpisMensais,
    ReceitaDecomposicao,
)
from venergy_api.schemas import (
    ContinuidadeAlimentadorMensalSchema,
    DimUcSchema,
    FaturamentoMensalSchema,
    FilaSuspeitaSchema,
    KpisMensaisSchema,
    ReceitaDecomposicaoSchema,
)

FIELDS = list(DimUcSchema.model_fields)

# Cobre todas as classes de consumo, UCs com e sem painel solar e municípios citados pelas
# lideranças. Os códigos são fixos para que o time possa citá-los ("busque a UC 0003").
# O titular C0001 tem duas UCs (casa e comércio), caso que o contrato prevê. A potência só
# existe para UCs com painel solar. O subgrupo fica vazio: o domínio ainda não foi definido.
_JABOATAO = "Jaboatão dos Guararapes"
_CABO = "Cabo de Santo Agostinho"
_ROWS = [
    # cod_uc, municipio, bairro, classe, cod_alimentador, possui_gd, consumo_medio_kwh_12m,
    # cod_cliente, subgrupo, potencia_kw
    ("0001", "Recife", "Boa Viagem", "B1", "AL-01", False, 162.5, "C0001", None, None),
    ("0002", "Recife", "Casa Amarela", "B1", "AL-02", True, 48.0, "C0002", None, 3.3),
    ("0003", "Olinda", "Casa Caiada", "B1", "AL-03", True, 95.3, "C0003", None, 5.0),
    ("0004", _JABOATAO, "Piedade", "B3", "AL-04", False, 1240.0, "C0004", None, None),
    ("0005", "Paulista", "Janga", "B1", "AL-05", False, 210.7, "C0005", None, None),
    ("0006", _CABO, "Zona Rural", "B2", "AL-06", True, 380.0, "C0006", None, 10.0),
    ("0007", "Recife", "Santo Amaro", "B3", "AL-01", False, 2850.0, "C0001", None, None),
    ("0008", _JABOATAO, "Prazeres", "A4", "AL-07", False, 48500.0, "C0008", None, None),
]

# Montar pelo schema faz a própria amostra falhar se sair do contrato.
SAMPLE_UCS = tuple(DimUcSchema(**dict(zip(FIELDS, row, strict=True))) for row in _ROWS)

# Receita: dois anos, calculados por fórmula fixa (sem aleatoriedade), para que os números
# sejam os mesmos em todas as máquinas e o time possa citá-los.
COMPETENCIAS = tuple(f"{ano}-{mes:02d}" for ano in (2024, 2025) for mes in range(1, 13))
_KWH = Decimal("0.001")
_CENTAVO = Decimal("0.01")
# Consumo de cada mês, de janeiro a dezembro, em % da média (média 100): mais no verão.
_SAZONALIDADE_PCT = (110, 112, 108, 100, 95, 90, 88, 90, 95, 100, 105, 107)
# R$/kWh por classe. De 2024 para 2025 a tarifa sobe 8% e o consumo cai 3%, para a
# decomposição ter efeito preço e efeito volume. 2025 fica com o consumo médio da dimensão.
_TARIFA = {
    "B1": Decimal("0.85"),
    "B2": Decimal("0.62"),
    "B3": Decimal("0.80"),
    "A4": Decimal("0.55"),
}
_REAJUSTE = {2024: Decimal("1.00"), 2025: Decimal("1.08")}
_VOLUME = {2024: Decimal("1.03"), 2025: Decimal("1.00")}
# Bandeira de janeiro a dezembro: vermelha na seca, quando as térmicas entram.
_BANDEIRAS = (
    "verde",
    "verde",
    "amarela",
    "verde",
    "amarela",
    "vermelha_p1",
    "vermelha_p2",
    "vermelha_p1",
    "amarela",
    "verde",
    "verde",
    "verde",
)
# Formato do período ainda "a confirmar" no contrato.
_PERIODO = {2024: "2024-01/2024-12", 2025: "2025-01/2025-12"}


def _faturamento() -> tuple[FaturamentoMensalSchema, ...]:
    rows = []
    for uc in SAMPLE_UCS:
        for competencia in COMPETENCIAS:
            ano, mes = int(competencia[:4]), int(competencia[5:])
            kwh = uc.consumo_medio_kwh_12m * _SAZONALIDADE_PCT[mes - 1] / 100 * _VOLUME[ano]
            # O painel solar da UC 0002 compensa todo o consumo de janeiro: kWh faturado
            # zero e tarifa média vazia, caso que o contrato prevê.
            if uc.cod_uc == "0002" and mes == 1:
                kwh = Decimal(0)
            kwh = kwh.quantize(_KWH)
            receita = (kwh * _TARIFA[uc.classe] * _REAJUSTE[ano]).quantize(_CENTAVO)
            # A UC 0005 não pagou as três últimas faturas: arrecadado zero, e não vazio,
            # porque "não pagou" é um fato.
            nao_pagou = uc.cod_uc == "0005" and competencia >= "2025-10"
            rows.append(
                FaturamentoMensalSchema(
                    cod_uc=uc.cod_uc,
                    competencia=competencia,
                    kwh_faturado=kwh,
                    receita_faturada=receita,
                    receita_arrecadada=Decimal("0.00") if nao_pagou else receita,
                    tarifa_media=float(receita / kwh) if kwh else None,
                    bandeira=_BANDEIRAS[mes - 1],
                )
            )
    return tuple(rows)


# UCs atendidas e DEC/FEC de referência por alimentador. O AL-06, rural e de rede longa, é
# o pior, para o ranking de continuidade ter um destaque claro.
_ALIMENTADORES = {
    # cod_alimentador: (n_uc, DEC de referência em horas, FEC de referência)
    "AL-01": (4200, 0.8, 0.5),
    "AL-02": (3100, 1.1, 0.7),
    "AL-03": (2800, 0.9, 0.6),
    "AL-04": (5200, 1.4, 0.9),
    "AL-05": (3600, 1.0, 0.6),
    "AL-06": (1300, 3.2, 1.8),
    "AL-07": (900, 0.6, 0.4),
}
# Interrupções de cada mês, de janeiro a dezembro, em % da referência: mais na estação chuvosa.
_CHUVA_PCT = (85, 85, 95, 115, 130, 140, 125, 100, 90, 85, 80, 85)


def _continuidade() -> tuple[ContinuidadeAlimentadorMensalSchema, ...]:
    # Pelo contrato, dec = horas_interrompidas ÷ n_uc e fec = n_interrupcoes ÷ n_uc. Para o
    # DEC sair em horas por consumidor, horas e interrupções somam o que cada UC afetada
    # sofreu (consumidor × hora), e não o tempo de relógio da ocorrência.
    rows = []
    for cod_alimentador, (n_uc, dec_referencia, fec_referencia) in _ALIMENTADORES.items():
        for competencia in COMPETENCIAS:
            chuva = _CHUVA_PCT[int(competencia[5:]) - 1] / 100
            horas = round(n_uc * dec_referencia * chuva, 1)
            interrupcoes = round(n_uc * fec_referencia * chuva)
            rows.append(
                ContinuidadeAlimentadorMensalSchema(
                    cod_alimentador=cod_alimentador,
                    competencia=competencia,
                    dec=horas / n_uc,
                    fec=interrupcoes / n_uc,
                    n_uc=n_uc,
                    n_interrupcoes=interrupcoes,
                    horas_interrompidas=horas,
                )
            )
    return tuple(rows)


def _kpis(
    faturamento: tuple[FaturamentoMensalSchema, ...],
    continuidade: tuple[ContinuidadeAlimentadorMensalSchema, ...],
) -> tuple[KpisMensaisSchema, ...]:
    # Somas do faturamento, para que o painel da diretoria bata com a soma das UCs.
    # Chamados e satisfação ainda não têm definição no contrato.
    rows = []
    for competencia in COMPETENCIAS:
        do_mes = [linha for linha in faturamento if linha.competencia == competencia]
        rede = [linha for linha in continuidade if linha.competencia == competencia]
        # DEC e FEC da empresa: totais sobre o total de UCs atendidas, e não a média dos
        # alimentadores, que daria o mesmo peso a um rural pequeno e a um urbano grande.
        n_uc = sum(linha.n_uc for linha in rede)
        rows.append(
            KpisMensaisSchema(
                competencia=competencia,
                kwh_faturado=sum((linha.kwh_faturado for linha in do_mes), Decimal(0)),
                receita_faturada=sum((linha.receita_faturada for linha in do_mes), Decimal(0)),
                dec=sum(linha.horas_interrompidas for linha in rede) / n_uc,
                fec=sum(linha.n_interrupcoes for linha in rede) / n_uc,
                n_chamados=None,
                satisfacao_media=None,
            )
        )
    return tuple(rows)


def _decomposicao(
    faturamento: tuple[FaturamentoMensalSchema, ...],
) -> tuple[ReceitaDecomposicaoSchema, ...]:
    # Totais de kWh e receita por segmento (município, bairro, classe) e ano.
    segmento_da_uc = {uc.cod_uc: (uc.municipio, uc.bairro, uc.classe) for uc in SAMPLE_UCS}
    totais: dict[tuple[tuple[str, str, str], int], list[Decimal]] = {}
    for linha in faturamento:
        chave = (segmento_da_uc[linha.cod_uc], int(linha.competencia[:4]))
        kwh, receita = totais.get(chave, [Decimal(0), Decimal(0)])
        totais[chave] = [kwh + linha.kwh_faturado, receita + linha.receita_faturada]

    rows = []
    for municipio, bairro, classe in sorted({segmento for segmento, _ in totais}):
        kwh_base, receita_base = totais[((municipio, bairro, classe), 2024)]
        kwh_atual, receita_atual = totais[((municipio, bairro, classe), 2025)]
        tarifa_base, tarifa_atual = receita_base / kwh_base, receita_atual / kwh_atual
        efeito_preco = ((tarifa_atual - tarifa_base) * kwh_atual).quantize(_CENTAVO)
        efeito_volume = ((kwh_atual - kwh_base) * tarifa_base).quantize(_CENTAVO)
        rows.append(
            ReceitaDecomposicaoSchema(
                periodo_base=_PERIODO[2024],
                periodo_atual=_PERIODO[2025],
                municipio=municipio,
                bairro=bairro,
                classe=classe,
                receita_base=receita_base,
                receita_atual=receita_atual,
                efeito_preco=efeito_preco,
                efeito_volume=efeito_volume,
                # Num segmento só, preço e volume já explicam toda a variação: aqui o mix é
                # o resíduo do arredondamento, e a conta fecha. A fórmula oficial, com o mix
                # entre segmentos, é do Diagnóstico.
                efeito_mix=receita_atual - receita_base - efeito_preco - efeito_volume,
            )
        )
    return tuple(rows)


# Fila de suspeitas, da maior para a menor prioridade. A UC 0004 ainda não tem estimativa
# de energia recuperável: o gerente de perdas vê a suspeita mesmo sem o valor.
SAMPLE_FILA = (
    FilaSuspeitaSchema(
        cod_uc="0005",
        score_suspeita=0.91,
        motivos=["leituras estimadas em 3 dos últimos 6 meses", "medidor com mais de 15 anos"],
        kwh_recuperavel_est=Decimal("1850.000"),
    ),
    FilaSuspeitaSchema(
        cod_uc="0007",
        score_suspeita=0.78,
        motivos=["inspeção anterior encontrou irregularidade"],
        kwh_recuperavel_est=Decimal("4200.000"),
    ),
    FilaSuspeitaSchema(
        cod_uc="0004",
        score_suspeita=0.64,
        motivos=["leituras estimadas em 2 dos últimos 6 meses"],
        kwh_recuperavel_est=None,
    ),
)

SAMPLE_FATURAMENTO = _faturamento()
SAMPLE_CONTINUIDADE = _continuidade()
SAMPLE_KPIS = _kpis(SAMPLE_FATURAMENTO, SAMPLE_CONTINUIDADE)
SAMPLE_DECOMPOSICAO = _decomposicao(SAMPLE_FATURAMENTO)

# Linhas por tabela da Gold. A carga exige um CSV para cada tabela de GOLD_TABLES, e o
# teste da amostra falha se alguma ficar de fora.
SAMPLE: dict[type[Base], tuple[BaseModel, ...]] = {
    DimUc: SAMPLE_UCS,
    FatoFaturamentoMensal: SAMPLE_FATURAMENTO,
    ReceitaDecomposicao: SAMPLE_DECOMPOSICAO,
    KpisMensais: SAMPLE_KPIS,
    ContinuidadeAlimentadorMensal: SAMPLE_CONTINUIDADE,
    FilaSuspeita: SAMPLE_FILA,
}


def _to_csv_cell(value: object) -> object:
    # Formato do contrato: booleanos em minúsculas, como o Spark exporta ("true"/"false"),
    # e listas numa célula só, com os itens separados por ponto e vírgula.
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return ARRAY_SEPARATOR.join(value)
    return value


def _to_csv_row(row: BaseModel) -> dict[str, object]:
    return {field: _to_csv_cell(value) for field, value in row.model_dump().items()}


def write_sample(gold_dir: Path, *, force: bool) -> list[Path]:
    """Grava um CSV por tabela da Gold em gold_dir. Sem force, não sobrescreve nenhum."""
    csv_paths = {table: gold_dir / table.file_name for table in GOLD_TABLES}
    # Confere todos antes de gravar o primeiro: misturar amostra com a Gold real deixaria
    # números de origens diferentes lado a lado, pior do que não gravar nada.
    existing = [path for path in csv_paths.values() if path.exists()]
    if existing and not force:
        raise FileExistsError(
            f"{existing[0]} já existe e pode ser a Gold real. Use --force para sobrescrever."
        )

    gold_dir.mkdir(parents=True, exist_ok=True)
    for table, csv_path in csv_paths.items():
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(table.schema.model_fields))
            writer.writeheader()
            writer.writerows(_to_csv_row(row) for row in SAMPLE[table.model])
    return list(csv_paths.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a amostra sintética da Gold.")
    parser.add_argument("--force", action="store_true", help="sobrescreve os CSVs existentes")
    args = parser.parse_args()

    gold_dir = get_settings().gold_dir
    try:
        csv_paths = write_sample(gold_dir, force=args.force)
    except FileExistsError as error:
        raise SystemExit(str(error)) from error
    print(f"Amostra sintética gravada em {gold_dir}: {', '.join(p.name for p in csv_paths)}")


if __name__ == "__main__":
    main()
