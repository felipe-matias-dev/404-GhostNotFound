import type { components } from "#/lib/api-schema.gen";

export type KpisMensais = components["schemas"]["KpisMensaisSchema"];

export type ParPeriodos = components["schemas"]["ParPeriodosSchema"];

/** Os seis indicadores dos cards; o nome é o da coluna da `gold_kpis_mensais`. */
export type Indicador = Extract<
	keyof KpisMensais,
	| "receita_faturada"
	| "kwh_faturado"
	| "dec"
	| "fec"
	| "n_chamados"
	| "satisfacao_media"
>;

export type IndicadoresPeriodo = {
	periodo: string;
	valores: Record<Indicador, number | null>;
};

export type ComparacaoIndicadores = {
	base: IndicadoresPeriodo;
	atual: IndicadoresPeriodo;
	variacao: Record<Indicador, number | null>;
};
