import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { buscarDecomposicao, receitaKeys } from "../api";
import type { DecomposicaoFiltro } from "../types";

export function useDecomposicao(filtro: DecomposicaoFiltro, enabled = true) {
	return useQuery({
		queryKey: receitaKeys.decomposicao(filtro),
		queryFn: () => buscarDecomposicao(filtro),
		enabled,
		// No drill-down, o nível atual fica na tela até o próximo chegar.
		placeholderData: keepPreviousData,
	});
}
