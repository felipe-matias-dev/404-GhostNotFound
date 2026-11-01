import type { components } from "#/lib/api-schema.gen";

export type Criterio = "dec" | "fec";

export type VisaoRede = "alimentadores" | "localidades";

export type Periodo = { inicio: string; fim: string };

export type { Recorte } from "#/lib/filtros";

export type AlimentadorMensal =
	components["schemas"]["ContinuidadeAlimentadorMensalSchema"];

export type RankingContinuidade =
	components["schemas"]["RankingContinuidadeSchema"];

export type RecortesContinuidade =
	components["schemas"]["RecortesContinuidadeSchema"];

export type LinhaContinuidade =
	components["schemas"]["RecorteContinuidadeSchema"];

export type NivelRecorte = RecortesContinuidade["nivel"];

/** A linha da tabela com a posição que ela tem na ordem da API (o ranking). */
export type LinhaTabela = LinhaContinuidade & { posicao: number };
