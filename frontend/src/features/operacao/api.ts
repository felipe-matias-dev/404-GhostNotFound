import { api, unwrap } from "#/lib/api";
import type {
	ContinuidadeMensal,
	Criterio,
	NivelRecorte,
	Periodo,
	RankingContinuidade,
	Recorte,
	RecortesContinuidade,
	ResumoOcorrencias,
	UcsAtingidas,
} from "./types";

export const TAMANHO_PAGINA_UCS = 10;

export const continuidadeKeys = {
	all: ["continuidade"] as const,
	ranking: (
		periodo: Periodo | undefined,
		criterio: Criterio,
		recorte: Recorte,
		base: Periodo | undefined,
	) =>
		[
			...continuidadeKeys.all,
			"ranking",
			periodo,
			criterio,
			recorte,
			base,
		] as const,
	recortes: (
		periodo: Periodo | undefined,
		criterio: Criterio,
		recorte: Recorte,
		nivel: NivelRecorte | undefined,
		base: Periodo | undefined,
	) =>
		[
			...continuidadeKeys.all,
			"recortes",
			periodo,
			criterio,
			recorte,
			nivel,
			base,
		] as const,
	mensal: (
		periodo: Periodo | undefined,
		recorte: Recorte,
		alimentador: string | undefined,
	) =>
		[...continuidadeKeys.all, "mensal", periodo, recorte, alimentador] as const,
	resumo: (
		periodo: Periodo | undefined,
		recorte: Recorte,
		alimentador: string | undefined,
	) =>
		[...continuidadeKeys.all, "resumo", periodo, recorte, alimentador] as const,
	ucs: (
		periodo: Periodo | undefined,
		recorte: Recorte,
		alimentador: string | undefined,
		pagina: number,
	) =>
		[
			...continuidadeKeys.all,
			"ucs",
			periodo,
			recorte,
			alimentador,
			pagina,
		] as const,
};

const doPeriodoBase = (base: Periodo | undefined) =>
	base ? { base_inicio: base.inicio, base_fim: base.fim } : {};

/** Os alimentadores do recorte, cada um com a variação sobre a base, quando houver. */
export function buscarRankingContinuidade(
	periodo: Periodo,
	criterio: Criterio,
	recorte: Recorte,
	base: Periodo | undefined,
	signal?: AbortSignal,
): Promise<RankingContinuidade> {
	return unwrap(
		api.GET("/continuidade/alimentadores/ranking", {
			params: {
				query: {
					inicio: periodo.inicio,
					fim: periodo.fim,
					criterio,
					...recorte,
					...doPeriodoBase(base),
				},
			},
			signal,
		}),
	);
}

/** Um nível do recorte; sem `nivel`, o próximo abaixo da geografia escolhida. */
export function buscarRecortesContinuidade(
	periodo: Periodo,
	criterio: Criterio,
	recorte: Recorte,
	nivel: NivelRecorte | undefined,
	base: Periodo | undefined,
	signal?: AbortSignal,
): Promise<RecortesContinuidade> {
	return unwrap(
		api.GET("/continuidade/recortes", {
			params: {
				query: {
					inicio: periodo.inicio,
					fim: periodo.fim,
					criterio,
					...recorte,
					...(nivel ? { nivel } : {}),
					...doPeriodoBase(base),
				},
			},
			signal,
		}),
	);
}

/** A série mensal do recorte; com alimentador, só ele dentro do recorte. */
export function buscarContinuidadeMensal(
	periodo: Periodo,
	recorte: Recorte,
	alimentador: string | undefined,
	signal?: AbortSignal,
): Promise<ContinuidadeMensal[]> {
	return unwrap(
		api.GET("/continuidade/mensal", {
			params: {
				query: {
					inicio: periodo.inicio,
					fim: periodo.fim,
					...recorte,
					...(alimentador ? { cod_alimentador: alimentador } : {}),
				},
			},
			signal,
		}),
	);
}

/** Causas, tipos, UCs e duração das ocorrências do alimentador no recorte. */
export function buscarResumoOcorrencias(
	periodo: Periodo,
	recorte: Recorte,
	alimentador: string,
	signal?: AbortSignal,
): Promise<ResumoOcorrencias> {
	return unwrap(
		api.GET("/continuidade/ocorrencias/resumo", {
			params: {
				query: {
					inicio: periodo.inicio,
					fim: periodo.fim,
					...recorte,
					cod_alimentador: alimentador,
				},
			},
			signal,
		}),
	);
}

/** Uma página das UCs mais atingidas do alimentador no recorte. */
export function buscarUcsAtingidas(
	periodo: Periodo,
	recorte: Recorte,
	alimentador: string,
	pagina: number,
	signal?: AbortSignal,
): Promise<UcsAtingidas> {
	return unwrap(
		api.GET("/continuidade/ocorrencias/ucs", {
			params: {
				query: {
					inicio: periodo.inicio,
					fim: periodo.fim,
					...recorte,
					cod_alimentador: alimentador,
					pagina,
					tamanho: TAMANHO_PAGINA_UCS,
				},
			},
			signal,
		}),
	);
}
