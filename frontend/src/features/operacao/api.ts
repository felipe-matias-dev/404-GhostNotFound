import { api, unwrap } from "#/lib/api";
import type {
	AlimentadorMensal,
	Criterio,
	Periodo,
	RankingContinuidade,
	Recorte,
	RecortesContinuidade,
} from "./types";

export const continuidadeKeys = {
	all: ["continuidade"] as const,
	ranking: (periodo: Periodo | undefined, criterio: Criterio) =>
		[...continuidadeKeys.all, "ranking", periodo, criterio] as const,
	recortes: (
		periodo: Periodo | undefined,
		criterio: Criterio,
		recorte: Recorte,
	) =>
		[...continuidadeKeys.all, "recortes", periodo, criterio, recorte] as const,
	serie: (periodo: Periodo | undefined, alimentador: string | undefined) =>
		[...continuidadeKeys.all, "serie", periodo, alimentador] as const,
};

/** O ranking global dos alimentadores: a geografia não recorta este endpoint. */
export function buscarRankingContinuidade(
	periodo: Periodo,
	criterio: Criterio,
	signal?: AbortSignal,
): Promise<RankingContinuidade> {
	return unwrap(
		api.GET("/continuidade/alimentadores/ranking", {
			params: {
				query: { inicio: periodo.inicio, fim: periodo.fim, criterio },
			},
			signal,
		}),
	);
}

/** O nível abaixo do recorte atual, recortado pela geografia e pela classe escolhidas. */
export function buscarRecortesContinuidade(
	periodo: Periodo,
	criterio: Criterio,
	recorte: Recorte,
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
				},
			},
			signal,
		}),
	);
}

/** A série global de um alimentador; nunca sem código, que na API significaria todos. */
export function buscarSerieAlimentador(
	periodo: Periodo,
	alimentador: string,
	signal?: AbortSignal,
): Promise<AlimentadorMensal[]> {
	return unwrap(
		api.GET("/continuidade/alimentadores/mensal", {
			params: {
				query: {
					inicio: periodo.inicio,
					fim: periodo.fim,
					cod_alimentador: [alimentador],
				},
			},
			signal,
		}),
	);
}
