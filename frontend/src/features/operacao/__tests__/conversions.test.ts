import { describe, expect, it } from "vitest";
import {
	mesesDoPeriodo,
	resolverPeriodo,
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

describe("resolverPeriodo", () => {
	it("pega os últimos 12 meses de calendário até a competência mais recente", () => {
		const entrada = [
			"2026-06",
			"2025-07",
			"2026-01",
			"2026-06",
			"2025-09",
			"2025-08",
			"2026-02",
			"2025-12",
			"2025-11",
			"2025-10",
			"2026-03",
			"2026-05",
			"2026-04",
			"2025-01",
		];
		const copia = [...entrada];

		expect(resolverPeriodo({}, entrada)).toEqual({
			inicio: "2025-07",
			fim: "2026-06",
		});
		expect(entrada).toEqual(copia);
	});

	it("limita o início à competência mais antiga da base", () => {
		expect(
			resolverPeriodo({}, ["2026-03", "2026-05", "2026-06", "2026-04"]),
		).toEqual({ inicio: "2026-03", fim: "2026-06" });
	});

	it("mantém a URL completa e válida, mesmo fora do calendário", () => {
		expect(
			resolverPeriodo({ inicio: "2030-01", fim: "2030-03" }, ["2026-05"]),
		).toEqual({ inicio: "2030-01", fim: "2030-03" });
	});

	it("volta ao padrão com período incompleto ou invertido", () => {
		const calendario = ["2024-01", "2024-02", "2025-05", "2025-06"];

		expect(resolverPeriodo({ inicio: "2025-01" }, calendario)).toEqual({
			inicio: "2024-07",
			fim: "2025-06",
		});
		expect(
			resolverPeriodo({ inicio: "2025-06", fim: "2025-01" }, calendario),
		).toEqual({ inicio: "2024-07", fim: "2025-06" });
		expect(
			resolverPeriodo({ inicio: "2025-13", fim: "2025-01" }, calendario),
		).toEqual({ inicio: "2024-07", fim: "2025-06" });
	});

	it("não resolve período sem URL nem competências", () => {
		expect(resolverPeriodo({}, [])).toBeUndefined();
		expect(
			resolverPeriodo({ inicio: undefined, fim: undefined }, []),
		).toBeUndefined();
	});

	it("resolve a URL válida mesmo com o calendário vazio", () => {
		expect(resolverPeriodo({ inicio: "2031-01", fim: "2031-02" }, [])).toEqual({
			inicio: "2031-01",
			fim: "2031-02",
		});
	});
});

describe("mesesDoPeriodo", () => {
	it("inclui as duas pontas e cruza o ano", () => {
		expect(mesesDoPeriodo({ inicio: "2024-11", fim: "2025-02" })).toEqual([
			"2024-11",
			"2024-12",
			"2025-01",
			"2025-02",
		]);
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
