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
import { type ConsultaAtiva, consultarAgente } from "../consulta";
import {
	gerarTituloSessao,
	MAX_SESSOES,
	parseSessoesSalvas,
	SESSOES_STORAGE_KEY,
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

export function AgenteProvider({
	children,
	usuario,
}: {
	children: ReactNode;
	usuario: string;
}) {
	const chave = `${SESSOES_STORAGE_KEY}:${usuario}`;
	const rota = useLocation({ select: (loc) => loc.pathname });
	const [sessoes, setSessoes] = useState(() => [novaSessao(usuario)]);
	const [sessaoAtivaId, setSessaoAtivaId] = useState<string | null>(null);
	const [escopo, setEscopo] = useState<EscopoSugestao>("Todos os dados");
	const [enviando, setEnviando] = useState(false);
	const [widgetAberto, setWidgetAberto] = useState(false);
	const [chaveCarregada, setChaveCarregada] = useState<string | null>(null);
	const [localDisponivel, setLocalDisponivel] = useState(true);
	const consultaRef = useRef<ConsultaAtiva | null>(null);

	const sessaoAtiva = useMemo(
		() =>
			sessoes.find((sessao) => sessao.sessionId === sessaoAtivaId) ??
			sessoes[0],
		[sessoes, sessaoAtivaId],
	);

	useEffect(() => {
		function carregar(): SessaoConversa[] {
			try {
				const salvas = parseSessoesSalvas(localStorage.getItem(chave));
				return salvas.length > 0 ? salvas : [novaSessao(usuario)];
			} catch {
				setLocalDisponivel(false);
				return [novaSessao(usuario)];
			}
		}
		const iniciais = carregar();
		setSessoes(iniciais);
		setSessaoAtivaId(iniciais[0].sessionId);
		setChaveCarregada(chave);
	}, [chave, usuario]);

	useEffect(() => {
		if (chaveCarregada !== chave || !localDisponivel) return;
		try {
			const persistiveis = sessoes
				.filter((sessao) => sessao.turnos.length > 0)
				.slice(0, MAX_SESSOES);
			localStorage.setItem(chave, JSON.stringify(persistiveis));
		} catch {
			setLocalDisponivel(false);
		}
	}, [sessoes, chaveCarregada, localDisponivel, chave]);

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

	const renomearSessao = useCallback(
		(sessionId: string, novoTitulo: string) => {
			const limpo = novoTitulo.trim().replace(/\s+/g, " ");
			if (!limpo) return;
			const agora = new Date().toISOString();
			setSessoes((atuais) =>
				atuais.map((sessao) =>
					sessao.sessionId === sessionId
						? { ...sessao, titulo: limpo.slice(0, 80), atualizadaEm: agora }
						: sessao,
				),
			);
		},
		[],
	);

	const alternarFavorita = useCallback((sessionId: string) => {
		setSessoes((atuais) =>
			atuais.map((sessao) =>
				sessao.sessionId === sessionId
					? { ...sessao, favorita: !sessao.favorita }
					: sessao,
			),
		);
	}, []);

	const removerSessao = useCallback(
		(sessionId: string) => {
			if (consultaRef.current?.sessionId === sessionId) cancelarConsulta();
			setSessoes((atuais) => {
				const restantes = atuais.filter(
					(sessao) => sessao.sessionId !== sessionId,
				);
				return restantes.length > 0 ? restantes : [novaSessao(usuario)];
			});
			setSessaoAtivaId((atual) => (atual === sessionId ? null : atual));
		},
		[usuario, cancelarConsulta],
	);

	const limparHistorico = useCallback(() => {
		cancelarConsulta();
		setSessoes([novaSessao(usuario)]);
		setSessaoAtivaId(null);
	}, [usuario, cancelarConsulta]);
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
		],
	);

	return <AgenteContext value={valor}>{children}</AgenteContext>;
}
