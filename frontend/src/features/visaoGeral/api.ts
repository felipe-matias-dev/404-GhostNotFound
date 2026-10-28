import { api, unwrap } from "#/lib/api";
import type { Janelas } from "./conversions";

export const visaoGeralKeys = {
	all: ["visaoGeral"] as const,
	mensal: () => [...visaoGeralKeys.all, "mensal"] as const,
	comparacao: (janelas: Janelas | undefined) =>
		[...visaoGeralKeys.all, "comparacao", janelas] as const,
};

/** A série inteira da `gold_kpis_mensais`, do mês mais antigo ao mais recente. */
export function buscarKpisMensais() {
	return unwrap(api.GET("/receita/mensal"));
}

/** Receita e kWh faturados das duas janelas, somados no backend, e a variação. */
export function buscarComparacaoReceita({ base, atual }: Janelas) {
	const [base_inicio = "", base_fim = ""] = base.split("/");
	const [atual_inicio = "", atual_fim = ""] = atual.split("/");
	return unwrap(
		api.GET("/receita/comparacao", {
			params: { query: { base_inicio, base_fim, atual_inicio, atual_fim } },
		}),
	);
}
