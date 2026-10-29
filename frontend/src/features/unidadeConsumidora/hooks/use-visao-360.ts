import { skipToken, useQuery } from "@tanstack/react-query";
import { buscarVisao360, unidadeConsumidoraKeys } from "../api";

export function useVisao360(codUc: string | undefined) {
	return useQuery({
		queryKey: unidadeConsumidoraKeys.visao360(codUc),
		queryFn: codUc ? ({ signal }) => buscarVisao360(codUc, signal) : skipToken,
		enabled: Boolean(codUc),
		retry: false,
	});
}
