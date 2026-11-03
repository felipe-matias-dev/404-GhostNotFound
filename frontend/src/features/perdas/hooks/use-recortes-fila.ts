import { useQuery } from "@tanstack/react-query";
import type { Recorte } from "#/lib/filtros";
import { recortesFila, recortesFilaKey } from "../api";

export function useRecortesFila(
	recorte: Recorte,
	nivel: "municipio" | "bairro",
	enabled = true,
) {
	return useQuery({
		queryKey: recortesFilaKey(recorte, nivel),
		queryFn: () => recortesFila(recorte, nivel),
		enabled,
	});
}
