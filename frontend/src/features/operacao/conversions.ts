import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type {
	AlimentadorMensal,
	Criterio,
	LinhaContinuidade,
	Periodo,
	RankingContinuidade,
} from "./types";

const MES = /^\d{4}-(0[1-9]|1[0-2])$/;

const deslocar = (competencia: string, meses: number) => {
	const [ano, mes] = competencia.split("-").map(Number);
	const total = Math.max(0, (ano ?? 0) * 12 + (mes ?? 1) - 1 + meses);
	const anoDestino = String(Math.floor(total / 12)).padStart(4, "0");
	return `${anoDestino}-${String((total % 12) + 1).padStart(2, "0")}`;
};

export const MAX_MESES_GRAFICO = 120;

export function periodoExcedeGrafico({ inicio, fim }: Periodo): boolean {
	const [anoInicio, mesInicio] = inicio.split("-").map(Number);
	const [anoFim, mesFim] = fim.split("-").map(Number);
	return (anoFim - anoInicio) * 12 + mesFim - mesInicio + 1 > MAX_MESES_GRAFICO;
}

/** Todos os meses do período, inclusive, dentro do limite de apresentação do gráfico. */
export function mesesDoPeriodo(periodo: Periodo): string[] {
	if (
		!MES.test(periodo.inicio) ||
		!MES.test(periodo.fim) ||
		periodo.inicio > periodo.fim ||
		periodoExcedeGrafico(periodo)
	)
		return [];
	const meses: string[] = [];
	let mes = periodo.inicio;
	while (true) {
		meses.push(mes);
		if (mes === periodo.fim) break;
		mes = deslocar(mes, 1);
	}
	return meses;
}

/** As linhas do ranking na mesma ordem e com os mesmos nulos; só o código vira segmento. */
export function linhasDoRanking(
	ranking: RankingContinuidade,
): LinhaContinuidade[] {
	return ranking.alimentadores.map(({ cod_alimentador, ...linha }) => ({
		...linha,
		segmento: cod_alimentador,
	}));
}

/** A série mensal do alimentador no período: um ponto por mês, sem interpolar as lacunas. */
export function serieDoAlimentador(
	linhas: readonly AlimentadorMensal[],
	periodo: Periodo,
	alimentador: string,
	criterio: Criterio,
): { categories: TrendCategory[]; series: TrendSeries[] } {
	const categories = mesesDoPeriodo(periodo).map((competencia) => ({
		key: competencia,
		label: formatCompetenciaCurta(competencia),
		title: formatCompetencia(competencia),
	}));
	const porCompetencia = new Map<string, AlimentadorMensal>();
	for (const linha of linhas) {
		if (linha.cod_alimentador === alimentador) {
			porCompetencia.set(linha.competencia, linha);
		}
	}
	const values = categories.map(
		({ key }) => porCompetencia.get(key)?.[criterio] ?? null,
	);
	return {
		categories,
		series: [{ id: alimentador, label: alimentador, values }],
	};
}
