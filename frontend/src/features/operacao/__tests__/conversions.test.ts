import { describe, expect, it } from "vitest";
import {
	barrasDeOcorrencias,
	filtrarSegmentos,
	historicoDoAlimentador,
	linhasDaTabela,
	mesesDoPeriodo,
} from "../conversions";
import type { ContinuidadeMensal, LinhaContinuidade, Periodo } from "../types";

const linha = (
	competencia: string,
	dec: number | null,
	fec: number | null,
): ContinuidadeMensal => ({
	competencia,
	dec,
	fec,
	n_uc: 10,
	n_interrupcoes: 1,
	horas_interrompidas: 2,
});

const semLinhaNoRecorte = (competencia: string): ContinuidadeMensal => ({
	competencia,
	dec: null,
	fec: null,
	n_uc: null,
	n_interrupcoes: null,
	horas_interrompidas: null,
});

const periodo: Periodo = { inicio: "2024-12", fim: "2025-02" };

describe("mesesDoPeriodo", () => {
	it("inclui as duas pontas e cruza o ano", () => {
		expect(mesesDoPeriodo({ inicio: "2024-11", fim: "2025-02" })).toEqual([
			"2024-11",
			"2024-12",
			"2025-01",
			"2025-02",
		]);
	});

	it("termina em dezembro de 9999 sem ultrapassar o calendário", () => {
		expect(mesesDoPeriodo({ inicio: "9999-11", fim: "9999-12" })).toEqual([
			"9999-11",
			"9999-12",
		]);
	});

	it("não cria uma série para períodos maiores que 120 meses", () => {
		expect(mesesDoPeriodo({ inicio: "0001-01", fim: "9999-12" })).toEqual([]);
		expect(mesesDoPeriodo({ inicio: "2015-01", fim: "2024-12" })).toHaveLength(
			120,
		);
		expect(mesesDoPeriodo({ inicio: "2015-01", fim: "2025-01" })).toEqual([]);
	});
});

describe("historicoDoAlimentador", () => {
	it("cobre todos os meses do período, com zero em zero e lacuna nula", () => {
		const { categories, meses, series } = historicoDoAlimentador(
			[linha("2024-12", 0, 0), linha("2025-02", 2.5, 3)],
			periodo,
			"ALM-A",
			undefined,
		);

		expect(categories.map(({ key }) => key)).toEqual([
			"2024-12",
			"2025-01",
			"2025-02",
		]);
		expect(meses.map((mes) => mes?.competencia)).toEqual([
			"2024-12",
			undefined,
			"2025-02",
		]);
		expect(series.dec).toHaveLength(1);
		expect(series.dec[0]?.id).toBe("ALM-A");
		expect(series.dec[0]?.values).toEqual([0, null, 2.5]);
		expect(series.fec[0]?.values).toEqual([0, null, 3]);
	});

	it("trata o mês sem linha no recorte como lacuna, e não como dado", () => {
		const { meses, series } = historicoDoAlimentador(
			[linha("2024-12", 1, 0.5), semLinhaNoRecorte("2025-01")],
			periodo,
			"ALM-A",
			undefined,
		);

		expect(meses[1]).toBeUndefined();
		expect(series.dec[0]?.values).toEqual([1, null, null]);
	});

	it("alinha a referência pela competência, com o mês sem dado nulo e fora do período ignorado", () => {
		const { series } = historicoDoAlimentador(
			[linha("2024-12", 7, 0.5)],
			periodo,
			"ALM-A",
			{
				rotulo: "Recife",
				rotuloCurto: "recorte",
				linhas: [
					linha("2024-11", 9, 9),
					linha("2025-02", 1.5, 0.8),
					linha("2024-12", 1.2, null),
				],
			},
		);

		expect(series.dec.map(({ label }) => label)).toEqual(["ALM-A", "Recife"]);
		expect(series.dec[1]?.shortLabel).toBe("recorte");
		expect(series.dec[1]?.values).toEqual([1.2, null, 1.5]);
		expect(series.fec[1]?.values).toEqual([null, null, 0.8]);
	});
});

const recorte = (
	segmento: string,
	municipio?: string | null,
): LinhaContinuidade => ({
	segmento,
	municipio,
	dec: 1,
	fec: 1,
	horas_interrompidas: 1,
	n_interrupcoes: 1,
	n_uc_medio: 1,
});

describe("linhasDaTabela", () => {
	it("dá ao bairro o município no nome e na identidade, mantendo a ordem da API", () => {
		const linhas = linhasDaTabela([
			recorte("Centro", "Recife"),
			recorte("Centro", "Olinda"),
			recorte("ALM-01", null),
		]);

		expect(linhas.map(({ rotulo }) => rotulo)).toEqual([
			"Centro, Recife",
			"Centro, Olinda",
			"ALM-01",
		]);
		expect(new Set(linhas.map(({ id }) => id)).size).toBe(3);
		expect(linhas.map(({ posicao }) => posicao)).toEqual([1, 2, 3]);
	});
});

describe("filtrarSegmentos", () => {
	const linhas = [
		{ rotulo: "Jaboatão dos Guararapes" },
		{ rotulo: "Recife" },
		{ rotulo: "ALM-REC-024" },
		{ rotulo: "Centro, Olinda" },
	];

	it("acha sem diferenciar acento, caixa e espaço nas pontas", () => {
		expect(filtrarSegmentos(linhas, "  JABOATAO ")).toEqual([linhas[0]]);
		expect(filtrarSegmentos(linhas, "rec")).toEqual([linhas[1], linhas[2]]);
	});

	it("acha o bairro pelo município", () => {
		expect(filtrarSegmentos(linhas, "olinda")).toEqual([linhas[3]]);
	});

	it("devolve todas as linhas, na mesma ordem, sem termo", () => {
		expect(filtrarSegmentos(linhas, "   ")).toEqual(linhas);
	});
});

describe("barrasDeOcorrencias", () => {
	it("escreve a causa nula por extenso e mede cada barra pela maior", () => {
		const barras = barrasDeOcorrencias([
			{ nome: "CLIMATICA", n_interrupcoes: 4, horas_interrompidas: 8 },
			{ nome: null, n_interrupcoes: 2, horas_interrompidas: 2 },
		]);

		expect(barras).toEqual([
			{ nome: "CLIMATICA", horas: 8, interrupcoes: 4, fracao: 1 },
			{ nome: "Não informada", horas: 2, interrupcoes: 2, fracao: 0.25 },
		]);
	});

	it("não divide por zero quando nenhum grupo tem horas", () => {
		expect(
			barrasDeOcorrencias([
				{ nome: "OSCILACAO", n_interrupcoes: 1, horas_interrompidas: 0 },
			])[0]?.fracao,
		).toBe(0);
	});
});
