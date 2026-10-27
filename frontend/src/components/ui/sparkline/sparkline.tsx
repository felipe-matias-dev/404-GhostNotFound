// Sparkline: a forma de uma série num espaço pequeno, ao lado do número que ela explica.
// - decorativa (`aria-hidden`): o valor e a variação já estão em texto no card;
// - "destaque com uma cor só" (Fundamentos/Cores): a linha em `chart-muted` e só o ponto que
//   importa em `chart-1`; a referência (ex.: o mês base) é um anel neutro;
// - linha reta entre os pontos, e `null` interrompe a linha em vez de inventar o valor;
// - estica na largura do container: o SVG escala sem `preserveAspectRatio` e os pontos são
//   HTML posicionados em %, para não virarem elipses.
import { cn } from "#/lib/utils";

export type SparklineProps = {
	/** Um valor por período, em ordem; `null` é um buraco na linha. */
	values: (number | null)[];
	/** Índice do ponto em destaque (ex.: o mês atual). */
	highlight?: number;
	/** Índice do ponto de referência (ex.: o mês base). */
	reference?: number;
	className?: string;
};

const HEIGHT = 100;
// Folga em cima e embaixo para o ponto não ser cortado no mínimo e no máximo.
const PAD = 12;

export function Sparkline({
	values,
	highlight,
	reference,
	className,
}: SparklineProps) {
	const defined = values.filter((v): v is number => v !== null);
	if (defined.length < 2) return null;
	const lo = Math.min(...defined);
	const span = Math.max(...defined) - lo;
	const last = Math.max(1, values.length - 1);
	const x = (i: number) => (i / last) * 100;
	const y = (v: number) =>
		span === 0 ? HEIGHT / 2 : PAD + (1 - (v - lo) / span) * (HEIGHT - 2 * PAD);

	const segments: string[] = [];
	let current: string[] = [];
	values.forEach((v, i) => {
		if (v === null) {
			if (current.length > 1) segments.push(current.join(" "));
			current = [];
			return;
		}
		current.push(`${x(i).toFixed(2)},${y(v).toFixed(2)}`);
	});
	if (current.length > 1) segments.push(current.join(" "));

	const dot = (i: number | undefined, tone: "highlight" | "reference") => {
		const v = i === undefined ? null : values[i];
		if (i === undefined || v === null || v === undefined) return null;
		return (
			<span
				className={cn(
					"-translate-x-1/2 -translate-y-1/2 absolute size-1.5 rounded-full",
					tone === "highlight"
						? "bg-chart-1"
						: "border border-text-muted bg-surface-1",
				)}
				style={{ left: `${x(i)}%`, top: `${y(v)}%` }}
			/>
		);
	};

	return (
		<div aria-hidden className={cn("relative h-8 w-full", className)}>
			<svg
				aria-hidden="true"
				viewBox={`0 0 100 ${HEIGHT}`}
				preserveAspectRatio="none"
				className="block size-full overflow-visible"
			>
				{segments.map((points) => (
					<polyline
						key={points}
						points={points}
						fill="none"
						strokeWidth={1.5}
						strokeLinecap="round"
						strokeLinejoin="round"
						vectorEffect="non-scaling-stroke"
						className="stroke-chart-muted"
					/>
				))}
			</svg>
			{dot(reference, "reference")}
			{dot(highlight, "highlight")}
		</div>
	);
}
