import { api, unwrap } from "#/lib/api";
import type { DecomposicaoFiltro } from "./types";

export const receitaKeys = {
	all: ["receita"] as const,
	decomposicao: (filtro: DecomposicaoFiltro) =>
		[...receitaKeys.all, "decomposicao", filtro] as const,
	insight: (filtro: DecomposicaoFiltro) =>
		[...receitaKeys.all, "insight", filtro] as const,
};

export function buscarDecomposicao(filtro: DecomposicaoFiltro) {
	return unwrap(
		api.GET("/receita/decomposicao", { params: { query: filtro } }),
	);
}

export function buscarInsight(filtro: DecomposicaoFiltro) {
	return unwrap(api.GET("/receita/insight", { params: { query: filtro } }));
}
