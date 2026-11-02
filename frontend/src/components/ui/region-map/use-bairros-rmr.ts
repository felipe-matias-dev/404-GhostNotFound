import { useQuery } from "@tanstack/react-query";

/** Geometria dos bairros da RMR, baixada uma vez quando o primeiro município é escolhido. */
export function useBairrosRmr(enabled: boolean) {
	return useQuery({
		queryKey: ["geo", "rmr-bairros"],
		queryFn: () => import("./rmr-bairros.gen").then((m) => m.RMR_BAIRROS),
		enabled,
		staleTime: Number.POSITIVE_INFINITY,
		gcTime: Number.POSITIVE_INFINITY,
	});
}
