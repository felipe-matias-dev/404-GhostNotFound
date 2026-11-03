import { useLocation } from "@tanstack/react-router";
import {
	createContext,
	type ReactNode,
	use,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import { ApiError } from "#/lib/api";
import { alterarSessaoIa, buscarSessoesIa, excluirSessaoIa } from "../api";
import { type ConsultaAtiva, consultarAgente } from "../consulta";
import {
	type CamposSessao,
	desfazerAlteracao,
	gerarTituloSessao,
	MAX_SESSOES,
	mesclarSessoes,
	reinserirSessao,
	sessaoDaApi,
	validarPergunta,
} from "../conversions";
import type { EscopoSugestao, SessaoConversa, TurnoConversa } from "../types";

export interface AgenteContextValue {
	sessoes: SessaoConversa[];
	sessaoAtiva: SessaoConversa;
	escopo: EscopoSugestao;
	setEscopo: (escopo: EscopoSugestao) => void;
	enviando: boolean;
	cancelarConsulta: () => void;
	widgetAberto: boolean;
	setWidgetAberto: (aberto: boolean) => void;
	alternarWidget: () => void;
	novaConversa: () => string;
	selecionarSessao: (sessionId: string) => void;
	renomearSessao: (sessionId: string, novoTitulo: string) => void;
	alternarFavorita: (sessionId: string) => void;
	removerSessao: (sessionId: string) => void;
	limparHistorico: () => void;
	enviarPergunta: (perguntaTexto: string) => Promise<void>;
	tentarNovamente: (turnoId: string) => Promise<void>;
	/** O histórico do servidor não carregou: a tela mostra só a conversa nova. */
	historicoIndisponivel: boolean;
}

const AgenteContext = createContext<AgenteContextValue | null>(null);

export function useAgente() {
	const contexto = use(AgenteContext);
	if (!contexto) throw new Error("Agente requer AgenteProvider");
	return contexto;
}

function novaSessao(usuarioLogin?: string): SessaoConversa {
	const agora = new Date().toISOString();
	return {
		sessionId: crypto.randomUUID(),
		usuarioLogin,
		titulo: "Nova conversa",
		favorita: false,
		criadaEm: agora,
		atualizadaEm: agora,
		turnos: [],
	};
}

// A conversa só existe no servidor depois da primeira resposta: é a auditoria que a cria.
function noServidor(sessao: SessaoConversa): boolean {
	return sessao.turnos.some((turno) => turno.resposta);
}

// 404: a conversa já não existe para este usuário, e não há o que desfazer na tela.
function semConversa(erro: unknown) {
	return erro instanceof ApiError && erro.status === 404;
}

export function AgenteProvider({
	children,
	usuario,
}: {
	children: ReactNode;
	usuario: string;
}) {
	const rota = useLocation({ select: (loc) => loc.pathname });
	const [sessoes, setSessoes] = useState(() => [novaSessao(usuario)]);
	const [sessaoAtivaId, setSessaoAtivaId] = useState<string | null>(null);
	const [escopo, setEscopo] = useState<EscopoSugestao>("Todos os dados");
	const [enviando, setEnviando] = useState(false);
	const [widgetAberto, setWidgetAberto] = useState(false);
	const [historicoIndisponivel, setHistoricoIndisponivel] = useState(false);
	const consultaRef = useRef<ConsultaAtiva | null>(null);
	// Conversas com pergunta enviada: o servidor pode já ter gravado a auditoria delas.
	const perguntadas = useRef(new Set<string>());
	// Título e estrela mudados antes da primeira resposta, enviados quando ela chega.
	const pendentes = useRef(new Map<string, CamposSessao>());

	const sessaoAtiva = useMemo(
		() =>
			sessoes.find((sessao) => sessao.sessionId === sessaoAtivaId) ??
			sessoes[0],
		[sessoes, sessaoAtivaId],
	);

	// O histórico é do usuário no banco (GET /ai/sessions), e segue o login em qualquer
	// computador. Sem resposta da API, a conversa nova continua disponível.
	useEffect(() => {
		const controller = new AbortController();
		setSessoes([novaSessao(usuario)]);
		setSessaoAtivaId(null);
		setHistoricoIndisponivel(false);
		perguntadas.current.clear();
		pendentes.current.clear();
		buscarSessoesIa(controller.signal)
			.then((lista) => {
				const salvas = lista.map((sessao) => sessaoDaApi(sessao, usuario));
				setSessoes((atuais) => {
					const todas = mesclarSessoes(atuais, salvas);
					return todas.length > 0 ? todas : atuais;
				});
			})
			.catch(() => {
				if (!controller.signal.aborted) setHistoricoIndisponivel(true);
			});
		return () => controller.abort();
	}, [usuario]);

	useEffect(() => {
		if (rota === "/agente") setWidgetAberto(false);
	}, [rota]);

	useEffect(() => {
		function atalho(event: globalThis.KeyboardEvent) {
			if (
				event.defaultPrevented ||
				event.repeat ||
				event.altKey ||
				!(event.ctrlKey || event.metaKey) ||
				event.key.toLowerCase() !== "j"
			)
				return;
			if (rota === "/agente") return;
			if (!widgetAberto && document.querySelector('[aria-modal="true"]'))
				return;
			event.preventDefault();
			setWidgetAberto(!widgetAberto);
		}
		window.addEventListener("keydown", atalho);
		return () => window.removeEventListener("keydown", atalho);
	}, [rota, widgetAberto]);

	const alternarWidget = useCallback(() => {
		setWidgetAberto((aberto) => !aberto);
	}, []);

	const atualizarTurno = useCallback(
		(sessionId: string, turnoId: string, mudanca: Partial<TurnoConversa>) => {
			const agora = new Date().toISOString();
			setSessoes((atuais) =>
				atuais.map((sessao) =>
					sessao.sessionId === sessionId
						? {
								...sessao,
								atualizadaEm: agora,
								turnos: sessao.turnos.map((turno) =>
									turno.id === turnoId ? { ...turno, ...mudanca } : turno,
								),
							}
						: sessao,
				),
			);
		},
		[],
	);

	const cancelarConsulta = useCallback(() => {
		const consulta = consultaRef.current;
		if (!consulta) return;
		consultaRef.current = null;
		consulta.controller.abort();
		atualizarTurno(consulta.sessionId, consulta.turnoId, {
			status: "error",
			erro: "Consulta cancelada. Tente novamente.",
			etapa: undefined,
		});
		setEnviando(false);
	}, [atualizarTurno]);

	useEffect(() => {
		if (rota !== "/agente") return;
		return () => cancelarConsulta();
	}, [rota, cancelarConsulta]);
	useEffect(() => () => cancelarConsulta(), [cancelarConsulta]);

	const consultar = useCallback(
		(sessionId: string, turnoId: string, question: string) =>
			consultarAgente(
				consultaRef,
				{ sessionId, turnoId, question },
				{ atualizarTurno, setEnviando },
			),
		[atualizarTurno],
	);

	const enviarPergunta = useCallback(
		async (perguntaTexto: string) => {
			if (consultaRef.current) return;
			const validacao = validarPergunta(perguntaTexto);
			if (!validacao.ok) return;
			const sessionId = sessaoAtiva.sessionId;
			perguntadas.current.add(sessionId);
			const turnoId = crypto.randomUUID();
			const agora = new Date().toISOString();
			setSessoes((atuais) =>
				atuais.map((sessao) =>
					sessao.sessionId === sessionId
						? {
								...sessao,
								titulo:
									sessao.turnos.length === 0
										? gerarTituloSessao(validacao.question)
										: sessao.titulo,
								atualizadaEm: agora,
								turnos: [
									...sessao.turnos,
									{
										id: turnoId,
										question: validacao.question,
										criadoEm: agora,
										status: "pending" as const,
									},
								],
							}
						: sessao,
				),
			);
			await consultar(sessionId, turnoId, validacao.question);
		},
		[sessaoAtiva, consultar],
	);

	const tentarNovamente = useCallback(
		async (turnoId: string) => {
			if (consultaRef.current) return;
			const sessao = sessoes.find((atual) =>
				atual.turnos.some((turno) => turno.id === turnoId),
			);
			const turno = sessao?.turnos.find((atual) => atual.id === turnoId);
			if (!sessao || !turno) return;
			atualizarTurno(sessao.sessionId, turnoId, {
				status: "pending",
				resposta: undefined,
				erro: undefined,
			});
			await consultar(sessao.sessionId, turnoId, turno.question);
		},
		[sessoes, atualizarTurno, consultar],
	);

	const novaConversa = useCallback(() => {
		cancelarConsulta();
		const nova = novaSessao(usuario);
		setSessoes((atuais) =>
			[nova, ...atuais.filter((sessao) => sessao.turnos.length > 0)].slice(
				0,
				MAX_SESSOES,
			),
		);
		setSessaoAtivaId(nova.sessionId);
		return nova.sessionId;
	}, [usuario, cancelarConsulta]);

	const selecionarSessao = useCallback(
		(sessionId: string) => {
			if (consultaRef.current?.sessionId !== sessionId) cancelarConsulta();
			setSessaoAtivaId(sessionId);
		},
		[cancelarConsulta],
	);

	const enviarAlteracao = useCallback(
		(sessionId: string, enviado: CamposSessao, anterior: CamposSessao) => {
			alterarSessaoIa(sessionId, enviado)
				.then((salva) =>
					setSessoes((atuais) =>
						atuais.map((atual) =>
							atual.sessionId === sessionId
								? { ...atual, atualizadaEm: salva.atualizada_em }
								: atual,
						),
					),
				)
				.catch((erro) => {
					if (semConversa(erro)) return;
					// Falhou no servidor: a tela volta ao que ele guarda, campo a campo.
					setSessoes((atuais) =>
						atuais.map((atual) =>
							atual.sessionId === sessionId
								? desfazerAlteracao(atual, enviado, anterior)
								: atual,
						),
					);
				});
		},
		[],
	);

	// A primeira resposta cria a conversa no servidor: só então título e estrela vão para lá.
	useEffect(() => {
		for (const [sessionId, campos] of pendentes.current) {
			const sessao = sessoes.find((atual) => atual.sessionId === sessionId);
			if (!sessao) {
				pendentes.current.delete(sessionId);
				continue;
			}
			if (!noServidor(sessao)) continue;
			pendentes.current.delete(sessionId);
			// O que o servidor tem sem alteração: a primeira pergunta como título, sem estrela.
			const padrao = {
				titulo: sessao.turnos[0].question.slice(0, 80),
				favorita: false,
			};
			enviarAlteracao(sessionId, campos, padrao);
		}
	}, [sessoes, enviarAlteracao]);

	const alterarSessao = useCallback(
		(sessionId: string, mudanca: CamposSessao) => {
			const sessao = sessoes.find((atual) => atual.sessionId === sessionId);
			if (!sessao) return;
			const anterior = { titulo: sessao.titulo, favorita: sessao.favorita };
			setSessoes((atuais) =>
				atuais.map((atual) =>
					atual.sessionId === sessionId ? { ...atual, ...mudanca } : atual,
				),
			);
			if (noServidor(sessao)) enviarAlteracao(sessionId, mudanca, anterior);
			else
				pendentes.current.set(sessionId, {
					...pendentes.current.get(sessionId),
					...mudanca,
				});
		},
		[sessoes, enviarAlteracao],
	);

	const renomearSessao = useCallback(
		(sessionId: string, novoTitulo: string) => {
			const limpo = novoTitulo.trim().replace(/\s+/g, " ");
			if (limpo) alterarSessao(sessionId, { titulo: limpo.slice(0, 80) });
		},
		[alterarSessao],
	);

	const alternarFavorita = useCallback(
		(sessionId: string) => {
			const sessao = sessoes.find((atual) => atual.sessionId === sessionId);
			if (sessao) alterarSessao(sessionId, { favorita: !sessao.favorita });
		},
		[sessoes, alterarSessao],
	);

	const excluirNoServidor = useCallback(
		(sessao: SessaoConversa, indice: number) => {
			pendentes.current.delete(sessao.sessionId);
			// Com pergunta enviada, o DELETE vai mesmo sem resposta na tela: ele espera a
			// pergunta em andamento terminar (DEC-053), e a conversa não volta na próxima carga.
			if (!noServidor(sessao) && !perguntadas.current.has(sessao.sessionId))
				return;
			excluirSessaoIa(sessao.sessionId).catch((erro) => {
				if (!semConversa(erro))
					setSessoes((atuais) => reinserirSessao(atuais, sessao, indice));
			});
		},
		[],
	);

	const removerSessao = useCallback(
		(sessionId: string) => {
			if (consultaRef.current?.sessionId === sessionId) cancelarConsulta();
			const indice = sessoes.findIndex(
				(atual) => atual.sessionId === sessionId,
			);
			setSessoes((atuais) => {
				const restantes = atuais.filter(
					(atual) => atual.sessionId !== sessionId,
				);
				return restantes.length > 0 ? restantes : [novaSessao(usuario)];
			});
			setSessaoAtivaId((atual) => (atual === sessionId ? null : atual));
			if (indice >= 0) excluirNoServidor(sessoes[indice], indice);
		},
		[sessoes, usuario, cancelarConsulta, excluirNoServidor],
	);

	const limparHistorico = useCallback(() => {
		cancelarConsulta();
		sessoes.forEach((sessao, indice) => {
			excluirNoServidor(sessao, indice);
		});
		setSessoes([novaSessao(usuario)]);
		setSessaoAtivaId(null);
	}, [sessoes, usuario, cancelarConsulta, excluirNoServidor]);
	const valor = useMemo<AgenteContextValue>(
		() => ({
			sessoes,
			sessaoAtiva,
			escopo,
			setEscopo,
			enviando,
			cancelarConsulta,
			widgetAberto,
			setWidgetAberto,
			alternarWidget,
			novaConversa,
			selecionarSessao,
			renomearSessao,
			alternarFavorita,
			removerSessao,
			limparHistorico,
			enviarPergunta,
			tentarNovamente,
			historicoIndisponivel,
		}),
		[
			sessoes,
			sessaoAtiva,
			escopo,
			enviando,
			cancelarConsulta,
			widgetAberto,
			alternarWidget,
			novaConversa,
			selecionarSessao,
			renomearSessao,
			alternarFavorita,
			removerSessao,
			limparHistorico,
			enviarPergunta,
			tentarNovamente,
			historicoIndisponivel,
		],
	);

	return <AgenteContext value={valor}>{children}</AgenteContext>;
}
