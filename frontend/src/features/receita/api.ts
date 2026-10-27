import { api, unwrap } from "#/lib/api";
import type { DecomposicaoFiltro } from "./types";

export const receitaKeys = {
	all: ["receita"] as const,
	periodos: () => [...receitaKeys.all, "periodos"] as const,
	decomposicao: (filtro: DecomposicaoFiltro) =>
		[...receitaKeys.all, "decomposicao", filtro] as const,
};

export function buscarDecomposicao(filtro: DecomposicaoFiltro) {
	return unwrap(
		api.GET("/receita/decomposicao", { params: { query: filtro } }),
	);
}

export function buscarPeriodos() {
	return unwrap(api.GET("/receita/decomposicao/periodos"));
}
