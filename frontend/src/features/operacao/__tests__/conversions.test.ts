import { describe, expect, it } from "vitest";
import {
	filtrarSegmentos,
	historicoDoAlimentador,
	mesesDoPeriodo,
} from "../conversions";
import type { AlimentadorMensal, Periodo } from "../types";

const linha = (
	competencia: string,
	dec: number,
	fec: number,
	cod = "ALM-A",
): AlimentadorMensal => ({
	cod_alimentador: cod,
	competencia,
	dec,
	fec,
	n_uc: 10,
	n_interrupcoes: 1,
	horas_interrompidas: 2,
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

	it("não mistura outro alimentador nem agrega meses", () => {
		const { series } = historicoDoAlimentador(
			[
				linha("2024-12", 1, 0.5),
				linha("2024-12", 9, 9, "ALM-B"),
				linha("2025-01", 4, 0.5, "ALM-B"),
				linha("2025-02", 2, 0.5),
			],
			periodo,
			"ALM-A",
			undefined,
		);

		expect(series.dec[0]?.values).toEqual([1, null, 2]);
	});

	it("alinha a empresa pela competência, com o mês sem dado nulo e fora do período ignorado", () => {
		const { series } = historicoDoAlimentador(
			[linha("2024-12", 7, 0.5)],
			periodo,
			"ALM-A",
			[
				{ competencia: "2024-11", dec: 9, fec: 9 },
				{ competencia: "2025-02", dec: 1.5, fec: 0.8 },
				{ competencia: "2024-12", dec: 1.2, fec: null },
			],
		);

		expect(series.dec.map(({ id }) => id)).toEqual(["ALM-A", "empresa"]);
		expect(series.dec[1]?.values).toEqual([1.2, null, 1.5]);
		expect(series.fec[1]?.values).toEqual([null, null, 0.8]);
	});

	it("deixa a série toda nula quando não há linha do alimentador", () => {
		const { series } = historicoDoAlimentador(
			[linha("2024-12", 1, 1, "ALM-B")],
			periodo,
			"ALM-A",
			undefined,
		);

		expect(series.dec[0]?.values).toEqual([null, null, null]);
	});
});

describe("filtrarSegmentos", () => {
	const linhas = [
		{ segmento: "Jaboatão dos Guararapes" },
		{ segmento: "Recife" },
		{ segmento: "ALM-REC-024" },
	];

	it("acha sem diferenciar acento, caixa e espaço nas pontas", () => {
		expect(filtrarSegmentos(linhas, "  JABOATAO ")).toEqual([linhas[0]]);
		expect(filtrarSegmentos(linhas, "rec")).toEqual([linhas[1], linhas[2]]);
	});

	it("devolve todas as linhas, na mesma ordem, sem termo", () => {
		expect(filtrarSegmentos(linhas, "   ")).toEqual(linhas);
	});
});
