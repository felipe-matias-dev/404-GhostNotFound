import { describe, expect, it } from "vitest";
import {
	aplicarPatch,
	aplicarPeriodoPadrao,
	type FiltrosCompartilhados,
	gravarFiltrosCompartilhados,
	lerFiltrosCompartilhados,
	periodoAnterior,
} from "../filtros";

const vazio: FiltrosCompartilhados = {
	municipio: undefined,
	bairro: undefined,
	classe: undefined,
	periodo_base: undefined,
	periodo_atual: undefined,
};

const recorte: FiltrosCompartilhados = {
	municipio: "Paulista",
	bairro: "Janga",
	classe: "B1",
	periodo_base: "2024-01/2024-03",
	periodo_atual: "2025-01/2025-03",
};

describe("filtros compartilhados", () => {
	it("traduz o período da Rede sem perder base ou recorte", () => {
		expect(
			lerFiltrosCompartilhados(
				"/rede",
				gravarFiltrosCompartilhados("/rede", recorte),
			),
		).toEqual(recorte);
	});

	it("grava a Rede em duas pontas, nunca com o par inteiro", () => {
		const busca = gravarFiltrosCompartilhados("/rede", recorte);
		expect(busca).toEqual({
			municipio: "Paulista",
			bairro: "Janga",
			classe: "B1",
			periodo_base: "2024-01/2024-03",
			inicio: "2025-01",
			fim: "2025-03",
		});
		expect("periodo_atual" in busca).toBe(false);
	});

	it("só aceita o período pelo contrato de cada tela", () => {
		expect(
			lerFiltrosCompartilhados("/receita", {
				inicio: "2025-01",
				fim: "2025-03",
			}),
		).toEqual(vazio);
		expect(
			lerFiltrosCompartilhados("/rede", {
				periodo_atual: "2025-01/2025-03",
			}),
		).toEqual(vazio);
	});

	it("descarta base sem atual, mês 13 e faixa invertida", () => {
		expect(
			lerFiltrosCompartilhados("/", { periodo_base: "2023-01/2023-03" }),
		).toEqual(vazio);
		expect(
			lerFiltrosCompartilhados("/", { periodo_atual: "2025-13/2025-14" }),
		).toEqual(vazio);
		expect(
			lerFiltrosCompartilhados("/", { periodo_atual: "2025-03/2025-01" }),
		).toEqual(vazio);
		expect(
			lerFiltrosCompartilhados("/rede", {
				inicio: "2025-03",
				fim: "2025-01",
			}),
		).toEqual(vazio);
	});

	it("normaliza períodos inválidos e bairro órfão", () => {
		expect(
			lerFiltrosCompartilhados("/", {
				periodo_atual: "2025-13/2025-14",
				bairro: "Janga",
			}),
		).toEqual(vazio);
	});

	it("sugere a base anterior sem substituir o período atual", () => {
		expect(
			lerFiltrosCompartilhados("/", { periodo_atual: "2025-01/2025-03" })
				.periodo_base,
		).toBe("2024-01/2024-03");
		expect(periodoAnterior("2025-01/2025-03")).toBe("2024-01/2024-03");
		expect(periodoAnterior("0000-01/0000-03")).toBeUndefined();
	});
});

describe("aplicarPatch", () => {
	it("trocar ou remover município limpa o bairro e mantém classe e período", () => {
		expect(aplicarPatch(recorte, { municipio: "Recife" })).toMatchObject({
			municipio: "Recife",
			bairro: undefined,
			classe: "B1",
			periodo_base: recorte.periodo_base,
			periodo_atual: recorte.periodo_atual,
		});
		expect(
			aplicarPatch(recorte, { municipio: undefined }).bairro,
		).toBeUndefined();
	});

	it("deixa o bairro explícito do patch e ignora troca de classe", () => {
		expect(
			aplicarPatch(recorte, {
				municipio: "Recife",
				bairro: "Boa Viagem",
			}).bairro,
		).toBe("Boa Viagem");
		expect(aplicarPatch(recorte, { classe: "A4" })).toMatchObject({
			bairro: "Janga",
			classe: "A4",
		});
	});

	it("não mantém bairro sem município", () => {
		expect(
			aplicarPatch({ municipio: undefined, bairro: "Janga" }, {}).bairro,
		).toBeUndefined();
	});
});

describe("aplicarPeriodoPadrao", () => {
	const padrao = {
		periodo_base: "2024-01/2024-03",
		periodo_atual: "2025-01/2025-03",
	};

	it("usa o padrão só sem período atual", () => {
		expect(aplicarPeriodoPadrao({ municipio: "Paulista" }, padrao)).toMatchObject(
			padrao,
		);
	});

	it("não inventa período sem catálogo", () => {
		expect(aplicarPeriodoPadrao({}, undefined)).toEqual(vazio);
	});

	it("preserva exato o período válido que veio da URL", () => {
		const explicito = {
			periodo_base: "2024-11/2024-12",
			periodo_atual: "2025-11/2025-12",
		};
		expect(aplicarPeriodoPadrao(explicito, padrao)).toEqual({
			...vazio,
			...explicito,
		});
	});
});
