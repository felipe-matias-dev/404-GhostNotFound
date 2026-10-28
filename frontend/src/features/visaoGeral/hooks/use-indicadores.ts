import { queryOptions, skipToken, useQuery } from "@tanstack/react-query";
import {
	buscarComparacaoIndicadores,
	buscarJanelas,
	buscarKpisMensais,
	visaoGeralKeys,
} from "../api";
import { tesoura } from "../conversions";
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

const janelasQuery = queryOptions({
	queryKey: visaoGeralKeys.janelas(),
	queryFn: buscarJanelas,
});

export function useJanelas() {
	return useQuery(janelasQuery);
}

export function useComparacaoIndicadores(par: ParPeriodos | undefined) {
	return useQuery({
		queryKey: visaoGeralKeys.comparacao(par),
		queryFn: par ? () => buscarComparacaoIndicadores(par) : skipToken,
	});
}

export function useTesoura() {
	return useQuery({ ...janelasQuery, select: tesoura });
}
