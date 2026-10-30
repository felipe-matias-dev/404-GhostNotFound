import { api, unwrap } from "#/lib/api";
import type { AuditoriaIa, PerguntaIa, RespostaIa } from "./types";

export const agenteKeys = {
	all: ["agente"] as const,
	auditoria: (id: number) => ["agente", "auditoria", id] as const,
};

export function perguntarAoAgente(
	body: PerguntaIa,
	signal?: AbortSignal,
): Promise<RespostaIa> {
	return unwrap(api.POST("/ai/ask", { body, signal }));
}

export function buscarAuditoriaIa(
	auditId: number,
	signal?: AbortSignal,
): Promise<AuditoriaIa> {
	return unwrap(
		api.GET("/ai/audit/{audit_id}", {
			params: { path: { audit_id: auditId } },
			signal,
		}),
	);
}
