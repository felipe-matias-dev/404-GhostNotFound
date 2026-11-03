import { useQuery } from "@tanstack/react-query";
import type { Recorte } from "#/lib/filtros";
import { indicadoresPerdas, indicadoresPerdasKey } from "../api";

export function useIndicadoresPerdas(recorte: Recorte) {
	return useQuery({
		queryKey: indicadoresPerdasKey(recorte),
		queryFn: () => indicadoresPerdas(recorte),
	});
}
