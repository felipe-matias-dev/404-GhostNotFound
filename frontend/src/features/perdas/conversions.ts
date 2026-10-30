import { ApiError } from "#/lib/api";
import type {
	AcaoOrdem,
	EventoOrdem,
	Ordem,
	ResultadoOrdem,
	StatusOrdem,
	VisaoOrdens,
} from "./types";

/** Rótulo e cor do ponto do badge (Fundamentos/Estados) de cada status da OI. */
export const STATUS_ORDEM_VISUAL: Record<
	StatusOrdem,
	{ rotulo: string; ponto: string }
> = {
	GERADA: { rotulo: "Gerada", ponto: "bg-accent" },
	EM_CAMPO: { rotulo: "Em campo", ponto: "bg-info" },
	CONCLUIDA: { rotulo: "Concluída", ponto: "bg-success" },
	CANCELADA: { rotulo: "Cancelada", ponto: "bg-text-muted" },
};

export const RESULTADO_ORDEM_ROTULO: Record<ResultadoOrdem, string> = {
	IRREGULAR_CONFIRMADA: "Irregularidade confirmada",
	REGULAR: "Regular",
	NAO_REALIZADA: "Não realizada",
};

/**
 * Ações oferecidas em cada status. Espelha `TRANSICOES` de `backend/.../ordens.py` só para
 * mostrar os botões certos; quem decide é o backend, que responde 409 a uma transição inválida.
 */
export const ACOES_POR_STATUS: Record<StatusOrdem, readonly AcaoOrdem[]> = {
	GERADA: ["enviar", "cancelar"],
	EM_CAMPO: ["concluir", "cancelar"],
	CONCLUIDA: [],
	CANCELADA: [],
};

export const STATUS_DESTINO: Record<AcaoOrdem, StatusOrdem> = {
	enviar: "EM_CAMPO",
	concluir: "CONCLUIDA",
	cancelar: "CANCELADA",
};

export const ACAO_ORDEM_ROTULO: Record<AcaoOrdem, string> = {
	enviar: "Enviar a campo",
	concluir: "Concluir",
	cancelar: "Cancelar",
};

export function acaoParaDestino(
	origem: StatusOrdem,
	destino: StatusOrdem,
): AcaoOrdem | null {
	return (
		ACOES_POR_STATUS[origem].find((acao) => STATUS_DESTINO[acao] === destino) ??
		null
	);
}

/**
 * Título de um evento do histórico em partes: `origem` nula quando a OI foi criada.
 * A tela separa as partes para dar à seta um `aria-hidden` e ao leitor de tela "para".
 */
export function tituloEvento(
	evento: Pick<EventoOrdem, "status_anterior" | "status_novo">,
): { origem: string | null; destino: string } {
	return {
		origem: evento.status_anterior
			? STATUS_ORDEM_VISUAL[evento.status_anterior].rotulo
			: null,
		destino: STATUS_ORDEM_VISUAL[evento.status_novo].rotulo,
	};
}

/**
 * Quem fez a mudança: o nome, ou o login se o usuário não existe mais. Nulo nos eventos de
 * antes do login, que não têm autor (DEC-050).
 */
export function autorEvento(
	evento: Pick<EventoOrdem, "autor_nome" | "autor_login">,
): string | null {
	return evento.autor_nome ?? evento.autor_login ?? null;
}

/**
 * Mensagem para o usuário a partir da falha da API: o `detail` do FastAPI é texto no 404/409
 * e lista de erros de validação no 422. Sem `detail` legível (rede, 500), usa `padrao`.
 */
export function mensagemErroOrdem(error: unknown, padrao: string): string {
	if (!(error instanceof ApiError)) return padrao;
	const detail = (error.body as { detail?: unknown } | null)?.detail;
	if (typeof detail === "string" && detail) return detail;
	if (Array.isArray(detail)) {
		const mensagens = detail
			.map((item) => (item as { msg?: unknown })?.msg)
			.filter((msg): msg is string => typeof msg === "string" && msg !== "")
			.map((msg) => msg.replace(/^Value error, /, ""));
		if (mensagens.length > 0) return mensagens.join(" ");
	}
	return padrao;
}

/**
 * Altura da viewport → quantas finalizadas cada coluna mostra. As faixas casam com as
 * telas do case (notebook, PC, desktop grande); o limite maior precisa caber sem
 * transformar o quadro num paredão de cartões.
 */
export const LIMITES_FINALIZADAS = [
	{ alturaMinima: 0, limite: 3 },
	{ alturaMinima: 900, limite: 5 },
	{ alturaMinima: 1300, limite: 8 },
] as const;

export function limiteFinalizadas(alturaViewport: number): number {
	let limite: number = LIMITES_FINALIZADAS[0].limite;
	for (const faixa of LIMITES_FINALIZADAS) {
		if (alturaViewport >= faixa.alturaMinima) limite = faixa.limite;
	}
	return limite;
}

export type ColunaFinalizada = { visiveis: Ordem[]; total: number };

export type OrdensKanbanAgrupadas = {
	GERADA: Ordem[];
	EM_CAMPO: Ordem[];
	CONCLUIDA: ColunaFinalizada;
	CANCELADA: ColunaFinalizada;
};

function colunaFinalizada(
	ordens: Ordem[],
	status: StatusOrdem,
	limite: number,
): ColunaFinalizada {
	const todas = ordens.filter((ordem) => ordem.status === status);
	const visiveis = [...todas]
		.sort((a, b) => {
			const porData = Date.parse(b.atualizada_em) - Date.parse(a.atualizada_em);
			return porData !== 0 ? porData : b.id - a.id;
		})
		.slice(0, Math.max(0, limite));
	return { visiveis, total: todas.length };
}

/**
 * Separa as OIs do Kanban: ativas inteiras, na ordem da API (mais recentes primeiro), e
 * finalizadas pelas atualizadas mais recentes, cortadas no `limite` da altura da tela.
 */
export function agruparOrdensKanban(
	ordens: Ordem[],
	limite: number,
): OrdensKanbanAgrupadas {
	return {
		GERADA: ordens.filter((ordem) => ordem.status === "GERADA"),
		EM_CAMPO: ordens.filter((ordem) => ordem.status === "EM_CAMPO"),
		CONCLUIDA: colunaFinalizada(ordens, "CONCLUIDA", limite),
		CANCELADA: colunaFinalizada(ordens, "CANCELADA", limite),
	};
}

export type CodigosUcLidos = { codigos: string[]; repetidos: number };

export function lerCodigosUc(texto: string): CodigosUcLidos {
	const vistos = new Set<string>();
	let repetidos = 0;
	for (const codigo of texto.split(/[\s,;]+/)) {
		if (!codigo) continue;
		if (vistos.has(codigo)) {
			repetidos += 1;
			continue;
		}
		vistos.add(codigo);
	}
	return { codigos: [...vistos], repetidos };
}

export function lerVisaoSalva(valor: string | null): VisaoOrdens {
	return valor === "tabela" ? "tabela" : "kanban";
}
