import { api, unwrap } from "#/lib/api";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { intervaloDoPar } from "./conversions";

export const visaoGeralKeys = {
	all: ["visaoGeral"] as const,
	mensal: (par: ParPeriodos | undefined, recorte: Recorte) =>
		[...visaoGeralKeys.all, "mensal", par, recorte] as const,
	janelas: (meses: number, recorte: Recorte) =>
		[...visaoGeralKeys.all, "janelas", meses, recorte] as const,
	comparacao: (par: ParPeriodos | undefined, recorte: Recorte) =>
		[...visaoGeralKeys.all, "comparacao", par, recorte] as const,
};

/** As sparklines do período: a série da Gold no recorte, do menor início ao maior fim. */
export function buscarIndicadoresMensais(par: ParPeriodos, recorte: Recorte) {
	const { inicio, fim } = intervaloDoPar(par);
	return unwrap(
		api.GET("/indicadores/mensal", {
			params: { query: { inicio, fim, ...recorte } },
		}),
	);
}

/** As janelas corridas de `meses` meses do recorte, da mais antiga para a mais recente. */
export function buscarJanelas(meses: number, recorte: Recorte) {
	return unwrap(
		api.GET("/indicadores/janelas", {
			params: { query: { meses, ...recorte } },
		}),
	);
}

export function buscarComparacaoIndicadores(
	{ periodo_base, periodo_atual }: ParPeriodos,
	recorte: Recorte,
) {
	const [base_inicio = "", base_fim = ""] = periodo_base.split("/");
	const [atual_inicio = "", atual_fim = ""] = periodo_atual.split("/");
	return unwrap(
		api.GET("/indicadores/comparacao", {
			params: {
				query: {
					base_inicio,
					base_fim,
					atual_inicio,
					atual_fim,
					...recorte,
				},
			},
		}),
	);
}
