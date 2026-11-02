import { api, unwrap } from "#/lib/api";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { intervaloDoPar } from "./conversions";

export const indicadoresKeys = {
	all: ["indicadores"] as const,
	mensal: (par: ParPeriodos | undefined, recorte: Recorte) =>
		[...indicadoresKeys.all, "mensal", par, recorte] as const,
	comparacao: (par: ParPeriodos | undefined, recorte: Recorte) =>
		[...indicadoresKeys.all, "comparacao", par, recorte] as const,
};

/** A série mensal da Gold no recorte, do menor início ao maior fim do par. */
export function buscarIndicadoresMensais(par: ParPeriodos, recorte: Recorte) {
	const { inicio, fim } = intervaloDoPar(par);
	return unwrap(
		api.GET("/indicadores/mensal", {
			params: { query: { inicio, fim, ...recorte } },
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
