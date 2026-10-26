"""Gera uma amostra sintética da Gold para trabalhar sem o dataset confidencial.

Os valores são inventados (nenhum vem do dataset da V-Energy), mas seguem o contrato de
schemas.py e percorrem o mesmo caminho da Gold real: CSV → carga → banco.

Uso: uv run python -m venergy_api.amostra [--force]
"""

import argparse
import calendar
import csv
from datetime import date
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
    KpisSegmentoMensal,
    ReceitaDecomposicao,
    ReconciliacaoFaturamento,
)
from venergy_api.schemas import (
    ContinuidadeAlimentadorMensalSchema,
    DimUcSchema,
    FaturamentoMensalSchema,
    FilaSuspeitaSchema,
    KpisMensaisSchema,
    KpisSegmentoMensalSchema,
    ReceitaDecomposicaoSchema,
    ReconciliacaoFaturamentoSchema,
)

FIELDS = list(DimUcSchema.model_fields)

# Cobre as 4 classes de consumo e as 5 do cadastro (o B3 aparece como Poder Público e como
# Comercial), UCs com e sem painel solar e municípios citados pelas lideranças. Os códigos
# são fixos para que o time possa citá-los ("busque a UC 0003"). Titular e documento são
# inventados e já mascarados, como chegam da Gold. A potência, a conexão e a energia injetada só
# existem com painel solar, e a conexão é anterior a 2024 (o GD de cada mês é o do cadastro).
# Todas as UCs foram ligadas antes do primeiro mês, então o n_uc é o mesmo em toda competência.
_JABOATAO = "Jaboatão dos Guararapes"
_CABO = "Cabo de Santo Agostinho"
_CPF = "***.***.**{}-{}"
_CNPJ = "**.***.***/***{}-{}"
_ROWS = [
    # cod_uc, municipio, bairro, classe, classe_cadastro, cod_alimentador, possui_gd,
    # consumo_medio_kwh_12m, titular_mascarado, documento_mascarado, potencia_kwp, data_ligacao,
    # data_conexao_gd, modalidade_gd, energia_injetada_kwh_mes
    (
        "0001",
        "Recife",
        "Boa Viagem",
        "B1",
        "Residencial",
        "AL-01",
        False,
        162.5,
        "M. S.",
        _CPF.format(1, "23"),
        None,
        date(2015, 6, 1),
        None,
        None,
        None,
    ),
    (
        "0002",
        "Recife",
        "Casa Amarela",
        "B1",
        "Residencial",
        "AL-02",
        True,
        48.0,
        "A. L. P.",
        _CPF.format(4, "56"),
        3.3,
        date(2018, 6, 1),
        date(2022, 3, 15),
        "geracao_propria_uc",
        Decimal("396.000"),
    ),
    (
        "0003",
        "Olinda",
        "Casa Caiada",
        "B1",
        "Residencial",
        "AL-03",
        True,
        95.3,
        "J. C.",
        _CPF.format(7, "89"),
        5.0,
        date(2019, 6, 1),
        date(2023, 6, 20),
        "autoconsumo_remoto",
        Decimal("600.000"),
    ),
    (
        "0004",
        _JABOATAO,
        "Piedade",
        "B3",
        "Poder Público",
        "AL-04",
        False,
        1240.0,
        "E. M. P.",
        _CNPJ.format(0, "11"),
        None,
        date(2012, 6, 1),
        None,
        None,
        None,
    ),
    (
        "0005",
        "Paulista",
        "Janga",
        "B1",
        "Residencial",
        "AL-05",
        False,
        210.7,
        "R. F.",
        _CPF.format(2, "34"),
        None,
        date(2016, 6, 1),
        None,
        None,
        None,
    ),
    (
        "0006",
        _CABO,
        "Zona Rural",
        "B2",
        "Rural",
        "AL-06",
        True,
        380.0,
        "S. B. A.",
        _CPF.format(5, "67"),
        10.0,
        date(2010, 6, 1),
        date(2021, 11, 5),
        "geracao_propria_uc",
        Decimal("1200.000"),
    ),
    (
        "0007",
        "Recife",
        "Santo Amaro",
        "B3",
        "Comercial",
        "AL-01",
        False,
        2850.0,
        "P. N. L.",
        _CNPJ.format(8, "90"),
        None,
        date(2014, 6, 1),
        None,
        None,
        None,
    ),
    (
        "0008",
        _JABOATAO,
        "Prazeres",
        "A4",
        "Industrial",
        "AL-07",
        False,
        48500.0,
        "M. I. N.",
        _CNPJ.format(3, "45"),
        None,
        date(2008, 6, 1),
        None,
        None,
        None,
    ),
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
# Bandeiras de 2025, de janeiro a dezembro: vermelha na seca, quando as térmicas entram.
# 2024 fica todo em verde, como o período base do diagnóstico, para a decomposição ter
# efeito bandeira.
_BANDEIRAS_2025 = (
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
# Acréscimo por kWh em cada bandeira, na ordem de grandeza das bandeiras tarifárias.
_ADICIONAL_BANDEIRA = {
    "verde": Decimal("0"),
    "amarela": Decimal("0.019"),
    "vermelha_p1": Decimal("0.045"),
    "vermelha_p2": Decimal("0.079"),
}
# Formato confirmado no contrato v0.2: AAAA-MM/AAAA-MM.
_PERIODO = {2024: "2024-01/2024-12", 2025: "2025-01/2025-12"}


def _bandeira(competencia: str) -> str:
    if competencia < "2025-01":
        return "verde"
    return _BANDEIRAS_2025[int(competencia[5:]) - 1]


# Tributos sobre a energia numa alíquota única inventada: na fatura real ela varia.
_ALIQUOTA_TRIBUTOS = Decimal("0.25")
# Um caso de cada regra de leitura negativa que o contrato prevê (DEC-023).
_TROCA_MEDIDOR = ("0003", "2025-03")
_SINAL_INVERTIDO = ("0006", "2024-08")
_PAGOU_COM_ATRASO = ("0001", "2025-03")
# Leituras estimadas (o leiturista não chegou ao medidor), nos últimos seis meses das UCs da
# fila de suspeitas: 3 de 6 na UC 0005 e 2 de 6 na UC 0004.
_LEITURAS_ESTIMADAS = {
    "0005": ("2025-08", "2025-10", "2025-12"),
    "0004": ("2025-09", "2025-11"),
}
# Tipo do medidor de cada UC. A UC 0003 troca o eletromecânico por um eletrônico no mês da
# troca de medidor (a mesma em que a leitura vem negativa).
_MEDIDOR = {
    "0001": "eletronico",
    "0002": "smart",
    "0003": "eletronico",
    "0004": "eletronico",
    "0005": "eletromecanico",
    "0006": "eletronico",
    "0007": "smart",
    "0008": "smart",
}
_MEDIDOR_ANTES_DA_TROCA = "eletromecanico"


def _mes_seguinte(competencia: str, dia: int) -> date:
    ano, mes = int(competencia[:4]), int(competencia[5:])
    return date(ano + mes // 12, mes % 12 + 1, dia)


def _leitura(cod_uc: str, competencia: str, kwh_faturado: Decimal) -> tuple[Decimal, str]:
    """Consumo da leitura antes da correção e a regra que leva ao kwh_faturado."""
    if (cod_uc, competencia) == _TROCA_MEDIDOR:
        # O medidor novo parte do zero, a diferença das leituras sai negativa, e vale a
        # leitura atual.
        return kwh_faturado - Decimal("5000.000"), "leitura_atual_troca_medidor"
    if (cod_uc, competencia) == _SINAL_INVERTIDO:
        return -kwh_faturado, "consumo_absoluto"
    return kwh_faturado, "leitura"


def tipo_medidor_da_leitura(cod_uc: str, competencia: str) -> str:
    """Tipo do medidor que fez a leitura do mês."""
    if cod_uc == _TROCA_MEDIDOR[0] and competencia < _TROCA_MEDIDOR[1]:
        return _MEDIDOR_ANTES_DA_TROCA
    return _MEDIDOR[cod_uc]


def _dias_faturados(competencia: str) -> int | None:
    # A leitura é feita no mesmo dia de todo mês, então os dias entre duas leituras são os do
    # mês. A primeira leitura da UC não tem anterior.
    if competencia == COMPETENCIAS[0]:
        return None
    return calendar.monthrange(int(competencia[:4]), int(competencia[5:]))[1]


def _situacao(vencimento: date, pagamento: date | None, corte: date) -> tuple[str, int | None]:
    """Status e dias de atraso da fatura, pela regra do contrato (conventions.invoice_status)."""
    if pagamento is not None:
        atraso = (pagamento - vencimento).days
        return ("paga_com_atraso", atraso) if atraso > 0 else ("paga", None)
    if vencimento < corte:
        return "em_atraso", (corte - vencimento).days
    return "em_aberto", None


def _faturamento() -> tuple[FaturamentoMensalSchema, ...]:
    faturas = []
    for uc in SAMPLE_UCS:
        for competencia in COMPETENCIAS:
            ano, mes = int(competencia[:4]), int(competencia[5:])
            kwh = uc.consumo_medio_kwh_12m * _SAZONALIDADE_PCT[mes - 1] / 100 * _VOLUME[ano]
            # O painel solar da UC 0002 compensa todo o consumo de janeiro: kWh faturado
            # zero e tarifa média vazia, caso que o contrato prevê.
            if uc.cod_uc == "0002" and mes == 1:
                kwh = Decimal(0)
            kwh = kwh.quantize(_KWH)
            tarifa = (
                _TARIFA[uc.classe] * _REAJUSTE[ano] + _ADICIONAL_BANDEIRA[_bandeira(competencia)]
            )
            energia = (kwh * tarifa).quantize(_CENTAVO)
            tributos = (energia * _ALIQUOTA_TRIBUTOS).quantize(_CENTAVO)
            # A UC 0005 não pagou as três últimas faturas: arrecadado zero, e não vazio,
            # porque "não pagou" é um fato. As demais pagam no dia 8, antes do vencimento.
            nao_pagou = uc.cod_uc == "0005" and competencia >= "2025-10"
            dia_pagamento = 20 if (uc.cod_uc, competencia) == _PAGOU_COM_ATRASO else 8
            faturas.append(
                {
                    "uc": uc,
                    "competencia": competencia,
                    "kwh": kwh,
                    "energia": energia,
                    "tributos": tributos,
                    "emissao": _mes_seguinte(competencia, 1),
                    "vencimento": _mes_seguinte(competencia, 10),
                    "pagamento": None if nao_pagou else _mes_seguinte(competencia, dia_pagamento),
                    "bandeira": (kwh * _ADICIONAL_BANDEIRA[_bandeira(competencia)]).quantize(
                        _CENTAVO
                    ),
                }
            )

    # Data de corte: a maior data presente nas faturas, de emissão ou de pagamento, porque o
    # dado é uma extração única. A fatura de dezembro da UC 0005 vence depois dela e fica em
    # aberto; as de outubro e novembro, em atraso.
    corte = max(max(f["emissao"], f["pagamento"] or f["emissao"]) for f in faturas)
    rows = []
    for f in faturas:
        kwh_leitura, origem_kwh = _leitura(f["uc"].cod_uc, f["competencia"], f["kwh"])
        status, dias_em_atraso = _situacao(f["vencimento"], f["pagamento"], corte)
        total = f["energia"] + f["tributos"]
        rows.append(
            FaturamentoMensalSchema(
                cod_uc=f["uc"].cod_uc,
                competencia=f["competencia"],
                kwh_faturado=f["kwh"],
                kwh_leitura=kwh_leitura,
                origem_kwh=origem_kwh,
                receita_faturada=total,
                receita_energia=f["energia"],
                tributos=f["tributos"],
                receita_arrecadada=total if f["pagamento"] else Decimal("0.00"),
                # Sem tributos, como o contrato redefiniu (DEC-023).
                tarifa_media=float(f["energia"] / f["kwh"]) if f["kwh"] else None,
                bandeira=_bandeira(f["competencia"]),
                data_vencimento=f["vencimento"],
                data_pagamento=f["pagamento"],
                status_pagamento=status,
                dias_em_atraso=dias_em_atraso,
                receita_bandeira=f["bandeira"],
                tipo_leitura=(
                    "estimada"
                    if f["competencia"] in _LEITURAS_ESTIMADAS.get(f["uc"].cod_uc, ())
                    else "real"
                ),
                tipo_medidor=tipo_medidor_da_leitura(f["uc"].cod_uc, f["competencia"]),
                dias_faturados=_dias_faturados(f["competencia"]),
            )
        )
    return tuple(rows)


# DEC e FEC de referência de cada alimentador, por UC e por mês. O AL-06, rural e de rede
# longa, é o pior, para o ranking de continuidade ter um destaque claro.
_ALIMENTADORES = {
    # cod_alimentador: (DEC de referência em horas, FEC de referência)
    "AL-01": (0.8, 0.5),
    "AL-02": (1.1, 0.7),
    "AL-03": (0.9, 0.6),
    "AL-04": (1.4, 0.9),
    "AL-05": (1.0, 0.6),
    "AL-06": (3.2, 1.8),
    "AL-07": (0.6, 0.4),
}
# Interrupções de cada mês, de janeiro a dezembro, em % da referência: mais na estação chuvosa.
_CHUVA_PCT = (85, 85, 95, 115, 130, 140, 125, 100, 90, 85, 80, 85)


def _interrupcoes(uc: DimUcSchema, competencia: str) -> tuple[int, float]:
    """Interrupções e horas sem energia de uma UC num mês (no case, cada ocorrência é uma UC)."""
    dec_referencia, fec_referencia = _ALIMENTADORES[uc.cod_alimentador]
    chuva = _CHUVA_PCT[int(competencia[5:]) - 1] / 100
    interrupcoes = round(fec_referencia * chuva)
    # Cada interrupção dura a média do alimentador: sem interrupção, sem hora parada.
    return interrupcoes, round(interrupcoes * dec_referencia / fec_referencia, 1)


def _chamados(uc: DimUcSchema, competencia: str) -> tuple[int, int | None]:
    """Chamados abertos pela UC no mês e a nota do atendimento, de 1 a 5."""
    mes, numero = int(competencia[5:]), int(uc.cod_uc)
    if (mes + numero) % 4:
        return 0, None
    # Parte dos chamados fica sem nota, e fica fora da média (ATD-01).
    nota = None if mes % 3 == 0 else 1 + (mes + 2 * numero) % 5
    return 1, nota


def _continuidade() -> tuple[ContinuidadeAlimentadorMensalSchema, ...]:
    # Somada das UCs da amostra, para bater com os KPIs por recorte: n_uc é o número de UCs
    # do cadastro que o alimentador atende. Pelo contrato, dec = horas_interrompidas ÷ n_uc
    # e fec = n_interrupcoes ÷ n_uc, com as horas em consumidor × hora.
    rows = []
    for cod_alimentador in _ALIMENTADORES:
        ucs = [uc for uc in SAMPLE_UCS if uc.cod_alimentador == cod_alimentador]
        for competencia in COMPETENCIAS:
            ocorrencias = [_interrupcoes(uc, competencia) for uc in ucs]
            interrupcoes = sum(n for n, _ in ocorrencias)
            horas = sum(h for _, h in ocorrencias)
            rows.append(
                ContinuidadeAlimentadorMensalSchema(
                    cod_alimentador=cod_alimentador,
                    competencia=competencia,
                    dec=horas / len(ucs),
                    fec=interrupcoes / len(ucs),
                    n_uc=len(ucs),
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
    rows = []
    for competencia in COMPETENCIAS:
        do_mes = [linha for linha in faturamento if linha.competencia == competencia]
        rede = [linha for linha in continuidade if linha.competencia == competencia]
        # DEC e FEC da empresa: totais sobre o total de UCs atendidas, e não a média dos
        # alimentadores, que daria o mesmo peso a um rural pequeno e a um urbano grande.
        n_uc = sum(linha.n_uc for linha in rede)
        chamados = [_chamados(uc, competencia) for uc in SAMPLE_UCS]
        notas = [nota for _, nota in chamados if nota is not None]
        rows.append(
            KpisMensaisSchema(
                competencia=competencia,
                kwh_faturado=sum((linha.kwh_faturado for linha in do_mes), Decimal(0)),
                receita_faturada=sum((linha.receita_faturada for linha in do_mes), Decimal(0)),
                receita_energia=sum((linha.receita_energia for linha in do_mes), Decimal(0)),
                dec=sum(linha.horas_interrompidas for linha in rede) / n_uc,
                fec=sum(linha.n_interrupcoes for linha in rede) / n_uc,
                n_chamados=sum(n for n, _ in chamados),
                # Soma das notas ÷ chamados com nota; vazia no mês sem nenhuma avaliação.
                satisfacao_media=sum(notas) / len(notas) if notas else None,
            )
        )
    return tuple(rows)


def _kpis_segmento(
    faturamento: tuple[FaturamentoMensalSchema, ...],
) -> tuple[KpisSegmentoMensalSchema, ...]:
    # Somados das UCs com as mesmas regras do faturamento, da continuidade e dos chamados:
    # a soma de cada mês bate com os KPIs da empresa e com a continuidade por alimentador.
    fatura = {(linha.cod_uc, linha.competencia): linha for linha in faturamento}
    recortes: dict[tuple[str, str, str, bool], list[DimUcSchema]] = {}
    for uc in SAMPLE_UCS:
        # Na amostra, os painéis solares já estavam conectados antes de 2024, então o GD de
        # cada competência é o do cadastro.
        chave = (uc.municipio, uc.bairro, uc.classe_cadastro, uc.possui_gd)
        recortes.setdefault(chave, []).append(uc)

    rows = []
    for competencia in COMPETENCIAS:
        for (municipio, bairro, classe_cadastro, possui_gd), ucs in sorted(recortes.items()):
            faturas = [fatura[(uc.cod_uc, competencia)] for uc in ucs]
            ocorrencias = [_interrupcoes(uc, competencia) for uc in ucs]
            chamados = [_chamados(uc, competencia) for uc in ucs]
            notas = [nota for _, nota in chamados if nota is not None]
            arrecadado = [f.receita_arrecadada for f in faturas if f.receita_arrecadada is not None]
            rows.append(
                KpisSegmentoMensalSchema(
                    competencia=competencia,
                    municipio=municipio,
                    bairro=bairro,
                    classe_cadastro=classe_cadastro,
                    classe=ucs[0].classe,
                    possui_gd=possui_gd,
                    n_uc=len(ucs),
                    kwh_faturado=sum((f.kwh_faturado for f in faturas), Decimal(0)),
                    receita_faturada=sum((f.receita_faturada for f in faturas), Decimal(0)),
                    receita_energia=sum((f.receita_energia for f in faturas), Decimal(0)),
                    tributos=sum((f.tributos for f in faturas), Decimal(0)),
                    receita_arrecadada=sum(arrecadado, Decimal(0)) if arrecadado else None,
                    horas_interrompidas=sum(h for _, h in ocorrencias),
                    n_interrupcoes=sum(n for n, _ in ocorrencias),
                    n_chamados=sum(n for n, _ in chamados),
                    soma_notas=float(sum(notas)) if notas else None,
                    n_notas=len(notas),
                )
            )
    return tuple(rows)


# Faturas de UCs fora do cadastro, em todo mês: valores inventados, para a parcela de órfãs
# da reconciliação não ficar zerada.
_FATURAS_ORFAS = (Decimal("187.40"), Decimal("92.15"))


def _correcao_kwh(faturas: list[FaturamentoMensalSchema], origem: str) -> Decimal:
    """Quanto a regra de uma origem somou ao consumo bruto da leitura."""
    return sum(
        (
            fatura.kwh_faturado - fatura.kwh_leitura
            for fatura in faturas
            if fatura.origem_kwh == origem
        ),
        Decimal(0),
    )


def _reconciliacao(
    faturamento: tuple[FaturamentoMensalSchema, ...],
) -> tuple[ReconciliacaoFaturamentoSchema, ...]:
    # O cadastro é a soma do fato por UC; as órfãs entram só aqui, porque não têm UC para
    # ligar. As correções de energia vêm da regra que gerou cada kwh_faturado (origem_kwh).
    rows = []
    for competencia in COMPETENCIAS:
        do_mes = [linha for linha in faturamento if linha.competencia == competencia]
        cadastro = sum((linha.receita_faturada for linha in do_mes), Decimal(0))
        orfas = sum(_FATURAS_ORFAS, Decimal(0))
        rows.append(
            ReconciliacaoFaturamentoSchema(
                competencia=competencia,
                receita_faturada_total=cadastro + orfas,
                receita_faturada_orfas=orfas,
                receita_faturada_cadastro=cadastro,
                tributos_cadastro=sum((linha.tributos for linha in do_mes), Decimal(0)),
                receita_energia_cadastro=sum(
                    (linha.receita_energia for linha in do_mes), Decimal(0)
                ),
                n_faturas_orfas=len(_FATURAS_ORFAS),
                kwh_leitura_total=sum((linha.kwh_leitura for linha in do_mes), Decimal(0)),
                kwh_correcao_troca_medidor=_correcao_kwh(do_mes, "leitura_atual_troca_medidor"),
                kwh_correcao_sinal_invertido=_correcao_kwh(do_mes, "consumo_absoluto"),
                kwh_faturado_total=sum((linha.kwh_faturado for linha in do_mes), Decimal(0)),
            )
        )
    return tuple(rows)


def _decomposicao(
    faturamento: tuple[FaturamentoMensalSchema, ...],
) -> tuple[ReceitaDecomposicaoSchema, ...]:
    # Totais de kWh, receita de energia e acréscimo de bandeira por segmento e ano. A base é a
    # receita de energia, sem tributos (DEC-023).
    segmento_da_uc = {
        uc.cod_uc: (uc.municipio, uc.bairro, uc.classe, uc.possui_gd) for uc in SAMPLE_UCS
    }
    totais: dict[tuple[tuple[str, str, str, bool], int], list[Decimal]] = {}
    for linha in faturamento:
        chave = (segmento_da_uc[linha.cod_uc], int(linha.competencia[:4]))
        kwh, receita, bandeira = totais.get(chave, [Decimal(0), Decimal(0), Decimal(0)])
        totais[chave] = [
            kwh + linha.kwh_faturado,
            receita + linha.receita_energia,
            bandeira + linha.kwh_faturado * _ADICIONAL_BANDEIRA[linha.bandeira],
        ]

    rows = []
    for segmento in sorted({segmento for segmento, _ in totais}):
        municipio, bairro, classe, possui_gd = segmento
        kwh_base, receita_base, bandeira_base = totais[(segmento, 2024)]
        kwh_atual, receita_atual, bandeira_atual = totais[(segmento, 2025)]
        tarifa_base, tarifa_atual = receita_base / kwh_base, receita_atual / kwh_atual
        efeito_preco = ((tarifa_atual - tarifa_base) * kwh_atual).quantize(_CENTAVO)
        # A parte do preço que veio da bandeira: o acréscimo médio por kWh mudou entre os
        # períodos. O resto do efeito preço é o reajuste da tarifa base.
        adicional_base, adicional_atual = bandeira_base / kwh_base, bandeira_atual / kwh_atual
        efeito_bandeira = ((adicional_atual - adicional_base) * kwh_atual).quantize(_CENTAVO)
        rows.append(
            ReceitaDecomposicaoSchema(
                periodo_base=_PERIODO[2024],
                periodo_atual=_PERIODO[2025],
                municipio=municipio,
                bairro=bairro,
                classe=classe,
                possui_gd=possui_gd,
                receita_base=receita_base,
                receita_atual=receita_atual,
                efeito_preco=efeito_preco,
                efeito_tarifa=efeito_preco - efeito_bandeira,
                efeito_bandeira=efeito_bandeira,
                efeito_volume=((kwh_atual - kwh_base) * tarifa_base).quantize(_CENTAVO),
                # Calculado, e não resíduo (contrato v0.2): num segmento de uma classe só, o
                # peso entre classes não muda, então o mix é zero. Preço e volume fecham com a
                # variação dentro da tolerância de arredondamento (R$ 0,02 por linha).
                efeito_mix=Decimal("0.00"),
            )
        )
    return tuple(rows)


# Fila de suspeitas, pela posição no ranking (1 = mais suspeita). A UC 0004 ainda não tem estimativa
# de energia recuperável: o gerente de perdas vê a suspeita mesmo sem o valor.
SAMPLE_FILA = (
    FilaSuspeitaSchema(
        cod_uc="0005",
        score_suspeita=1,
        motivos=["leituras estimadas em 3 dos últimos 6 meses", "medidor com mais de 15 anos"],
        kwh_recuperavel_est=Decimal("1850.000"),
    ),
    FilaSuspeitaSchema(
        cod_uc="0007",
        score_suspeita=2,
        motivos=["inspeção anterior encontrou irregularidade"],
        kwh_recuperavel_est=Decimal("4200.000"),
    ),
    FilaSuspeitaSchema(
        cod_uc="0004",
        score_suspeita=3,
        motivos=["leituras estimadas em 2 dos últimos 6 meses"],
        kwh_recuperavel_est=None,
    ),
)

SAMPLE_FATURAMENTO = _faturamento()
SAMPLE_CONTINUIDADE = _continuidade()
SAMPLE_KPIS = _kpis(SAMPLE_FATURAMENTO, SAMPLE_CONTINUIDADE)
SAMPLE_KPIS_SEGMENTO = _kpis_segmento(SAMPLE_FATURAMENTO)
SAMPLE_RECONCILIACAO = _reconciliacao(SAMPLE_FATURAMENTO)
SAMPLE_DECOMPOSICAO = _decomposicao(SAMPLE_FATURAMENTO)

# Linhas por tabela da Gold. A carga exige um CSV para cada tabela de GOLD_TABLES, e o
# teste da amostra falha se alguma ficar de fora.
SAMPLE: dict[type[Base], tuple[BaseModel, ...]] = {
    DimUc: SAMPLE_UCS,
    FatoFaturamentoMensal: SAMPLE_FATURAMENTO,
    ReceitaDecomposicao: SAMPLE_DECOMPOSICAO,
    KpisMensais: SAMPLE_KPIS,
    KpisSegmentoMensal: SAMPLE_KPIS_SEGMENTO,
    ReconciliacaoFaturamento: SAMPLE_RECONCILIACAO,
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
