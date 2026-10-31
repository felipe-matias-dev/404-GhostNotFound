import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "#/lib/api";

export const filtrosKeys = {
	periodos: ["filtros", "periodos"] as const,
	competencias: ["filtros", "competencias"] as const,
	localidades: ["filtros", "localidades"] as const,
};

export function usePeriodosDecomposicao() {
	return useQuery({
		queryKey: filtrosKeys.periodos,
		queryFn: () => unwrap(api.GET("/receita/decomposicao/periodos")),
		staleTime: Number.POSITIVE_INFINITY,
	});
}

export function useCompetencias() {
	return useQuery({
		queryKey: filtrosKeys.competencias,
		queryFn: () => unwrap(api.GET("/receita/mensal")),
		select: (linhas) => linhas.map((linha) => linha.competencia),
	});
}

export function useLocalidades() {
	return useQuery({
		queryKey: filtrosKeys.localidades,
		queryFn: () => unwrap(api.GET("/unidades-consumidoras/localidades")),
	});
}
