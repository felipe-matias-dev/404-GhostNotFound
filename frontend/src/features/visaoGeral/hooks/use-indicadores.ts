import { useQuery } from "@tanstack/react-query";
import { buscarKpisMensais, visaoGeralKeys } from "../api";
import { compararMeses } from "../conversions";
import type { KpisMensais, ParPeriodos } from "../types";

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
