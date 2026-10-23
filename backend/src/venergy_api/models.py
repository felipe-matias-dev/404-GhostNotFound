"""Tabelas do banco local: as da Gold (só leitura) e as da aplicação (ordens de inspeção)."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    ARRAY,
    DateTime,
    Double,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from venergy_api.database import Base
from venergy_api.ordens import STATUS_ATIVOS, ResultadoOrdem, StatusOrdem

# Tipos money e energy_kwh do contrato da Gold. Numeric, nunca float (DEC-010): o agente
# soma direto em SQL, e a soma exata faz o número dele bater com o do portal.
_MONEY = Numeric(14, 2)
_ENERGY = Numeric(16, 3)


class DimUc(Base):
    """Dimensão de unidades consumidoras, uma linha por UC, como em contracts/gold_schema.yaml."""

    __tablename__ = "gold_dim_uc"
    # Schema gold: recarregável a partir dos CSVs e o único que o agente de IA consegue ler.
    __table_args__ = {"schema": "gold"}

    # Texto, e não número: o código da UC é um identificador e pode ter zeros à esquerda.
    cod_uc: Mapped[str] = mapped_column(primary_key=True)
    municipio: Mapped[str]
    bairro: Mapped[str]
    classe: Mapped[str]
    # As 5 classes do cadastro, ao lado da classe de consumo: separa Comercial de Poder
    # Público, que dividem o B3 (DEC-023).
    classe_cadastro: Mapped[str]
    cod_alimentador: Mapped[str]
    possui_gd: Mapped[bool]
    # O Postgres arredonda para as 3 casas do tipo de energia. Vazio, e não zero, para a UC
    # sem nenhuma leitura: sem leitura não há média (DEC-023).
    consumo_medio_kwh_12m: Mapped[Decimal | None] = mapped_column(_ENERGY)
    # Só o mascarado chega à Gold, para o atendente confirmar a identidade na UC 360. São
    # sensitive no contrato: ficam fora das views do agente (DEC-022).
    titular_mascarado: Mapped[str | None]
    documento_mascarado: Mapped[str | None]
    # Double, o tipo "ratio" do contrato. Potência de pico em kWp, como vem da origem.
    potencia_kwp: Mapped[float | None] = mapped_column(Double)


class FatoFaturamentoMensal(Base):
    """Faturamento por UC e competência: base dos KPIs, da tela de Receita e da UC 360."""

    __tablename__ = "gold_fato_faturamento_mensal"
    __table_args__ = {"schema": "gold"}

    # Sem chave estrangeira física para gold_dim_uc: a carga recria tabela por tabela, e o
    # contrato deixa essa checagem para a qualidade de dados (foreign_keys: logical).
    cod_uc: Mapped[str] = mapped_column(primary_key=True)
    competencia: Mapped[str] = mapped_column(primary_key=True)
    kwh_faturado: Mapped[Decimal] = mapped_column(_ENERGY)
    # O consumo da leitura antes da correção, e a regra que gerou o kwh_faturado: rastreia
    # a troca de medidor e o sinal invertido até a origem (DEC-023).
    kwh_leitura: Mapped[Decimal] = mapped_column(_ENERGY)
    origem_kwh: Mapped[str]
    # Total da fatura = energia + tributos. A energia é a base provisória do PVM (DEC-023).
    receita_faturada: Mapped[Decimal] = mapped_column(_MONEY)
    receita_energia: Mapped[Decimal] = mapped_column(_MONEY)
    tributos: Mapped[Decimal] = mapped_column(_MONEY)
    receita_arrecadada: Mapped[Decimal | None] = mapped_column(_MONEY)
    tarifa_media: Mapped[float | None] = mapped_column(Double)
    bandeira: Mapped[str | None]
    # Uma fatura por UC e competência (conferido pelo time de Dados), então a situação da
    # fatura mora no fato. O status é calculado na Gold, e não aqui.
    data_vencimento: Mapped[date]
    data_pagamento: Mapped[date | None]
    status_pagamento: Mapped[str]
    dias_em_atraso: Mapped[int | None]


class ReceitaDecomposicao(Base):
    """Variação da receita entre dois períodos, por município, bairro, classe e GD."""

    __tablename__ = "gold_receita_decomposicao"
    __table_args__ = {"schema": "gold"}

    periodo_base: Mapped[str] = mapped_column(primary_key=True)
    periodo_atual: Mapped[str] = mapped_column(primary_key=True)
    municipio: Mapped[str] = mapped_column(primary_key=True)
    bairro: Mapped[str] = mapped_column(primary_key=True)
    classe: Mapped[str] = mapped_column(primary_key=True)
    # Na chave para isolar o efeito da geração própria: é o efeito volume das linhas com GD,
    # sem coluna de efeito própria (DEC-023).
    possui_gd: Mapped[bool] = mapped_column(primary_key=True)
    receita_base: Mapped[Decimal] = mapped_column(_MONEY)
    receita_atual: Mapped[Decimal] = mapped_column(_MONEY)
    # efeito_preco = efeito_tarifa (reajuste) + efeito_bandeira (acréscimo da bandeira).
    efeito_preco: Mapped[Decimal] = mapped_column(_MONEY)
    efeito_tarifa: Mapped[Decimal] = mapped_column(_MONEY)
    efeito_bandeira: Mapped[Decimal] = mapped_column(_MONEY)
    efeito_volume: Mapped[Decimal] = mapped_column(_MONEY)
    efeito_mix: Mapped[Decimal] = mapped_column(_MONEY)


class KpisMensais(Base):
    """Indicadores executivos por competência: o painel da diretoria."""

    __tablename__ = "gold_kpis_mensais"
    __table_args__ = {"schema": "gold"}

    competencia: Mapped[str] = mapped_column(primary_key=True)
    kwh_faturado: Mapped[Decimal] = mapped_column(_ENERGY)
    receita_faturada: Mapped[Decimal] = mapped_column(_MONEY)
    receita_energia: Mapped[Decimal] = mapped_column(_MONEY)
    dec: Mapped[float | None] = mapped_column(Double)
    fec: Mapped[float | None] = mapped_column(Double)
    n_chamados: Mapped[int | None]
    satisfacao_media: Mapped[float | None] = mapped_column(Double)


class ContinuidadeAlimentadorMensal(Base):
    """DEC e FEC por alimentador e competência: a tela de continuidade e o ranking."""

    __tablename__ = "gold_continuidade_alimentador_mensal"
    __table_args__ = {"schema": "gold"}

    cod_alimentador: Mapped[str] = mapped_column(primary_key=True)
    competencia: Mapped[str] = mapped_column(primary_key=True)
    dec: Mapped[float] = mapped_column(Double)
    fec: Mapped[float] = mapped_column(Double)
    n_uc: Mapped[int]
    n_interrupcoes: Mapped[int]
    horas_interrompidas: Mapped[float] = mapped_column(Double)


class FilaSuspeita(Base):
    """UCs suspeitas de perda não técnica: de onde o gerente de perdas gera as OIs."""

    __tablename__ = "gold_fila_suspeitas"
    __table_args__ = {"schema": "gold"}

    cod_uc: Mapped[str] = mapped_column(primary_key=True)
    score_suspeita: Mapped[float] = mapped_column(Double)
    # Lista nativa do Postgres (text[]), e não uma tabela de motivos à parte: os motivos só
    # são lidos junto com a UC, e o agente consegue filtrar com ANY() no mesmo SELECT.
    motivos: Mapped[list[str]] = mapped_column(ARRAY(Text))
    kwh_recuperavel_est: Mapped[Decimal | None] = mapped_column(_ENERGY)


def _enum_como_texto(enum: type[StrEnum], nome_check: str) -> Enum:
    # VARCHAR com CHECK, e não ENUM nativo do Postgres: sem migrações, acrescentar um valor
    # a um ENUM nativo exige ALTER TYPE à mão; o CHECK é recriado junto com a tabela.
    # O nome é explícito porque o padrão vem do enum, e duas colunas com o mesmo enum na
    # mesma tabela gerariam dois CHECK com o mesmo nome, que o Postgres recusa.
    return Enum(enum, name=nome_check, native_enum=False, create_constraint=True, length=30)


# Valores fixos do código, nunca entrada de usuário: montar o SQL do índice com eles é seguro.
_FILTRO_ATIVAS = "status IN ({})".format(", ".join(f"'{s}'" for s in sorted(STATUS_ATIVOS)))


class OrdemInspecao(Base):
    """Pedido de vistoria em campo para uma UC, gerado pelo gerente de perdas a partir da fila."""

    __tablename__ = "ordem_inspecao"
    __table_args__ = (
        # No máximo uma OI ativa por UC: evita mandar duas equipes ao mesmo imóvel. Fica no
        # banco, e não só no Python, para valer também com dois cliques simultâneos.
        Index(
            "uq_ordem_inspecao_uc_ativa",
            "cod_uc",
            unique=True,
            postgresql_where=text(_FILTRO_ATIVAS),
        ),
        # Schema app: dados digitados no portal. O loader da Gold nunca apaga este schema.
        {"schema": "app"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sem chave estrangeira para gold_dim_uc: a carga da Gold apaga e reinsere as UCs, e uma
    # FK travaria a carga ou apagaria as OIs junto. A existência da UC é checada na API.
    cod_uc: Mapped[str] = mapped_column(index=True)
    status: Mapped[StatusOrdem] = mapped_column(
        _enum_como_texto(StatusOrdem, "ck_ordem_inspecao_status"), default=StatusOrdem.GERADA
    )
    resultado: Mapped[ResultadoOrdem | None] = mapped_column(
        _enum_como_texto(ResultadoOrdem, "ck_ordem_inspecao_resultado")
    )
    observacao: Mapped[str | None]
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    eventos: Mapped[list["OrdemEvento"]] = relationship(
        back_populates="ordem", order_by="OrdemEvento.id"
    )


class OrdemEvento(Base):
    """Uma mudança de status de uma OI: o histórico de quem passou por onde e quando."""

    __tablename__ = "ordem_evento"
    __table_args__ = {"schema": "app"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ordem_id: Mapped[int] = mapped_column(ForeignKey("app.ordem_inspecao.id"), index=True)
    # Vazio no evento de criação, quando a OI ainda não tinha status.
    status_anterior: Mapped[StatusOrdem | None] = mapped_column(
        _enum_como_texto(StatusOrdem, "ck_ordem_evento_status_anterior")
    )
    status_novo: Mapped[StatusOrdem] = mapped_column(
        _enum_como_texto(StatusOrdem, "ck_ordem_evento_status_novo")
    )
    observacao: Mapped[str | None]
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ordem: Mapped[OrdemInspecao] = relationship(back_populates="eventos")
