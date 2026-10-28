// KpiCard: o número, o que ele mede e para onde foi, nesta ordem de leitura.
// - rótulo em `text-small` muted; valor em `font-display`; variação em `text-small`;
// - a unidade e o sinal ("R$", "mi", "%", "kWh") saem em `font-sans` menor e muted: a Söhne
//   não tem esses glifos, e o número fica sozinho no destaque (Fundamentos/Tipografia);
// - a variação leva seta e sinal; a cor diz se a mudança é boa (`favorable`), nunca sozinha;
// - `link` deixa o card inteiro clicável (o rótulo é o nome do link) e mantém o `hint`
//   e o "Tentar de novo" clicáveis por cima;
// - abaixo de 16rem de largura o valor desce de `text-metric` para `text-title`.
// Partes exportadas para compor fora do card: `KpiValue` e `KpiDelta`.
import { useRender } from "@base-ui/react/use-render";
import {
	ArrowDownIcon,
	ArrowsClockwiseIcon,
	ArrowUpIcon,
	CaretRightIcon,
	InfoIcon,
	WarningCircleIcon,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { ReactElement, ReactNode } from "react";
import { Button } from "#/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "#/components/ui/popover";
import { useSkeletonSwap } from "#/components/ui/skeleton-swap";
import { formatNumero, formatPct } from "#/lib/format";
import { cn } from "#/lib/utils";

const CROSSFADE = {
	type: "spring",
	stiffness: 260,
	damping: 34,
	mass: 0.8,
} as const;

const VALUE_TEXT = "text-title @3xs:text-metric";

// "R$ 45,7 mi" → "R$ " | "45,7" | " mi"; "+3,9%" → "+" | "3,9" | "%".
const PARTS = /^(.*?)(\d(?:[\d.,]*\d)?)(.*)$/s;

type Format = (value: number) => string;

export type KpiValueProps = {
	value: number;
	/** Formatador de `#/lib/format`. Padrão: número com até uma casa. */
	format?: Format;
	/** Número em `accent-text`: o KPI que importa na tela (um por região). */
	highlight?: boolean;
	className?: string;
};

export function KpiValue({
	value,
	format = formatNumero,
	highlight = false,
	className,
}: KpiValueProps) {
	const text = format(value);
	const parts = PARTS.exec(text);
	const affix = "whitespace-pre font-sans text-heading text-text-muted";
	return (
		<p className={cn(VALUE_TEXT, "tabular-nums", className)}>
			{parts ? (
				<>
					{parts[1] ? <span className={affix}>{parts[1]}</span> : null}
					<span className={cn("font-display", highlight && "text-accent-text")}>
						{parts[2]}
					</span>
					{parts[3] ? <span className={affix}>{parts[3]}</span> : null}
				</>
			) : (
				text
			)}
		</p>
	);
}

export type KpiDeltaProps = {
	/** Variação contra a referência; com o formatador padrão, uma fração (-0.052 = -5,2%). */
	value: number;
	/** Precisa marcar o sinal (`{ sinal: true }`): a direção sai do texto já arredondado. */
	format?: Format;
	/** Direção boa: "up" (receita), "down" (DEC, FEC, perdas) ou "none" (só informa). */
	favorable?: "up" | "down" | "none";
	/** Contra o que se compara: "vs. set/2025". */
	comparison?: string;
	className?: string;
};

const signedPct: Format = (value) => formatPct(value, { sinal: true });

function directionOf(text: string) {
	if (text.startsWith("+")) return "up";
	if (text.startsWith("-") || text.startsWith("−")) return "down";
	return "flat";
}

export function KpiDelta({
	value,
	format = signedPct,
	favorable = "up",
	comparison,
	className,
}: KpiDeltaProps) {
	const text = format(value);
	const direction = directionOf(text);
	const good =
		direction === "flat" || favorable === "none"
			? null
			: direction === favorable;
	const Icon =
		direction === "up"
			? ArrowUpIcon
			: direction === "down"
				? ArrowDownIcon
				: null;
	return (
		<p
			className={cn(
				"flex flex-wrap items-center gap-x-1.5 text-small",
				className,
			)}
		>
			<span
				className={cn(
					"inline-flex items-center gap-1 tabular-nums",
					good === true && "text-success",
					good === false && "text-danger",
					good === null && direction === "flat" && "text-text-muted",
				)}
			>
				{Icon ? <Icon aria-hidden weight="bold" className="size-3" /> : null}
				{text}
				{good === null ? null : (
					<span className="sr-only">, {good ? "melhora" : "piora"}</span>
				)}
			</span>
			{comparison ? (
				<span className="text-text-muted">{comparison}</span>
			) : null}
		</p>
	);
}

export type KpiCardProps = {
	/** O que o número mede, curto: "Receita faturada". */
	label: string;
	/** `null`: sem dado (estado vazio). `undefined` com `loading`: carregando. */
	value: number | null | undefined;
	format?: Format;
	delta?: KpiDeltaProps;
	/** Definição da métrica, aberta pelo (i) ao lado do rótulo. */
	hint?: ReactNode;
	/** Destino do card, ex.: `<Link to="/receita" />`. O card inteiro vira o link. */
	link?: ReactElement;
	highlight?: boolean;
	loading?: boolean;
	/** Mensagem curta de erro; com ela, o card mostra o estado de erro. */
	error?: string | null;
	onRetry?: () => void;
	emptyMessage?: string;
	/** Conteúdo extra abaixo do número (minigráfico, nota). */
	children?: ReactNode;
	className?: string;
};

export function KpiCard({
	label,
	value,
	format,
	delta,
	hint,
	link,
	highlight = false,
	loading = false,
	error = null,
	onRetry,
	emptyMessage = "Sem dados no período.",
	children,
	className,
}: KpiCardProps) {
	const reduced = useReducedMotion();
	const pending = !error && loading && value === undefined;
	const { showSkeleton } = useSkeletonSwap({ ready: !pending });

	let state: "error" | "skeleton" | "empty" | "value";
	let body: ReactNode;
	if (error) {
		state = "error";
		body = (
			<>
				<p className="flex items-center gap-1.5 text-body">
					<WarningCircleIcon
						aria-hidden
						className="size-4 shrink-0 text-danger"
					/>
					{error}
				</p>
				{onRetry ? (
					<Button
						variant="ghost"
						size="xs"
						onClick={onRetry}
						className="pointer-events-auto -ml-1.5"
					>
						<ArrowsClockwiseIcon aria-hidden />
						Tentar de novo
					</Button>
				) : null}
			</>
		);
	} else if (pending || showSkeleton) {
		state = "skeleton";
		body = <Skeleton visible={showSkeleton} />;
	} else if (value == null) {
		state = "empty";
		body = (
			<>
				<p aria-hidden className={cn(VALUE_TEXT, "text-text-muted")}>
					—
				</p>
				<p className="text-small text-text-muted">{emptyMessage}</p>
			</>
		);
	} else {
		state = "value";
		body = (
			<>
				<KpiValue value={value} format={format} highlight={highlight} />
				{delta ? <KpiDelta {...delta} /> : null}
			</>
		);
	}

	const labelElement = useRender({
		defaultTagName: "span",
		render: link,
		props: {
			className: cn(
				"min-w-0",
				link &&
					"text-text-muted outline-none transition-colors group-hover/kpi:text-text focus-visible:ring-0 after:absolute after:-inset-px after:z-10 after:rounded-md focus-visible:after:border focus-visible:after:border-focus-ring focus-visible:after:ring-3 focus-visible:after:ring-focus-ring/50",
			),
			children: label,
		},
		state: { slot: link ? "kpi-card-link" : "kpi-card-label" },
	});

	return (
		<div
			aria-busy={loading || undefined}
			className={cn(
				"group/kpi @container relative flex flex-col gap-3 rounded-md border border-border bg-surface-1 p-5 shadow-edge",
				link && "transition-colors hover:border-border-strong",
				className,
			)}
		>
			<dl className="flex flex-col gap-3">
				<dt className="flex items-center gap-1.5 text-small text-text-muted">
					{labelElement}
					{hint ? (
						<Popover>
							<PopoverTrigger
								openOnHover
								delay={200}
								aria-label={`Sobre ${label}`}
								className="relative z-20 -m-1 grid size-6 shrink-0 place-items-center rounded-sm text-text-muted outline-none transition-colors hover:text-text focus-visible:ring-3 focus-visible:ring-focus-ring/50"
							>
								<InfoIcon aria-hidden className="size-3.5" />
							</PopoverTrigger>
							<PopoverContent className="max-w-64 p-3 text-body">
								{hint}
							</PopoverContent>
						</Popover>
					) : null}
					{link ? (
						<CaretRightIcon
							aria-hidden
							className="ml-auto size-3.5 shrink-0 transition-[color,translate] group-hover/kpi:translate-x-0.5 group-hover/kpi:text-text motion-reduce:transition-none"
						/>
					) : null}
				</dt>
				<dd className="grid">
					<AnimatePresence initial={false}>
						<motion.div
							key={state}
							// O filtro da animação cria um contexto de empilhamento que cobriria o link:
							// com link, a camada sobe e deixa o clique passar, exceto no "Tentar de novo".
							className={cn(
								"col-start-1 row-start-1 flex min-w-0 flex-col items-start gap-1.5",
								link && "pointer-events-none relative z-20",
							)}
							initial={
								reduced ? { opacity: 0 } : { opacity: 0, filter: "blur(4px)" }
							}
							animate={
								reduced ? { opacity: 1 } : { opacity: 1, filter: "blur(0px)" }
							}
							exit={{ opacity: 0 }}
							transition={reduced ? { duration: 0 } : CROSSFADE}
						>
							{body}
						</motion.div>
					</AnimatePresence>
				</dd>
			</dl>
			{children}
		</div>
	);
}

// Reserva a altura do valor e da variação; as barras só aparecem depois do atraso do
// useSkeletonSwap, para uma resposta rápida não piscar.
function Skeleton({ visible }: { visible: boolean }) {
	const bar = cn("rounded-sm", visible && "bg-pressed");
	return (
		<div aria-hidden className="flex w-full flex-col gap-1.5">
			<div className={cn(VALUE_TEXT, "flex items-center")}>
				<span className={cn(bar, "h-6 w-3/5")} />
			</div>
			<div className="flex h-4 items-center">
				<span className={cn(bar, "h-2 w-2/5")} />
			</div>
		</div>
	);
}
