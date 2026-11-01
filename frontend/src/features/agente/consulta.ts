import { perguntarAoAgente } from "./api";
import { extrairMensagemErro } from "./conversions";
import type { TurnoConversa } from "./types";

export interface ConsultaAtiva {
	controller: AbortController;
	sessionId: string;
	turnoId: string;
}

interface ConsultaRef {
	current: ConsultaAtiva | null;
}

interface AtualizacoesConsulta {
	atualizarTurno: (
		sessionId: string,
		turnoId: string,
		mudanca: Partial<TurnoConversa>,
	) => void;
	setEnviando: (enviando: boolean) => void;
}

export async function consultarAgente(
	consultaRef: ConsultaRef,
	pedido: { sessionId: string; turnoId: string; question: string },
	{ atualizarTurno, setEnviando }: AtualizacoesConsulta,
): Promise<void> {
	if (consultaRef.current) return;
	const { sessionId, turnoId, question } = pedido;
	const controller = new AbortController();
	consultaRef.current = { controller, sessionId, turnoId };
	setEnviando(true);
	try {
		const resposta = await perguntarAoAgente(
			{ question, session_id: sessionId },
			controller.signal,
			(etapa) => {
				if (!controller.signal.aborted)
					atualizarTurno(sessionId, turnoId, { etapa });
			},
		);
		if (!controller.signal.aborted)
			atualizarTurno(sessionId, turnoId, {
				status: "completed",
				resposta,
				etapa: undefined,
			});
	} catch (erro) {
		if (!controller.signal.aborted)
			atualizarTurno(sessionId, turnoId, {
				status: "error",
				erro: extrairMensagemErro(erro),
				etapa: undefined,
			});
	} finally {
		if (consultaRef.current?.controller === controller) {
			consultaRef.current = null;
			setEnviando(false);
		}
	}
}
