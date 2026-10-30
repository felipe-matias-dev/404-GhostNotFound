import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { buscarDecomposicao, receitaKeys } from "../api";
import type { DecomposicaoFiltro } from "../types";


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
