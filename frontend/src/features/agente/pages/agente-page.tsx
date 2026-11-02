import {
	BuildingsIcon,
	CaretDownIcon,
	ChatCircleIcon,
	ClipboardTextIcon,
	CurrencyCircleDollarIcon,
	DotsThreeIcon,
	GaugeIcon,
	PencilSimpleIcon,
	PlusIcon,
	StarIcon,
	TrashIcon,
	XIcon,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { HeaderTrilha } from "#/components/layout/header";
import { LogoMark } from "#/components/layout/logo";
import { Button } from "#/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "#/components/ui/dropdown-menu";
import { cn } from "#/lib/utils";
import { AgenteComposer } from "../components/agente-composer";
import { AgenteTurnoItem } from "../components/agente-mensagem";
import { useAgente } from "../components/agente-provider";
import {
	EXEMPLOS_PERGUNTAS,
	filtrarExemplosPorEscopo,
	formatarSessaoComoMarkdown,
	formatarTempoRelativo,
} from "../conversions";
import type { ExemploPergunta } from "../types";

const ICONE_POR_ESCOPO: Record<
	ExemploPergunta["escopo"],
	typeof CurrencyCircleDollarIcon
> = {
	"Receita e faturamento": CurrencyCircleDollarIcon,
	"Rede (DEC/FEC)": GaugeIcon,
	"Unidades consumidoras": BuildingsIcon,
	"Atendimento e medidores": ChatCircleIcon,
};

export function AgentePage() {
	const {
		sessoes,
		sessaoAtiva,
		escopo,
		setEscopo,
		enviando,
		cancelarConsulta,
		novaConversa,
		selecionarSessao,
		renomearSessao,
		alternarFavorita,
		removerSessao,
		enviarPergunta,
		tentarNovamente,
	} = useAgente();
	const [mostrarExemplos, setMostrarExemplos] = useState(true);
	const [editandoTitulo, setEditandoTitulo] = useState(false);
	const [tituloTemp, setTituloTemp] = useState("");
	const inputTituloRef = useRef<HTMLInputElement>(null);
	const fimConversaRef = useRef<HTMLDivElement>(null);
	const ultimoTurno = sessaoAtiva.turnos.at(-1);
	const ultimoTurnoId = ultimoTurno?.id;
	const ultimoTurnoStatus = ultimoTurno?.status;

	useEffect(() => {
		if (!ultimoTurnoId || !ultimoTurnoStatus) return;
		fimConversaRef.current?.scrollIntoView({
			behavior: "smooth",
			block: "end",
		});
	}, [ultimoTurnoId, ultimoTurnoStatus]);

	const exemplos = filtrarExemplosPorEscopo(EXEMPLOS_PERGUNTAS, escopo).slice(
		0,
		3,
	);
	const vazia = sessaoAtiva.turnos.length === 0;
	const sessoesComHistorico = sessoes.filter((s) => s.turnos.length > 0);
	const sessoesFavoritas = sessoesComHistorico.filter((s) => s.favorita);
	const sessoesRecentes = sessoesComHistorico.filter((s) => !s.favorita);

	function iniciarRenomeacao() {
		setTituloTemp(sessaoAtiva.titulo);
		setEditandoTitulo(true);
		requestAnimationFrame(() => {
			inputTituloRef.current?.focus();
			inputTituloRef.current?.select();
		});
	}

	function confirmarRenomeacao() {
		if (tituloTemp.trim()) {
			renomearSessao(sessaoAtiva.sessionId, tituloTemp);
		}
		setEditandoTitulo(false);
	}

	async function copiarComoMarkdown() {
		if (!navigator.clipboard) return;
		try {
			await navigator.clipboard.writeText(
				formatarSessaoComoMarkdown(sessaoAtiva),
			);
		} catch {
			// Ignora quando o navegador bloqueia a área de transferência
		}
	}

	useEffect(() => {
		function aoTeclarAtalho(event: globalThis.KeyboardEvent) {
			if (vazia || editandoTitulo || event.defaultPrevented || event.repeat)
				return;
			const alvo = event.target;
			if (
				alvo instanceof HTMLElement &&
				(alvo.isContentEditable ||
					["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName))
			)
				return;
			if (document.querySelector('[aria-modal="true"]')) return;

			if (
				event.shiftKey &&
				!event.ctrlKey &&
				!event.metaKey &&
				!event.altKey &&
				event.key.toLowerCase() === "r"
			) {
				event.preventDefault();
				setTituloTemp(sessaoAtiva.titulo);
				setEditandoTitulo(true);
				requestAnimationFrame(() => {
					inputTituloRef.current?.focus();
					inputTituloRef.current?.select();
				});
				return;
			}

			if (
				(event.ctrlKey || event.metaKey) &&
				!event.shiftKey &&
				!event.altKey &&
				(event.key === "Delete" || event.key === "Backspace")
			) {
				event.preventDefault();
				removerSessao(sessaoAtiva.sessionId);
			}
		}
		window.addEventListener("keydown", aoTeclarAtalho);
		return () => window.removeEventListener("keydown", aoTeclarAtalho);
	}, [
		vazia,
		editandoTitulo,
		sessaoAtiva.sessionId,
		sessaoAtiva.titulo,
		removerSessao,
	]);

	return (
		<>
			<HeaderTrilha>
				<div className="flex min-w-0 items-center gap-0.5">
					{editandoTitulo ? (
						<input
							ref={inputTituloRef}
							type="text"
							value={tituloTemp}
							aria-label="Nome da conversa"
							onChange={(e) => setTituloTemp(e.target.value)}
							onBlur={confirmarRenomeacao}
							onKeyDown={(e) => {
								if (e.key === "Enter") {
									e.preventDefault();
									confirmarRenomeacao();
								} else if (e.key === "Escape") {
									e.preventDefault();
									setEditandoTitulo(false);
								}
							}}
							className="h-6 w-56 rounded-sm border border-focus-ring bg-surface-2 px-2 text-body font-medium text-text outline-none"
						/>
					) : (
						<DropdownMenu>
							<DropdownMenuTrigger className="inline-flex h-6 min-w-0 cursor-pointer items-center gap-1.5 rounded-md px-2 text-small font-medium text-text outline-none transition-colors hover:bg-hover focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover">
								<span className="max-w-64 truncate">{sessaoAtiva.titulo}</span>
								<CaretDownIcon
									aria-hidden
									className="size-3.5 text-text-muted"
								/>
							</DropdownMenuTrigger>
							<DropdownMenuContent align="start" className="w-72 p-1.5">
								<DropdownMenuItem
									onClick={() => void novaConversa()}
									className="font-medium"
								>
									<PlusIcon aria-hidden />
									Nova conversa
								</DropdownMenuItem>
								{sessoesFavoritas.length > 0 && (
									<>
										<DropdownMenuSeparator />
										<DropdownMenuGroup>
											<DropdownMenuLabel>Favoritas</DropdownMenuLabel>
											{sessoesFavoritas.map((sessao) => {
												const ativa =
													sessao.sessionId === sessaoAtiva.sessionId;
												return (
													<DropdownMenuItem
														key={sessao.sessionId}
														onClick={() => selecionarSessao(sessao.sessionId)}
														className={cn(ativa && "bg-hover font-medium")}
													>
														<StarIcon
															aria-hidden
															weight="fill"
															className="size-3.5 text-accent-text"
														/>
														<span className="min-w-0 flex-1 truncate">
															{sessao.titulo}
														</span>
														<span className="shrink-0 text-small text-text-muted">
															{formatarTempoRelativo(sessao.atualizadaEm)}
														</span>
													</DropdownMenuItem>
												);
											})}
										</DropdownMenuGroup>
									</>
								)}
								{sessoesRecentes.length > 0 && (
									<>
										<DropdownMenuSeparator />
										<DropdownMenuGroup>
											<DropdownMenuLabel>Hoje</DropdownMenuLabel>
											{sessoesRecentes.map((sessao) => {
												const ativa =
													sessao.sessionId === sessaoAtiva.sessionId;
												return (
													<DropdownMenuItem
														key={sessao.sessionId}
														onClick={() => selecionarSessao(sessao.sessionId)}
														className={cn(ativa && "bg-hover font-medium")}
													>
														<span className="min-w-0 flex-1 truncate">
															{sessao.titulo}
														</span>
														<span className="shrink-0 text-small text-text-muted">
															{formatarTempoRelativo(sessao.atualizadaEm)}
														</span>
													</DropdownMenuItem>
												);
											})}
										</DropdownMenuGroup>
									</>
								)}
							</DropdownMenuContent>
						</DropdownMenu>
					)}

					{!vazia && (
						<>
							<Button
								type="button"
								variant="ghost"
								size="icon-xs"
								aria-label={
									sessaoAtiva.favorita
										? "Remover dos favoritos"
										: "Favoritar conversa"
								}
								aria-pressed={Boolean(sessaoAtiva.favorita)}
								onClick={() => alternarFavorita(sessaoAtiva.sessionId)}
								className={cn(
									"rounded-full",
									sessaoAtiva.favorita
										? "text-accent-text hover:text-accent-hover"
										: "text-text-muted hover:text-text",
								)}
							>
								<StarIcon
									aria-hidden
									weight={sessaoAtiva.favorita ? "fill" : "regular"}
									className="size-3.5"
								/>
							</Button>

							<DropdownMenu>
								<DropdownMenuTrigger
									aria-label="Opções da conversa"
									className="inline-flex size-6 cursor-pointer items-center justify-center rounded-full text-text-muted outline-none transition-colors hover:bg-hover hover:text-text focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-surface-2 data-popup-open:text-text"
								>
									<DotsThreeIcon aria-hidden weight="bold" className="size-4" />
								</DropdownMenuTrigger>
								<DropdownMenuContent align="start" className="w-56 p-1.5">
									<DropdownMenuGroup>
										<DropdownMenuItem onClick={iniciarRenomeacao}>
											<PencilSimpleIcon
												aria-hidden
												className="text-text-muted"
											/>
											<span className="flex-1">Renomear…</span>
											<kbd className="font-sans text-small text-text-muted">
												⇧ R
											</kbd>
										</DropdownMenuItem>
										<DropdownMenuItem onClick={() => void copiarComoMarkdown()}>
											<ClipboardTextIcon
												aria-hidden
												className="text-text-muted"
											/>
											<span className="flex-1">Copiar como markdown</span>
										</DropdownMenuItem>
									</DropdownMenuGroup>
									<DropdownMenuSeparator />
									<DropdownMenuGroup>
										<DropdownMenuItem
											onClick={() => removerSessao(sessaoAtiva.sessionId)}
										>
											<TrashIcon aria-hidden className="text-text-muted" />
											<span className="flex-1">Excluir</span>
											<kbd className="font-sans text-small text-text-muted">
												Ctrl Delete
											</kbd>
										</DropdownMenuItem>
									</DropdownMenuGroup>
								</DropdownMenuContent>
							</DropdownMenu>
						</>
					)}
				</div>
			</HeaderTrilha>

			<div className="flex min-h-full flex-col justify-between">
				{vazia ? (
					<div className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-6 px-4 py-12">
						<AgenteComposer
							autoFocus
							onSubmit={(texto) => void enviarPergunta(texto)}
							enviando={enviando}
							onStop={cancelarConsulta}
							escopo={escopo}
							onEscopoChange={setEscopo}
							placeholder="Pergunte sobre consumo, faturamento, DEC/FEC ou uma UC…"
						/>
						<p className="mx-auto inline-flex items-center gap-1.5 rounded-full border border-border-strong bg-surface-2 px-3 py-1 text-small text-text-muted">
							<LogoMark className="size-3.5 text-accent-text" />
							Conectado à camada Gold · 9 views auditáveis
						</p>
						{mostrarExemplos && (
							<section aria-label="Exemplos de perguntas" className="space-y-3">
								<div className="flex items-center justify-between text-small text-text-muted">
									<span>Comece com alguns exemplos</span>
									<Button
										variant="ghost"
										size="icon-xs"
										aria-label="Ocultar exemplos"
										onClick={() => setMostrarExemplos(false)}
									>
										<XIcon aria-hidden />
									</Button>
								</div>
								<div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
									{exemplos.map((exemplo) => (
										<CartaoExemplo
											key={exemplo.id}
											exemplo={exemplo}
											onEscolher={() => void enviarPergunta(exemplo.pergunta)}
										/>
									))}
								</div>
							</section>
						)}
					</div>
				) : (
					<>
						<div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-8">
							{sessaoAtiva.turnos.map((turno, indice) => (
								<AgenteTurnoItem
									key={turno.id}
									turno={turno}
									enviando={enviando}
									mostrarHorario={indice === 0}
									onRetry={(id) => void tentarNovamente(id)}
								/>
							))}
							<div ref={fimConversaRef} className="scroll-mb-32" />
						</div>
						<div className="sticky bottom-0 z-10 bg-gradient-to-t from-surface-1 via-surface-1 to-transparent px-4 pt-2 pb-4">
							<div className="mx-auto max-w-2xl">
								<AgenteComposer
									compacto
									onSubmit={(texto) => void enviarPergunta(texto)}
									enviando={enviando}
									onStop={cancelarConsulta}
									escopo={escopo}
									onEscopoChange={setEscopo}
									placeholder="Responder…"
								/>
							</div>
						</div>
					</>
				)}
			</div>
		</>
	);
}

function CartaoExemplo({
	exemplo,
	onEscolher,
}: {
	exemplo: ExemploPergunta;
	onEscolher: () => void;
}) {
	const Icone = ICONE_POR_ESCOPO[exemplo.escopo];

	return (
		<button
			type="button"
			onClick={onEscolher}
			className="group flex min-h-36 cursor-pointer flex-col justify-between rounded-lg border border-border bg-surface-2/60 p-4 text-left transition-colors hover:border-border-strong hover:bg-surface-2 focus-visible:border-focus-ring"
		>
			<Icone
				aria-hidden
				className="size-4 text-text-muted transition-colors group-hover:text-accent-text"
			/>
			<div className="space-y-1 pt-6">
				<div className="font-medium text-body text-text">{exemplo.titulo}</div>
				<p className="text-small text-text-muted text-pretty">
					{exemplo.descricao}
				</p>
			</div>
		</button>
	);
}
