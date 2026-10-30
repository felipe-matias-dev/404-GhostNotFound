import { describe, expect, it } from "vitest";
import type { ParPeriodos } from "#/lib/filtros";
import {
	efeitosDaReceita,
	intervaloDoPar,
	janelasDoIntervalo,
	leitura,
	mesesDoPeriodo,
	tesoura,
} from "../conversions";
import type { JanelaIndicadores } from "../types";

const janela = (
	inicio: string,
	fim: string,
	receita: number,
	kwh: number,
): JanelaIndicadores => ({
	inicio,
	fim,
	receita_faturada: receita,
	receita_energia: receita,
	kwh_faturado: kwh,
	n_uc_medio: 10,
	tarifa_media: receita / kwh,
	tarifa_base_media: receita / kwh,
});

const par = (base: string, atual: string): ParPeriodos => ({
	periodo_base: base,
	periodo_atual: atual,
});

describe("mesesDoPeriodo", () => {
	it("conta os meses inclusive nas duas pontas", () => {
		expect(mesesDoPeriodo("2025-01/2025-12")).toBe(12);
		expect(mesesDoPeriodo("2025-03/2025-03")).toBe(1);
		expect(mesesDoPeriodo("2024-01/2025-03")).toBe(15);
	});

	it("atravessa mais de um ano e passa do limite do gráfico", () => {
		expect(mesesDoPeriodo("2024-01/2026-01")).toBe(25);
	});
});

describe("intervaloDoPar", () => {
	it("vai do menor início ao maior fim dos dois períodos", () => {
		expect(
			intervaloDoPar(par("2024-03/2024-05", "2025-01/2025-02")),
		).toEqual({ inicio: "2024-03", fim: "2025-02" });
	});

	it("aceita o período atual começando antes da base", () => {
		expect(
			intervaloDoPar(par("2025-01/2025-03", "2024-11/2024-12")),
		).toEqual({ inicio: "2024-11", fim: "2025-03" });
	});
});

describe("janelasDoIntervalo", () => {
	const janelas = [
		janela("2023-12", "2024-02", 100, 1000),
		janela("2024-01", "2024-03", 110, 1050),
		janela("2024-02", "2024-04", 120, 1100),
		janela("2025-01", "2025-03", 150, 1300),
	];

	it("mantém só as janelas completas dentro do intervalo", () => {
		expect(
			janelasDoIntervalo(janelas, { inicio: "2024-01", fim: "2025-03" }).map(
				(j) => j.inicio,
			),
		).toEqual(["2024-01", "2024-02", "2025-01"]);
	});

	it("não deixa escapar uma janela que atravessa a borda", () => {
		expect(
			janelasDoIntervalo(janelas, { inicio: "2024-02", fim: "2024-04" }).map(
				(j) => j.inicio,
			),
		).toEqual(["2024-02"]);
	});
});

describe("tesoura", () => {
	it("mede a variação das somas recebidas sem acumular novamente as janelas", () => {
		const t = tesoura(
			[
				janela("2024-01", "2024-12", 120, 1200),
				janela("2024-02", "2025-01", 132, 1176),
			],
			12,
		);
		expect(t.categories.map((c) => c.key)).toEqual(["2024-12", "2025-01"]);
		expect(t.series[0].values).toEqual([0, expect.closeTo(0.1)]);
		expect(t.series[1].values).toEqual([0, expect.closeTo(-0.02)]);
		expect(t.somas[1]).toEqual({ receita: 132, kwh: 1176 });
	});

	it("usa o tamanho da janela selecionada no rótulo", () => {
		const trimestre = tesoura(
			[
				janela("2024-01", "2024-03", 120, 1200),
				janela("2024-02", "2024-04", 132, 1176),
			],
			3,
		);
		expect(trimestre.categories[0]?.title).toBe("3 meses até mar/2024");
		expect(
			tesoura(
				[
					janela("2025-01", "2025-01", 10, 100),
					janela("2025-02", "2025-02", 11, 110),
				],
				1,
			).categories[0]?.title,
		).toBe("1 mês até jan/2025");
	});

	it("mantém os meses retornados mesmo quando há um intervalo sem janelas", () => {
		expect(
			tesoura(
				[
					janela("2024-01", "2024-12", 120, 1200),
					janela("2024-04", "2025-03", 132, 1176),
				],
				12,
			).categories.map((c) => c.key),
		).toEqual(["2024-12", "2025-03"]);
		expect(
			tesoura([janela("2024-01", "2024-12", 120, 1200)], 12).series,
		).toEqual([]);
	});

	it("não inventa variação para uma série cuja primeira soma é zero", () => {
		const t = tesoura(
			[
				janela("2024-01", "2024-12", 0, 1200),
				janela("2024-02", "2025-01", 132, 1176),
			],
			12,
		);
		expect(t.series[0].values).toEqual([null, null]);
		expect(t.series[1].values[1]).toBeCloseTo(-0.02);
	});

	it("não desenha a tesoura com menos de duas janelas", () => {
		expect(tesoura([], 12).categories).toEqual([]);
	});
});

describe("leitura", () => {
	it("descreve a tesoura pela direção das duas variações", () => {
		expect(leitura(8, -4)).toBe(
			"A receita cresceu com menos energia faturada.",
		);
		expect(leitura(3, 5)).toBe(
			"A receita cresceu menos que a energia faturada.",
		);
		expect(leitura(-5, -2)).toBe("A receita caiu mais que a energia faturada.");
	});

	it("trata como estável a variação que arredonda para 0,0%", () => {
		expect(leitura(0.04, -3)).toBe(
			"A receita ficou estável com menos energia faturada.",
		);
		expect(leitura(null, 2)).toBeNull();
	});
});

describe("efeitosDaReceita", () => {
	it("dá o peso de cada efeito sobre a receita base, sem os totais", () => {
		const efeitos = efeitosDaReceita([
			{ id: "base", label: "Receita base", value: 200, kind: "total" },
			{ id: "tarifa", label: "Preço · tarifa", value: 16, kind: "delta" },
			{ id: "volume", label: "Volume", value: -6, kind: "delta" },
			{ id: "atual", label: "Receita atual", value: 210, kind: "total" },
		]);
		expect(efeitos.map((e) => [e.id, e.pct])).toEqual([
			["tarifa", 0.08],
			["volume", -0.03],
		]);
	});

	it("não dá peso sem receita base", () => {
		const [efeito] = efeitosDaReceita([
			{ id: "base", label: "Receita base", value: 0, kind: "total" },
			{ id: "tarifa", label: "Preço · tarifa", value: 5, kind: "delta" },
		]);
		expect(efeito?.pct).toBeNull();
	});
});
