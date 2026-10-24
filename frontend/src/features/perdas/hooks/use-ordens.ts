import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { listarOrdens, ordensKeys } from "../api";
import type { StatusOrdem } from "../types";

export function useOrdens(status: StatusOrdem | undefined) {
	return useQuery({
		queryKey: ordensKeys.lista(status),
		queryFn: () => listarOrdens(status),
		// Ao trocar o filtro, as linhas atuais ficam até as novas chegarem: a tabela anima a
		// troca em vez de piscar o molde de carregamento.
		placeholderData: keepPreviousData,
	});
}
