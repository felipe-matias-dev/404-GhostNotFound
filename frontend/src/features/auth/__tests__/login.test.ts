import { describe, expect, it } from "vitest";
import { ApiError } from "#/lib/api";
import { falhaDoLogin } from "../conversions";

describe("falhaDoLogin", () => {
	it("401 pede para conferir os dados e marca os campos", () => {
		const falha = falhaDoLogin(
			new ApiError(401, { detail: "Login ou senha inválidos" }),
		);

		expect(falha.credenciaisInvalidas).toBe(true);
		expect(falha.mensagem).toContain("Usuário ou senha inválidos");
	});

	it("429 mostra o aviso do backend com o tempo de espera e não marca os campos", () => {
		const detail = "Muitas tentativas de login. Tente de novo em 7 minutos.";

		expect(falhaDoLogin(new ApiError(429, { detail }))).toEqual({
			mensagem: detail,
			credenciaisInvalidas: false,
		});
	});

	it("429 sem texto legível usa um aviso de espera, e não o de dados inválidos", () => {
		const falha = falhaDoLogin(new ApiError(429, null));

		expect(falha.mensagem).toContain("Muitas tentativas");
		expect(falha.credenciaisInvalidas).toBe(false);
	});

	it("qualquer outra falha (500, rede) usa a mensagem genérica", () => {
		for (const erro of [new ApiError(500, null), new TypeError("fetch")]) {
			const falha = falhaDoLogin(erro);

			expect(falha.mensagem).toContain("Não foi possível entrar");
			expect(falha.credenciaisInvalidas).toBe(false);
		}
	});
});
