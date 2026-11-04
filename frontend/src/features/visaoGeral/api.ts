import { api, unwrap } from "#/lib/api";
import type { ParPeriodos, Recorte } from "#/lib/filtros";

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
export function buscarInsight(
	{ periodo_base, periodo_atual }: ParPeriodos,
	recorte: Recorte,
) {
	const [base_inicio = "", base_fim = ""] = periodo_base.split("/");
	const [atual_inicio = "", atual_fim = ""] = periodo_atual.split("/");
	return unwrap(
		api.GET("/indicadores/insight", {
			params: {
				query: { base_inicio, base_fim, atual_inicio, atual_fim, ...recorte },
			},
		}),
	);
}
