import { skipToken, useQuery } from "@tanstack/react-query";
import {
	buscarContinuidadeMensal,
	buscarRankingContinuidade,
	buscarRecortesContinuidade,
	buscarResumoOcorrencias,
	buscarUcsAtingidas,
	continuidadeKeys,
} from "../api";
import type { Criterio, NivelRecorte, Periodo, Recorte } from "../types";

export function useRankingContinuidade(
	periodo: Periodo | undefined,
	criterio: Criterio,
	recorte: Recorte,
	base: Periodo | undefined,
	enabled: boolean,
) {
	return useQuery({
		queryKey: continuidadeKeys.ranking(periodo, criterio, recorte, base),
		queryFn:
			enabled && periodo
				? ({ signal }) =>
						buscarRankingContinuidade(periodo, criterio, recorte, base, signal)
				: skipToken,
	});
}

export function useRecortesContinuidade(
	periodo: Periodo | undefined,
	criterio: Criterio,
	recorte: Recorte,
	nivel: NivelRecorte | undefined,
	base: Periodo | undefined,
	enabled: boolean,
) {
	return useQuery({
		queryKey: continuidadeKeys.recortes(
			periodo,
			criterio,
			recorte,
			nivel,
			base,
		),
		queryFn:
			enabled && periodo
				? ({ signal }) =>
						buscarRecortesContinuidade(
							periodo,
							criterio,
							recorte,
							nivel,
							base,
							signal,
						)
				: skipToken,
	});
}

/** A série do recorte (sem alimentador) ou do alimentador dentro dele; só com o painel aberto. */
export function useContinuidadeMensal(
	periodo: Periodo | undefined,
	recorte: Recorte,
	alimentador: string | undefined,
	enabled: boolean,
) {
	return useQuery({
		queryKey: continuidadeKeys.mensal(periodo, recorte, alimentador),
		queryFn:
			enabled && periodo
				? ({ signal }) =>
						buscarContinuidadeMensal(periodo, recorte, alimentador, signal)
				: skipToken,
	});
}

export function useResumoOcorrencias(
	periodo: Periodo | undefined,
	recorte: Recorte,
	alimentador: string | undefined,
) {
	return useQuery({
		queryKey: continuidadeKeys.resumo(periodo, recorte, alimentador),
		queryFn:
			periodo && alimentador
				? ({ signal }) =>
						buscarResumoOcorrencias(periodo, recorte, alimentador, signal)
				: skipToken,
	});
}

export function useUcsAtingidas(
	periodo: Periodo | undefined,
	recorte: Recorte,
	alimentador: string | undefined,
	pagina: number,
) {
	const queryKey = continuidadeKeys.ucs(periodo, recorte, alimentador, pagina);
	const conjunto = JSON.stringify(queryKey.slice(0, -1));
	return useQuery({
		queryKey,
		queryFn:
			periodo && alimentador
				? ({ signal }) =>
						buscarUcsAtingidas(periodo, recorte, alimentador, pagina, signal)
				: skipToken,
		// Trocar de página mantém a anterior na tela até a nova chegar; outro alimentador,
		// período ou recorte não herda as UCs do anterior.
		placeholderData: (anterior, consultaAnterior) =>
			consultaAnterior &&
			JSON.stringify(consultaAnterior.queryKey.slice(0, -1)) === conjunto
				? anterior
				: undefined,
	});
}
