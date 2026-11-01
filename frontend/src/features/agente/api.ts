import { API_URL, ApiError, api, unwrap } from "#/lib/api";
import type { paths } from "#/lib/api-schema.gen";
import type { AuditoriaIa, PerguntaIa, RespostaIa } from "./types";

export const agenteKeys = {
	all: ["agente"] as const,
	auditoria: (id: number) => ["agente", "auditoria", id] as const,
};

type Evento =
	paths["/ai/ask/stream"]["post"]["responses"][200]["content"]["text/event-stream"];

export class AgentProtocolError extends Error {}

export async function perguntarAoAgente(
	body: PerguntaIa,
	signal: AbortSignal,
	onStage: (label: string) => void,
): Promise<RespostaIa> {
	const response = await fetch(`${API_URL}/ai/ask/stream`, {
		method: "POST",
		credentials: "include",
		headers: {
			"Content-Type": "application/json",
			Accept: "text/event-stream",
		},
		body: JSON.stringify(body),
		signal,
	});
	if (!response.ok) {
		if (response.status === 401)
			window.dispatchEvent(new Event("venergy:session-expired"));
		const error = await response.json().catch(() => null);
		throw new ApiError(response.status, error);
	}
	if (!response.body) throw new Error("A conexão com o agente foi encerrada.");
	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	try {
		while (true) {
			const { value, done } = await reader.read();
			buffer += decoder.decode(value, { stream: !done });
			const messages = buffer.split(/\r\n\r\n|\r\r|\n\n/);
			buffer = messages.pop() ?? "";
			for (const message of messages) {
				const data = message
					.split(/\r\n|\r|\n/)
					.filter((line) => line.startsWith("data:"))
					.map((line) => line.slice(5).replace(/^ /, ""))
					.join("\n");
				if (!data) continue;
				let event: Evento;
				try {
					event = JSON.parse(data) as Evento;
				} catch (cause) {
					throw new AgentProtocolError(
						"Não foi possível interpretar a resposta do agente. Tente novamente.",
						{ cause },
					);
				}
				if (event.type === "stage") onStage(event.label);
				else if (event.type === "answer") return event.answer;
				else if (event.type === "error") throw new Error(event.detail);
			}
			if (done)
				throw new AgentProtocolError(
					"A conexão terminou antes da resposta. Tente novamente.",
				);
		}
	} finally {
		await reader.cancel().catch(() => {});
	}
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
