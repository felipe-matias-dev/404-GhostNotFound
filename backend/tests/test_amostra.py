from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from venergy_api.amostra import SAMPLE, SAMPLE_FILA, write_sample
from venergy_api.carga import load_gold
from venergy_api.models import (
    FatoFaturamentoMensal,
    FilaSuspeita,
    KpisMensais,
    ReceitaDecomposicao,
)


def test_generated_sample_passes_the_gold_load(tmp_path: Path, engine: Engine) -> None:
    write_sample(tmp_path / "gold", force=False)

    counts = load_gold(tmp_path / "gold", engine)

    # A carga exige um CSV por tabela da Gold: se faltar amostra de uma, ela falha antes.
    assert counts == {model.__tablename__: len(rows) for model, rows in SAMPLE.items()}


def test_billing_follows_the_contract_checks(tmp_path: Path, engine: Engine) -> None:
    # As validações do fato no contrato (checks) e a regra do kwh_faturado da DEC-023, depois
    # de CSV, carga e banco: é o que a Gold real também terá que cumprir.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        faturas = session.scalars(select(FatoFaturamentoMensal)).all()

    for fatura in faturas:
        assert abs(fatura.receita_faturada - fatura.receita_energia - fatura.tributos) <= Decimal(
            "0.01"
        )
        nao_paga = fatura.status_pagamento in ("em_aberto", "em_atraso")
        assert (fatura.data_pagamento is None) == nao_paga
        sem_atraso = fatura.status_pagamento in ("paga", "em_aberto")
        assert (fatura.dias_em_atraso is None) == sem_atraso
        if fatura.origem_kwh == "leitura":
            assert fatura.kwh_faturado == fatura.kwh_leitura
        else:
            assert fatura.kwh_leitura < 0
        if fatura.origem_kwh == "consumo_absoluto":
            assert fatura.kwh_faturado == -fatura.kwh_leitura
    # A amostra exercita todos os valores que o contrato prevê.
    assert {f.status_pagamento for f in faturas} == {
        "paga",
        "paga_com_atraso",
        "em_aberto",
        "em_atraso",
    }
    assert {f.origem_kwh for f in faturas} == {
        "leitura",
        "leitura_atual_troca_medidor",
        "consumo_absoluto",
    }


def test_revenue_bridge_follows_the_contract_checks(tmp_path: Path, engine: Engine) -> None:
    # As duas validações da decomposição no contrato, com as tolerâncias de arredondamento.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        linhas = session.scalars(select(ReceitaDecomposicao)).all()

    for linha in linhas:
        preco = linha.efeito_tarifa + linha.efeito_bandeira
        assert abs(linha.efeito_preco - preco) <= Decimal("0.01")
        efeitos = linha.efeito_preco + linha.efeito_volume + linha.efeito_mix
        assert abs(efeitos - (linha.receita_atual - linha.receita_base)) <= Decimal("0.02")
    # A amostra separa as linhas com GD e tem acréscimo de bandeira para mostrar.
    assert {linha.possui_gd for linha in linhas} == {True, False}
    assert all(linha.efeito_bandeira > 0 for linha in linhas)


def test_kpis_match_the_sum_of_the_billing_in_the_database(tmp_path: Path, engine: Engine) -> None:
    # A mesma conferência vale para a Gold real: o painel da diretoria tem que bater com a
    # soma do faturamento das UCs, mês a mês, depois de passar por CSV, carga e banco.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        billing = session.execute(
            select(
                FatoFaturamentoMensal.competencia,
                func.sum(FatoFaturamentoMensal.kwh_faturado),
                func.sum(FatoFaturamentoMensal.receita_faturada),
                func.sum(FatoFaturamentoMensal.receita_energia),
            ).group_by(FatoFaturamentoMensal.competencia)
        )
        kpis = session.execute(
            select(
                KpisMensais.competencia,
                KpisMensais.kwh_faturado,
                KpisMensais.receita_faturada,
                KpisMensais.receita_energia,
            )
        )
        assert set(kpis) == set(billing)


def test_queue_reasons_come_back_as_a_list_from_the_database(
    tmp_path: Path, engine: Engine
) -> None:
    # Ida e volta completa: lista → célula com ";" no CSV → text[] no banco → lista.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        stored = session.get(FilaSuspeita, "0005")

    assert stored is not None
    assert stored.motivos == SAMPLE_FILA[0].motivos


def test_does_not_overwrite_existing_csv_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "gold" / "gold_dim_uc.csv"
    existing.parent.mkdir()
    existing.write_text("conteúdo da Gold real", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--force"):
        write_sample(tmp_path / "gold", force=False)

    assert existing.read_text(encoding="utf-8") == "conteúdo da Gold real"
