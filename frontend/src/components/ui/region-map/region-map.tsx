// Mapa de regiões em SVG para escolher um recorte geográfico (ex.: município e bairro da RMR).
// - Cada região habilitada é um link (`getHref`): Tab percorre o mapa, Enter abre, e o
//   botão do meio/Ctrl+clique abre em outra aba. Regiões sem dado ficam visíveis, sem link.
// - Ao escolher, o mapa enquadra a região com mola (viewBox animado); os botões aproximam,
//   afastam e enquadram de novo. Arrastar move o mapa; Ctrl+roda (ou pinça no trackpad) dá
//   zoom no ponto do cursor. A roda sozinha continua rolando a página.
// - Cor contínua (`getIntensity`, de -1 a 1): queda em `danger`, alta em `success`, misturadas
//   à superfície pela intensidade; quanto mais forte, mais o contorno brilha (glow). Hover e
//   seleção são contornos por cima de tudo, então valem sobre qualquer cor.
// - Desenho em duas passadas: todos os preenchimentos e depois todos os contornos. Assim a
//   borda que dois vizinhos dividem nunca fica meio coberta pelo preenchimento do segundo.
// - Contorno com largura fixa na tela: `--u` (unidades do viewBox por pixel) acompanha o
//   viewBox animado, em vez de `vector-effect: non-scaling-stroke`, que o Chrome às vezes
//   deixa de repintar quando o viewBox muda (linhas somem em pedaços).
// - O mapa é um atalho visual: a tela precisa oferecer a mesma escolha numa lista (menu do
//   topo, tabela), para quem não usa ponteiro nem vê o mapa.
import {
	CornersOutIcon,
	MinusIcon,
	PlusIcon,
	XIcon,
} from "@phosphor-icons/react";
import {
	animate,
	type MotionStyle,
	motion,
	useMotionValue,
	useReducedMotion,
	useTransform,
} from "motion/react";
import {
	type MouseEvent,
	type PointerEvent,
	useEffect,
	useId,
	useRef,
	useState,
} from "react";
import { Button } from "#/components/ui/button";
import { cn } from "#/lib/utils";

const VIEW = {
	type: "spring",
	stiffness: 170,
	damping: 26,
	mass: 0.9,
} as const;
const ZOOM_STEP = 1.6;
const DRAG_THRESHOLD = 4;
/** Fração da largura total: menor que isso, o enquadramento de uma região pequena cresce. */
const MIN_FIT = 0.05;
const MAX_ZOOM = 40;

export type RegionMapShape = {
	id: string;
	nome: string;
	/** Caminho SVG no sistema do `viewBox`. */
	d: string;
	/** Caixa da região: x, y, largura, altura. */
	caixa: [number, number, number, number];
	/** Ponto interno para o rótulo. */
	rotulo: [number, number];
};

// Cor da intensidade: tokens da marca misturados à superfície (color-mix), sem paleta própria.
const mix = (cor: string, pct: number, sobre: string) =>
	`color-mix(in oklab, ${cor} ${pct.toFixed(1)}%, ${sobre})`;

/** Cor e brilho da intensidade; `apagado` (fora do foco) guarda só um resto da cor, sem brilho. */
function corDaIntensidade(intensidade: number, apagado = false) {
	const t = Math.min(1, Math.abs(intensidade));
	const cor = intensidade < 0 ? "var(--color-danger)" : "var(--color-success)";
	if (apagado)
		return {
			t: 0,
			fill:
				t === 0
					? "var(--color-surface-2)"
					: mix(cor, 6 + 12 * t, "var(--color-surface-2)"),
			stroke: "var(--color-border-strong)",
			glow: undefined,
		};
	return {
		t,
		fill:
			t === 0
				? "var(--color-surface-2)"
				: mix(cor, 18 + 57 * t, "var(--color-surface-2)"),
		stroke:
			t === 0
				? "var(--color-text-muted)"
				: mix(cor, 45 + 50 * t, "var(--color-border-strong)"),
		// Brilho só a partir de um quarto da escala, crescendo em raio e opacidade.
		glow:
			t < 0.25
				? undefined
				: `drop-shadow(0 0 calc(var(--u) * ${(2 + 10 * t).toFixed(1)}px) ${mix(cor, 35 + 50 * t, "transparent")})`,
	};
}

const LEGEND_GRADIENT = `linear-gradient(to right, ${mix("var(--color-danger)", 75, "var(--color-surface-2)")}, var(--color-surface-2), ${mix("var(--color-success)", 75, "var(--color-surface-2)")})`;

type View = { x: number; y: number; w: number; h: number };

export type RegionMapProps = {
	/** Nome acessível do mapa. */
	label: string;
	viewBox: { width: number; height: number };
	shapes: RegionMapShape[];
	/** Caminhos só de contexto (vizinhos, litoral), sem interação. */
	context?: string[];
	selectedId?: string | null;
	/** Regiões clicáveis; as outras aparecem apagadas. Padrão: todas. */
	enabledIds?: ReadonlySet<string>;
	/**
	 * Intensidade de cada região habilitada, de -1 (queda máxima) a 1 (alta máxima); 0 é
	 * neutro. Sem ela, todas ficam neutras.
	 */
	getIntensity?: (shape: RegionMapShape) => number;
	/**
	 * Regiões que servem de fundo para sub-regiões desenhadas por cima (ex.: o município
	 * com os bairros dele): ficam em cinza neutro, para que frestas entre as malhas não
	 * apareçam na cor da faixa ou da seleção.
	 */
	containerIds?: ReadonlySet<string>;
	/**
	 * Regiões em foco (ex.: o bairro escolhido, ou os bairros do município escolhido). Com
	 * ele, as demais ficam apagadas: cor bem fraca e sem brilho, como fundo de contexto.
	 */
	focusIds?: ReadonlySet<string>;
	/** Região destacada de fora do mapa (ex.: linha da tabela sob o ponteiro): ganha contorno. */
	highlightId?: string | null;
	/** Legenda da escala: barra de queda a alta, com `ticks` espaçados embaixo. */
	legend?: {
		title: string;
		ticks: [string, string, string];
		/** Texto da escala para leitor de tela (a barra é só visual). */
		description: string;
	};
	getHref: (shape: RegionMapShape) => string;
	onSelect: (shape: RegionMapShape) => void;
	/** Some com o recorte (volta ao nível de cima). Sem ele, não há botão de limpar. */
	onClear?: () => void;
	clearLabel?: string;
	/** Linha extra da dica e do nome acessível (ex.: "Variação: R$ 1.473,12"). */
	describe?: (shape: RegionMapShape) => string | null;
	className?: string;
};

function fit([x, y, w, h]: [number, number, number, number], full: View): View {
	const pad = 0.18;
	const fw = Math.max(w * (1 + pad * 2), full.w * MIN_FIT);
	const fh = Math.max(h * (1 + pad * 2), full.h * MIN_FIT);
	return { x: x + w / 2 - fw / 2, y: y + h / 2 - fh / 2, w: fw, h: fh };
}

function zoomAt(
	view: View,
	factor: number,
	cx: number,
	cy: number,
	full: View,
): View {
	const w = Math.min(
		full.w * 1.2,
		Math.max(full.w / MAX_ZOOM, view.w / factor),
	);
	const h = (w / view.w) * view.h;
	return {
		x: cx - ((cx - view.x) / view.w) * w,
		y: cy - ((cy - view.y) / view.h) * h,
		w,
		h,
	};
}

/** Largura do contorno em pixels da tela, convertida para unidades do viewBox via `--u`. */
const stroke = (px: number) => ({ strokeWidth: `calc(var(--u) * ${px})` });

export function RegionMap({
	label,
	viewBox,
	shapes,
	context = [],
	selectedId = null,
	enabledIds,
	getIntensity,
	containerIds,
	focusIds,
	highlightId = null,
	legend,
	getHref,
	onSelect,
	onClear,
	clearLabel = "Ver a região inteira",
	describe,
	className,
}: RegionMapProps) {
	const reduced = useReducedMotion() ?? false;
	const titleId = useId();
	const svgRef = useRef<SVGSVGElement>(null);
	const containerRef = useRef<HTMLDivElement>(null);
	const full: View = { x: 0, y: 0, w: viewBox.width, h: viewBox.height };
	const selected = shapes.find((s) => s.id === selectedId) ?? null;
	const shapeById = new Map(shapes.map((s) => [s.id, s]));
	const isEnabled = (id: string) => (enabledIds ? enabledIds.has(id) : true);

	const target = selected ? fit(selected.caixa, full) : full;
	const [view, setView] = useState<View>(target);
	const [instant, setInstant] = useState(false);
	const [focused, setFocused] = useState<string | null>(null);
	const [hover, setHover] = useState<{
		shape: RegionMapShape;
		x: number;
		y: number;
	} | null>(null);

	// Nova seleção (clique, menu, URL): enquadra de novo.
	const [previousSelected, setPreviousSelected] = useState(selectedId);
	if (selectedId !== previousSelected) {
		setPreviousSelected(selectedId);
		setView(target);
		setInstant(false);
	}

	// viewBox animado em motion values: o mesmo valor que a tela mostra calcula `--u`.
	const vx = useMotionValue(view.x);
	const vy = useMotionValue(view.y);
	const vw = useMotionValue(view.w);
	const vh = useMotionValue(view.h);
	const boxW = useMotionValue(0);
	const boxH = useMotionValue(0);
	const viewBoxAttr = useTransform([vx, vy, vw, vh], ([x, y, w, h]) =>
		[x, y, w, h].join(" "),
	);
	// `meet`: vale a maior das duas razões.
	const unitsPerPixel = useTransform(
		[vw, vh, boxW, boxH],
		([w, h, bw, bh]: number[]) =>
			bw && bh ? Math.max(w / bw, h / bh) : w / 300,
	);

	useEffect(() => {
		const pares: [typeof vx, number][] = [
			[vx, view.x],
			[vy, view.y],
			[vw, view.w],
			[vh, view.h],
		];
		if (reduced || instant) {
			for (const [mv, v] of pares) mv.set(v);
			return;
		}
		const controles = pares.map(([mv, v]) => animate(mv, v, VIEW));
		return () => {
			for (const c of controles) c.stop();
		};
	}, [view, instant, reduced, vx, vy, vw, vh]);

	useEffect(() => {
		const el = containerRef.current;
		if (!el) return;
		const ro = new ResizeObserver(([entry]) => {
			if (!entry) return;
			boxW.set(entry.contentRect.width);
			boxH.set(entry.contentRect.height);
		});
		ro.observe(el);
		return () => ro.disconnect();
	}, [boxW, boxH]);

	const drag = useRef<{
		id: number;
		x: number;
		y: number;
		view: View;
		moved: boolean;
	} | null>(null);

	const unitsAt = (v: View) => {
		const rect = svgRef.current?.getBoundingClientRect();
		if (!rect || rect.width === 0) return 1;
		return Math.max(v.w / rect.width, v.h / rect.height);
	};

	const toViewPoint = (clientX: number, clientY: number, v: View) => {
		const rect = svgRef.current?.getBoundingClientRect();
		if (!rect) return { x: v.x + v.w / 2, y: v.y + v.h / 2 };
		const k = unitsAt(v);
		return {
			x: v.x + v.w / 2 + (clientX - (rect.left + rect.width / 2)) * k,
			y: v.y + v.h / 2 + (clientY - (rect.top + rect.height / 2)) * k,
		};
	};

	// Ctrl+roda: listener nativo, porque o React registra `wheel` como passivo e o
	// preventDefault (que impede o zoom da página) seria ignorado.
	useEffect(() => {
		const svg = svgRef.current;
		if (!svg) return;
		const onWheel = (event: WheelEvent) => {
			if (!event.ctrlKey && !event.metaKey) return;
			event.preventDefault();
			setInstant(true);
			setView((v) => {
				const p = toViewPoint(event.clientX, event.clientY, v);
				// Pinça do trackpad manda deltas pequenos; a roda do mouse, ~100 por clique:
				// o teto deixa cada clique em ~1,6× sem travar a pinça.
				const delta = Math.max(-50, Math.min(50, event.deltaY));
				return zoomAt(v, Math.exp(-delta * 0.01), p.x, p.y, full);
			});
		};
		svg.addEventListener("wheel", onWheel, { passive: false });
		return () => svg.removeEventListener("wheel", onWheel);
	});

	const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
		if (event.button !== 0 || event.pointerType === "touch") return;
		drag.current = {
			id: event.pointerId,
			x: event.clientX,
			y: event.clientY,
			view,
			moved: false,
		};
	};

	const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
		const d = drag.current;
		if (d && d.id === event.pointerId) {
			const dx = event.clientX - d.x;
			const dy = event.clientY - d.y;
			if (!d.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
			if (!d.moved) {
				d.moved = true;
				event.currentTarget.setPointerCapture(event.pointerId);
				setHover(null);
			}
			const k = unitsAt(d.view);
			setInstant(true);
			setView({ ...d.view, x: d.view.x - dx * k, y: d.view.y - dy * k });
			return;
		}
		if (event.pointerType === "touch") return;
		// A região sob o ponteiro sai do alvo do evento, e não de pointerenter por região:
		// assim a dica acompanha cada região ao passar de uma para a vizinha.
		const id = (event.target as Element)
			.closest("[data-region-id]")
			?.getAttribute("data-region-id");
		const shape = id ? shapeById.get(id) : undefined;
		const rect = containerRef.current?.getBoundingClientRect();
		setHover(
			shape && rect
				? { shape, x: event.clientX - rect.left, y: event.clientY - rect.top }
				: null,
		);
	};

	const endDrag = (event: PointerEvent<SVGSVGElement>) => {
		if (drag.current?.id !== event.pointerId) return;
		// O clique que encerra um arrasto não escolhe região (ver onClickCapture).
		if (!drag.current.moved) drag.current = null;
	};

	const onClickCapture = (event: MouseEvent<SVGSVGElement>) => {
		if (drag.current?.moved) {
			event.preventDefault();
			event.stopPropagation();
		}
		drag.current = null;
	};

	const zoomBy = (factor: number) => {
		setInstant(false);
		setView((v) => zoomAt(v, factor, v.x + v.w / 2, v.y + v.h / 2, full));
	};

	const refit = () => {
		setInstant(false);
		setView(target);
	};

	// Contornos na ordem em que se sobrepõem: sem dado, com dado, selecionado, hover, foco.
	const comDado = shapes.filter((s) => isEnabled(s.id));
	const semDado = shapes.filter((s) => !isEnabled(s.id));
	const overlays = [
		{ id: selectedId, cls: "stroke-accent", px: 2 },
		{ id: highlightId, cls: "stroke-text", px: 2 },
		{ id: hover?.shape.id, cls: "stroke-text", px: 1.5 },
		{ id: focused, cls: "stroke-focus-ring", px: 2.5 },
	];
	const apagado = (id: string) => focusIds !== undefined && !focusIds.has(id);

	return (
		<div
			ref={containerRef}
			className={cn(
				"relative overflow-hidden rounded-lg border border-border bg-surface-1",
				className,
			)}
		>
			<motion.svg
				ref={svgRef}
				aria-labelledby={titleId}
				className="block size-full cursor-grab touch-pan-y select-none active:cursor-grabbing"
				preserveAspectRatio="xMidYMid meet"
				viewBox={viewBoxAttr}
				style={{ "--u": unitsPerPixel } as MotionStyle}
				onPointerDown={onPointerDown}
				onPointerMove={onPointerMove}
				onPointerUp={endDrag}
				onPointerCancel={endDrag}
				onPointerLeave={() => setHover(null)}
				onClickCapture={onClickCapture}
			>
				<title id={titleId}>{label}</title>
				<g aria-hidden className="fill-none stroke-border" style={stroke(1)}>
					{context.map((d, i) => (
						// biome-ignore lint/suspicious/noArrayIndexKey: contorno estático, sem identidade.
						<path key={i} d={d} />
					))}
				</g>

				{/* 1ª passada: preenchimentos, com os links. */}
				{shapes.map((shape) => {
					const enabled = isEnabled(shape.id);
					const neutro =
						containerIds?.has(shape.id) || !enabled || shape.id === selectedId;
					const fill = cn(
						"stroke-none transition-[fill] duration-200",
						containerIds?.has(shape.id) || !enabled
							? "fill-surface-2"
							: shape.id === selectedId && "fill-accent-subtle",
					);
					const fillStyle = neutro
						? undefined
						: {
								fill: corDaIntensidade(
									getIntensity?.(shape) ?? 0,
									apagado(shape.id),
								).fill,
							};
					if (!enabled)
						return (
							<path
								key={shape.id}
								aria-hidden
								data-region-id={shape.id}
								d={shape.d}
								className={fill}
							/>
						);
					const extra = describe?.(shape);
					return (
						<a
							key={shape.id}
							data-region-id={shape.id}
							href={getHref(shape)}
							draggable={false}
							aria-label={[shape.nome, extra].filter(Boolean).join(". ")}
							aria-current={shape.id === selectedId ? "true" : undefined}
							className="cursor-pointer outline-none"
							onClick={(event) => {
								if (
									event.metaKey ||
									event.ctrlKey ||
									event.shiftKey ||
									event.button !== 0
								)
									return;
								event.preventDefault();
								onSelect(shape);
							}}
							onFocus={(event) => {
								if (event.currentTarget.matches(":focus-visible"))
									setFocused(shape.id);
							}}
							onBlur={() => setFocused(null)}
						>
							<path d={shape.d} className={fill} style={fillStyle} />
						</a>
					);
				})}

				{/* 2ª passada: contornos, por cima de todos os preenchimentos. */}
				<g
					aria-hidden
					className="pointer-events-none fill-none stroke-border-strong"
					style={stroke(1)}
				>
					{semDado.map((s) => (
						<path key={s.id} d={s.d} />
					))}
				</g>
				{/* Com dado: contorno na cor da intensidade, os mais fortes por cima e com brilho. */}
				{comDado
					.map((s) => ({
						s,
						cor: corDaIntensidade(
							containerIds?.has(s.id) ? 0 : (getIntensity?.(s) ?? 0),
							apagado(s.id),
						),
					}))
					.sort((a, b) => a.cor.t - b.cor.t)
					.map(({ s, cor }) => (
						<path
							key={s.id}
							aria-hidden
							d={s.d}
							className="pointer-events-none fill-none"
							style={{
								...stroke(1 + 0.5 * cor.t),
								stroke: cor.stroke,
								filter: cor.glow,
							}}
						/>
					))}
				{overlays.map(({ id, cls, px }) => {
					const shape = id ? shapeById.get(id) : undefined;
					return shape ? (
						<path
							key={cls}
							aria-hidden
							d={shape.d}
							className={cn("pointer-events-none fill-none", cls)}
							style={stroke(px)}
						/>
					) : null;
				})}

				{selected && (
					<text
						aria-hidden
						x={selected.rotulo[0]}
						y={selected.rotulo[1]}
						textAnchor="middle"
						dominantBaseline="middle"
						className="pointer-events-none fill-text stroke-surface-1 font-medium [paint-order:stroke]"
						style={{
							fontSize: "calc(var(--u) * 13px)",
							strokeWidth: "calc(var(--u) * 3.5)",
						}}
					>
						{selected.nome}
					</text>
				)}
			</motion.svg>

			{hover && (
				<div
					aria-hidden
					className="pointer-events-none absolute z-10 flex max-w-56 flex-col rounded-md border border-border-strong bg-surface-2 px-2 py-1 text-small text-text shadow-overlay"
					style={{
						left: hover.x,
						top: hover.y,
						transform: "translate(-50%, calc(-100% - 12px))",
					}}
				>
					<span className="truncate font-medium">{hover.shape.nome}</span>
					{describe?.(hover.shape) && (
						<span className="truncate text-text-muted tabular-nums">
							{describe(hover.shape)}
						</span>
					)}
				</div>
			)}

			{selected && onClear && (
				<Button
					variant="secondary"
					size="xs"
					onClick={onClear}
					className="absolute top-2 left-2"
				>
					<XIcon aria-hidden />
					{clearLabel}
				</Button>
			)}

			<div className="absolute top-2 right-2 flex flex-col gap-1 rounded-md border border-border bg-surface-1 p-0.5">
				<Button
					variant="ghost"
					size="icon-xs"
					aria-label="Aproximar"
					onClick={() => zoomBy(ZOOM_STEP)}
				>
					<PlusIcon aria-hidden />
				</Button>
				<Button
					variant="ghost"
					size="icon-xs"
					aria-label="Afastar"
					onClick={() => zoomBy(1 / ZOOM_STEP)}
				>
					<MinusIcon aria-hidden />
				</Button>
				<Button
					variant="ghost"
					size="icon-xs"
					aria-label={
						selected ? `Enquadrar ${selected.nome}` : "Enquadrar o mapa"
					}
					onClick={refit}
				>
					<CornersOutIcon aria-hidden />
				</Button>
			</div>

			{legend && (
				<figure className="absolute bottom-2 left-2 rounded-md border border-border bg-surface-1 px-2 py-1.5">
					<figcaption className="mb-1 text-small text-text-muted">
						{legend.title}
						<span className="sr-only">. {legend.description}</span>
					</figcaption>
					<div
						aria-hidden
						className="h-2.5 w-36 rounded-sm border border-border-strong"
						style={{ backgroundImage: LEGEND_GRADIENT }}
					/>
					<div
						aria-hidden
						className="mt-0.5 flex justify-between text-small text-text-muted tabular-nums"
					>
						{legend.ticks.map((tick) => (
							<span key={tick}>{tick}</span>
						))}
					</div>
				</figure>
			)}
		</div>
	);
}
