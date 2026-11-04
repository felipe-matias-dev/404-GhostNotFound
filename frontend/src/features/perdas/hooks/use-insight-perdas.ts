import { useQuery } from "@tanstack/react-query";
import type { Recorte } from "#/lib/filtros";
import { insightPerdas } from "../api";
import { useIndicadoresPerdas } from "./use-indicadores-perdas";

/**
 * Só busca quando o usuário pede (`refetch`), como nas outras telas. Os indicadores entram na
 * chave: gerar ou concluir uma ordem muda os números, e o texto antigo some em vez de ficar
 * desatualizado ao lado deles.
 */
export function useInsightPerdas(recorte: Recorte) {
	const { data } = useIndicadoresPerdas(recorte);
	return useQuery({
		queryKey: ["insight-perdas", recorte, data] as const,
		queryFn: () => insightPerdas(recorte),
		enabled: false,
		retry: false,
	});
}
