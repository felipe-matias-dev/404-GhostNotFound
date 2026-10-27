import { describe, expect, it } from "vitest";
import { atalhos, parDoAtual, passosDaPonte } from "../conversions";
import type { DecomposicaoLinha, ParPeriodos } from "../types";

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

const linha = (
	segmento: string,
	receita_base: number,
	tarifa: number,
	bandeira: number,
	volume: number,
	mix: number,
): DecomposicaoLinha => {
	const variacao = tarifa + bandeira + volume + mix;
	return {
		nivel: "municipio",
		segmento,
		periodo_base: "2024-01/2024-12",
		periodo_atual: "2025-01/2025-12",
		receita_base,
		receita_atual: receita_base + variacao,
		variacao_receita: variacao,
		efeito_preco: tarifa + bandeira,
		efeito_tarifa: tarifa,
		efeito_bandeira: bandeira,
		efeito_volume: volume,
		efeito_mix: mix,
	};
};

describe("passosDaPonte", () => {
	it("soma os segmentos e fecha da receita base à atual sem contar o preço duas vezes", () => {
		const passos = passosDaPonte([
			linha("Recife", 1000.1, 30.2, -12.3, -40.1, 0.1),
			linha("Olinda", 500.2, 10.1, -6.2, 15.3, -0.2),
		]);
		expect(passos.map((p) => [p.id, p.value])).toEqual([
			["base", 1500.3],
			["tarifa", 40.3],
			["bandeira", -18.5],
			["volume", -24.8],
			["mix", -0.1],
			["atual", 1497.2],
		]);
		const [base, ...resto] = passos;
		const efeitos = resto.filter((p) => p.kind === "delta");
		const fim = efeitos.reduce((total, p) => total + p.value, base?.value ?? 0);
		expect(fim).toBeCloseTo(passos.at(-1)?.value ?? Number.NaN, 2);
	});
});
