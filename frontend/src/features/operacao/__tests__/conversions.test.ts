import { describe, expect, it } from "vitest";
import {
	filtrarSegmentos,
	mesesDoPeriodo,
	serieDoAlimentador,
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

describe("serieDoAlimentador", () => {
	it("cobre todos os meses do período, com zero em zero e lacuna nula", () => {
		const { categories, series } = serieDoAlimentador(
			[linha("2024-12", 0, 0), linha("2025-02", 2.5, 3)],
			periodo,
			"ALM-A",
			"dec",
		);

		expect(categories.map(({ key }) => key)).toEqual([
			"2024-12",
			"2025-01",
			"2025-02",
		]);
		expect(series).toHaveLength(1);
		expect(series[0]?.id).toBe("ALM-A");
		expect(series[0]?.label).toBe("ALM-A");
		expect(series[0]?.values).toEqual([0, null, 2.5]);
	});

	it("não mistura outro alimentador nem agrega meses", () => {
		const { series } = serieDoAlimentador(
			[
				linha("2024-12", 1, 0.5),
				linha("2024-12", 9, 9, "ALM-B"),
				linha("2025-01", 4, 0.5, "ALM-B"),
				linha("2025-02", 2, 0.5),
			],
			periodo,
			"ALM-A",
			"dec",
		);

		expect(series[0]?.values).toEqual([1, null, 2]);
	});

	it("preserva o FEC quando é o critério", () => {
		const { series } = serieDoAlimentador(
			[linha("2024-12", 7, 0.5), linha("2025-02", 7, 3)],
			periodo,
			"ALM-A",
			"fec",
		);

		expect(series[0]?.values).toEqual([0.5, null, 3]);
	});

	it("deixa a série toda nula quando não há linha do alimentador", () => {
		const { series } = serieDoAlimentador(
			[linha("2024-12", 1, 1, "ALM-B")],
			periodo,
			"ALM-A",
			"dec",
		);

		expect(series[0]?.values).toEqual([null, null, null]);
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
