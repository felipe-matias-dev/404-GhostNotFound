import { useQuery } from "@tanstack/react-query";
import { ordensKeys, temposPorEtapa } from "../api";

export function useTemposPorEtapa() {
	return useQuery({
		queryKey: ordensKeys.temposPorEtapa,
		queryFn: temposPorEtapa,
	});
}
