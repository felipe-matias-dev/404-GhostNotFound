import { describe, expect, it } from "vitest";
import { maiorParte, partesDaConta, toConsumoChart } from "../conversions";
import type { VariacaoConta } from "../types";

describe("toConsumoChart", () => {
	it("keeps seasonal pairs across years and distinguishes missing readings from zero", () => {
		const chart = toConsumoChart([
			{
				competencia: "2024-12",
				kwh_ano_anterior: 0,
				kwh_faturado: null,
				receita_faturada: null,
				bandeira: null,
				dias_faturados: null,
			},
			{
				competencia: "2025-01",
				kwh_ano_anterior: null,
				kwh_faturado: 0,
				receita_faturada: 0,
				bandeira: "verde",
				dias_faturados: 30,
			},
		]);
		expect(chart.categories).toEqual([
			{ key: "2024-12", label: "dez 24", title: "dez/2024 / dez/2023" },
			{ key: "2025-01", label: "jan 25", title: "jan/2025 / jan/2024" },
		]);
		expect(chart.series.map(({ id, values }) => ({ id, values }))).toEqual([
			{ id: "atual", values: [null, 0] },
			{ id: "ano-anterior", values: [0, null] },
		]);
	});
});

// Valores inventados, no formato da amostra sintética: nada vem da Gold real (DEC-024).
const variacao: VariacaoConta = {
	competencia: "2025-12",
	competencia_comparada: "2024-12",
	conta: 230.5,
	conta_comparada: 200,
	diferenca: 30.5,
	dias: null,
	consumo: 40,
	tarifa: -5,
	bandeira: -8,
	tributos: 3.5,
	leitura_estimada: false,
};

describe("partesDaConta", () => {
	it("keeps the card order and leaves out days when the API merges them into consumption", () => {
		expect(partesDaConta(variacao).map((p) => [p.id, p.valor])).toEqual([
			["consumo", 40],
			["tarifa", -5],
			["bandeira", -8],
			["tributos", 3.5],
		]);
	});

	it("shows days right after consumption when the API separates them", () => {
		const partes = partesDaConta({ ...variacao, dias: 12, consumo: 28 });
		expect(partes.map((p) => p.id)).toEqual([
			"consumo",
			"dias",
			"tarifa",
			"bandeira",
			"tributos",
		]);
	});
});

describe("maiorParte", () => {
	it("picks the largest part that raised the bill when the bill went up", () => {
		const partes = partesDaConta({ ...variacao, consumo: 100, bandeira: -900 });
		expect(maiorParte(partes, 30.5)?.id).toBe("consumo");
	});

	it("picks the largest part that lowered the bill when the bill went down", () => {
		const partes = partesDaConta({
			...variacao,
			consumo: 300,
			tarifa: -200,
			bandeira: -250,
			tributos: 30,
		});
		expect(maiorParte(partes, -120)?.id).toBe("bandeira");
	});

	it("keeps the first part of the card order on a tie", () => {
		const partes = partesDaConta({
			...variacao,
			consumo: 0,
			tarifa: 50,
			bandeira: 50,
			tributos: 0,
		});
		expect(maiorParte(partes, 100)?.id).toBe("tarifa");
	});

	it("returns null when the bill did not change", () => {
		const partes = partesDaConta({
			...variacao,
			consumo: 50,
			tarifa: -50,
			bandeira: 0,
			tributos: 0,
		});
		expect(maiorParte(partes, 0)).toBeNull();
	});
});
