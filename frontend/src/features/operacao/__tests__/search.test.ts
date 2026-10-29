import { describe, expect, it } from "vitest";
import { redeSearchSchema } from "../search";

describe("redeSearchSchema", () => {
	it("remove um bairro órfão de município", () => {
		const search = redeSearchSchema.parse({ bairro: "Boa Viagem" });

		expect(search.bairro).toBeUndefined();
		expect(search.visao).toBeUndefined();
	});

	it("limpa a geografia quando a visão global é explícita", () => {
		const search = redeSearchSchema.parse({
			visao: "alimentadores",
			municipio: "Recife",
			bairro: "Boa Viagem",
		});

		expect(search.visao).toBe("alimentadores");
		expect(search.municipio).toBeUndefined();
		expect(search.bairro).toBeUndefined();
	});

	it("infere localidades a partir de um município com bairro", () => {
		const search = redeSearchSchema.parse({
			municipio: "Recife",
			bairro: "Boa Viagem",
		});

		expect(search.visao).toBe("localidades");
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

		expect(mesTreze.inicio).toBeUndefined();
		expect(mesCurto.inicio).toBeUndefined();
	});

	it("remove as duas pontas de um período incompleto ou invertido", () => {
		const soInicio = redeSearchSchema.parse({ inicio: "2025-03" });
		const invertido = redeSearchSchema.parse({
			inicio: "2025-03",
			fim: "2025-01",
		});

		expect(soInicio.inicio).toBeUndefined();
		expect(soInicio.fim).toBeUndefined();
		expect(invertido.inicio).toBeUndefined();
		expect(invertido.fim).toBeUndefined();
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

	it("remove a série sem alimentador", () => {
		const sozinha = redeSearchSchema.parse({ serie: "fec" });
		const comAlimentador = redeSearchSchema.parse({
			serie: "fec",
			alimentador: "ALM-A",
		});

		expect(sozinha.serie).toBeUndefined();
		expect(comAlimentador.serie).toBe("fec");
	});

	it("barra critério e visão desconhecidos", () => {
		const search = redeSearchSchema.parse({
			criterio: "dec",
			visao: "bairros",
		});

		expect(search.criterio).toBe("dec");
		expect(search.visao).toBeUndefined();
		expect(
			redeSearchSchema.parse({ criterio: "ruim" }).criterio,
		).toBeUndefined();
	});
});
