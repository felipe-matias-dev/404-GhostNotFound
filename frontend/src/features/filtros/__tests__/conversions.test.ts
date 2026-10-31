import { describe, expect, it } from "vitest";
import type { ParPeriodos } from "#/lib/filtros";
import { parDoAtual, parPadrao, parPadraoMensal } from "../conversions";

const par = (periodo_base: string, periodo_atual: string): ParPeriodos => ({
	periodo_base,
	periodo_atual,
});

describe("parPadrao", () => {
	it("prefere a janela anual mais recente gravada", () => {
		const pares = [
			par("2023-01/2023-12", "2024-01/2024-12"),
			par("2024-01/2024-12", "2025-01/2025-12"),
			par("2023-05/2023-07", "2024-05/2024-07"),
		];
		expect(parPadrao(pares)).toEqual(par("2024-01/2024-12", "2025-01/2025-12"));
	});

	it("sem janela anual, usa o período atual mais recente", () => {
		const pares = [
			par("2024-11/2024-11", "2025-03/2025-03"),
			par("2024-10/2024-10", "2025-02/2025-02"),
		];
		expect(parPadrao(pares)).toEqual(par("2024-11/2024-11", "2025-03/2025-03"));
	});

	it("não inventa período sem catálogo", () => {
		expect(parPadrao([])).toBeUndefined();
	});
});

describe("parPadraoMensal", () => {
	it("compara o mês mais recente com o mesmo mês do ano anterior", () => {
		expect(
			parPadraoMensal(["2024-03", "2024-04", "2025-03", "2025-04"]),
		).toEqual(par("2024-04/2024-04", "2025-04/2025-04"));
	});

	it("cai no mês anterior quando não há o mesmo mês do ano anterior", () => {
		expect(parPadraoMensal(["2024-12", "2025-01"])).toEqual(
			par("2024-12/2024-12", "2025-01/2025-01"),
		);
	});

	it("não cria período com série insuficiente", () => {
		expect(parPadraoMensal([])).toBeUndefined();
		expect(parPadraoMensal(["2025-03"])).toBeUndefined();
	});
});

describe("parDoAtual", () => {
	it("não inventa par para período fora do catálogo", () => {
		const pares = [par("2024-01/2024-12", "2025-01/2025-12")];
		expect(parDoAtual(pares, "2025-01/2025-03")).toBeUndefined();
	});
	it("ignora pares do catálogo cuja base toca ou ultrapassa o período atual", () => {
		const atual = "2025-01/2025-03";
		const invalido = par("2024-12/2025-01", atual);
		const valido = par("2023-01/2023-03", atual);
		expect(
			parDoAtual([invalido, valido], atual, invalido.periodo_base),
		).toEqual(valido);
		expect(parDoAtual([invalido], atual)).toBeUndefined();
		expect(parPadrao([invalido])).toBeUndefined();
	});
});
