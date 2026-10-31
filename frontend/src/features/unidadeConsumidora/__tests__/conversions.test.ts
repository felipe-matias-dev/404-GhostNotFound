import { describe, expect, it } from "vitest";
import {
	maiorParte,
	partesDaConta,
	textoDosDias,
	toConsumoChart,
} from "../conversions";
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
	dias_faturados: 31,
	dias_faturados_comparada: 30,
	consumo: 40,
	tarifa: -5,
	bandeira: -8,
	tributos: 3.5,
	leitura_estimada: false,
};

describe("partesDaConta", () => {
	it("keeps the fixed card order, without a part for the days", () => {
		expect(partesDaConta(variacao).map((p) => [p.id, p.valor])).toEqual([
			["consumo", 40],
			["tarifa", -5],
			["bandeira", -8],
			["tributos", 3.5],
		]);
	});
});

describe("textoDosDias", () => {
	it("says how many days each bill covered", () => {
		expect(
			textoDosDias({
				...variacao,
				dias_faturados: 33,
				dias_faturados_comparada: 29,
			}),
		).toBe("Esta conta cobriu 33 dias; a do ano anterior, 29.");
	});

	it("uses the singular for one day", () => {
		expect(
			textoDosDias({
				...variacao,
				dias_faturados: 1,
				dias_faturados_comparada: 30,
			}),
		).toBe("Esta conta cobriu 1 dia; a do ano anterior, 30.");
	});

	it("says only what is known when a bill does not bring the days", () => {
		expect(textoDosDias({ ...variacao, dias_faturados_comparada: null })).toBe(
			"Esta conta cobriu 31 dias.",
		);
		expect(textoDosDias({ ...variacao, dias_faturados: null })).toBe(
			"A conta do ano anterior cobriu 30 dias.",
		);
	});

	it("is empty when neither bill brings the days", () => {
		expect(
			textoDosDias({
				...variacao,
				dias_faturados: null,
				dias_faturados_comparada: null,
			}),
		).toBeNull();
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
