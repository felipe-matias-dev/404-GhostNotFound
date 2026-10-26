from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from venergy_api.amostra import COMPETENCIAS, SAMPLE, SAMPLE_FILA, write_sample
from venergy_api.carga import load_gold
from venergy_api.models import (
    AtendimentoUc,
    ContinuidadeAlimentadorMensal,
    FatoFaturamentoMensal,
    FilaSuspeita,
    InspecaoUc,
    InterrupcaoUc,
    KpisMensais,
    KpisSegmentoMensal,
    MedidorUc,
    ReceitaDecomposicao,
    ReconciliacaoFaturamento,
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
        assert 0 <= fatura.receita_bandeira <= fatura.receita_energia
        if fatura.bandeira == "verde":
            assert fatura.receita_bandeira == 0
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
    assert {f.tipo_leitura for f in faturas} == {"real", "estimada"}
    assert {f.tipo_medidor for f in faturas} == {"eletromecanico", "eletronico", "smart"}
    # Só a primeira leitura de cada UC fica sem dias faturados.
    assert sum(f.dias_faturados is None for f in faturas) == len({f.cod_uc for f in faturas})


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


def test_segment_kpis_add_up_to_the_company_and_the_feeders(tmp_path: Path, engine: Engine) -> None:
    # Os checks da gold_kpis_segmento_mensal no contrato: somados por mês, os recortes batem
    # com o total da empresa e com a continuidade por alimentador.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    segmento = KpisSegmentoMensal

    with Session(engine) as session:
        recortes = session.execute(
            select(
                segmento.competencia,
                func.sum(segmento.kwh_faturado),
                func.sum(segmento.receita_faturada),
                func.sum(segmento.receita_energia),
            ).group_by(segmento.competencia)
        )
        empresa = session.execute(
            select(
                KpisMensais.competencia,
                KpisMensais.kwh_faturado,
                KpisMensais.receita_faturada,
                KpisMensais.receita_energia,
            )
        )
        assert set(recortes) == set(empresa)

        recortes_rede = session.execute(
            select(
                segmento.competencia,
                segmento.cod_alimentador,
                func.sum(segmento.n_uc),
                func.sum(segmento.horas_interrompidas),
                func.sum(segmento.n_interrupcoes),
            ).group_by(segmento.competencia, segmento.cod_alimentador)
        ).all()
        alimentadores = {
            (linha.competencia, linha.cod_alimentador): linha
            for linha in session.scalars(select(ContinuidadeAlimentadorMensal))
        }
        linhas = session.scalars(select(segmento)).all()

    assert len(recortes_rede) == len(alimentadores)
    for competencia, cod_alimentador, n_uc, horas, interrupcoes in recortes_rede:
        continuidade = alimentadores[(competencia, cod_alimentador)]
        assert n_uc == continuidade.n_uc
        # Horas são double precision: a ordem da soma muda a última casa.
        assert horas == pytest.approx(continuidade.horas_interrompidas)
        assert interrupcoes == continuidade.n_interrupcoes
    for linha in linhas:
        assert abs(linha.receita_faturada - linha.receita_energia - linha.tributos) <= Decimal(
            "0.01"
        )


def test_reconciliation_bridges_every_invoice_to_the_billing(
    tmp_path: Path, engine: Engine
) -> None:
    # Os quatro checks da gold_reconciliacao_faturamento no contrato: a ponte de cada mês
    # fecha e bate com a soma do fato por UC.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    fato = FatoFaturamentoMensal

    with Session(engine) as session:
        pontes = session.scalars(select(ReconciliacaoFaturamento)).all()
        somas_do_fato = {
            competencia: (faturada, energia, tributos, kwh)
            for competencia, faturada, energia, tributos, kwh in session.execute(
                select(
                    fato.competencia,
                    func.sum(fato.receita_faturada),
                    func.sum(fato.receita_energia),
                    func.sum(fato.tributos),
                    func.sum(fato.kwh_faturado),
                ).group_by(fato.competencia)
            )
        }

    centavo, um_wh = Decimal("0.01"), Decimal("0.001")
    assert len(pontes) == len(somas_do_fato)
    for ponte in pontes:
        receita = ponte.receita_faturada_cadastro + ponte.receita_faturada_orfas
        assert abs(ponte.receita_faturada_total - receita) <= centavo
        cadastro = ponte.receita_energia_cadastro + ponte.tributos_cadastro
        assert abs(ponte.receita_faturada_cadastro - cadastro) <= centavo
        correcoes = ponte.kwh_correcao_troca_medidor + ponte.kwh_correcao_sinal_invertido
        assert abs(ponte.kwh_faturado_total - ponte.kwh_leitura_total - correcoes) <= um_wh
        assert somas_do_fato[ponte.competencia] == (
            ponte.receita_faturada_cadastro,
            ponte.receita_energia_cadastro,
            ponte.tributos_cadastro,
            ponte.kwh_faturado_total,
        )
    # A amostra tem faturas órfãs e as duas correções de leitura para mostrar.
    assert all(ponte.n_faturas_orfas > 0 for ponte in pontes)
    assert any(ponte.kwh_correcao_troca_medidor > 0 for ponte in pontes)
    assert any(ponte.kwh_correcao_sinal_invertido > 0 for ponte in pontes)


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


def test_queue_positions_start_at_one_without_gaps() -> None:
    # O score é a posição no ranking (1 = mais suspeita), e não uma nota.
    positions = sorted(suspeita.score_suspeita for suspeita in SAMPLE_FILA)

    assert positions == list(range(1, len(SAMPLE_FILA) + 1))


def test_does_not_overwrite_existing_csv_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "gold" / "gold_dim_uc.csv"
    existing.parent.mkdir()
    existing.write_text("conteúdo da Gold real", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--force"):
        write_sample(tmp_path / "gold", force=False)

    assert existing.read_text(encoding="utf-8") == "conteúdo da Gold real"


def test_segment_invoice_and_reading_components_add_up_to_the_billing(
    tmp_path: Path, engine: Engine
) -> None:
    # Os componentes de faturas e leituras dos recortes saem do fato: somados por mês, são as
    # faturas do mês, e a situação é a da data de corte (DEC-027).
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    segmento = KpisSegmentoMensal
    fato = FatoFaturamentoMensal

    with Session(engine) as session:
        recortes = {
            competencia: valores
            for competencia, *valores in session.execute(
                select(
                    segmento.competencia,
                    func.sum(segmento.n_faturas),
                    func.sum(segmento.n_faturas_nao_pagas),
                    func.sum(segmento.valor_nao_pago),
                    func.sum(segmento.n_faturas_pagas_com_atraso),
                    func.sum(segmento.soma_dias_em_atraso),
                    func.sum(segmento.n_leituras),
                    func.sum(segmento.n_leituras_estimadas),
                    func.sum(segmento.receita_bandeira),
                ).group_by(segmento.competencia)
            )
        }
        nao_paga = fato.status_pagamento.in_(["em_aberto", "em_atraso"])
        faturas = {
            competencia: valores
            for competencia, *valores in session.execute(
                select(
                    fato.competencia,
                    func.count(),
                    func.count().filter(nao_paga),
                    func.coalesce(func.sum(fato.receita_faturada).filter(nao_paga), 0),
                    func.count().filter(fato.status_pagamento == "paga_com_atraso"),
                    func.coalesce(func.sum(fato.dias_em_atraso), 0),
                    func.count(),
                    func.count().filter(fato.tipo_leitura == "estimada"),
                    func.sum(fato.receita_bandeira),
                ).group_by(fato.competencia)
            )
        }

    assert recortes == faturas
    # A amostra exercita a situação das faturas e as leituras estimadas.
    assert sum(valores[1] for valores in recortes.values()) > 0
    assert sum(valores[5] for valores in recortes.values()) > 0


def test_occurrences_add_up_to_the_feeder_continuity(tmp_path: Path, engine: Engine) -> None:
    # Check do contrato: somadas por competência e alimentador, as ocorrências por UC dão as
    # horas e a contagem da continuidade.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        ocorrencias = {
            (competencia, cod_alimentador): (horas, quantidade)
            for competencia, cod_alimentador, horas, quantidade in session.execute(
                select(
                    InterrupcaoUc.competencia,
                    InterrupcaoUc.cod_alimentador,
                    func.sum(InterrupcaoUc.duracao_horas),
                    func.count(),
                ).group_by(InterrupcaoUc.competencia, InterrupcaoUc.cod_alimentador)
            )
        }
        continuidade = session.scalars(select(ContinuidadeAlimentadorMensal)).all()
        todas = session.scalars(select(InterrupcaoUc)).all()

    com_interrupcao = {
        (linha.competencia, linha.cod_alimentador): linha
        for linha in continuidade
        if linha.n_interrupcoes
    }
    assert set(ocorrencias) == set(com_interrupcao)
    for chave, (horas, quantidade) in ocorrencias.items():
        assert horas == pytest.approx(com_interrupcao[chave].horas_interrompidas)
        assert quantidade == com_interrupcao[chave].n_interrupcoes
    for ocorrencia in todas:
        assert ocorrencia.data_encerramento > ocorrencia.data_abertura
        assert ocorrencia.data_abertura.strftime("%Y-%m") == ocorrencia.competencia
    # A amostra tem ocorrência com e sem causa registrada (OCO-01).
    assert {o.causa is None for o in todas} == {True, False}


def test_calls_add_up_to_the_segment_components(tmp_path: Path, engine: Engine) -> None:
    # n_chamados, soma_notas e n_notas dos recortes saem dos chamados por UC: o que a UC 360
    # mostra e o que a diretoria soma são os mesmos chamados.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    segmento = KpisSegmentoMensal

    with Session(engine) as session:
        recortes = {
            competencia: (chamados, soma_notas, notas)
            for competencia, chamados, soma_notas, notas in session.execute(
                select(
                    segmento.competencia,
                    func.sum(segmento.n_chamados),
                    func.sum(segmento.soma_notas),
                    func.sum(segmento.n_notas),
                ).group_by(segmento.competencia)
            )
        }
        chamados = {
            competencia: (quantidade, soma_notas, notas)
            for competencia, quantidade, soma_notas, notas in session.execute(
                select(
                    AtendimentoUc.competencia,
                    func.count(),
                    func.sum(AtendimentoUc.nota_satisfacao),
                    func.count(AtendimentoUc.nota_satisfacao),
                ).group_by(AtendimentoUc.competencia)
            )
        }

    # Mês sem chamado fica de fora da tabela por chamado; no recorte, tem zero.
    for competencia, (quantidade, soma_notas, notas) in recortes.items():
        assert chamados.get(competencia, (0, None, 0)) == (quantidade, soma_notas, notas)


def test_current_meter_matches_the_last_reading_and_the_replacement(
    tmp_path: Path, engine: Engine
) -> None:
    # O medidor vigente é o da última leitura, e a troca de medidor do fato aparece como troca
    # no medidor da UC (UC 360 e fila de suspeitas).
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)
    ultima = COMPETENCIAS[-1]

    with Session(engine) as session:
        medidores = session.scalars(select(MedidorUc)).all()
        da_ultima_leitura = {
            cod_uc: tipo_medidor
            for cod_uc, tipo_medidor in session.execute(
                select(FatoFaturamentoMensal.cod_uc, FatoFaturamentoMensal.tipo_medidor).where(
                    FatoFaturamentoMensal.competencia == ultima
                )
            )
        }
        trocas = set(
            session.scalars(
                select(FatoFaturamentoMensal.cod_uc).where(
                    FatoFaturamentoMensal.origem_kwh == "leitura_atual_troca_medidor"
                )
            )
        )

    assert {m.cod_uc: m.tipo_medidor for m in medidores} == da_ultima_leitura
    assert {m.cod_uc for m in medidores if m.n_trocas} == trocas
    for medidor in medidores:
        assert (medidor.data_ultima_troca is None) == (medidor.n_trocas == 0)
        assert medidor.idade_anos > 0


def test_inspections_follow_the_contract_and_stay_out_of_the_queue(
    tmp_path: Path, engine: Engine
) -> None:
    # Pela DEC-030, a fila só tem UCs ainda não inspecionadas; e energia recuperada só existe
    # onde a inspeção confirmou irregularidade.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        inspecoes = session.scalars(select(InspecaoUc)).all()
        fila = set(session.scalars(select(FilaSuspeita.cod_uc)))

    assert {i.cod_uc for i in inspecoes}.isdisjoint(fila)
    assert {i.resultado for i in inspecoes} == {"irregularidade_confirmada", "sem_irregularidade"}
    for inspecao in inspecoes:
        assert inspecao.data_inspecao.strftime("%Y-%m") == inspecao.competencia
        confirmada = inspecao.resultado == "irregularidade_confirmada"
        assert (inspecao.tipo_irregularidade is not None) == confirmada
        assert (inspecao.kwh_recuperado > 0) == confirmada
