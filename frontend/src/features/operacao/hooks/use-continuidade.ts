import { skipToken, useQuery } from "@tanstack/react-query";
import {
	buscarRankingContinuidade,
	buscarRecortesContinuidade,
	buscarSerieAlimentador,
	continuidadeKeys,
} from "../api";
import type { Criterio, Periodo, Recorte } from "../types";

export function useRankingContinuidade(
	periodo: Periodo | undefined,
	criterio: Criterio,
	enabled: boolean,
) {
	return useQuery({
		queryKey: continuidadeKeys.ranking(periodo, criterio),
		queryFn:
			enabled && periodo
				? ({ signal }) => buscarRankingContinuidade(periodo, criterio, signal)
				: skipToken,
	});
}

export function useRecortesContinuidade(
	periodo: Periodo | undefined,
	criterio: Criterio,
	recorte: Recorte,
	enabled: boolean,
) {
	return useQuery({
		queryKey: continuidadeKeys.recortes(periodo, criterio, recorte),
		queryFn:
			enabled && periodo
				? ({ signal }) =>
						buscarRecortesContinuidade(periodo, criterio, recorte, signal)
				: skipToken,
	});
}

export function useSerieAlimentador(
	periodo: Periodo | undefined,
	alimentador: string | undefined,
) {
	return useQuery({
		queryKey: continuidadeKeys.serie(periodo, alimentador),
		queryFn:
			periodo && alimentador
				? ({ signal }) => buscarSerieAlimentador(periodo, alimentador, signal)
				: skipToken,
	});
}
