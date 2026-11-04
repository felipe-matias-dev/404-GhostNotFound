import { keepPreviousData, skipToken, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { buscarUcs, unidadeConsumidoraKeys } from "../api";

const ESPERA_MS = 150;

export function useBuscaUc(texto: string) {
	const [termo, setTermo] = useState(texto);
	useEffect(() => {
		const timer = setTimeout(() => setTermo(texto), ESPERA_MS);
		return () => clearTimeout(timer);
	}, [texto]);
	const query = useQuery({
		queryKey: unidadeConsumidoraKeys.busca(termo),
		queryFn: termo ? ({ signal }) => buscarUcs(termo, signal) : skipToken,
		placeholderData: keepPreviousData,
		staleTime: 60_000,
	});
	return {
		ucs: texto ? (query.data ?? []) : [],
		buscando: Boolean(texto) && (termo !== texto || query.isFetching),
		erro: query.isError,
	};
}
