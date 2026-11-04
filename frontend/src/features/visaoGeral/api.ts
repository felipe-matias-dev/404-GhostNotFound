import { api, unwrap } from "#/lib/api";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { periodosDoInsight } from "./conversions";

export const visaoGeralKeys = {
	all: ["visaoGeral"] as const,
	janelas: (meses: number, recorte: Recorte) =>
		[...visaoGeralKeys.all, "janelas", meses, recorte] as const,
	insight: (par: ParPeriodos | undefined, recorte: Recorte) =>
		[...visaoGeralKeys.all, "insight", par, recorte] as const,
};

/** As janelas corridas de `meses` meses do recorte, da mais antiga para a mais recente. */
export function buscarJanelas(meses: number, recorte: Recorte) {
	return unwrap(
		api.GET("/indicadores/janelas", {
			params: { query: { meses, ...recorte } },
		}),
	);
}

/** O insight de IA da comparação de indicadores do par, no recorte. */
export function buscarInsight(par: ParPeriodos, recorte: Recorte) {
	return unwrap(
		api.GET("/indicadores/insight", {
			params: { query: { ...periodosDoInsight(par), ...recorte } },
		}),
	);
}
