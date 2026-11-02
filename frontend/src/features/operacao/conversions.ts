import type { TrendCategory, TrendSeries } from "#/components/ui/trend-chart";
import { formatCompetencia, formatCompetenciaCurta } from "#/lib/format";
import type {
	ContinuidadeMensal,
	Criterio,
	GrupoOcorrencias,
	LinhaContinuidade,
	LinhaTabela,
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

/** O nome da linha: o bairro leva o município, porque o mesmo nome existe em outros. */
export function rotuloDoSegmento(linha: LinhaContinuidade): string {
	return linha.municipio
		? `${linha.segmento}, ${linha.municipio}`
		: linha.segmento;
}

/** As linhas da API com a posição no ranking, uma identidade única e o nome exibido. */
export function linhasDaTabela(
	linhas: readonly LinhaContinuidade[],
): LinhaTabela[] {
	return linhas.map((linha, indice) => ({
		...linha,
		posicao: indice + 1,
		id: linha.municipio
			? `${linha.municipio}|${linha.segmento}`
			: linha.segmento,
		rotulo: rotuloDoSegmento(linha),
	}));
}

const semAcento = (texto: string) =>
	texto
		.normalize("NFD")
		.replace(/\p{Diacritic}/gu, "")
		.toLocaleLowerCase("pt-BR")
		.trim();

/** As linhas cujo nome contém o termo, sem diferenciar acento, caixa nem espaço nas pontas. */
export function filtrarSegmentos<T extends { rotulo: string }>(
	linhas: readonly T[],
	termo: string,
): T[] {
	const procurado = semAcento(termo);
	if (!procurado) return [...linhas];
	return linhas.filter((linha) => semAcento(linha.rotulo).includes(procurado));
}

/** Causa ou tipo não registrado (OCO-01) aparece, nunca é descartado. */
export const NAO_INFORMADA = "Não informada";

export type BarraOcorrencias = {
	nome: string;
	horas: number;
	interrupcoes: number;
	/** Comprimento da barra: as horas do grupo sobre as do maior grupo da lista. */
	fracao: number;
};

/** Os grupos na ordem da API (mais horas primeiro), com o nome nulo por extenso. */
export function barrasDeOcorrencias(
	grupos: readonly GrupoOcorrencias[],
): BarraOcorrencias[] {
	const maior = Math.max(
		0,
		...grupos.map((grupo) => grupo.horas_interrompidas),
	);
	return grupos.map((grupo) => ({
		nome: grupo.nome ?? NAO_INFORMADA,
		horas: grupo.horas_interrompidas,
		interrupcoes: grupo.n_interrupcoes,
		fracao: maior > 0 ? grupo.horas_interrompidas / maior : 0,
	}));
}

/** A referência do gráfico: o recorte inteiro, ou a empresa sem recorte. */
export type ReferenciaHistorico = {
	rotulo: string;
	/** Nome no fim da linha do gráfico: "empresa" ou "recorte". */
	rotuloCurto: string;
	linhas: readonly ContinuidadeMensal[];
};

export type HistoricoAlimentador = {
	categories: TrendCategory[];
	/** O alimentador em cada mês do período; `undefined` é lacuna, não zero. */
	meses: (ContinuidadeMensal | undefined)[];
	/** Por índice: o alimentador e, quando houver, a referência no mesmo mês. */
	series: Record<Criterio, TrendSeries[]>;
};

/** Mês sem linha no recorte: a API devolve as somas nulas, e o gráfico mostra lacuna. */
const comDado = (linha: ContinuidadeMensal | undefined) =>
	linha && linha.n_uc !== null ? linha : undefined;

/**
 * O histórico mensal do alimentador no recorte, um ponto por mês e sem interpolar as lacunas,
 * com o DEC e o FEC da referência no mesmo mês.
 */
export function historicoDoAlimentador(
	linhas: readonly ContinuidadeMensal[],
	periodo: Periodo,
	alimentador: string,
	referencia: ReferenciaHistorico | undefined,
): HistoricoAlimentador {
	const competencias = mesesDoPeriodo(periodo);
	const doAlimentador = new Map(
		linhas.map((linha) => [linha.competencia, linha]),
	);
	const daReferencia = new Map(
		(referencia?.linhas ?? []).map((linha) => [linha.competencia, linha]),
	);
	const meses = competencias.map((competencia) =>
		comDado(doAlimentador.get(competencia)),
	);
	const seriesDe = (indice: Criterio): TrendSeries[] => {
		const proprio: TrendSeries = {
			id: alimentador,
			label: alimentador,
			values: meses.map((linha) => linha?.[indice] ?? null),
			emphasis: true,
		};
		if (!referencia) return [proprio];
		return [
			proprio,
			{
				id: "referencia",
				label: referencia.rotulo,
				shortLabel: referencia.rotuloCurto,
				color: "muted",
				values: competencias.map(
					(competencia) => daReferencia.get(competencia)?.[indice] ?? null,
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
