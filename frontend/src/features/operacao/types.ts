import type { components } from "#/lib/api-schema.gen";

export type Criterio = "dec" | "fec";

export type VisaoRede = "alimentadores" | "localidades";

export type Periodo = { inicio: string; fim: string };

export type Recorte = { municipio?: string; bairro?: string };

export type AlimentadorMensal =
	components["schemas"]["ContinuidadeAlimentadorMensalSchema"];

export type RankingContinuidade =
	components["schemas"]["RankingContinuidadeSchema"];

export type RecortesContinuidade =
	components["schemas"]["RecortesContinuidadeSchema"];

export type LinhaContinuidade =
	components["schemas"]["RecorteContinuidadeSchema"];

export type NivelRecorte = RecortesContinuidade["nivel"];
