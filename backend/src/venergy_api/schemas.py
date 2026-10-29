"""Contrato dos dados: o formato que a Gold entrega e que a API recebe e devolve."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_validator,
    model_validator,
)
from venergy_agent.domain.answer import AnswerStatus, Confidence

from venergy_api.ordens import ResultadoOrdem, StatusOrdem

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Exato na carga e no banco; número no JSON. Sem o serializador, o Pydantic mandaria o
# Decimal como texto ("152.400") e o frontend teria que converter em toda tela.
ExactNumber = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

# Chaves e domínios compartilhados do contrato da Gold (conventions.shared_keys).
# Competência em texto AAAA-MM (DEC-011): não depende de como CSV, Delta e Postgres leem datas.
Competencia = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
Classe = Literal["B1", "B2", "B3", "A4"]
ClasseCadastro = Literal["Residencial", "Comercial", "Industrial", "Rural", "Poder Público"]
Bandeira = Literal["verde", "amarela", "vermelha_p1", "vermelha_p2"]
OrigemKwh = Literal["leitura", "leitura_atual_troca_medidor", "consumo_absoluto"]
StatusPagamento = Literal["paga", "paga_com_atraso", "em_aberto", "em_atraso"]
TipoLeitura = Literal["real", "estimada"]
TipoMedidor = Literal["eletromecanico", "eletronico", "smart"]
TipoMedidorRecorte = Literal["eletromecanico", "eletronico", "smart", "sem_medidor"]
ResultadoInspecao = Literal["irregularidade_confirmada", "sem_irregularidade"]
ModalidadeGd = Literal["geracao_propria_uc", "autoconsumo_remoto", "geracao_compartilhada"]
Tendencia = Literal["subiu", "estavel", "caiu", "sem_comparacao"]

# Um período da decomposição, no formato do contrato: AAAA-MM/AAAA-MM, da primeira à última
# competência.
PeriodoDecomposicao = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, pattern=r"^\d{4}-(0[1-9]|1[0-2])/\d{4}-(0[1-9]|1[0-2])$"
    ),
]

# Teto por pedido na ordem da capacidade mensal da equipe de campo (~200 inspeções):
# acima disso é engano de seleção, e o limite evita um pedido gigante travar o banco.
MAX_ORDENS_POR_PEDIDO = 200


class DimUcSchema(BaseModel):
    # Permite montar o schema direto de um objeto do banco (models.DimUc).
    model_config = ConfigDict(from_attributes=True)

    cod_uc: RequiredText
    municipio: RequiredText
    bairro: RequiredText
    classe: Classe
    classe_cadastro: ClasseCadastro
    cod_alimentador: RequiredText
    possui_gd: bool
    # Sem valor padrão de propósito: a coluna precisa existir no CSV, mesmo vazia.
    consumo_medio_kwh_12m: Annotated[ExactNumber, Field(ge=0)] | None
    titular_mascarado: RequiredText | None
    documento_mascarado: RequiredText | None
    potencia_kwp: float | None
    data_ligacao: date
    data_conexao_gd: date | None
    modalidade_gd: ModalidadeGd | None
    energia_injetada_kwh_mes: Annotated[ExactNumber, Field(ge=0)] | None


class FaturamentoMensalSchema(BaseModel):
    """Faturamento de uma UC numa competência."""

    cod_uc: RequiredText
    competencia: Competencia
    kwh_faturado: ExactNumber
    # Pode ser negativo: é a leitura antes da correção.
    kwh_leitura: ExactNumber
    origem_kwh: OrigemKwh
    receita_faturada: ExactNumber
    receita_energia: ExactNumber
    tributos: ExactNumber
    receita_arrecadada: ExactNumber | None
    # Vazia quando kwh_faturado é zero (ex.: painel solar compensando todo o consumo).
    tarifa_media: float | None
    bandeira: Bandeira | None
    data_vencimento: date
    data_pagamento: date | None
    status_pagamento: StatusPagamento
    dias_em_atraso: int | None
    receita_bandeira: Annotated[ExactNumber, Field(ge=0)]
    tipo_leitura: TipoLeitura
    tipo_medidor: TipoMedidor
    dias_faturados: Annotated[int, Field(ge=1)] | None


class ReceitaDecomposicaoSchema(BaseModel):
    """Variação da receita entre dois períodos, separada em efeito preço, volume e mix."""

    periodo_base: PeriodoDecomposicao
    periodo_atual: PeriodoDecomposicao
    municipio: RequiredText
    bairro: RequiredText
    classe: Classe
    possui_gd: bool
    receita_base: ExactNumber
    receita_atual: ExactNumber
    # Sem limite de sinal: queda de preço ou de volume é efeito negativo.
    efeito_preco: ExactNumber
    efeito_tarifa: ExactNumber
    efeito_bandeira: ExactNumber
    efeito_volume: ExactNumber
    efeito_mix: ExactNumber


class KpisMensaisSchema(BaseModel):
    """Indicadores executivos de uma competência."""

    model_config = ConfigDict(from_attributes=True)

    competencia: Competencia
    kwh_faturado: ExactNumber
    # Total da fatura (com tributos) e só a energia: a variação percentual é a mesma, mas os
    # valores absolutos não (DEC-023).
    receita_faturada: ExactNumber
    receita_energia: ExactNumber
    dec: float | None
    fec: float | None
    n_chamados: int | None
    satisfacao_media: float | None


def _inicio_ate_o_fim(inicio: str | None, fim: str | None) -> None:
    # Na validação do schema, e não na rota: o erro sai no mesmo formato 422 do formato
    # inválido, e o client do frontend trata um só. Texto AAAA-MM compara na ordem do calendário.
    if inicio and fim and inicio > fim:
        raise ValueError(f"O início do período ({inicio}) é depois do fim ({fim})")


class PeriodoSchema(BaseModel):
    """Recorte de competências, inclusivo nas duas pontas. Sem limites, a série inteira."""

    inicio: Competencia | None = None
    fim: Competencia | None = None

    @model_validator(mode="after")
    def inicio_ate_o_fim(self) -> "PeriodoSchema":
        _inicio_ate_o_fim(self.inicio, self.fim)
        return self


class ComparacaoFiltroSchema(BaseModel):
    """Dois períodos e, se quiser, o segmento: município, bairro e classe."""

    base_inicio: Competencia
    base_fim: Competencia
    atual_inicio: Competencia
    atual_fim: Competencia
    municipio: RequiredText | None = None
    bairro: RequiredText | None = None
    classe: Classe | None = None

    @model_validator(mode="after")
    def periodos_e_segmento_validos(self) -> "ComparacaoFiltroSchema":
        _inicio_ate_o_fim(self.base_inicio, self.base_fim)
        _inicio_ate_o_fim(self.atual_inicio, self.atual_fim)
        # O mesmo nome de bairro pode existir em dois municípios: somar os dois daria um
        # número que ninguém pediu.
        if self.bairro and not self.municipio:
            raise ValueError("Informe o município junto com o bairro")
        return self


class TotaisPeriodoSchema(BaseModel):
    """kWh e receita faturados, somados num período."""

    inicio: Competencia
    fim: Competencia
    kwh_faturado: ExactNumber
    receita_faturada: ExactNumber


class ComparacaoReceitaSchema(BaseModel):
    """Totais de dois períodos e quanto o atual variou sobre a base."""

    base: TotaisPeriodoSchema
    atual: TotaisPeriodoSchema
    variacao_kwh: ExactNumber
    variacao_receita: ExactNumber
    # Em %, vazia quando a base é zero (ex.: bairro sem faturamento no período base): não
    # existe variação percentual sobre nada.
    variacao_kwh_pct: float | None
    variacao_receita_pct: float | None


class ParPeriodosSchema(BaseModel):
    """Um par de períodos que a Gold gravou na decomposição (DEC-028)."""

    periodo_base: PeriodoDecomposicao
    periodo_atual: PeriodoDecomposicao


class DecomposicaoFiltroSchema(BaseModel):
    """Onde está o Henrique no drill-down: o nível da resposta é o próximo abaixo do filtro."""

    # Obrigatório: a Gold guarda centenas de pares, e a ponte de um par só faz sentido sozinha.
    # Os pares válidos vêm de /receita/decomposicao/periodos.
    periodo_base: PeriodoDecomposicao
    periodo_atual: PeriodoDecomposicao
    municipio: RequiredText | None = None
    bairro: RequiredText | None = None
    classe: Classe | None = None

    @model_validator(mode="after")
    def bairro_com_municipio(self) -> "DecomposicaoFiltroSchema":
        if self.bairro and not self.municipio:
            raise ValueError("Informe o município junto com o bairro")
        return self


class DecomposicaoLinhaSchema(BaseModel):
    """Um segmento da ponte de receita: quanto variou e quanto disso foi preço, volume e mix."""

    nivel: Literal["municipio", "bairro", "classe"]
    segmento: RequiredText
    periodo_base: RequiredText
    periodo_atual: RequiredText
    receita_base: ExactNumber
    receita_atual: ExactNumber
    variacao_receita: ExactNumber
    efeito_preco: ExactNumber
    efeito_tarifa: ExactNumber
    efeito_bandeira: ExactNumber
    efeito_volume: ExactNumber
    efeito_mix: ExactNumber


class InsightReceitaSchema(BaseModel):
    """O insight de IA da tela de Receita e as métricas que sustentam cada número do texto."""

    # Vazio quando o redator recusa o texto (número fora das métricas) ou falha: a tela
    # aparece sem insight. Também vazio, sem chamar o modelo, se o recorte não tem segmentos.
    texto: str | None
    metricas: dict[str, Any] | None


class KpisSegmentoMensalSchema(BaseModel):
    """Componentes somáveis de um recorte (município, bairro, classe e GD) numa competência."""

    competencia: Competencia
    municipio: RequiredText
    bairro: RequiredText
    classe_cadastro: ClasseCadastro
    classe: Classe
    possui_gd: bool
    cod_alimentador: RequiredText
    tipo_medidor: TipoMedidorRecorte
    n_uc: int
    kwh_faturado: ExactNumber
    receita_faturada: ExactNumber
    receita_energia: ExactNumber
    tributos: ExactNumber
    receita_arrecadada: ExactNumber | None
    horas_interrompidas: float
    n_interrupcoes: int
    n_chamados: int
    soma_notas: float | None
    n_notas: int
    receita_bandeira: ExactNumber
    n_faturas: int
    n_faturas_nao_pagas: int
    valor_nao_pago: ExactNumber
    n_faturas_pagas_com_atraso: int
    soma_dias_em_atraso: int
    n_leituras: int
    n_leituras_estimadas: int


class ReconciliacaoFaturamentoSchema(BaseModel):
    """De onde vem a receita e a energia de uma competência, parcela por parcela."""

    competencia: Competencia
    receita_faturada_total: ExactNumber
    receita_faturada_orfas: ExactNumber
    receita_faturada_cadastro: ExactNumber
    tributos_cadastro: ExactNumber
    receita_energia_cadastro: ExactNumber
    n_faturas_orfas: int
    kwh_leitura_total: ExactNumber
    kwh_correcao_troca_medidor: ExactNumber
    kwh_correcao_sinal_invertido: ExactNumber
    kwh_faturado_total: ExactNumber


class ContinuidadeAlimentadorMensalSchema(BaseModel):
    """DEC e FEC de um alimentador numa competência."""

    cod_alimentador: RequiredText
    competencia: Competencia
    dec: float
    fec: float
    n_uc: int
    n_interrupcoes: int
    horas_interrompidas: float


class InterrupcaoUcSchema(BaseModel):
    """Uma interrupção que afetou uma UC."""

    model_config = ConfigDict(from_attributes=True)

    cod_ocorrencia: RequiredText
    cod_uc: RequiredText
    cod_alimentador: RequiredText
    competencia: Competencia
    data_abertura: datetime
    data_encerramento: datetime
    duracao_horas: Annotated[float, Field(gt=0)]
    tipo: RequiredText
    causa: RequiredText | None


class AtendimentoUcSchema(BaseModel):
    """Um chamado de atendimento de uma UC."""

    model_config = ConfigDict(from_attributes=True)

    protocolo: RequiredText
    cod_uc: RequiredText
    competencia: Competencia
    data_abertura: datetime
    data_fechamento: datetime
    canal: RequiredText
    assunto: RequiredText
    subassunto: RequiredText | None
    nota_satisfacao: Annotated[float, Field(ge=1, le=5)] | None


class MedidorUcSchema(BaseModel):
    """O medidor vigente de uma UC e quantas vezes ele já foi trocado."""

    model_config = ConfigDict(from_attributes=True)

    cod_uc: RequiredText
    cod_medidor: RequiredText
    tipo_medidor: TipoMedidor
    modelo: RequiredText | None
    data_instalacao: date
    idade_anos: Annotated[float, Field(ge=0)]
    n_trocas: Annotated[int, Field(ge=0)]
    data_ultima_troca: date | None


class InspecaoUcSchema(BaseModel):
    """Uma inspeção de campo numa UC e o que ela encontrou."""

    model_config = ConfigDict(from_attributes=True)

    cod_inspecao: RequiredText
    cod_uc: RequiredText
    data_inspecao: date
    competencia: Competencia
    resultado: ResultadoInspecao
    tipo_irregularidade: RequiredText | None
    kwh_recuperado: Annotated[ExactNumber, Field(ge=0)]


class ConsumoMesSchema(BaseModel):
    """Um mês do consumo da UC ao lado do mesmo mês do ano anterior."""

    competencia: Competencia
    # Vazio, e não zero, no mês sem fatura: zero diria que a UC não consumiu.
    kwh_faturado: ExactNumber | None
    kwh_ano_anterior: ExactNumber | None
    # Mostram por que a conta mudou sem o consumo mudar: bandeira mais cara ou mais dias.
    receita_faturada: ExactNumber | None
    bandeira: Bandeira | None
    dias_faturados: int | None


class ConsumoUcSchema(BaseModel):
    """Os 12 meses até a última competência da Gold, contra o mesmo período do ano anterior."""

    # Vazia só se a Gold não tem nenhuma fatura.
    referencia: Competencia | None
    meses: list[ConsumoMesSchema]
    kwh_12m: ExactNumber
    kwh_12m_ano_anterior: ExactNumber
    # Em %. A de 12 meses compara só os meses com fatura nos dois anos (`meses_comparados`) e
    # fica vazia sem nenhum par ou com a base em zero; a do último mês fica vazia se faltar a
    # fatura de um dos dois meses ou se a base for zero. Os totais acima somam tudo o que foi
    # faturado.
    variacao_12m_pct: float | None
    meses_comparados: int
    variacao_ultimo_mes_pct: float | None
    # A resposta para "minha conta veio alta": o último mês contra o mesmo mês do ano anterior.
    tendencia: Tendencia


class FaturaNaoPagaSchema(BaseModel):
    """Uma fatura da UC que ainda não foi paga."""

    model_config = ConfigDict(from_attributes=True)

    competencia: Competencia
    receita_faturada: ExactNumber
    data_vencimento: date
    status_pagamento: Literal["em_aberto", "em_atraso"]
    # Vazio na fatura em aberto: ainda está no prazo.
    dias_em_atraso: int | None


class FaturasNaoPagasSchema(BaseModel):
    """As faturas não pagas da UC, a mais antiga primeiro, e quanto a UC deve no total."""

    quantidade: int
    valor_total: ExactNumber
    itens: list[FaturaNaoPagaSchema]


class Uc360Schema(BaseModel):
    """Tudo o que o atendente precisa de uma UC numa tela só."""

    cadastro: DimUcSchema
    consumo: ConsumoUcSchema
    faturas_nao_pagas: FaturasNaoPagasSchema
    # Vazio na UC sem medidor instalado: não há linha em gold_medidor_uc.
    medidor: MedidorUcSchema | None
    # Do mais recente para o mais antigo: o atendente olha primeiro o que aconteceu há pouco.
    interrupcoes: list[InterrupcaoUcSchema]
    atendimentos: list[AtendimentoUcSchema]
    inspecoes: list[InspecaoUcSchema]


class ContinuidadeSerieFiltroSchema(PeriodoSchema):
    """Período da série e, se quiser, só alguns alimentadores (o parâmetro se repete na URL)."""

    cod_alimentador: list[RequiredText] = Field(default_factory=list)


class IndicesContinuidadeSchema(BaseModel):
    """DEC e FEC de um período, calculados sobre os componentes somados."""

    # Nulos quando não há UC atendida no período: sem divisor, não existe índice.
    dec: float | None
    fec: float | None
    horas_interrompidas: float
    n_interrupcoes: int
    # Média mensal das UCs atendidas, o divisor do DEC e do FEC de um período.
    n_uc_medio: float | None


class RankingFiltroSchema(BaseModel):
    """Período do ranking, obrigatório: a média mensal só existe sobre um período."""

    inicio: Competencia
    fim: Competencia
    criterio: Literal["dec", "fec"] = "dec"

    @model_validator(mode="after")
    def inicio_ate_o_fim(self) -> "RankingFiltroSchema":
        _inicio_ate_o_fim(self.inicio, self.fim)
        return self


class RankingAlimentadorSchema(IndicesContinuidadeSchema):
    cod_alimentador: RequiredText


class RankingContinuidadeSchema(BaseModel):
    """Os alimentadores do pior para o melhor, e quantos meses entraram na média."""

    inicio: Competencia
    fim: Competencia
    criterio: Literal["dec", "fec"]
    # Meses com dado dentro do período: o divisor da média mensal de UCs. Zero, sem dados.
    n_meses: int
    alimentadores: list[RankingAlimentadorSchema]


class RecortesFiltroSchema(BaseModel):
    """Período e onde o gerente está no drill-down: o nível da resposta é o próximo abaixo."""

    inicio: Competencia
    fim: Competencia
    criterio: Literal["dec", "fec"] = "dec"
    municipio: RequiredText | None = None
    bairro: RequiredText | None = None
    classe: Classe | None = None

    @model_validator(mode="after")
    def periodo_e_bairro_validos(self) -> "RecortesFiltroSchema":
        _inicio_ate_o_fim(self.inicio, self.fim)
        if self.bairro and not self.municipio:
            raise ValueError("Informe o município junto com o bairro")
        return self


class RecorteContinuidadeSchema(IndicesContinuidadeSchema):
    segmento: RequiredText


class RecortesContinuidadeSchema(BaseModel):
    """DEC e FEC do nível abaixo do filtro, do pior para o melhor."""

    inicio: Competencia
    fim: Competencia
    criterio: Literal["dec", "fec"]
    nivel: Literal["municipio", "bairro", "alimentador"]
    n_meses: int
    recortes: list[RecorteContinuidadeSchema]


class FilaSuspeitaSchema(BaseModel):
    """Uma UC suspeita de perda não técnica, com o porquê e o quanto vale inspecionar."""

    cod_uc: RequiredText
    # Posição no ranking: 1 = mais suspeita.
    score_suspeita: Annotated[int, Field(ge=1)]
    # Motivos legíveis para o gerente de perdas decidir; no CSV, separados por ";".
    motivos: list[RequiredText]
    kwh_recuperavel_est: ExactNumber | None


class FilaFiltroSchema(BaseModel):
    """Página da fila e, se quiser, só as UCs que ainda não têm ordem de inspeção ativa."""

    pagina: Annotated[int, Field(ge=1)] = 1
    # Mesmo teto do pedido de ordens: uma página inteira cabe num único pedido.
    tamanho: Annotated[int, Field(ge=1, le=MAX_ORDENS_POR_PEDIDO)] = 50
    sem_ordem_ativa: bool = False


class OrdemAtivaSchema(BaseModel):
    """A ordem de inspeção que já ocupa a UC (gerada ou em campo)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusOrdem


class FilaItemSchema(FilaSuspeitaSchema):
    """Uma UC da fila e a ordem ativa dela, para a tela não oferecer o que daria 409."""

    ordem_ativa: OrdemAtivaSchema | None


class FilaPaginaSchema(BaseModel):
    """Uma página da fila pela posição no ranking, e quantas UCs a fila tem no filtro."""

    itens: list[FilaItemSchema]
    total: int
    pagina: int
    tamanho: int


class CriarOrdensSchema(BaseModel):
    """UCs escolhidas na fila de suspeitas; gera uma OI para cada uma."""

    cod_ucs: list[RequiredText] = Field(min_length=1, max_length=MAX_ORDENS_POR_PEDIDO)

    @field_validator("cod_ucs")
    @classmethod
    def sem_repetidas(cls, cod_ucs: list[str]) -> list[str]:
        # Repetir a UC no mesmo pedido geraria duas OIs ativas para ela: recusa já na entrada.
        repetidas = sorted({cod for cod in cod_ucs if cod_ucs.count(cod) > 1})
        if repetidas:
            raise ValueError(f"UCs repetidas no pedido: {', '.join(repetidas)}")
        return cod_ucs


class AtualizarOrdemSchema(BaseModel):
    """Mudança de status de uma OI. Cancelar é mudar para CANCELADA."""

    status: StatusOrdem
    resultado: ResultadoOrdem | None = None
    # O que a equipe viu em campo ou o motivo do cancelamento. Teto para não virar depósito
    # de texto: anexos e laudos ficam fora do escopo.
    observacao: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
        | None
    ) = None

    @model_validator(mode="after")
    def resultado_so_ao_concluir(self) -> "AtualizarOrdemSchema":
        # Erro de preenchimento, não de estado da OI: por isso 422 aqui, e não 409.
        if self.status == StatusOrdem.CONCLUIDA and self.resultado is None:
            raise ValueError("Informe o resultado da inspeção para concluir a ordem")
        if self.status != StatusOrdem.CONCLUIDA and self.resultado is not None:
            raise ValueError("O resultado só é registrado ao concluir a ordem")
        return self


class OrdemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cod_uc: str
    status: StatusOrdem
    resultado: ResultadoOrdem | None
    observacao: str | None
    criada_em: datetime
    atualizada_em: datetime


class EventoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_anterior: StatusOrdem | None
    status_novo: StatusOrdem
    observacao: str | None
    # Login de quem agiu; vazio nos eventos de antes do login (DEC-050).
    autor_login: str | None
    ocorrido_em: datetime


class OrdemDetalheSchema(OrdemSchema):
    """A OI com o histórico de mudanças de status, do mais antigo ao mais recente."""

    eventos: list[EventoSchema]


# A entrada é limitada na API, antes de chegar ao agente. O teto de 500 caracteres da pergunta
# continua sendo do agente; este é folgado, só para não aceitar um corpo gigante.
MAX_PERGUNTA_IA = 2000
MAX_SESSAO_IA = 100


class PerguntaIaSchema(BaseModel):
    """Pergunta em português para o agente de IA, dentro de uma conversa."""

    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_PERGUNTA_IA)
    ]
    session_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SESSAO_IA)
    ]


class RespostaIaSchema(BaseModel):
    """A resposta do agente (AgentAnswer) mais o id do registro de auditoria dela."""

    model_config = ConfigDict(from_attributes=True)

    # O registro é lido pelo atributo id; no JSON o campo se chama audit_id, para o portal
    # montar o link do painel de auditoria sem confundir com outros ids.
    audit_id: int = Field(validation_alias="id")
    answer: str
    status: AnswerStatus
    sql: str | None
    # Amostra: as colunas variam a cada pergunta. Decimal e data chegam como texto.
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    confidence: Confidence
    sources: list[str]
    assumptions: list[str]
    clarification: str | None
    refused_reason: str | None
    request_id: str
    model: str
    prompt_version: str
    latency_ms: int


class AuditoriaIaSchema(RespostaIaSchema):
    """O registro completo da auditoria: a resposta com a pergunta e o momento em que veio."""

    pergunta: str
    session_id: str
    criado_em: datetime


class ErroSchema(BaseModel):
    """Corpo das respostas de erro do FastAPI (HTTPException), documentado no OpenAPI."""

    detail: str


class IndicadoresComparacaoFiltroSchema(ComparacaoFiltroSchema):
    """Dois períodos e, se quiser, o recorte: os mesmos filtros da comparação de receita."""


class IndicadoresJanelasFiltroSchema(BaseModel):
    """Tamanho da janela corrida, em competências, e o recorte opcional."""

    meses: int = Field(default=12, ge=1, le=24)
    municipio: RequiredText | None = None
    bairro: RequiredText | None = None
    classe: Classe | None = None

    @model_validator(mode="after")
    def recorte_valido(self) -> "IndicadoresJanelasFiltroSchema":
        if self.bairro and not self.municipio:
            raise ValueError("Informe o município junto com o bairro")
        return self


class IndicadoresPeriodoSchema(BaseModel):
    """Os indicadores da diretoria somados num período, todos calculados no banco."""

    inicio: Competencia
    fim: Competencia
    # Competências com dado na tabela inteira dentro do período: o divisor de n_uc_medio.
    n_meses: int
    receita_faturada: ExactNumber
    receita_energia: ExactNumber
    tributos: ExactNumber
    kwh_faturado: ExactNumber
    n_uc_medio: float | None
    n_uc_fim: int
    tarifa_media: float | None
    tarifa_base_media: float | None
    horas_interrompidas: float
    n_interrupcoes: int
    dec: float | None
    fec: float | None
    n_chamados: int
    n_notas: int
    satisfacao_media: float | None


class VariacaoIndicadoresSchema(BaseModel):
    """Variação em % de cada indicador (8.0 = +8,0%); nula sem base ou com base zero."""

    receita_faturada: float | None
    receita_energia: float | None
    tributos: float | None
    kwh_faturado: float | None
    n_uc_medio: float | None
    n_uc_fim: float | None
    tarifa_media: float | None
    tarifa_base_media: float | None
    horas_interrompidas: float | None
    n_interrupcoes: float | None
    dec: float | None
    fec: float | None
    n_chamados: float | None
    n_notas: float | None
    satisfacao_media: float | None


class ComparacaoIndicadoresSchema(BaseModel):
    base: IndicadoresPeriodoSchema
    atual: IndicadoresPeriodoSchema
    variacao_pct: VariacaoIndicadoresSchema


class IndicadoresJanelaSchema(BaseModel):
    """Uma janela corrida completa: `meses` competências seguidas, todas com dado."""

    inicio: Competencia
    fim: Competencia
    receita_faturada: ExactNumber
    receita_energia: ExactNumber
    kwh_faturado: ExactNumber
    n_uc_medio: float | None
    tarifa_media: float | None
    tarifa_base_media: float | None


class LoginSchema(BaseModel):
    """Pedido de login. Os tetos evitam que um corpo gigante vire trabalho para o Argon2."""

    login: Annotated[
        str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=50)
    ]
    senha: Annotated[str, StringConstraints(min_length=1, max_length=200)]
