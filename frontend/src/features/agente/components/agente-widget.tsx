import {
	ArrowsOutSimpleIcon,
	BuildingsIcon,
	CaretDownIcon,
	ChatCircleIcon,
	ClockCounterClockwiseIcon,
	CurrencyCircleDollarIcon,
	GaugeIcon,
	MinusIcon,
	PlusIcon,
	SpinnerGapIcon,
	XIcon,
} from "@phosphor-icons/react";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef } from "react";
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
import {
	EXEMPLOS_PERGUNTAS,
	filtrarExemplosPorEscopo,
	formatarTempoRelativo,
} from "../conversions";
import type { EscopoSugestao } from "../types";
import { AgenteComposer } from "./agente-composer";
import { AgenteTurnoItem } from "./agente-mensagem";
import { useAgente } from "./agente-provider";

const ICONE_POR_ESCOPO: Record<
	Exclude<EscopoSugestao, "Todos os dados">,
	typeof CurrencyCircleDollarIcon
> = {
	"Receita e faturamento": CurrencyCircleDollarIcon,
	"Rede (DEC/FEC)": GaugeIcon,
	"Unidades consumidoras": BuildingsIcon,
	"Atendimento e medidores": ChatCircleIcon,
};

export function AgenteWidget() {
	const pathname = useLocation({ select: (loc) => loc.pathname });
	const navigate = useNavigate();
	const {
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
		enviarPergunta,
		tentarNovamente,
	} = useAgente();
	const fimConversaRef = useRef<HTMLDivElement>(null);
	const ultimoTurno = sessaoAtiva.turnos.at(-1);
	const ultimoTurnoId = ultimoTurno?.id;
	const ultimoTurnoStatus = ultimoTurno?.status;

	useEffect(() => {
		if (!widgetAberto || !ultimoTurnoId || !ultimoTurnoStatus) return;
		fimConversaRef.current?.scrollIntoView({
			behavior: "smooth",
			block: "end",
		});
	}, [widgetAberto, ultimoTurnoId, ultimoTurnoStatus]);

	if (pathname === "/agente") return null;

	const sugestoes = filtrarExemplosPorEscopo(EXEMPLOS_PERGUNTAS, escopo).slice(
		0,
		3,
	);
	const sessoesComHistorico = sessoes.filter((s) => s.turnos.length > 0);

	return (
		<div className="fixed right-4 bottom-4 z-40 flex flex-col items-end gap-2.5">
			<AnimatePresence>
				{widgetAberto && (
					<motion.section
						aria-label="Chat rápido do Agente de IA"
						initial={{ opacity: 0, y: 14, scale: 0.96 }}
						animate={{ opacity: 1, y: 0, scale: 1 }}
						exit={{ opacity: 0, y: 10, scale: 0.96 }}
						transition={{ type: "spring", stiffness: 500, damping: 36 }}
						className="flex h-[min(36rem,calc(100svh-5.5rem))] w-[min(25rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-lg border border-border-strong bg-surface-1 shadow-modal"
					>
						<div className="flex h-10 shrink-0 items-center justify-between gap-2 border-b border-border px-3">
							<DropdownMenu>
								<DropdownMenuTrigger className="inline-flex h-6 min-w-0 cursor-pointer items-center gap-1 rounded-md px-1.5 text-body font-medium text-text outline-none transition-colors hover:bg-hover focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:bg-hover">
									<span className="max-w-48 truncate">
										{sessaoAtiva.titulo}
									</span>
									<CaretDownIcon
										aria-hidden
										className="size-3.5 text-text-muted"
									/>
								</DropdownMenuTrigger>
								<DropdownMenuContent align="start" className="w-64 p-1.5">
									<DropdownMenuItem
										onClick={() => void novaConversa()}
										className="font-medium"
									>
										<PlusIcon aria-hidden />
										Nova conversa
									</DropdownMenuItem>
									{sessoesComHistorico.length > 0 && (
										<>
											<DropdownMenuSeparator />
											<DropdownMenuGroup>
												<DropdownMenuLabel>Hoje</DropdownMenuLabel>
												{sessoesComHistorico.map((sessao) => {
													const ativa =
														sessao.sessionId === sessaoAtiva.sessionId;
													return (
														<DropdownMenuItem
															key={sessao.sessionId}
															onClick={() => {
																selecionarSessao(sessao.sessionId);
																setWidgetAberto(true);
															}}
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
							<div className="flex items-center gap-0.5">
								<Button
									variant="ghost"
									size="icon-xs"
									aria-label="Minimizar janela do agente"
									onClick={() => setWidgetAberto(false)}
								>
									<MinusIcon aria-hidden />
								</Button>
								<Button
									variant="ghost"
									size="icon-xs"
									aria-label="Expandir para a tela do agente"
									onClick={() => {
										setWidgetAberto(false);
										void navigate({ to: "/agente" });
									}}
								>
									<ArrowsOutSimpleIcon aria-hidden />
								</Button>
								<Button
									variant="ghost"
									size="icon-xs"
									aria-label="Fechar janela do agente"
									onClick={() => setWidgetAberto(false)}
								>
									<XIcon aria-hidden />
								</Button>
							</div>
						</div>

						<div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
							{sessaoAtiva.turnos.length === 0 ? (
								<div className="mt-auto flex flex-col items-center justify-end gap-4 px-4 py-6 text-center">
									<LogoMark className="size-6 text-accent-text" />
									<div className="space-y-1">
										<h2 className="font-display text-heading text-text">
											Bem-vindo ao Agente V-Energy
										</h2>
										<p className="text-body text-text-muted">
											Pergunte qualquer coisa ou consulte indicadores da tela
											atual
										</p>
									</div>
									<div className="flex flex-wrap items-center justify-center gap-2">
										{sugestoes.map((sugestao) => {
											const Icone = ICONE_POR_ESCOPO[sugestao.escopo];
											return (
												<button
													key={sugestao.id}
													type="button"
													onClick={() => void enviarPergunta(sugestao.pergunta)}
													className="flex cursor-pointer items-center gap-1.5 rounded-full border border-border-strong bg-surface-2 px-3 py-1.5 text-small font-medium text-text transition-colors hover:border-focus-ring hover:bg-hover"
												>
													<Icone aria-hidden className="size-3.5" />
													{sugestao.titulo}
												</button>
											);
										})}
									</div>
								</div>
							) : (
								<div className="flex flex-col gap-4 p-3">
									{sessaoAtiva.turnos.map((turno, indice) => (
										<AgenteTurnoItem
											key={turno.id}
											turno={turno}
											enviando={enviando}
											compacto
											mostrarHorario={indice === 0}
											onRetry={(id) => void tentarNovamente(id)}
										/>
									))}
									<div ref={fimConversaRef} />
								</div>
							)}
						</div>

						<div className="border-t border-border bg-surface-1 p-2.5">
							<AgenteComposer
								compacto
								onSubmit={(texto) => void enviarPergunta(texto)}
								enviando={enviando}
								onStop={cancelarConsulta}
								escopo={escopo}
								onEscopoChange={setEscopo}
								placeholder={
									sessaoAtiva.turnos.length > 0
										? "Responder…"
										: "Pergunte sobre faturamento, rede ou UCs…"
								}
							/>
						</div>
					</motion.section>
				)}
			</AnimatePresence>

			<div className="flex items-center gap-1.5">
				<button
					type="button"
					onClick={alternarWidget}
					aria-expanded={widgetAberto}
					aria-keyshortcuts="Control+j Meta+j"
					className="flex h-9 cursor-pointer items-center gap-2 rounded-md border border-border-strong bg-surface-2 px-3.5 font-medium text-body text-text shadow-overlay transition-colors outline-none hover:border-focus-ring hover:bg-surface-1 focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50"
				>
					{enviando ? (
						<SpinnerGapIcon
							aria-hidden
							className="size-4 text-accent-text motion-safe:animate-spin"
						/>
					) : (
						<LogoMark
							weight={widgetAberto ? "fill" : "regular"}
							className="size-4 text-accent-text"
						/>
					)}
					<span>Agente</span>
					{sessaoAtiva.turnos.length > 0 && (
						<span className="rounded-full bg-accent-subtle px-1.5 font-mono text-small text-accent-text">
							{sessaoAtiva.turnos.length}
						</span>
					)}
				</button>
				<DropdownMenu>
					<DropdownMenuTrigger
						aria-label="Histórico de conversas do agente"
						className="inline-flex size-9 cursor-pointer items-center justify-center rounded-md border border-border-strong bg-surface-2 text-text shadow-overlay outline-none transition-colors hover:border-focus-ring hover:bg-surface-1 focus-visible:border-focus-ring focus-visible:ring-3 focus-visible:ring-focus-ring/50 data-popup-open:border-focus-ring"
					>
						<ClockCounterClockwiseIcon aria-hidden />
					</DropdownMenuTrigger>
					<DropdownMenuContent align="end" side="top" className="w-64 p-1.5">
						<DropdownMenuItem
							onClick={() => {
								void novaConversa();
								setWidgetAberto(true);
							}}
							className="font-medium"
						>
							<PlusIcon aria-hidden />
							Nova conversa
						</DropdownMenuItem>
						{sessoesComHistorico.length > 0 && (
							<>
								<DropdownMenuSeparator />
								<DropdownMenuGroup>
									<DropdownMenuLabel>Hoje</DropdownMenuLabel>
									{sessoesComHistorico.map((sessao) => {
										const ativa = sessao.sessionId === sessaoAtiva.sessionId;
										return (
											<DropdownMenuItem
												key={sessao.sessionId}
												onClick={() => {
													selecionarSessao(sessao.sessionId);
													setWidgetAberto(true);
												}}
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
			</div>
		</div>
	);
}
