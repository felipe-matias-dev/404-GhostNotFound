import { api, unwrap } from "#/lib/api";
import type { ParPeriodos } from "./types";

export const visaoGeralKeys = {
	all: ["visaoGeral"] as const,
	mensal: () => [...visaoGeralKeys.all, "mensal"] as const,
	janelas: () => [...visaoGeralKeys.all, "janelas", 12] as const,
	comparacao: (par: ParPeriodos | undefined) =>
		[...visaoGeralKeys.all, "comparacao", par] as const,
};

/** A série inteira da `gold_kpis_mensais`, do mês mais antigo ao mais recente. */
export function buscarKpisMensais() {
	return unwrap(api.GET("/receita/mensal"));
}

export function buscarJanelas() {
	return unwrap(
		api.GET("/indicadores/janelas", { params: { query: { meses: 12 } } }),
	);
}

export function buscarComparacaoIndicadores({
	periodo_base,
	periodo_atual,
}: ParPeriodos) {
	const [base_inicio = "", base_fim = ""] = periodo_base.split("/");
	const [atual_inicio = "", atual_fim = ""] = periodo_atual.split("/");
	return unwrap(
		api.GET("/indicadores/comparacao", {
			params: { query: { base_inicio, base_fim, atual_inicio, atual_fim } },
		}),
	);
}
