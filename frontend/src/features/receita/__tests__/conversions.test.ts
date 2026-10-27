import { describe, expect, it } from "vitest";
import { atalhos, parDoAtual } from "../conversions";
import type { ParPeriodos } from "../types";

const par = (periodo_base: string, periodo_atual: string): ParPeriodos => ({
	periodo_base,
	periodo_atual,
});

describe("parDoAtual", () => {
	const pares = [
		par("2023-01/2023-03", "2025-01/2025-03"),
		par("2024-01/2024-03", "2025-01/2025-03"),
		par("2023-07/2023-09", "2025-07/2025-09"),
	];

	it("prefere o mesmo trecho um ano antes", () => {
		expect(parDoAtual(pares, "2025-01/2025-03")).toEqual(
			par("2024-01/2024-03", "2025-01/2025-03"),
		);
	});

	it("respeita a base pedida quando a Gold a gravou", () => {
		expect(parDoAtual(pares, "2025-01/2025-03", "2023-01/2023-03")).toEqual(
			par("2023-01/2023-03", "2025-01/2025-03"),
		);
		expect(parDoAtual(pares, "2025-01/2025-03", "2022-01/2022-03")).toEqual(
			par("2024-01/2024-03", "2025-01/2025-03"),
		);
	});

	it("cai na base mais recente sem o ano anterior e devolve nada sem par", () => {
		expect(parDoAtual(pares, "2025-07/2025-09")).toEqual(
			par("2023-07/2023-09", "2025-07/2025-09"),
		);
		expect(parDoAtual(pares, "2025-04/2025-06")).toBeUndefined();
	});
});

describe("atalhos", () => {
	it("conta do último mês gravado, sem repetir período nem oferecer o que falta", () => {
		const pares = [
			par("2024-01/2024-12", "2025-01/2025-12"),
			par("2024-10/2024-12", "2025-10/2025-12"),
			par("2024-12/2024-12", "2025-12/2025-12"),
		];
		expect(atalhos(pares)).toEqual([
			{ rotulo: "Últimos 12 meses", atual: "2025-01/2025-12" },
			{ rotulo: "Último trimestre", atual: "2025-10/2025-12" },
			{ rotulo: "Último mês", atual: "2025-12/2025-12" },
		]);
	});

	it("atravessa a virada do ano", () => {
		const pares = [par("2024-02/2025-01", "2025-02/2026-01")];
		expect(atalhos(pares)).toEqual([
			{ rotulo: "Últimos 12 meses", atual: "2025-02/2026-01" },
		]);
	});
});
