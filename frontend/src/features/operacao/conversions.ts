import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type { RedeSearch } from "./search";
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

/**
 * O período da tabela: a URL válida prevalece, mesmo fora do calendário; sem ela, os últimos
 * 12 meses de calendário até a competência mais recente, limitados à mais antiga da base.
 */
export function resolverPeriodo(
	search: Pick<RedeSearch, "inicio" | "fim">,
	competencias: readonly string[],
): Periodo | undefined {
	const { inicio, fim } = search;
	if (inicio && fim && MES.test(inicio) && MES.test(fim) && inicio <= fim) {
		return { inicio, fim };
	}
	const ordenadas = [
		...new Set(competencias.filter((c) => MES.test(c))),
	].sort();
	const primeira = ordenadas[0];
	const ultima = ordenadas.at(-1);
	if (!primeira || !ultima) return undefined;
	const candidato = deslocar(ultima, -11);
	return { inicio: candidato > primeira ? candidato : primeira, fim: ultima };
}

/** Todos os meses do período, inclusive, cruzando anos; vazio se o período está invertido. */
export function mesesDoPeriodo(periodo: Periodo): string[] {
	const meses: string[] = [];
	for (let mes = periodo.inicio; mes <= periodo.fim; mes = deslocar(mes, 1)) {
		meses.push(mes);
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
