import { useQuery } from "@tanstack/react-query";
import { obterOrdem, ordensKeys } from "../api";

export function useOrdem(id: number | null) {
	return useQuery({
		queryKey: ordensKeys.detalhe(id ?? 0),
		queryFn: () => obterOrdem(id as number),
		enabled: id !== null,
	});
}
