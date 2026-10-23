import { useQuery } from "@tanstack/react-query";
import { carregarBairrosRmr } from "#/components/ui/region-map";

/** Geometria dos bairros da RMR, baixada uma vez quando o primeiro município é escolhido. */
export function useBairrosRmr(enabled: boolean) {
	return useQuery({
		queryKey: ["geo", "rmr-bairros"],
		queryFn: carregarBairrosRmr,
		enabled,
		staleTime: Number.POSITIVE_INFINITY,
		gcTime: Number.POSITIVE_INFINITY,
	});
}
