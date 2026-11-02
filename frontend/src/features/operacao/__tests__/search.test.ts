import { describe, expect, it } from "vitest";
import { lerFiltrosCompartilhados } from "#/lib/filtros";
import { redeSearchSchema } from "../search";

describe("redeSearchSchema", () => {
	it("remove um bairro órfão de município", () => {
		const search = redeSearchSchema.parse({ bairro: "Boa Viagem" });

		expect(search.bairro).toBeUndefined();
		expect(search.visao).toBeUndefined();
	});

	it("preserva a geografia na visão de alimentadores", () => {
		const search = redeSearchSchema.parse({
			visao: "alimentadores",
			municipio: "Recife",
			bairro: "Boa Viagem",
		});

		expect(search.visao).toBe("alimentadores");
		expect(search.municipio).toBe("Recife");
		expect(search.bairro).toBe("Boa Viagem");
	});

	it("barra mês fora do formato AAAA-MM", () => {
		const mesTreze = redeSearchSchema.parse({
			inicio: "2025-13",
			fim: "2025-12",
		});
		const mesCurto = redeSearchSchema.parse({
			inicio: "2025-1",
			fim: "2025-12",
		});

		expect(
			lerFiltrosCompartilhados("/rede", mesTreze).periodo_atual,
		).toBeUndefined();
		expect(
			lerFiltrosCompartilhados("/rede", mesCurto).periodo_atual,
		).toBeUndefined();
	});

	it("remove as duas pontas de um período incompleto ou invertido", () => {
		const soInicio = redeSearchSchema.parse({ inicio: "2025-03" });
		const invertido = redeSearchSchema.parse({
			inicio: "2025-03",
			fim: "2025-01",
		});

		expect(
			lerFiltrosCompartilhados("/rede", soInicio).periodo_atual,
		).toBeUndefined();
		expect(
			lerFiltrosCompartilhados("/rede", invertido).periodo_atual,
		).toBeUndefined();
	});

	it("mantém um período completo e em ordem", () => {
		const search = redeSearchSchema.parse({
			inicio: "2024-07",
			fim: "2025-06",
		});

		expect(search.inicio).toBe("2024-07");
		expect(search.fim).toBe("2025-06");
	});

	it("não transforma texto vazio em código", () => {
		const vazio = redeSearchSchema.parse({ alimentador: "   " });
		const semMunicipio = redeSearchSchema.parse({ municipio: "" });
		const comEspacos = redeSearchSchema.parse({
			alimentador: "  ALM-REC-006 ",
		});

		expect(vazio.alimentador).toBeUndefined();
		expect(semMunicipio.municipio).toBeUndefined();
		expect(comEspacos.alimentador).toBe("ALM-REC-006");
	});

	it("barra critério e visão desconhecidos", () => {
		const search = redeSearchSchema.parse({
			criterio: "dec",
			visao: "ucs",
		});

		expect(search.criterio).toBe("dec");
		expect(search.visao).toBeUndefined();
		expect(
			redeSearchSchema.parse({ criterio: "ruim" }).criterio,
		).toBeUndefined();
	});

	it("preserva a classe conhecida e descarta a desconhecida", () => {
		expect(redeSearchSchema.parse({ classe: "B1" }).classe).toBe("B1");
		expect(redeSearchSchema.parse({ classe: "C1" }).classe).toBeUndefined();
	});

	it("preserva o par base com meses reais e em ordem", () => {
		const search = redeSearchSchema.parse({
			periodo_base: "2024-01/2024-12",
		});

		expect(search.periodo_base).toBe("2024-01/2024-12");
	});

	it("descarta o par base com mês inválido ou invertido", () => {
		const mesTreze = redeSearchSchema.parse({
			periodo_base: "2024-13/2024-12",
		});
		const invertido = redeSearchSchema.parse({
			periodo_base: "2024-12/2024-01",
		});

		expect(
			lerFiltrosCompartilhados("/rede", mesTreze).periodo_base,
		).toBeUndefined();
		expect(
			lerFiltrosCompartilhados("/rede", invertido).periodo_base,
		).toBeUndefined();
	});

	it("mantém a classe ao remover um bairro órfão de município", () => {
		const search = redeSearchSchema.parse({
			bairro: "Boa Viagem",
			classe: "B3",
		});

		expect(search.bairro).toBeUndefined();
		expect(search.classe).toBe("B3");
	});
});
