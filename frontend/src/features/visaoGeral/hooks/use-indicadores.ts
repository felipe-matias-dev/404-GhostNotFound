import { useQuery } from "@tanstack/react-query";
import { buscarKpisMensais, visaoGeralKeys } from "../api";
import { compararMeses, tendencia, type VisaoTendencia } from "../conversions";
import type { Indicador, KpisMensais, ParPeriodos } from "../types";

const competencias = (linhas: KpisMensais[]) =>
	linhas.map((linha) => linha.competencia);

/** Os meses que a Gold tem: o que o seletor de período pode oferecer. */
export function useCompetencias() {
	return useQuery({
		queryKey: visaoGeralKeys.mensal(),
		queryFn: buscarKpisMensais,
		select: competencias,
	});
}

/**
 * Os indicadores dos dois períodos e a variação. Hoje sai da série mensal (mês contra mês);
 * quando o backend tiver a rota de comparação, só esta consulta muda (DEC-036).
 */
export function useComparacaoIndicadores(par: ParPeriodos | undefined) {
	return useQuery({
		queryKey: visaoGeralKeys.mensal(),
		queryFn: buscarKpisMensais,
		enabled: Boolean(par),
		select: (linhas: KpisMensais[]) =>
			par ? compararMeses(linhas, par) : undefined,
	});
}

/** O indicador ao longo da série mensal, mês a mês ou ano a ano, para o gráfico. */
export function useTendencia(
	indicador: Indicador,
	visao: VisaoTendencia,
	rotulo: string,
) {
	return useQuery({
		queryKey: visaoGeralKeys.mensal(),
		queryFn: buscarKpisMensais,
		select: (linhas: KpisMensais[]) =>
			tendencia(linhas, indicador, visao, rotulo),
	});
}
