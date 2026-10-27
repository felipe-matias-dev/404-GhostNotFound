import { api, unwrap } from "#/lib/api";

export const visaoGeralKeys = {
	all: ["visaoGeral"] as const,
	mensal: () => [...visaoGeralKeys.all, "mensal"] as const,
};

/** A série inteira da `gold_kpis_mensais`, do mês mais antigo ao mais recente. */
export function buscarKpisMensais() {
	return unwrap(api.GET("/receita/mensal"));
}
