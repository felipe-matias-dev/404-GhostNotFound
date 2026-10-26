// Gráfico de cascata (ponte) horizontal: um total inicial, os efeitos que somam ou subtraem
// e o total final. Cada etapa é uma linha de tabela (rótulo, barra e valor), então o leitor
// de tela lê a ponte como dados, e a barra é só reforço visual (`aria-hidden`).
// - Totais partem do zero; se o zero ficasse longe demais, o eixo começa perto do menor
//   acumulado para os efeitos aparecerem, e as barras de total ganham um corte e uma nota.
// - Alta em `success`, queda em `danger`; o sinal do valor diz o mesmo sem depender da cor.
// - As barras crescem a partir do acumulado anterior e, quando os dados mudam, deslizam até a
//   nova posição (mola); com movimento reduzido, trocam sem animação.
// - Com `onSelect`, cada efeito vira um botão (`aria-pressed`) que cobre a linha; o marcado
//   fica em `accent`. Os totais não são clicáveis.
// - Efeito igual a zero vira uma linha baixa (sem barra a mostrar); o degrau acompanha a
//   altura de cada linha.
import {
	ArrowsClockwiseIcon,
	TrayIcon,
	WarningCircleIcon,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import { Button } from "#/components/ui/button";
import {
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from "#/components/ui/tooltip";
import { formatBRL, formatPct } from "#/lib/format";
import { cn } from "#/lib/utils";

const SPRING = {
	type: "spring",
	stiffness: 260,
	damping: 32,
	mass: 0.8,
} as const;
const STAGGER = 0.04;
const INSTANT = { duration: 0 } as const;
// Folga abaixo do menor acumulado, em fração da amplitude, quando o eixo não começa no zero.
const FOLGA = 0.6;
// Molde de uma ponte em queda: [início, largura] de cada barra, em % da trilha.
const SKELETON_BARS = [
	[0, 78],
	[64, 14],
	[70, 9],
	[50, 20],
	[46, 4],
	[0, 46],
] as const;

export type WaterfallStep = {
	id: string;
	label: string;
	/** Total: o nível naquele ponto. Efeito: quanto soma (positivo) ou subtrai (negativo). */
	value: number;
	kind: "total" | "delta";
};

export type WaterfallChartProps = {
	/** Nome acessível da tabela (legenda lida pelo leitor de tela). */
	label: string;
	/** `undefined` enquanto nunca carregou. */
	steps?: WaterfallStep[];
	/** Frase de leitura rápida, acima das barras. */
	summary?: ReactNode;
	formatValue?: (value: number) => string;
	/** Complemento do título do tooltip da variação líquida ("Diferença vs. início"). */
	compareLabel?: string;
	/** Cabeçalho (lido pelo leitor de tela) da coluna de percentual sobre o primeiro total. */
	percentLabel?: string;
	loading?: boolean;
	error?: string | null;
	onRetry?: () => void;
	emptyMessage?: string;
	skeletonRows?: number;
	/** Efeito marcado (ex.: o que ordena uma tabela ao lado). */
	selectedId?: string | null;
	/**
	 * Com ele, os efeitos (não os totais) viram botões: clicar escolhe o efeito, e cabe a quem
	 * chama desmarcar quando o mesmo efeito é clicado de novo.
	 */
	onSelect?: (step: WaterfallStep) => void;
	/** Dica no rodapé quando os efeitos são clicáveis (ex.: o que o clique faz). */
	selectHint?: string;
	className?: string;
};

type Bar = {
	step: WaterfallStep;
	/** Início da barra; `null` nos totais, que partem da âncora do eixo. */
	start: number | null;
	/** Acumulado depois da etapa. */
	end: number;
};

function bars(steps: WaterfallStep[]): Bar[] {
	let running = 0;
	return steps.map((step) => {
		if (step.kind === "total") {
			running = step.value;
			return { step, start: null, end: step.value };
		}
		const start = running;
		running += step.value;
		return { step, start, end: running };
	});
}

function scale(rows: Bar[]) {
	const values = rows.flatMap((b) =>
		b.start === null ? [b.end] : [b.start, b.end],
	);
	const lo = Math.min(...values);
	const hi = Math.max(...values);
	const span = hi - lo || Math.abs(hi) * 0.1 || 1;
	const min = lo >= 0 ? Math.max(0, lo - span * FOLGA) : lo;
	const max = hi <= 0 ? Math.min(0, hi + span * FOLGA) : hi;
	const anchor = Math.min(Math.max(0, min), max);
	const x = (v: number) => ((v - min) / (max - min || 1)) * 100;
	return { x, anchor, truncated: anchor !== 0 };
}

function StateBlock({
	tone,
	children,
	action,
}: {
	tone: "error" | "empty";
	children: ReactNode;
	action?: ReactNode;
}) {
	const Icon = tone === "error" ? WarningCircleIcon : TrayIcon;
	return (
		<div className="flex min-h-40 flex-col items-center justify-center gap-3 px-4 py-8 text-center">
			<Icon
				aria-hidden
				className={cn(
					"size-6",
					tone === "error" ? "text-danger" : "text-text-muted",
				)}
			/>
			<p
				className={cn(
					"max-w-prose text-body",
					tone === "error" ? "text-text" : "text-text-muted",
				)}
			>
				{children}
			</p>
			{action}
		</div>
	);
}

function tone(bar: Bar) {
	if (bar.step.kind === "total") return "total";
	if (bar.step.value > 0) return "up";
	if (bar.step.value < 0) return "down";
	return "flat";
}

// Efeito zero não tem barra: a linha fica baixa, para não ocupar o espaço de um efeito real.
const isZero = (bar: Bar) => bar.step.kind === "delta" && bar.step.value === 0;
const rowHeight = (bar: Bar) => (isZero(bar) ? 24 : 40);

const BAR_TONE = {
	total: "bg-text-muted",
	up: "bg-success",
	down: "bg-danger",
	flat: "bg-border-strong",
} as const;

const VALUE_TONE = {
	total: "font-medium text-text",
	up: "text-success",
	down: "text-danger",
	flat: "text-text-muted",
} as const;

export function WaterfallChart({
	label,
	steps,
	summary,
	formatValue = formatBRL,
	compareLabel = "vs. início",
	percentLabel = "Sobre o total inicial",
	loading = false,
	error = null,
	onRetry,
	emptyMessage = "Sem dados para a ponte.",
	skeletonRows = 6,
	selectedId = null,
	onSelect,
	selectHint,
	className,
}: WaterfallChartProps) {
	const reduced = useReducedMotion();
	const showSkeleton = !error && loading && steps === undefined;
	const showEmpty = !error && !showSkeleton && (steps?.length ?? 0) === 0;

	const shell = cn(
		"@container rounded-lg border border-border bg-surface-1",
		className,
	);

	if (error) {
		return (
			<div className={shell}>
				<StateBlock
					tone="error"
					action={
						onRetry ? (
							<Button variant="outline" size="sm" onClick={onRetry}>
								<ArrowsClockwiseIcon aria-hidden />
								Tentar de novo
							</Button>
						) : undefined
					}
				>
					{error}
				</StateBlock>
			</div>
		);
	}

	if (showSkeleton) {
		return (
			<div className={cn(shell, "px-4 py-3")} aria-busy>
				<span className="sr-only">Carregando {label.toLowerCase()}</span>
				<div aria-hidden className="flex flex-col">
					{Array.from({ length: skeletonRows }, (_, i) => {
						const [left, width] = SKELETON_BARS[i % SKELETON_BARS.length] ?? [
							0, 40,
						];
						return (
							// biome-ignore lint/suspicious/noArrayIndexKey: molde fixo, sem identidade.
							<div key={i} className="flex h-10 items-center gap-4">
								<div className="h-2 w-20 rounded-sm bg-pressed" />
								<div className="relative h-3 flex-1">
									<div
										className="absolute inset-y-0 rounded-sm bg-pressed"
										style={{ left: `${left}%`, width: `${width}%` }}
									/>
								</div>
								<div className="h-2 w-24 rounded-sm bg-pressed" />
							</div>
						);
					})}
				</div>
			</div>
		);
	}

	if (showEmpty || !steps) {
		return (
			<div className={shell}>
				<StateBlock tone="empty">{emptyMessage}</StateBlock>
			</div>
		);
	}

	const rows = bars(steps);
	const { x, anchor, truncated } = scale(rows);
	const first = steps[0];
	const base =
		first?.kind === "total" && first.value !== 0 ? first.value : null;
	const hasUp = steps.some((s) => s.kind === "delta" && s.value > 0);
	const hasDown = steps.some((s) => s.kind === "delta" && s.value < 0);

	const percent = (bar: Bar, index: number) => {
		if (base === null || index === 0) return null;
		return bar.step.kind === "delta"
			? bar.step.value / base
			: (bar.end - base) / base;
	};

	return (
		<div className={cn(shell, "px-4 py-3")} aria-busy={loading}>
			{summary && <p className="mb-2 text-body text-text-muted">{summary}</p>}
			<table className="w-full border-collapse">
				<caption className="sr-only">{label}</caption>
				<thead className="sr-only">
					<tr>
						<th scope="col">Etapa</th>
						<td aria-hidden />
						<th scope="col">Valor</th>
						<th scope="col" className="hidden @lg:table-cell">
							{percentLabel}
						</th>
					</tr>
				</thead>
				<tbody>
					{rows.map((bar, i) => {
						const t = tone(bar);
						const from = bar.start ?? anchor;
						const left = x(Math.min(from, bar.end));
						const width = Math.abs(x(bar.end) - x(from));
						// Cresce do acumulado anterior (efeito) ou da âncora (total) até o fim.
						const origin = x(from);
						const next = rows[i + 1];
						// Degrau: do centro desta linha ao centro da próxima (efeito zero é mais baixo).
						const stepHeight = next
							? (rowHeight(bar) + rowHeight(next)) / 2
							: 0;
						// Piso do efeito: o que já estava acumulado e continua depois dele.
						const floor =
							bar.start === null ? null : x(Math.min(bar.start, bar.end));
						const pct = percent(bar, i);
						const isLastTotal =
							i === rows.length - 1 && bar.step.kind === "total" && i > 0;
						const transition = reduced
							? INSTANT
							: { ...SPRING, delay: i * STAGGER };
						// Total final: quanto mudou desde o primeiro total, em destaque na barra e no valor.
						const net = isLastTotal && base !== null ? bar.end - base : null;
						const netTone =
							net === null || net === 0 ? "flat" : net > 0 ? "up" : "down";
						const signed =
							bar.step.kind === "delta" && bar.step.value > 0
								? `+${formatValue(bar.step.value)}`
								: formatValue(bar.step.value);
						const value = (
							<span className={cn("text-body", VALUE_TONE[t])}>{signed}</span>
						);
						const selectable =
							onSelect !== undefined && bar.step.kind === "delta";
						const selected = selectable && bar.step.id === selectedId;
						return (
							<tr
								key={bar.step.id}
								className={cn(
									"group transition-colors hover:bg-hover",
									isLastTotal && "border-t border-border",
									selectable && "relative cursor-pointer",
									selected && "bg-accent-subtle hover:bg-accent-subtle",
								)}
							>
								<th
									scope="row"
									className={cn(
										"w-px whitespace-nowrap py-0 pr-4 pl-1 text-left text-body font-normal text-text-muted @max-md:pt-2 @max-md:align-top",
										selected && "font-medium text-accent-text",
									)}
								>
									{selectable ? (
										// O botão cobre a linha inteira (`after`); barra e valor não pegam o clique.
										<button
											type="button"
											aria-pressed={selected}
											onClick={() => onSelect(bar.step)}
											className="cursor-pointer text-left underline decoration-border-strong decoration-dotted underline-offset-4 outline-none after:absolute after:inset-0 after:rounded-sm after:content-[''] group-hover:decoration-current focus-visible:after:shadow-[inset_0_0_0_2px_var(--color-focus-ring)]"
										>
											{bar.step.label}
										</button>
									) : (
										bar.step.label
									)}
								</th>
								{/* A barra não é dado para o leitor de tela: o valor está na coluna seguinte. */}
								<td
									aria-hidden
									className={cn("p-0", selectable && "pointer-events-none")}
								>
									{/* Estreito: valor em cima e a barra embaixo, com a largura toda da célula. O degrau
									    atravessaria o valor da linha seguinte; ali o trilho do acumulado basta. */}
									<div
										className={cn(
											"flex items-center @max-md:h-14 @max-md:flex-col-reverse @max-md:items-stretch @max-md:justify-center @max-md:gap-1.5",
											isZero(bar) ? "h-6" : "h-10",
										)}
									>
										<div className="relative h-3 flex-1 @max-md:flex-none">
											{floor !== null && (
												<motion.div
													className="absolute inset-y-0 rounded-l-sm bg-pressed transition-colors group-hover:bg-border-strong"
													initial={{ left: `${x(anchor)}%`, width: "0%" }}
													animate={{
														left: `${x(anchor)}%`,
														width: `${floor - x(anchor)}%`,
													}}
													transition={transition}
												/>
											)}
											{/* Degrau: liga o fim desta barra ao início da próxima, uma linha abaixo. */}
											{next && (
												<motion.div
													className="absolute top-1/2 w-0 border-l border-border-strong @max-md:hidden"
													style={{ height: stepHeight }}
													initial={{ left: `${x(bar.end)}%` }}
													animate={{ left: `${x(bar.end)}%` }}
													transition={transition}
												/>
											)}
											<motion.div
												className={cn(
													"absolute inset-y-0 min-w-0.5 overflow-hidden rounded-sm",
													BAR_TONE[t],
												)}
												initial={{ left: `${origin}%`, width: "0%" }}
												animate={{ left: `${left}%`, width: `${width}%` }}
												transition={transition}
											>
												{t === "total" && truncated && (
													<span className="absolute inset-y-0 left-2 w-0.75 -skew-x-20 bg-surface-1" />
												)}
											</motion.div>
											{net !== null && net !== 0 && base !== null && (
												// Diferença do total final contra o inicial. Com o tooltip aberto (estado do
												// Base UI no gatilho), o trecho cresce e ganha halo.
												<motion.div
													className={cn(
														"absolute inset-y-0 rounded-r-sm transition-[top,bottom,background-color,box-shadow] duration-150 has-data-popup-open:-inset-y-1",
														net > 0
															? "bg-success has-data-popup-open:ring-3 has-data-popup-open:ring-success/30"
															: "border border-dashed border-danger has-data-popup-open:bg-danger-subtle",
													)}
													initial={{ left: `${x(base)}%`, width: "0%" }}
													animate={{
														left: `${x(Math.min(base, bar.end))}%`,
														width: `${Math.abs(x(bar.end) - x(base))}%`,
													}}
													transition={transition}
												>
													<Tooltip>
														<TooltipTrigger
															delay={0}
															render={
																<span className="absolute inset-x-0 -inset-y-2 cursor-default" />
															}
														/>
														<TooltipContent className="flex-col items-start gap-0.5 tabular-nums">
															<span className="text-text-muted">
																Diferença {compareLabel}
															</span>
															<span
																className={cn(
																	"font-medium",
																	VALUE_TONE[netTone],
																)}
															>
																{net > 0 ? "+" : ""}
																{formatValue(net)} · {net > 0 ? "+" : ""}
																{formatPct(net / base)}
															</span>
															<span className="text-text-muted">
																{formatValue(base)} → {formatValue(bar.end)}
															</span>
														</TooltipContent>
													</Tooltip>
												</motion.div>
											)}
										</div>
										<div className="hidden flex-col items-end whitespace-nowrap tabular-nums @max-md:flex">
											{value}
										</div>
									</div>
								</td>
								{/* Coluna própria: a largura é a do maior valor, e todas as trilhas ficam iguais. */}
								<td className="w-px whitespace-nowrap py-0 pl-4 tabular-nums @max-md:sr-only">
									<div className="flex flex-col items-end">{value}</div>
								</td>
								<td
									className={cn(
										"hidden w-px whitespace-nowrap py-0 pr-1 pl-4 text-right text-small tabular-nums @lg:table-cell",
										net === null ? "text-text-muted" : VALUE_TONE[netTone],
									)}
								>
									{pct === null ? (
										<>
											<span aria-hidden>—</span>
											<span className="sr-only">não se aplica</span>
										</>
									) : (
										`${pct > 0 ? "+" : ""}${formatPct(pct)}`
									)}
								</td>
							</tr>
						);
					})}
				</tbody>
			</table>
			{(hasUp || hasDown || truncated || selectHint) && (
				<div className="mt-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-small text-text-muted">
					<div className="flex items-center gap-3">
						{hasUp && (
							<span className="flex items-center gap-1.5">
								<span aria-hidden className="size-2 rounded-sm bg-success" />
								Alta
							</span>
						)}
						{hasDown && (
							<span className="flex items-center gap-1.5">
								<span aria-hidden className="size-2 rounded-sm bg-danger" />
								Queda
							</span>
						)}
						{onSelect && selectHint && <span>{selectHint}</span>}
					</div>
					{truncated && (
						<span>
							Escala ampliada: as barras de total não começam no zero.
						</span>
					)}
				</div>
			)}
		</div>
	);
}
