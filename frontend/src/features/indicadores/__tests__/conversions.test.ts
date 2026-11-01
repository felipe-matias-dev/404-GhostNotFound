import { describe, expect, it } from "vitest";
import type { ParPeriodos } from "#/lib/filtros";
import { intervaloDoPar } from "../conversions";

const par = (base: string, atual: string): ParPeriodos => ({
	periodo_base: base,
	periodo_atual: atual,
});

describe("intervaloDoPar", () => {
	it("vai do menor início ao maior fim dos dois períodos", () => {
		expect(intervaloDoPar(par("2024-03/2024-05", "2025-01/2025-02"))).toEqual({
			inicio: "2024-03",
			fim: "2025-02",
		});
	});

	it("aceita o período atual começando antes da base", () => {
		expect(intervaloDoPar(par("2025-01/2025-03", "2024-11/2024-12"))).toEqual({
			inicio: "2024-11",
			fim: "2025-03",
		});
	});
});
