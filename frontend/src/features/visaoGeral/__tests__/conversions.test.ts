import { describe, expect, it } from "vitest";
import {
	compararMeses,
	parDoMes,
	parEscolhido,
	parPadrao,
} from "../conversions";
import type { KpisMensais, ParPeriodos } from "../types";

const par = (base: string, atual: string): ParPeriodos => ({
	periodo_base: `${base}/${base}`,
	periodo_atual: `${atual}/${atual}`,
});

const meses = (inicio: string, quantos: number) => {
	const [ano, mes] = inicio.split("-").map(Number);
	return Array.from({ length: quantos }, (_, i) => {
		const total = ano * 12 + mes - 1 + i;
		return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
	});
};

describe("parPadrao", () => {
	it("compara o mês mais recente com o mesmo mês do ano anterior", () => {
		expect(parPadrao(meses("2024-01", 24))).toEqual(par("2024-12", "2025-12"));
	});

	it("usa o mês anterior quando a série tem menos de um ano", () => {
		expect(parPadrao(meses("2025-01", 6))).toEqual(par("2025-05", "2025-06"));
	});

	it("não compara nada com um mês só", () => {
		expect(parPadrao(["2025-01"])).toBeUndefined();
	});
});

describe("parDoMes", () => {
	const competencias = meses("2024-01", 24);

	it("mantém a relação pedida quando a base existe", () => {
		expect(parDoMes(competencias, "2025-03", "mes")).toEqual(
			par("2025-02", "2025-03"),
		);
	});

	it("troca de relação quando a base pedida está fora da série", () => {
		expect(parDoMes(competencias, "2024-03", "ano")).toEqual(
			par("2024-02", "2024-03"),
		);
	});

	it("vira o ano no mês anterior de janeiro", () => {
		expect(parDoMes(competencias, "2025-01", "mes")).toEqual(
			par("2024-12", "2025-01"),
		);
	});
});

describe("parEscolhido", () => {
	const competencias = meses("2024-01", 24);

	it("aceita da URL dois meses da série, com a base antes do atual", () => {
		expect(
			parEscolhido(competencias, "2024-03/2024-03", "2025-07/2025-07"),
		).toEqual(par("2024-03", "2025-07"));
	});

	it.each([
		["trecho de vários meses", "2024-01/2024-12", "2025-01/2025-12"],
		["mês fora da série", "2023-12/2023-12", "2024-12/2024-12"],
		["base depois do atual", "2025-07/2025-07", "2024-07/2024-07"],
		["sem par na URL", undefined, undefined],
	])("volta ao padrão com %s", (_, base, atual) => {
		expect(parEscolhido(competencias, base, atual)).toEqual(
			par("2024-12", "2025-12"),
		);
	});
});

describe("compararMeses", () => {
	const linha = (
		competencia: string,
		valores: Partial<KpisMensais>,
	): KpisMensais => ({
		competencia,
		kwh_faturado: 1000,
		receita_faturada: 800,
		receita_energia: 700,
		dec: 2,
		fec: 0.5,
		n_chamados: 10,
		satisfacao_media: 4,
		...valores,
	});

	it("dá a variação em fração e respeita os valores da Gold", () => {
		const resultado = compararMeses(
			[
				linha("2024-03", {}),
				linha("2025-03", { receita_faturada: 840, dec: 1.5 }),
			],
			par("2024-03", "2025-03"),
		);
		expect(resultado.atual.valores.receita_faturada).toBe(840);
		expect(resultado.variacao.receita_faturada).toBeCloseTo(0.05);
		expect(resultado.variacao.dec).toBeCloseTo(-0.25);
		expect(resultado.variacao.kwh_faturado).toBe(0);
	});

	it("deixa a variação vazia sem valor num dos lados ou com base zero", () => {
		const resultado = compararMeses(
			[
				linha("2024-03", { satisfacao_media: null, n_chamados: 0 }),
				linha("2025-03", { dec: null }),
			],
			par("2024-03", "2025-03"),
		);
		expect(resultado.atual.valores.dec).toBeNull();
		expect(resultado.variacao.dec).toBeNull();
		expect(resultado.variacao.satisfacao_media).toBeNull();
		expect(resultado.variacao.n_chamados).toBeNull();
	});
});
