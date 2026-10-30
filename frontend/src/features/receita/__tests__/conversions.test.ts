import { describe, expect, it } from "vitest";
import {
	passosDaPonte,
	type Ranking,
	rankingDaQueda,
} from "../conversions";
import { atalhos, parDoAtual } from "#/features/filtros/conversions";
import type { ParPeriodos } from "#/lib/filtros";
import type { DecomposicaoLinha } from "../types";

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

	it("fecha a receita atual pelos passos quando as linhas só fecham dentro da tolerância", () => {
		const linhas = Array.from({ length: 90 }, (_, i) => ({
			...linha(`B${i}`, 1000, 10, -5, 20, -3),
			receita_atual: 1022.02,
		}));
		const passos = passosDaPonte(linhas);
		expect(passos.at(-1)?.value).toBe(90 * 1022);
	});
});

describe("rankingDaQueda", () => {
	const nomes = (r: Ranking) =>
		r.itens.map((c) => [c.linha.segmento, c.valor, c.fracao]);

	it("lista só quem caiu na causa escolhida, da maior queda, com barra relativa à maior", () => {
		const linhas = [
			linha("Recife", 1000, 50, -10, -40, 0),
			linha("Olinda", 500, -5, -20, -10, 0),
			linha("Paulista", 300, 0, 0, 25, 0),
		];
		const porVolume = rankingDaQueda(linhas, "volume");
		expect(porVolume.houveQueda).toBe(true);
		expect([porVolume.quedas, porVolume.total]).toEqual([2, 3]);
		expect(nomes(porVolume)).toEqual([
			["Recife", -40, 1],
			["Olinda", -10, 0.25],
		]);
		expect(nomes(rankingDaQueda(linhas, "variacao"))).toEqual([
			["Olinda", -35, 1],
		]);
	});

	it("sem queda, traz quem subiu menos e avisa que não houve queda", () => {
		const linhas = [
			linha("Recife", 1000, 0, 0, 40, 0),
			linha("Olinda", 500, 0, 0, 0, 0),
			linha("Paulista", 300, 0, 0, 20, 0),
		];
		const r = rankingDaQueda(linhas, "volume", "brl", 2);
		expect(r.houveQueda).toBe(false);
		expect(nomes(r)).toEqual([
			["Olinda", 0, 0],
			["Paulista", 20, 1],
		]);
	});

	it("corta no limite", () => {
		const linhas = Array.from({ length: 8 }, (_, i) =>
			linha(`S${i}`, 100, 0, 0, -(i + 1), 0),
		);
		const r = rankingDaQueda(linhas, "volume");
		expect(r.quedas).toBe(8);
		expect(r.itens.map((c) => c.linha.segmento)).toEqual([
			"S7",
			"S6",
			"S5",
			"S4",
			"S3",
		]);
	});

	it("em %, ranqueia pelo peso sobre a receita base e deixa de fora quem não tem base", () => {
		const linhas = [
			linha("Recife", 1000, 0, 0, -50, 0),
			linha("Olinda", 100, 0, 0, -20, 0),
			linha("Nova", 0, 0, 0, -5, 0),
		];
		expect(nomes(rankingDaQueda(linhas, "volume", "brl"))[0]?.[0]).toBe(
			"Recife",
		);
		const r = rankingDaQueda(linhas, "volume", "pct");
		expect([r.quedas, r.total]).toEqual([3, 3]);
		expect(r.itens.map((c) => [c.linha.segmento, c.pct, c.fracao])).toEqual([
			["Olinda", -0.2, 1],
			["Recife", -0.05, 0.25],
		]);
	});

	it("em %, conta como queda o segmento sem receita base mesmo fora da lista", () => {
		const linhas = [
			linha("Recife", 1000, 0, 0, 0, 10),
			linha("Olinda", 100, 0, 0, 0, 0),
			linha("Nova", 0, 0, 0, 0, -800),
		];
		const r = rankingDaQueda(linhas, "mix", "pct");
		expect(r.houveQueda).toBe(true);
		expect([r.quedas, r.total]).toEqual([1, 3]);
		expect(r.itens).toEqual([]);
	});
});
