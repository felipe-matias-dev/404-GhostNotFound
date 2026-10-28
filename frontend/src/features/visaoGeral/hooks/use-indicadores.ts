import { queryOptions, useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import {
	buscarComparacaoReceita,
	buscarKpisMensais,
	visaoGeralKeys,
} from "../api";
import { compararMeses, type Janelas, tesoura } from "../conversions";
import type { KpisMensais, ParPeriodos } from "../types";

const kpisMensaisQuery = queryOptions({
	queryKey: visaoGeralKeys.mensal(),
	queryFn: buscarKpisMensais,
});

/** A série mensal da Gold, inteira: a forma de cada indicador nas sparklines. */
export function useKpisMensais() {
	return useQuery(kpisMensaisQuery);
}

const competencias = (linhas: KpisMensais[]) =>
	linhas.map((linha) => linha.competencia);

/** Os meses que a Gold tem: o que o seletor de mês e as janelas de 12 meses podem usar. */
export function useCompetencias() {
	return useQuery({ ...kpisMensaisQuery, select: competencias });
}

/**
 * Os indicadores dos dois meses e a variação. Mês contra mês até a tela passar para a rota de
 * comparação do backend (DEC-041).
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
	return useQuery({ ...kpisMensaisQuery, enabled: Boolean(par), select });
}

/** Receita e energia das duas janelas de 12 meses, somadas pelo backend. */
export function useComparacaoReceita(janelas: Janelas | undefined) {
	return useQuery({
		queryKey: visaoGeralKeys.comparacao(janelas),
		queryFn: () => (janelas ? buscarComparacaoReceita(janelas) : undefined),
		enabled: Boolean(janelas),
	});
}

/** Receita e energia em 12 meses corridos, como índice: a tesoura. */
export function useTesoura() {
	return useQuery({ ...kpisMensaisQuery, select: tesoura });
}
