import { queryOptions, useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { buscarKpisMensais, visaoGeralKeys } from "../api";
import { compararMeses, tendencia, type VisaoTendencia } from "../conversions";
import type { Indicador, KpisMensais, ParPeriodos } from "../types";

const kpisMensaisQuery = queryOptions({
	queryKey: visaoGeralKeys.mensal(),
	queryFn: buscarKpisMensais,
});

const competencias = (linhas: KpisMensais[]) =>
	linhas.map((linha) => linha.competencia);

/** Os meses que a Gold tem: o que o seletor de período pode oferecer. */
export function useCompetencias() {
	return useQuery({ ...kpisMensaisQuery, select: competencias });
}

/**
 * Os indicadores dos dois períodos e a variação. Hoje sai da série mensal (mês contra mês);
 * quando o backend tiver a rota de comparação, só esta consulta muda (DEC-036).
 */
export function useComparacaoIndicadores(par: ParPeriodos | undefined) {
	const periodoBase = par?.periodo_base;
	const periodoAtual = par?.periodo_atual;
	const select = useCallback(
		(linhas: KpisMensais[]) =>
			periodoBase && periodoAtual
				? compararMeses(linhas, {
						periodo_base: periodoBase,
						periodo_atual: periodoAtual,
					})
				: undefined,
		[periodoBase, periodoAtual],
	);
	return useQuery({
		...kpisMensaisQuery,
		enabled: Boolean(par),
		select,
	});
}

/** O indicador ao longo da série mensal, mês a mês ou ano a ano, para o gráfico. */
export function useTendencia(
	indicador: Indicador,
	visao: VisaoTendencia,
	rotulo: string,
) {
	const select = useCallback(
		(linhas: KpisMensais[]) => tendencia(linhas, indicador, visao, rotulo),
		[indicador, visao, rotulo],
	);
	return useQuery({ ...kpisMensaisQuery, select });
}
