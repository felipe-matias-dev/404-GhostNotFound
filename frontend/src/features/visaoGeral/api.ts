import { api, unwrap } from "#/lib/api";
import type { Recorte } from "#/lib/filtros";

export const visaoGeralKeys = {
	all: ["visaoGeral"] as const,
	janelas: (meses: number, recorte: Recorte) =>
		[...visaoGeralKeys.all, "janelas", meses, recorte] as const,
};

/** As janelas corridas de `meses` meses do recorte, da mais antiga para a mais recente. */
export function buscarJanelas(meses: number, recorte: Recorte) {
	return unwrap(
		api.GET("/indicadores/janelas", {
			params: { query: { meses, ...recorte } },
		}),
	);
}
