import type { components } from "#/lib/api-schema.gen";

export type PerguntaIa = components["schemas"]["PerguntaIaSchema"];
export type RespostaIa = components["schemas"]["RespostaIaSchema"];
export type AuditoriaIa = components["schemas"]["AuditoriaIaSchema"];
export type AnswerStatus = components["schemas"]["AnswerStatus"];
export type Confidence = components["schemas"]["Confidence"];

export type EscopoSugestao =
	| "Todos os dados"
	| "Receita e faturamento"
	| "Rede (DEC/FEC)"
	| "Unidades consumidoras"
	| "Atendimento e medidores";

export type TurnoStatus = "pending" | "completed" | "error";

export interface TurnoConversa {
	id: string;
	question: string;
	criadoEm: string;
	status: TurnoStatus;
	resposta?: RespostaIa;
	erro?: string;
	etapa?: string;
}

export interface SessaoConversa {
	sessionId: string;
	usuarioLogin?: string;
	titulo: string;
	favorita?: boolean;
	criadaEm: string;
	atualizadaEm: string;
	turnos: TurnoConversa[];
}

export interface ExemploPergunta {
	id: string;
	titulo: string;
	descricao: string;
	pergunta: string;
	escopo: Exclude<EscopoSugestao, "Todos os dados">;
}
