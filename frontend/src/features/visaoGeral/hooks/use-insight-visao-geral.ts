import { skipToken, useQuery } from "@tanstack/react-query";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { buscarInsight, visaoGeralKeys } from "../api";

export function useInsightVisaoGeral(
	par: ParPeriodos | undefined,
	recorte: Recorte,
) {
	return useQuery({
		queryKey: visaoGeralKeys.insight(par, recorte),
		queryFn: par ? () => buscarInsight(par, recorte) : skipToken,
		// Como na Receita: o modelo custa tokens, e só busca quando o usuário pede (`refetch`).
		enabled: false,
		retry: false,
	});
}
