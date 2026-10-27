import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { buscarDecomposicao, buscarPeriodos, receitaKeys } from "../api";
import type { DecomposicaoFiltro, ParPeriodos, Recorte } from "../types";

export function usePeriodosDecomposicao() {
	return useQuery({
		queryKey: receitaKeys.periodos(),
		queryFn: buscarPeriodos,
		staleTime: Number.POSITIVE_INFINITY,
	});
}

export function useDecomposicao(
	par: ParPeriodos | undefined,
	recorte: Recorte,
	enabled = true,
) {
	const filtro = { ...recorte, ...par } as DecomposicaoFiltro;
	return useQuery({
		queryKey: receitaKeys.decomposicao(filtro),
		queryFn: () => buscarDecomposicao(filtro),
		enabled: Boolean(par) && enabled,
		// No drill-down, o nível atual fica na tela até o próximo chegar.
		placeholderData: keepPreviousData,
	});
}
