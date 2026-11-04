import { useQuery } from "@tanstack/react-query";
import { buscarInsightUc, unidadeConsumidoraKeys } from "../api";
import type { Uc360 } from "../types";

export function useInsightUc(data: Uc360) {
	const codUc = data.cadastro.cod_uc;
	// Os números que o insight narra: se mudarem (Gold recarregada), a chave muda junto.
	const versao = [data.consumo.referencia, data.variacao_conta];
	return useQuery({
		queryKey: unidadeConsumidoraKeys.insight(codUc, versao),
		queryFn: () => buscarInsightUc(codUc),
		// Como na Receita: o modelo custa tokens, e só busca quando o atendente pede (`refetch`).
		enabled: false,
		retry: false,
	});
}
