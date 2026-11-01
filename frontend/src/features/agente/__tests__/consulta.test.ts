import { beforeEach, describe, expect, it, vi } from "vitest";
import { perguntarAoAgente } from "../api";
import { type ConsultaAtiva, consultarAgente } from "../consulta";
import type { RespostaIa, TurnoConversa } from "../types";

vi.mock("../api", () => ({ perguntarAoAgente: vi.fn() }));

const resposta: RespostaIa = {
	audit_id: 1,
	answer: "Há 12 unidades consumidoras.",
	status: "answered",
	sql: "SELECT 12 AS total",
	rows: [{ total: 12 }],
	row_count: 1,
	truncated: false,
	confidence: "high",
	sources: [],
	assumptions: [],
	clarification: null,
	refused_reason: null,
	request_id: "request-1",
	model: "modelo-sintetico",
	prompt_version: "v3",
	latency_ms: 100,
	input_tokens: 0,
	output_tokens: 0,
	session_id: "session-1",
};

function prepararConsulta() {
	const chamadas: {
		signal: AbortSignal;
		etapa: (label: string) => void;
		resultado: {
			resolve: (resposta: RespostaIa) => void;
			reject: (erro: Error) => void;
		};
	}[] = [];
	vi.mocked(perguntarAoAgente).mockImplementation((_, signal, etapa) => {
		let resolve!: (resposta: RespostaIa) => void;
		let reject!: (erro: Error) => void;
		const promise = new Promise<RespostaIa>((resolver, rejeitar) => {
			resolve = resolver;
			reject = rejeitar;
		});
		chamadas.push({ signal, etapa, resultado: { resolve, reject } });
		return promise;
	});
	const referencia: { current: ConsultaAtiva | null } = { current: null };
	let enviando = false;
	const turnos = new Map<string, Partial<TurnoConversa>>();
	return {
		chamadas,
		referencia,
		consultaAtual: () => referencia.current,
		get enviando() {
			return enviando;
		},
		turno: (id: string) => turnos.get(id),
		consultar: (turnoId: string) =>
			consultarAgente(
				referencia,
				{ sessionId: "session-1", turnoId, question: "Quantas UCs existem?" },
				{
					atualizarTurno: (_, id, mudanca) =>
						turnos.set(id, { ...turnos.get(id), ...mudanca }),
					setEnviando: (valor) => {
						enviando = valor;
					},
				},
			),
	};
}

beforeEach(() => vi.resetAllMocks());

describe("ciclo da consulta do agente", () => {
	it("não substitui uma consulta ativa por outro envio", async () => {
		const estado = prepararConsulta();
		const primeira = estado.consultar("turno-1");
		estado.chamadas[0].etapa("Consultando os dados");
		await estado.consultar("turno-2");
		expect(estado.chamadas).toHaveLength(1);
		expect(estado.chamadas[0].signal.aborted).toBe(false);
		expect(estado.turno("turno-2")).toBeUndefined();
		expect(estado.turno("turno-1")?.etapa).toBe("Consultando os dados");
		expect(estado.enviando).toBe(true);
		estado.chamadas[0].resultado.resolve(resposta);
		await primeira;
		expect(estado.turno("turno-1")).toMatchObject({
			status: "completed",
			etapa: undefined,
		});
		expect(estado.enviando).toBe(false);
	});

	it.each([
		"resposta",
		"erro",
	] as const)("ignora etapa e %s atrasados sem encerrar a repetição em andamento", async (desfecho) => {
		const estado = prepararConsulta();
		const antiga = estado.consultar("turno-1");
		estado.referencia.current?.controller.abort();
		estado.referencia.current = null;
		const atual = estado.consultar("turno-1");
		estado.chamadas[1].etapa("Redigindo a resposta");
		estado.chamadas[0].etapa("Etapa antiga");
		if (desfecho === "resposta") estado.chamadas[0].resultado.resolve(resposta);
		else estado.chamadas[0].resultado.reject(new Error("Falha antiga"));
		await antiga;
		expect(estado.turno("turno-1")).toEqual({ etapa: "Redigindo a resposta" });
		expect(estado.enviando).toBe(true);
		expect(estado.consultaAtual()?.controller.signal).toBe(
			estado.chamadas[1].signal,
		);
		estado.chamadas[1].resultado.resolve(resposta);
		await atual;
		expect(estado.turno("turno-1")?.status).toBe("completed");
		expect(estado.enviando).toBe(false);
	});

	it("libera o envio e remove a etapa quando a consulta falha", async () => {
		const estado = prepararConsulta();
		const consulta = estado.consultar("turno-1");
		estado.chamadas[0].etapa("Consultando os dados");
		estado.chamadas[0].resultado.reject(new Error("Conexão interrompida"));
		await consulta;
		expect(estado.turno("turno-1")).toMatchObject({
			status: "error",
			etapa: undefined,
		});
		expect(estado.enviando).toBe(false);
		expect(estado.referencia.current).toBeNull();
	});
});
