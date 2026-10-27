// Gráfico de tendência: uma ou mais séries em linha sobre categorias em ordem (meses, anos).
// SVG próprio; escalas e curva do d3 (`d3-scale`, `d3-shape`), movimento do `motion`.
// - a série em destaque (`emphasis`; sozinha, ela é o destaque) fica por cima, mais grossa,
//   com área em degradê e um ponto no último valor; as outras ficam finas, atrás;
// - eixo y com ticks redondos (`nice`), opcionalmente a partir do zero; o eixo x mostra só os
//   rótulos que cabem, contados a partir do último (o mais recente sempre aparece);
// - dados novos: a série que continua (mesmo `id`, mesmos pontos) muda de forma com mola, a
//   que chega se desenha e a que sai some. Redimensionar e movimento reduzido trocam seco;
// - ponteiro, toque ou setas percorrem as categorias: régua com mola, pontos e tooltip com
//   todas as séries. Para o teclado e o leitor de tela, a área é um `slider` cujo texto é o
//   mesmo do tooltip; os dados completos vão numa tabela `sr-only`;
// - `markers` marcam categorias (ex.: os meses comparados) com uma régua tracejada;
// - cores só pelos tokens `chart-*` (Fundamentos/Cores › Gráficos e dados).
import {
	ArrowsClockwiseIcon,
	TrayIcon,
	WarningCircleIcon,
} from "@phosphor-icons/react";
import { scaleLinear, scalePoint } from "d3-scale";
import { area, curveMonotoneX, line } from "d3-shape";
import {
	AnimatePresence,
	type MotionValue,
	motion,
	useReducedMotion,
	useSpring,
} from "motion/react";
import {
	type KeyboardEvent,
	type PointerEvent,
	type ReactNode,
	useEffect,
	useId,
	useRef,
	useState,
} from "react";
import { Button } from "#/components/ui/button";
import { useSkeletonSwap } from "#/components/ui/skeleton-swap";
import { formatNumero } from "#/lib/format";
import { cn } from "#/lib/utils";

const SPRING = {
	type: "spring",
	stiffness: 260,
	damping: 32,
	mass: 0.8,
} as const;
const DRAW = { duration: 0.9, ease: [0.22, 1, 0.36, 1] } as const;
const FADE = { duration: 0.18 } as const;
const INSTANT = { duration: 0 } as const;
const CURSOR = { stiffness: 520, damping: 44, mass: 0.6 } as const;
// Depois do último evento de redimensionamento, quanto esperar para voltar a animar.
const RESIZE_SETTLE_MS = 160;
const MARGIN = { top: 12, right: 12, bottom: 28 } as const;
// Largura média de um caractere em `text-small` com números tabulares, para reservar o eixo.
const CHAR_PX = 7;
const NOT_APPLICABLE = "—";

const COLORS = {
	1: {
		stroke: "stroke-chart-1",
		fill: "fill-chart-1",
		halo: "fill-chart-1/20",
		swatch: "bg-chart-1",
		stop: "var(--color-chart-1)",
	},
	2: {
		stroke: "stroke-chart-2",
		fill: "fill-chart-2",
		halo: "fill-chart-2/20",
		swatch: "bg-chart-2",
		stop: "var(--color-chart-2)",
	},
	3: {
		stroke: "stroke-chart-3",
		fill: "fill-chart-3",
		halo: "fill-chart-3/20",
		swatch: "bg-chart-3",
		stop: "var(--color-chart-3)",
	},
	4: {
		stroke: "stroke-chart-4",
		fill: "fill-chart-4",
		halo: "fill-chart-4/20",
		swatch: "bg-chart-4",
		stop: "var(--color-chart-4)",
	},
	5: {
		stroke: "stroke-chart-5",
		fill: "fill-chart-5",
		halo: "fill-chart-5/20",
		swatch: "bg-chart-5",
		stop: "var(--color-chart-5)",
	},
	6: {
		stroke: "stroke-chart-6",
		fill: "fill-chart-6",
		halo: "fill-chart-6/20",
		swatch: "bg-chart-6",
		stop: "var(--color-chart-6)",
	},
	muted: {
		stroke: "stroke-chart-muted",
		fill: "fill-chart-muted",
		halo: "fill-chart-muted/20",
		swatch: "bg-chart-muted",
		stop: "var(--color-chart-muted)",
	},
} as const;

const PALETTE = [1, 2, 3, 4, 5, 6] as const;

/** Posição na ordem categórica (`chart-1` a `chart-6`) ou a série de contexto (`muted`). */
export type TrendColor = keyof typeof COLORS;

export type TrendCategory = {
	/** Identidade estável (ex.: a competência "2025-03"). */
	key: string;
	/** Rótulo curto do eixo: "mar 25". */
	label: string;
	/** Rótulo completo do tooltip e da tabela: "mar/2025". Padrão: `label`. */
	title?: string;
};

export type TrendSeries = {
	/** Identidade estável: a mesma série com dados novos muda de forma em vez de redesenhar. */
	id: string;
	label: string;
	/** Um valor por categoria, na mesma ordem; `null` interrompe a linha. */
	values: (number | null)[];
	/** Padrão: a ordem categórica, pela posição da série. */
	color?: TrendColor;
	/** Por cima, mais grossa, com área e ponto final. Padrão: só quando é a única série. */
	emphasis?: boolean;
};

export type TrendMarker = {
	/** `key` da categoria marcada. */
	at: string;
	/** O que a marca significa, no tooltip: "Mês atual". */
	label: string;
};

export type TrendChartProps = {
	/** Nome acessível do gráfico e legenda da tabela lida pelo leitor de tela. */
	label: string;
	/** `undefined` enquanto nunca carregou. */
	categories?: TrendCategory[];
	series?: TrendSeries[];
	/** Formatador de `#/lib/format` para o tooltip e a tabela. */
	formatValue?: (value: number) => string;
	/** Formatador dos ticks do eixo y. Padrão: `formatValue`. */
	formatTick?: (value: number) => string;
	/** Cabeçalho da coluna de categorias na tabela do leitor de tela. */
	categoryLabel?: string;
	markers?: TrendMarker[];
	/** Eixo y a partir do zero. Padrão: só a faixa dos dados, que é o que mostra tendência. */
	zeroBaseline?: boolean;
	/**
	 * Altura da área do gráfico, em px, ou `"fill"` para ocupar a altura que sobra no card
	 * (com `className="flex-1"` no gráfico e um pai em coluna); a largura acompanha o container.
	 */
	height?: number | "fill";
	/** Rodapé do tooltip para a categoria sob o cursor (ex.: a variação sobre a anterior). */
	tooltipFooter?: (index: number) => ReactNode;
	/** Leitura rápida, à esquerda do cabeçalho. */
	summary?: ReactNode;
	/** Controles do gráfico (indicador, visão), à direita do cabeçalho. */
	toolbar?: ReactNode;
	loading?: boolean;
	error?: string | null;
	onRetry?: () => void;
	emptyMessage?: string;
	className?: string;
};

function useSize() {
	const [node, setNode] = useState<HTMLDivElement | null>(null);
	const [size, setSize] = useState({ width: 0, height: 0 });
	const [resizing, setResizing] = useState(false);
	useEffect(() => {
		if (!node) return;
		let timer: ReturnType<typeof setTimeout> | undefined;
		let measured = false;
		const observer = new ResizeObserver(([entry]) => {
			if (!entry) return;
			setSize({
				width: Math.round(entry.contentRect.width),
				height: Math.round(entry.contentRect.height),
			});
			if (!measured) {
				measured = true;
				return;
			}
			setResizing(true);
			clearTimeout(timer);
			timer = setTimeout(() => setResizing(false), RESIZE_SETTLE_MS);
		});
		observer.observe(node);
		return () => {
			observer.disconnect();
			clearTimeout(timer);
		};
	}, [node]);
	return { ref: setNode, size, resizing };
}

type Layout = {
	left: number;
	plotWidth: number;
	plotHeight: number;
	step: number;
	px: (index: number) => number;
	py: (value: number) => number;
	ticks: number[];
	labelEvery: number;
};

function layout(
	categories: TrendCategory[],
	series: TrendSeries[],
	width: number,
	height: number,
	zeroBaseline: boolean,
	formatTick: (value: number) => string,
): Layout {
	const values = series.flatMap((s) =>
		s.values.filter((v): v is number => v !== null),
	);
	let lo = Math.min(...values);
	let hi = Math.max(...values);
	if (zeroBaseline) {
		lo = Math.min(lo, 0);
		hi = Math.max(hi, 0);
	}
	if (lo === hi) {
		const pad = Math.abs(lo) * 0.1 || 1;
		lo -= pad;
		hi += pad;
	}
	const plotHeight = Math.max(0, height - MARGIN.top - MARGIN.bottom);
	const y = scaleLinear().domain([lo, hi]).range([plotHeight, 0]).nice(4);
	const ticks = y.ticks(4);
	const widest = Math.max(...ticks.map((t) => formatTick(t).length));
	const left = widest * CHAR_PX + 12;
	const plotWidth = Math.max(0, width - left - MARGIN.right);
	const x = scalePoint<number>()
		.domain(categories.map((_, i) => i))
		.range([0, plotWidth]);
	const step = categories.length > 1 ? plotWidth / (categories.length - 1) : 0;
	const widestLabel = Math.max(...categories.map((c) => c.label.length));
	const labelEvery =
		step > 0 ? Math.max(1, Math.ceil((widestLabel * CHAR_PX + 16) / step)) : 1;
	return {
		left,
		plotWidth,
		plotHeight,
		step,
		px: (index) => x(index) ?? 0,
		py: (value) => y(value),
		ticks,
		labelEvery,
	};
}

const isEmphasized = (s: TrendSeries, all: TrendSeries[]) =>
	s.emphasis ?? all.length === 1;

const colorOf = (s: TrendSeries, index: number): TrendColor =>
	s.color ?? PALETTE[index % PALETTE.length] ?? 1;

const lastDefined = (values: (number | null)[]) => {
	for (let i = values.length - 1; i >= 0; i--) {
		if (values[i] !== null && values[i] !== undefined) return i;
	}
	return -1;
};

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
		<div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
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

// Molde: quatro linhas de grade e uma curva genérica, na altura final do gráfico.
function Skeleton({ visible }: { visible: boolean }) {
	return (
		<div aria-hidden className="flex h-full gap-3 pb-7">
			<div className="flex flex-col justify-between py-1">
				{[0, 1, 2, 3].map((i) => (
					<span
						key={i}
						className={cn("h-2 w-10 rounded-sm", visible && "bg-pressed")}
					/>
				))}
			</div>
			<svg
				viewBox="0 0 100 40"
				preserveAspectRatio="none"
				className="h-full flex-1"
				aria-hidden="true"
			>
				<path
					d="M0 30 C 12 27, 22 19, 36 22 S 60 13, 74 16 S 92 8, 100 9"
					vectorEffect="non-scaling-stroke"
					strokeWidth={2}
					strokeLinecap="round"
					className={cn(
						"fill-none",
						visible ? "stroke-pressed" : "stroke-transparent",
					)}
				/>
			</svg>
		</div>
	);
}

export function TrendChart({
	label,
	categories,
	series,
	formatValue = formatNumero,
	formatTick,
	categoryLabel = "Período",
	markers = [],
	zeroBaseline = false,
	height = 240,
	tooltipFooter,
	summary,
	toolbar,
	loading = false,
	error = null,
	onRetry,
	emptyMessage = "Sem dados para o gráfico.",
	className,
}: TrendChartProps) {
	const reduced = useReducedMotion() ?? false;
	const gradientId = useId();
	const { ref, size, resizing } = useSize();
	const plotHeight = height === "fill" ? size.height : height;
	const [active, setActive] = useState<number | null>(null);
	const cursorX = useSpring(0, CURSOR);
	const cursorShown = useRef(false);

	const pending = !error && loading && series === undefined;
	const { showSkeleton } = useSkeletonSwap({ ready: !pending });
	const count = categories?.length ?? 0;
	const hasData =
		count > 0 && (series ?? []).some((s) => s.values.some((v) => v !== null));
	const tick = formatTick ?? formatValue;
	const geo =
		hasData && categories && series && size.width > 0 && plotHeight > 0
			? layout(categories, series, size.width, plotHeight, zeroBaseline, tick)
			: null;
	const current = active !== null && active < count ? active : null;
	const cursorPx = geo && current !== null ? geo.px(current) : null;

	useEffect(() => {
		if (cursorPx === null) {
			cursorShown.current = false;
			return;
		}
		if (!cursorShown.current || reduced) cursorX.jump(cursorPx);
		else cursorX.set(cursorPx);
		cursorShown.current = true;
	}, [cursorPx, reduced, cursorX]);

	const motionFor = reduced || resizing ? INSTANT : SPRING;

	const valueText = (value: number | null | undefined) =>
		value === null || value === undefined ? NOT_APPLICABLE : formatValue(value);

	const describe = (index: number) => {
		const category = categories?.[index];
		if (!category || !series) return "";
		const values = series
			.map((s) => `${s.label}: ${valueText(s.values[index])}`)
			.join("; ");
		return `${category.title ?? category.label}. ${values}`;
	};

	const onPointer = (event: PointerEvent<HTMLDivElement>) => {
		if (!geo || count === 0) return;
		const box = event.currentTarget.getBoundingClientRect();
		const offset = event.clientX - box.left - geo.left;
		const index =
			geo.step > 0 ? Math.round(offset / geo.step) : Math.floor(count / 2);
		setActive(Math.min(count - 1, Math.max(0, index)));
	};

	const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
		if (count === 0) return;
		const from = current ?? count - 1;
		const next =
			event.key === "ArrowRight" || event.key === "ArrowUp"
				? Math.min(count - 1, from + 1)
				: event.key === "ArrowLeft" || event.key === "ArrowDown"
					? Math.max(0, from - 1)
					: event.key === "Home"
						? 0
						: event.key === "End"
							? count - 1
							: null;
		if (next === null) return;
		event.preventDefault();
		setActive(next);
	};

	const header =
		summary || toolbar ? (
			<div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
				<div className="min-w-0 text-body text-text-muted">{summary}</div>
				{toolbar ? (
					<div className="flex flex-wrap items-center gap-2">{toolbar}</div>
				) : null}
			</div>
		) : null;

	let body: ReactNode;
	if (error) {
		body = (
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
		);
	} else if (pending) {
		body = (
			<>
				<span className="sr-only">Carregando {label.toLowerCase()}</span>
				<Skeleton visible={showSkeleton} />
			</>
		);
	} else if (!hasData || !categories || !series) {
		body = <StateBlock tone="empty">{emptyMessage}</StateBlock>;
	} else {
		body = (
			<Plot
				geo={geo}
				categories={categories}
				series={series}
				markers={markers}
				current={current}
				height={plotHeight}
				gradientId={gradientId}
				motionFor={motionFor}
				reduced={reduced}
				cursorX={cursorX}
				label={label}
				valueText={valueText}
				describe={describe}
				tooltipFooter={tooltipFooter}
				onPointer={onPointer}
				onLeave={() => setActive(null)}
				onKeyDown={onKeyDown}
				onFocus={() => setActive((prev) => prev ?? count - 1)}
				onBlur={() => setActive(null)}
				formatTick={tick}
			/>
		);
	}

	const legend =
		!error && !pending && hasData && series && series.length > 1 ? (
			<ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-small text-text-muted">
				{series.map((s, i) => (
					<li key={s.id} className="flex items-center gap-1.5">
						<span
							aria-hidden
							className={cn(
								"h-0.5 w-3 rounded-full",
								COLORS[colorOf(s, i)].swatch,
							)}
						/>
						<span className={cn(isEmphasized(s, series) && "text-text")}>
							{s.label}
						</span>
					</li>
				))}
			</ul>
		) : null;

	return (
		<div
			aria-busy={loading || undefined}
			className={cn(
				"flex flex-col gap-4 rounded-md border border-border bg-surface-1 p-5 shadow-edge",
				className,
			)}
		>
			{header}
			{legend}
			<div
				ref={ref}
				className={cn("relative", height === "fill" && "min-h-60 flex-1")}
				style={height === "fill" ? undefined : { height }}
			>
				{body}
			</div>
			{hasData && categories && series ? (
				// Embrulhada: a `caption` escapa do `sr-only` aplicado direto na tabela.
				<div className="sr-only">
					<table>
						<caption>{label}</caption>
						<thead>
							<tr>
								<th scope="col">{categoryLabel}</th>
								{series.map((s) => (
									<th key={s.id} scope="col">
										{s.label}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{categories.map((c, i) => (
								<tr key={c.key}>
									<th scope="row">{c.title ?? c.label}</th>
									{series.map((s) => (
										<td key={s.id}>{valueText(s.values[i])}</td>
									))}
								</tr>
							))}
						</tbody>
					</table>
				</div>
			) : null}
		</div>
	);
}

type PlotProps = {
	geo: Layout | null;
	categories: TrendCategory[];
	series: TrendSeries[];
	markers: TrendMarker[];
	current: number | null;
	height: number;
	gradientId: string;
	motionFor: typeof SPRING | typeof INSTANT;
	reduced: boolean;
	cursorX: MotionValue<number>;
	label: string;
	valueText: (value: number | null | undefined) => string;
	describe: (index: number) => string;
	tooltipFooter?: (index: number) => ReactNode;
	onPointer: (event: PointerEvent<HTMLDivElement>) => void;
	onLeave: () => void;
	onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => void;
	onFocus: () => void;
	onBlur: () => void;
	formatTick: (value: number) => string;
};

function Plot({
	geo,
	categories,
	series,
	markers,
	current,
	height,
	gradientId,
	motionFor,
	reduced,
	cursorX,
	label,
	valueText,
	describe,
	tooltipFooter,
	onPointer,
	onLeave,
	onKeyDown,
	onFocus,
	onBlur,
	formatTick,
}: PlotProps) {
	const count = categories.length;

	if (!geo) return <div className="h-full" />;

	const { left, plotWidth, plotHeight, px, py, ticks, labelEvery } = geo;
	const toLine = line<number | null>()
		.defined((v) => v !== null)
		.x((_, i) => px(i))
		.y((v) => py(v ?? 0))
		.curve(curveMonotoneX)
		.digits(1);
	const toArea = area<number | null>()
		.defined((v) => v !== null)
		.x((_, i) => px(i))
		.y0(plotHeight)
		.y1((v) => py(v ?? 0))
		.curve(curveMonotoneX)
		.digits(1);

	const drawn = series
		.map((s, i) => ({
			s,
			color: colorOf(s, i),
			emphasis: isEmphasized(s, series),
			values: s.values.slice(0, count),
		}))
		.sort((a, b) => Number(a.emphasis) - Number(b.emphasis));
	const rows = [...drawn].reverse();
	const markerAt = new Map(markers.map((m) => [m.at, m.label]));
	const activeCategory = current === null ? undefined : categories[current];
	const flip = current !== null && px(current) > plotWidth / 2;
	const enter = reduced ? INSTANT : DRAW;

	return (
		<div
			role="slider"
			tabIndex={0}
			aria-label={label}
			aria-orientation="horizontal"
			aria-valuemin={0}
			aria-valuemax={count - 1}
			aria-valuenow={current ?? count - 1}
			aria-valuetext={describe(current ?? count - 1)}
			onPointerMove={onPointer}
			onPointerDown={onPointer}
			onPointerLeave={onLeave}
			onKeyDown={onKeyDown}
			onFocus={onFocus}
			onBlur={onBlur}
			className="relative h-full cursor-crosshair touch-pan-y rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-focus-ring/50"
		>
			<svg
				aria-hidden="true"
				width="100%"
				height={height}
				className="block overflow-visible"
			>
				<defs>
					{drawn
						.filter((d) => d.emphasis)
						.map((d) => (
							<linearGradient
								key={d.s.id}
								id={`${gradientId}-${d.s.id}`}
								x1="0"
								x2="0"
								y1="0"
								y2="1"
							>
								<stop
									offset="0%"
									stopOpacity={0.16}
									style={{ stopColor: COLORS[d.color].stop }}
								/>
								<stop
									offset="100%"
									stopOpacity={0}
									style={{ stopColor: COLORS[d.color].stop }}
								/>
							</linearGradient>
						))}
				</defs>
				<g transform={`translate(${left} ${MARGIN.top})`}>
					<AnimatePresence initial={false}>
						{ticks.map((t) => (
							<motion.g
								key={t}
								initial={{ opacity: 0, y: py(t) }}
								animate={{ opacity: 1, y: py(t) }}
								exit={{ opacity: 0, transition: FADE }}
								transition={motionFor}
							>
								<line x1={0} x2={plotWidth} className="stroke-border" />
								<text
									x={-12}
									dy="0.32em"
									textAnchor="end"
									className="fill-text-muted text-small tabular-nums"
								>
									{formatTick(t)}
								</text>
							</motion.g>
						))}
					</AnimatePresence>

					<AnimatePresence initial={false}>
						{categories.map((c, i) =>
							(count - 1 - i) % labelEvery === 0 ? (
								<motion.text
									key={c.key}
									x={px(i)}
									y={plotHeight + 20}
									textAnchor="middle"
									initial={{ opacity: 0 }}
									animate={{ opacity: 1 }}
									exit={{ opacity: 0 }}
									transition={FADE}
									className={cn(
										"text-small tabular-nums",
										i === current ? "fill-text" : "fill-text-muted",
									)}
								>
									{c.label}
								</motion.text>
							) : null,
						)}
					</AnimatePresence>

					<AnimatePresence initial={false}>
						{categories.map((c, i) =>
							markerAt.has(c.key) ? (
								<motion.line
									key={`marker-${c.key}`}
									x1={px(i)}
									x2={px(i)}
									y1={0}
									y2={plotHeight}
									strokeDasharray="2 4"
									initial={{ opacity: 0 }}
									animate={{ opacity: 1 }}
									exit={{ opacity: 0 }}
									transition={FADE}
									className="stroke-border-strong"
								/>
							) : null,
						)}
					</AnimatePresence>

					<AnimatePresence>
						{drawn
							.filter((d) => d.emphasis)
							.map((d) => {
								const path = toArea(d.values) ?? "";
								return (
									<motion.path
										key={`area-${d.s.id}`}
										fill={`url(#${gradientId}-${d.s.id})`}
										initial={reduced ? false : { d: path, opacity: 0 }}
										animate={{ d: path, opacity: 1 }}
										exit={{ opacity: 0, transition: FADE }}
										transition={{ ...motionFor, opacity: enter }}
									/>
								);
							})}
					</AnimatePresence>

					<AnimatePresence>
						{drawn.map((d) => {
							const path = toLine(d.values) ?? "";
							return (
								<motion.path
									key={d.s.id}
									fill="none"
									strokeWidth={d.emphasis ? 2 : 1.5}
									strokeLinecap="round"
									strokeLinejoin="round"
									className={COLORS[d.color].stroke}
									initial={
										reduced ? false : { d: path, pathLength: 0, opacity: 0 }
									}
									animate={{ d: path, pathLength: 1, opacity: 1 }}
									exit={{ opacity: 0, transition: FADE }}
									transition={{
										...motionFor,
										pathLength: enter,
										opacity: FADE,
									}}
								/>
							);
						})}
					</AnimatePresence>

					<AnimatePresence>
						{drawn
							.filter((d) => d.emphasis && current === null)
							.map((d) => {
								const last = lastDefined(d.values);
								const value = d.values[last];
								if (last < 0 || value === null || value === undefined)
									return null;
								return (
									<motion.g
										key={`end-${d.s.id}`}
										initial={
											reduced
												? false
												: { opacity: 0, x: px(last), y: py(value) }
										}
										animate={{ opacity: 1, x: px(last), y: py(value) }}
										exit={{ opacity: 0, transition: FADE }}
										transition={{
											...motionFor,
											opacity: reduced ? INSTANT : { ...FADE, delay: 0.5 },
										}}
									>
										<circle r={7} className={COLORS[d.color].halo} />
										<circle r={3.5} className={COLORS[d.color].fill} />
									</motion.g>
								);
							})}
					</AnimatePresence>

					<motion.g
						style={{ x: cursorX }}
						initial={false}
						animate={{ opacity: current === null ? 0 : 1 }}
						transition={FADE}
					>
						<line y1={0} y2={plotHeight} className="stroke-border-strong" />
						{current !== null
							? drawn.map((d) => {
									const value = d.values[current];
									if (value === null || value === undefined) return null;
									return (
										<motion.circle
											key={d.s.id}
											cx={0}
											r={d.emphasis ? 4 : 3}
											strokeWidth={2}
											initial={false}
											animate={{ cy: py(value) }}
											transition={motionFor}
											className={cn("fill-surface-1", COLORS[d.color].stroke)}
										/>
									);
								})
							: null}
					</motion.g>
				</g>
			</svg>

			<motion.div
				aria-hidden
				className="pointer-events-none absolute top-0"
				style={{ left, x: cursorX }}
			>
				<AnimatePresence>
					{activeCategory && current !== null ? (
						<motion.div
							key="tooltip"
							initial={{ opacity: 0, scale: reduced ? 1 : 0.96 }}
							animate={{ opacity: 1, scale: 1 }}
							exit={{ opacity: 0, transition: FADE }}
							transition={FADE}
							className={cn(
								"flex w-max min-w-40 max-w-64 flex-col gap-1.5 rounded-md border border-border-strong bg-surface-2 px-2.5 py-2 text-small text-text shadow-overlay",
								flip
									? "-translate-x-full -ml-3 origin-top-right"
									: "ml-3 origin-top-left",
							)}
						>
							<p className="flex items-baseline justify-between gap-3">
								<span className="font-medium">
									{activeCategory.title ?? activeCategory.label}
								</span>
								{markerAt.has(activeCategory.key) ? (
									<span className="text-text-muted">
										{markerAt.get(activeCategory.key)}
									</span>
								) : null}
							</p>
							<dl className="grid grid-cols-[auto_1fr_auto] items-center gap-x-2 gap-y-1">
								{rows.map((d) => (
									<div key={d.s.id} className="contents">
										<span
											className={cn(
												"h-0.5 w-2.5 rounded-full",
												COLORS[d.color].swatch,
											)}
										/>
										<dt
											className={cn(
												"truncate",
												d.emphasis ? "text-text" : "text-text-muted",
											)}
										>
											{d.s.label}
										</dt>
										<dd
											className={cn(
												"text-right tabular-nums",
												d.emphasis ? "font-medium" : "text-text-muted",
											)}
										>
											{valueText(d.values[current])}
										</dd>
									</div>
								))}
							</dl>
							{tooltipFooter ? (
								<div className="border-t border-border pt-1.5">
									{tooltipFooter(current)}
								</div>
							) : null}
						</motion.div>
					) : null}
				</AnimatePresence>
			</motion.div>
		</div>
	);
}
