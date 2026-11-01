import { afterEach, describe, expect, it, vi } from "vitest";
import { AgentProtocolError, perguntarAoAgente } from "../api";

const pedido = {
	question: "Qual a receita?",
	session_id: "00000000-0000-4000-8000-000000000000",
};
const answer = {
	answer: "Receita: R$ 10",
	session_id: pedido.session_id,
	rows: [{ receita: 10 }],
	confidence: "high",
};

afterEach(() => vi.unstubAllGlobals());

describe("stream do agente", () => {
	it("reconstitui eventos divididos em bytes e entrega etapas, correção e resposta", async () => {
		const bytes = new TextEncoder().encode(
			`: ping\r\n\r\nevent: stage\r\ndata: {"type":"stage","label":"Entendendo a pergunta"}\r\n\r\nevent: stage\r\ndata: {"type":"stage","label":"Consultando os dados"}\r\n\r\nevent: stage\r\ndata: {"type":"stage","label":"Ajustando a consulta"}\r\n\r\nevent: answer\r\ndata: ${JSON.stringify({ type: "answer", answer })}\r\n\r\n`,
		);
		vi.stubGlobal(
			"fetch",
			vi.fn(
				async () =>
					new Response(
						new ReadableStream({
							start(controller) {
								for (let i = 0; i < bytes.length; i += 3)
									controller.enqueue(bytes.slice(i, i + 3));
								controller.close();
							},
						}),
					),
			),
		);
		const etapas: string[] = [];
		const resultado = await perguntarAoAgente(
			pedido,
			new AbortController().signal,
			(etapa) => etapas.push(etapa),
		);
		expect(etapas).toEqual([
			"Entendendo a pergunta",
			"Consultando os dados",
			"Ajustando a consulta",
		]);
		expect(resultado).toEqual(answer);
	});

	it("informa desconexão sem resposta e erro SSE", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(
				async () =>
					new Response(
						'event: stage\ndata: {"type":"stage","label":"Consultando"}\n\n',
					),
			),
		);
		await expect(
			perguntarAoAgente(pedido, new AbortController().signal, () => {}),
		).rejects.toThrow("antes da resposta");
		vi.stubGlobal(
			"fetch",
			vi.fn(
				async () =>
					new Response(
						'event: error\ndata: {"type":"error","detail":"Falha na auditoria"}\n\n',
					),
			),
		);
		await expect(
			perguntarAoAgente(pedido, new AbortController().signal, () => {}),
		).rejects.toThrow("Falha na auditoria");
	});

	it("interrompe o stream em JSON inválido sem aceitar eventos posteriores", async () => {
		let cancelado = false;
		const etapas: string[] = [];
		vi.stubGlobal(
			"fetch",
			vi.fn(
				async () =>
					new Response(
						new ReadableStream({
							start(controller) {
								controller.enqueue(
									new TextEncoder().encode(
										`data: nao-e-json\n\ndata: {"type":"stage","label":"Etapa posterior"}\n\ndata: ${JSON.stringify({ type: "answer", answer })}\n\n`,
									),
								);
							},
							cancel() {
								cancelado = true;
							},
						}),
					),
			),
		);
		const erro = await perguntarAoAgente(
			pedido,
			new AbortController().signal,
			(etapa) => etapas.push(etapa),
		).catch((error: unknown) => error);
		expect(erro).toBeInstanceOf(AgentProtocolError);
		expect((erro as AgentProtocolError).cause).toBeInstanceOf(SyntaxError);
		expect(etapas).toEqual([]);
		expect(cancelado).toBe(true);
	});

	it.each([
		"",
		"\n",
	])("não entrega uma resposta sem a linha vazia final, com sufixo %j", async (sufixo) => {
		vi.stubGlobal(
			"fetch",
			vi.fn(
				async () =>
					new Response(
						`data: ${JSON.stringify({ type: "answer", answer })}${sufixo}`,
					),
			),
		);
		await expect(
			perguntarAoAgente(pedido, new AbortController().signal, () => {}),
		).rejects.toBeInstanceOf(AgentProtocolError);
	});
});
