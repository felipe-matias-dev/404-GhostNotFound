import { describe, expect, it } from "vitest";
import { ApiError } from "#/lib/api";
import {
	acaoParaDestino,
	mensagemErroOrdem,
	paraOrdensDaTela,
	segundosNoStatus,
} from "../conversions";
import { type Ordem, STATUS_ORDEM } from "../types";

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

const ORDEM_DA_API: Ordem = {
	id: 7,
	cod_uc: "0001",
	status: "EM_CAMPO",
	resultado: null,
	observacao: null,
	criada_em: "2026-10-01T00:00:00Z",
	atualizada_em: "2026-10-01T00:00:00Z",
	no_status_desde: "2026-10-01T00:00:00Z",
	segundos_no_status: 100,
	atrasada: false,
};

describe("segundosNoStatus", () => {
	const [ordem] = paraOrdensDaTela([ORDEM_DA_API], 1_000_000);

	it("é o que o servidor mediu quando a lista acabou de chegar", () => {
		expect(segundosNoStatus(ordem, 1_000_000)).toBe(100);
	});

	it("soma os segundos inteiros que passaram no navegador desde a resposta", () => {
		expect(segundosNoStatus(ordem, 1_000_000 + 12_999)).toBe(112);
		expect(segundosNoStatus(ordem, 1_000_000 + 60_000)).toBe(160);
	});

	it("não desconta nada se o relógio do navegador andou para trás", () => {
		expect(segundosNoStatus(ordem, 1_000_000 - 5_000)).toBe(100);
	});
});

describe("paraOrdensDaTela", () => {
	it("carimba todas as OIs com o mesmo instante e mantém os dados da API", () => {
		const outra: Ordem = { ...ORDEM_DA_API, id: 8, segundos_no_status: 5 };

		expect(paraOrdensDaTela([ORDEM_DA_API, outra], 42)).toEqual([
			{ ...ORDEM_DA_API, recebida_em: 42 },
			{ ...outra, recebida_em: 42 },
		]);
	});
});
