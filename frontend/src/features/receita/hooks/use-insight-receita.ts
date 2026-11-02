import { useQuery } from "@tanstack/react-query";
import type { ParPeriodos, Recorte } from "#/lib/filtros";
import { buscarInsight, receitaKeys } from "../api";
import type { DecomposicaoFiltro } from "../types";

export function useInsightReceita(
	par: ParPeriodos | undefined,
	recorte: Recorte,
) {
	const filtro = { ...recorte, ...par } as DecomposicaoFiltro;
	return useQuery({
		queryKey: receitaKeys.insight(filtro),
		queryFn: () => buscarInsight(filtro),
		// O modelo custa tokens: só busca quando o usuário pede (`refetch`). O texto já gerado
		// de um recorte continua no cache e reaparece ao voltar a ele.
		enabled: false,
		// Sem placeholder: o texto de outro recorte citaria números que a tela não mostra.
		// Sem retry: o 503 (IA desligada) só muda reiniciando a API, e a falha do provedor já
		// volta como texto vazio; o usuário pode tentar de novo.
		retry: false,
	});
}
