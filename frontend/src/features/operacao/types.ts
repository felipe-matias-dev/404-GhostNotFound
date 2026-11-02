import type { components } from "#/lib/api-schema.gen";

export type Criterio = "dec" | "fec";

export type VisaoRede = "alimentadores" | "bairros" | "localidades";

export type Periodo = { inicio: string; fim: string };

export type { Recorte } from "#/lib/filtros";

export type RankingContinuidade =
	components["schemas"]["RankingContinuidadeSchema"];

export type RecortesContinuidade =
	components["schemas"]["RecortesContinuidadeSchema"];

export type LinhaContinuidade =
	components["schemas"]["RecorteContinuidadeSchema"];

export type NivelRecorte = RecortesContinuidade["nivel"];

/** A linha da tabela com a posição na ordem da API (o ranking) e o nome exibido. */
export type LinhaTabela = LinhaContinuidade & {
	posicao: number;
	/** Identidade da linha: o bairro se repete entre municípios. */
	id: string;
	rotulo: string;
};

/** DEC e FEC de um recorte, ou de um alimentador dentro dele, num mês. */
export type ContinuidadeMensal =
	components["schemas"]["ContinuidadeMensalSchema"];

export type ResumoOcorrencias =
	components["schemas"]["ResumoOcorrenciasSchema"];

export type GrupoOcorrencias = components["schemas"]["GrupoOcorrenciasSchema"];

export type UcsAtingidas = components["schemas"]["UcsAtingidasSchema"];

export type UcAtingida = components["schemas"]["UcAtingidaSchema"];
