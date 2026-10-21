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

from venergy_api.carga import GOLD_TABLES
from venergy_api.config import get_settings
from venergy_api.database import Base
from venergy_api.models import DimUc, FatoFaturamentoMensal, KpisMensais, ReceitaDecomposicao
from venergy_api.schemas import (
    DimUcSchema,
    FaturamentoMensalSchema,
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


def _kpis(faturamento: tuple[FaturamentoMensalSchema, ...]) -> tuple[KpisMensaisSchema, ...]:
    # Somas do faturamento, para que o painel da diretoria bata com a soma das UCs.
    # DEC e FEC saem da continuidade, que ainda não tem amostra; chamados e satisfação
    # ainda não têm definição no contrato.
    rows = []
    for competencia in COMPETENCIAS:
        do_mes = [linha for linha in faturamento if linha.competencia == competencia]
        rows.append(
            KpisMensaisSchema(
                competencia=competencia,
                kwh_faturado=sum((linha.kwh_faturado for linha in do_mes), Decimal(0)),
                receita_faturada=sum((linha.receita_faturada for linha in do_mes), Decimal(0)),
                dec=None,
                fec=None,
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


SAMPLE_FATURAMENTO = _faturamento()
SAMPLE_KPIS = _kpis(SAMPLE_FATURAMENTO)
SAMPLE_DECOMPOSICAO = _decomposicao(SAMPLE_FATURAMENTO)

# Linhas por tabela da Gold. A carga exige um CSV para cada tabela de GOLD_TABLES, e o
# teste da amostra falha se alguma ficar de fora.
SAMPLE: dict[type[Base], tuple[BaseModel, ...]] = {
    DimUc: SAMPLE_UCS,
    FatoFaturamentoMensal: SAMPLE_FATURAMENTO,
    ReceitaDecomposicao: SAMPLE_DECOMPOSICAO,
    KpisMensais: SAMPLE_KPIS,
}


def _to_csv_row(row: BaseModel) -> dict[str, object]:
    # Booleanos em minúsculas, como o Spark exporta: "true"/"false".
    return {
        field: str(value).lower() if isinstance(value, bool) else value
        for field, value in row.model_dump().items()
    }


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
