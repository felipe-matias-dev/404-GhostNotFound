import { describe, expect, it } from "vitest";
import { toConsumoChart } from "../conversions";

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
