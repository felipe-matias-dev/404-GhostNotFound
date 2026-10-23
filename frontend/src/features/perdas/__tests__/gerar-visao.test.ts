import { describe, expect, it } from "vitest";
import { lerCodigosUc, lerVisaoSalva } from "../conversions";

describe("lerCodigosUc", () => {
	it("separa por vírgula, espaço, ponto e vírgula e quebra de linha", () => {
		expect(lerCodigosUc("0001, 0002\n0003;0001  ")).toEqual({
			codigos: ["0001", "0002", "0003"],
			repetidos: 1,
		});
	});

	it("conta as repetições que passam da primeira ocorrência", () => {
		expect(lerCodigosUc("0001 0001 0001 0002")).toEqual({
			codigos: ["0001", "0002"],
			repetidos: 2,
		});
	});

	it("mantém o código como veio, sem normalizar", () => {
		expect(lerCodigosUc(" uc-1 0002 ")).toEqual({
			codigos: ["uc-1", "0002"],
			repetidos: 0,
		});
	});

	it("texto vazio ou só separadores não tem códigos", () => {
		expect(lerCodigosUc("  \n;, ")).toEqual({ codigos: [], repetidos: 0 });
	});
});

describe("lerVisaoSalva", () => {
	it("aceita as visões conhecidas", () => {
		expect(lerVisaoSalva("kanban")).toBe("kanban");
		expect(lerVisaoSalva("tabela")).toBe("tabela");
	});

	it("cai no kanban sem valor salvo ou com valor inválido", () => {
		expect(lerVisaoSalva(null)).toBe("kanban");
		expect(lerVisaoSalva("")).toBe("kanban");
		expect(lerVisaoSalva("xyz")).toBe("kanban");
	});
});
