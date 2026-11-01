import { ApiError } from "#/lib/api";

const CREDENCIAIS_INVALIDAS =
	"Usuário ou senha inválidos. Confira os dados e tente novamente.";
const BLOQUEADO_SEM_TEXTO =
	"Muitas tentativas de login. Aguarde alguns minutos e tente de novo.";
const FALHA_GENERICA =
	"Não foi possível entrar no portal. Tente novamente em instantes.";

export type FalhaDoLogin = {
	mensagem: string;
	/** Só o 401 marca os campos: no 429 o problema não são os dados digitados. */
	credenciaisInvalidas: boolean;
};

/**
 * O que a tela de login mostra para cada falha da API. No 429 (senhas erradas demais) o texto
 * vem do backend, que sabe quanto falta para liberar ("Tente de novo em 7 minutos").
 */
export function falhaDoLogin(error: unknown): FalhaDoLogin {
	if (error instanceof ApiError && error.status === 401) {
		return { mensagem: CREDENCIAIS_INVALIDAS, credenciaisInvalidas: true };
	}
	if (error instanceof ApiError && error.status === 429) {
		const detail = (error.body as { detail?: unknown } | null)?.detail;
		const mensagem =
			typeof detail === "string" && detail ? detail : BLOQUEADO_SEM_TEXTO;
		return { mensagem, credenciaisInvalidas: false };
	}
	return { mensagem: FALHA_GENERICA, credenciaisInvalidas: false };
}
