import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type {
	AlimentadorMensal,
	Criterio,
	LinhaContinuidade,
	Periodo,
	RankingContinuidade,
	ReferenciaMensal,
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

const semAcento = (texto: string) =>
	texto
		.normalize("NFD")
		.replace(/\p{Diacritic}/gu, "")
		.toLocaleLowerCase("pt-BR")
		.trim();

/** As linhas cujo nome contém o termo, sem diferenciar acento, caixa nem espaço nas pontas. */
export function filtrarSegmentos<T extends { segmento: string }>(
	linhas: readonly T[],
	termo: string,
): T[] {
	const procurado = semAcento(termo);
	if (!procurado) return [...linhas];
	return linhas.filter((linha) =>
		semAcento(linha.segmento).includes(procurado),
	);
}

export type HistoricoAlimentador = {
	categories: TrendCategory[];
	/** A linha do alimentador em cada mês do período; `undefined` é lacuna, não zero. */
	meses: (AlimentadorMensal | undefined)[];
	/** Por índice: o alimentador e, quando houver, a empresa no mesmo mês. */
	series: Record<Criterio, TrendSeries[]>;
};

/**
 * O histórico mensal do alimentador no período, um ponto por mês e sem interpolar as lacunas,
 * com o DEC e o FEC da empresa no mesmo mês como referência.
 */
export function historicoDoAlimentador(
	linhas: readonly AlimentadorMensal[],
	periodo: Periodo,
	alimentador: string,
	empresa: readonly ReferenciaMensal[] | undefined,
): HistoricoAlimentador {
	const competencias = mesesDoPeriodo(periodo);
	const doAlimentador = new Map<string, AlimentadorMensal>();
	for (const linha of linhas) {
		if (linha.cod_alimentador === alimentador) {
			doAlimentador.set(linha.competencia, linha);
		}
	}
	const daEmpresa = new Map(
		(empresa ?? []).map((linha) => [linha.competencia, linha]),
	);
	const meses = competencias.map((competencia) =>
		doAlimentador.get(competencia),
	);
	const seriesDe = (indice: Criterio): TrendSeries[] => {
		const proprio: TrendSeries = {
			id: alimentador,
			label: alimentador,
			values: meses.map((linha) => linha?.[indice] ?? null),
			emphasis: true,
		};
		if (!empresa) return [proprio];
		return [
			proprio,
			{
				id: "empresa",
				label: "Empresa",
				shortLabel: "empresa",
				color: "muted",
				values: competencias.map(
					(competencia) => daEmpresa.get(competencia)?.[indice] ?? null,
				),
			},
		];
	};
	return {
		categories: competencias.map((competencia) => ({
			key: competencia,
			label: formatCompetenciaCurta(competencia),
			title: formatCompetencia(competencia),
		})),
		meses,
		series: { dec: seriesDe("dec"), fec: seriesDe("fec") },
	};
}
