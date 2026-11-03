import { ApiError } from "#/lib/api";
import {
	formatBRL,
	formatCompetencia,
	formatData,
	formatDataHora,
	formatHoras,
	formatIndice,
	formatKWh,
	formatNumero,
} from "#/lib/format";
import { AgentProtocolError } from "./api";
import type {
	AnswerStatus,
	Confidence,
	EscopoSugestao,
	ExemploPergunta,
	SessaoConversa,
	SessaoIa,
} from "./types";

export const MAX_PERGUNTA_CHARS = 500;

export const MAX_SESSOES = 15;

export const ESCOPOS_AGENTE = [
	"Todos os dados",
	"Receita e faturamento",
	"Rede (DEC/FEC)",
	"Unidades consumidoras",
	"Atendimento e medidores",
] as const satisfies readonly EscopoSugestao[];

export const EXEMPLOS_PERGUNTAS: readonly ExemploPergunta[] = [
	{
		id: "receita-mensal",
		titulo: "Receita de um mês",
		descricao: "Total faturado, energia e tributos de uma competência.",
		pergunta: "Qual foi a receita faturada em setembro de 2025?",
		escopo: "Receita e faturamento",
	},
	{
		id: "receita-efeito",
		titulo: "Preço ou volume",
		descricao:
			"Separa o efeito de tarifa e bandeira do efeito de volume e mix.",
		pergunta:
			"A queda de receita entre 2024 e 2025 veio do preço ou do volume faturado?",
		escopo: "Receita e faturamento",
	},
	{
		id: "rede-dec",
		titulo: "Piores alimentadores",
		descricao: "Ranking de DEC por alimentador no período mais recente.",
		pergunta: "Quais alimentadores tiveram o maior DEC nos últimos seis meses?",
		escopo: "Rede (DEC/FEC)",
	},
	{
		id: "rede-fec",
		titulo: "FEC da distribuidora",
		descricao: "Frequência média de interrupções mês a mês em 2025.",
		pergunta: "Como evoluiu o FEC da distribuidora ao longo de 2025?",
		escopo: "Rede (DEC/FEC)",
	},
	{
		id: "uc-gd",
		titulo: "Geração distribuída",
		descricao: "Quantas UCs com painel solar existem em cada município.",
		pergunta:
			"Quantas unidades consumidoras com geração distribuída há em Recife?",
		escopo: "Unidades consumidoras",
	},
	{
		id: "atendimento-satisfacao",
		titulo: "Satisfação do atendimento",
		descricao: "Nota média dos chamados e os assuntos mais frequentes.",
		pergunta: "Qual foi a nota média de satisfação dos chamados em Olinda?",
		escopo: "Atendimento e medidores",
	},
];

export function filtrarExemplosPorEscopo(
	exemplos: readonly ExemploPergunta[],
	escopo: EscopoSugestao,
): readonly ExemploPergunta[] {
	if (escopo === "Todos os dados") return exemplos;
	return exemplos.filter((exemplo) => exemplo.escopo === escopo);
}

export function gerarTituloSessao(pergunta: string): string {
	const limpa = pergunta.trim().replace(/\s+/g, " ");
	if (!limpa) return "Nova conversa";
	if (limpa.length <= 48) return limpa;
	return `${limpa.slice(0, 47).trimEnd()}…`;
}

export function validarPergunta(
	texto: string,
): { ok: true; question: string } | { ok: false; erro: string } {
	const question = texto.trim();
	if (!question)
		return { ok: false, erro: "Escreva uma pergunta para o agente." };
	if (question.length > MAX_PERGUNTA_CHARS)
		return {
			ok: false,
			erro: `A pergunta pode ter até ${MAX_PERGUNTA_CHARS} caracteres.`,
		};
	return { ok: true, question };
}

export function rotuloConfianca(confidence: Confidence): {
	rotulo: string;
	tom: "success" | "warning" | "neutral";
} {
	switch (confidence) {
		case "high":
			return { rotulo: "Confiança alta", tom: "success" };
		case "medium":
			return { rotulo: "Confiança média", tom: "warning" };
		case "low":
			return { rotulo: "Confiança baixa", tom: "warning" };
		case "unknown":
			return { rotulo: "Sem grau de confiança", tom: "neutral" };
	}
}

export function rotuloStatusResposta(status: AnswerStatus): {
	rotulo: string;
	tom: "success" | "info" | "warning" | "danger";
} {
	switch (status) {
		case "answered":
			return { rotulo: "Respondida", tom: "success" };
		case "clarify":
			return { rotulo: "Precisa de esclarecimento", tom: "info" };
		case "unknown":
			return { rotulo: "Fora da camada de dados", tom: "warning" };
		case "refused":
			return { rotulo: "Consulta recusada", tom: "danger" };
		case "failed":
			return { rotulo: "Falha na consulta", tom: "danger" };
	}
}

const NOMES_DAS_VIEWS: Record<string, string> = {
	sem_uc: "Cadastro de UCs",
	sem_faturamento_mensal: "Faturamento mensal",
	sem_continuidade_alimentador_mensal: "Continuidade por alimentador",
	sem_kpis_mensais: "KPIs mensais",
	sem_kpis_segmento_mensal: "KPIs por segmento",
	sem_interrupcoes_uc: "Interrupções por UC",
	sem_atendimentos_uc: "Atendimentos por UC",
	sem_medidor_uc: "Medidores por UC",
	sem_receita_decomposicao: "Decomposição de receita",
};

export function nomeAmigavelView(view: string): string {
	return NOMES_DAS_VIEWS[view] ?? view;
}

export function formatarCelulaResultado(
	coluna: string,
	valor: unknown,
): string {
	if (valor === null || valor === undefined) return "—";
	if (typeof valor === "boolean") return valor ? "Sim" : "Não";
	if (typeof valor === "string") {
		if (/^\d{4}-(0[1-9]|1[0-2])$/.test(valor)) return formatCompetencia(valor);
		if (/^\d{4}-\d{2}-\d{2}$/.test(valor)) return formatData(valor);
		const col = coluna.toLowerCase();
		if (
			!col.includes("cod_") &&
			col !== "protocolo" &&
			/^-?\d+(\.\d+)?$/.test(valor.trim())
		) {
			const numero = Number(valor);
			if (Number.isFinite(numero))
				return formatarCelulaResultado(coluna, numero);
		}
		return valor;
	}
	if (typeof valor === "number") {
		const col = coluna.toLowerCase();
		if (
			col.includes("receita") ||
			col.includes("tributo") ||
			col.includes("efeito") ||
			col.includes("tarifa")
		)
			return formatBRL(valor);
		if (col.includes("kwh")) return formatKWh(valor);
		if (col === "dec" || col.includes("horas")) return formatHoras(valor);
		if (col === "fec" || col.includes("satisfacao")) return formatIndice(valor);
		if (col.includes("pct") || col.includes("percentual"))
			return `${formatNumero(valor)}%`;
		return formatNumero(valor);
	}
	return String(valor);
}

export function formatarTempoRelativo(iso: string, agora = Date.now()): string {
	const ms = Date.parse(iso);
	if (!Number.isFinite(ms)) return "";
	const diffSec = Math.max(0, Math.floor((agora - ms) / 1000));
	if (diffSec < 60) return "agora mesmo";
	const diffMin = Math.floor(diffSec / 60);
	if (diffMin < 60) return `há ${diffMin} min`;
	const diffHoras = Math.floor(diffMin / 60);
	if (diffHoras < 24) return `há ${diffHoras} h`;
	return formatDataHora(iso);
}

/**
 * A conversa como o backend guarda (`GET /ai/sessions`): cada turno é um registro da
 * auditoria, e a resposta é a mesma que o `POST /ai/ask` devolveu.
 */
export function sessaoDaApi(
	sessao: SessaoIa,
	usuarioLogin: string,
): SessaoConversa {
	return {
		sessionId: sessao.session_id,
		usuarioLogin,
		titulo: sessao.titulo,
		favorita: sessao.favorita,
		criadaEm: sessao.criada_em,
		atualizadaEm: sessao.atualizada_em,
		turnos: sessao.turnos.map(({ pergunta, criado_em, ...resposta }) => ({
			id: String(resposta.audit_id),
			question: pergunta,
			criadoEm: criado_em,
			status: "completed",
			resposta: { ...resposta, session_id: sessao.session_id },
		})),
	};
}

export type CamposSessao = Partial<Pick<SessaoConversa, "titulo" | "favorita">>;

/**
 * Junta as conversas da tela com as do servidor. A de mesmo id fica com a versão que tem
 * mais turnos: uma pergunta feita antes de a lista chegar não some. A conversa vazia sai.
 */
export function mesclarSessoes(
	locais: SessaoConversa[],
	doServidor: SessaoConversa[],
): SessaoConversa[] {
	const comTurnos = new Map(
		locais
			.filter((sessao) => sessao.turnos.length > 0)
			.map((sessao) => [sessao.sessionId, sessao]),
	);
	const salvas = doServidor.map((salva) => {
		const local = comTurnos.get(salva.sessionId);
		comTurnos.delete(salva.sessionId);
		return local && local.turnos.length >= salva.turnos.length ? local : salva;
	});
	return [...comTurnos.values(), ...salvas];
}

/**
 * Desfaz uma alteração que o servidor recusou: só os campos que ela mudou, e só se a tela
 * ainda mostra o valor enviado (uma alteração mais nova não é desfeita por uma antiga).
 */
export function desfazerAlteracao(
	sessao: SessaoConversa,
	enviado: CamposSessao,
	anterior: CamposSessao,
): SessaoConversa {
	const desfeita = { ...sessao };
	if (
		"titulo" in enviado &&
		sessao.titulo === enviado.titulo &&
		anterior.titulo
	)
		desfeita.titulo = anterior.titulo;
	if ("favorita" in enviado && sessao.favorita === enviado.favorita)
		desfeita.favorita = anterior.favorita;
	return desfeita;
}

/** Devolve à lista uma conversa cuja exclusão falhou, na posição em que ela estava. */
export function reinserirSessao(
	lista: SessaoConversa[],
	sessao: SessaoConversa,
	indice: number,
): SessaoConversa[] {
	const outras = lista.filter((atual) => atual.sessionId !== sessao.sessionId);
	const primeiraVazia = outras.findIndex((atual) => atual.turnos.length === 0);
	const limite = primeiraVazia === -1 ? outras.length : primeiraVazia;
	outras.splice(Math.min(indice, limite), 0, sessao);
	return outras;
}

export function formatarSessaoComoMarkdown(sessao: SessaoConversa): string {
	const blocos = [`# ${sessao.titulo}`];
	for (const turno of sessao.turnos) {
		blocos.push(`## Pergunta\n\n${turno.question}`);
		if (turno.status === "completed" && turno.resposta) {
			blocos.push(`### Resposta\n\n${turno.resposta.answer}`);
			if (turno.resposta.rows.length > 0) {
				const cols = Object.keys(turno.resposta.rows[0] ?? {});
				if (cols.length > 0) {
					const cabecalho = `| ${cols.join(" | ")} |`;
					const divisor = `| ${cols.map(() => "---").join(" | ")} |`;
					const linhas = turno.resposta.rows.map(
						(linha) =>
							`| ${cols
								.map((col) => formatarCelulaResultado(col, linha[col]))
								.join(" | ")} |`,
					);
					blocos.push([cabecalho, divisor, ...linhas].join("\n"));
				}
			}
			if (turno.resposta.sql) {
				blocos.push(`\`\`\`sql\n${turno.resposta.sql}\n\`\`\``);
			}
		} else if (turno.status === "error" && turno.erro) {
			blocos.push(`> Erro: ${turno.erro}`);
		}
	}
	return blocos.join("\n\n");
}

export function extrairMensagemErro(error: unknown): string {
	if (error instanceof AgentProtocolError) return error.message;
	if (error instanceof ApiError) {
		if (error.status === 503)
			return "O agente de IA não está disponível neste ambiente (verifique a configuração da chave do modelo).";
		if (error.status === 422)
			return "A pergunta enviada é inválida (máximo de 500 caracteres).";
	}
	return "Não foi possível concluir a consulta ao agente. Tente novamente.";
}
