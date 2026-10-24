import { describe, expect, it } from "vitest";
import { ApiError } from "#/lib/api";
import { acaoParaDestino, mensagemErroOrdem } from "../conversions";
import { STATUS_ORDEM } from "../types";

describe("acaoParaDestino", () => {
	it("mapeia só as transições da máquina de estados do backend", () => {
		const transicoes = STATUS_ORDEM.flatMap((origem) =>
			STATUS_ORDEM.map((destino) => [
				origem,
				destino,
				acaoParaDestino(origem, destino),
			]),
		).filter(([, , acao]) => acao !== null);

		expect(transicoes).toEqual([
			["GERADA", "EM_CAMPO", "enviar"],
			["GERADA", "CANCELADA", "cancelar"],
			["EM_CAMPO", "CONCLUIDA", "concluir"],
			["EM_CAMPO", "CANCELADA", "cancelar"],
		]);
	});
});

describe("mensagemErroOrdem", () => {
	it("usa o detail em texto do 409", () => {
		const erro = new ApiError(409, {
			detail: "Não é possível mudar uma ordem de CONCLUIDA para CANCELADA",
		});
		expect(mensagemErroOrdem(erro, "padrão")).toBe(
			"Não é possível mudar uma ordem de CONCLUIDA para CANCELADA",
		);
	});

	it("junta as mensagens do 422 sem o prefixo do pydantic", () => {
		const erro = new ApiError(422, {
			detail: [
				{
					type: "value_error",
					loc: ["body"],
					msg: "Value error, Informe o resultado da inspeção para concluir a ordem",
				},
			],
		});
		expect(mensagemErroOrdem(erro, "padrão")).toBe(
			"Informe o resultado da inspeção para concluir a ordem",
		);
	});

	it("cai no padrão sem detail legível ou fora da API", () => {
		expect(
			mensagemErroOrdem(new ApiError(500, "Internal Server Error"), "padrão"),
		).toBe("padrão");
		expect(mensagemErroOrdem(new TypeError("Failed to fetch"), "padrão")).toBe(
			"padrão",
		);
	});
});
