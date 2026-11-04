import { useQuery } from "@tanstack/react-query";
import { buscarInsightUc, unidadeConsumidoraKeys } from "../api";

export function useInsightUc(codUc: string) {
	return useQuery({
		queryKey: unidadeConsumidoraKeys.insight(codUc),
		queryFn: () => buscarInsightUc(codUc),
		// Como na Receita: o modelo custa tokens, e só busca quando o atendente pede (`refetch`).
		enabled: false,
		retry: false,
	});
}
