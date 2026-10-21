// Skeleton Swap do interior.dev (https://www.interior.dev/docs/skeleton-swap), instalado por
// `npx shadcn@latest add https://www.interior.dev/r/skeleton-swap.json`. Lógica original;
// adaptações aos tokens da marca VE-360:
// - barras em `bg-pressed` (camada translúcida: aparece sobre bg, surface-1 e surface-2);
// - padrão de linha = `text-body` (20px), barra de 8px, raio `rounded-sm`;
// - cor do texto herdada do pai; aviso de leitor de tela em português.
// Uso: reserva a altura do conteúdo enquanto carrega e troca sem deslocar o layout.
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type * as React from "react";
import { useEffect, useRef, useState } from "react";
import { cn } from "#/lib/utils";

const CROSSFADE = {
	type: "spring",
	stiffness: 260,
	damping: 34,
	mass: 0.8,
} as const;

const WIDTHS = [100, 93, 97, 88, 95, 91] as const;

function widthFor(index: number, total: number) {
	if (total > 1 && index === total - 1) return 62;
	return WIDTHS[(index * 7 + 3) % WIDTHS.length];
}

export type UseSkeletonSwapOptions = {
	ready: boolean;
	delay?: number;
	minVisible?: number;
};

export function useSkeletonSwap({
	ready,
	delay = 120,
	minVisible = 380,
}: UseSkeletonSwapOptions) {
	const [visible, setVisible] = useState(false);
	const shownAt = useRef(0);

	useEffect(() => {
		if (!ready) {
			if (visible) return;
			const t = setTimeout(() => {
				shownAt.current = performance.now();
				setVisible(true);
			}, delay);
			return () => clearTimeout(t);
		}

		if (!visible) return;
		const rest = Math.max(
			0,
			minVisible - (performance.now() - shownAt.current),
		);
		const t = setTimeout(() => setVisible(false), rest);
		return () => clearTimeout(t);
	}, [ready, visible, delay, minVisible]);

	return { showSkeleton: visible, busy: !ready };
}

export type SkeletonSwapProps = {
	ready: boolean;
	children: React.ReactNode;
	lines?: number;
	lineHeight?: number;
	barHeight?: number;
	reserve?: number;
	delay?: number;
	minVisible?: number;
	label?: string;
	skeleton?: React.ReactNode;
	className?: string;
};

export function SkeletonSwap({
	ready,
	children,
	lines = 3,
	lineHeight = 20,
	barHeight = 8,
	reserve,
	delay = 120,
	minVisible = 380,
	label,
	skeleton,
	className,
}: SkeletonSwapProps) {
	const { showSkeleton } = useSkeletonSwap({ ready, delay, minVisible });
	const reduced = useReducedMotion();

	const shell = useRef<HTMLDivElement>(null);
	const body = useRef<HTMLDivElement>(null);
	const [scrollable, setScrollable] = useState(false);

	const box = reserve ?? lines * lineHeight;

	useEffect(() => {
		const el = shell.current;
		const inner = body.current;
		if (!el || typeof ResizeObserver === "undefined") return;

		const check = () => setScrollable(el.scrollHeight - el.clientHeight > 1);
		check();

		const ro = new ResizeObserver(check);
		ro.observe(el);
		if (inner) ro.observe(inner);
		return () => ro.disconnect();
	}, []);

	return (
		// `group` dá suporte ao aria-label (div genérica não aceita nome acessível).
		// biome-ignore lint/a11y/useSemanticElements: não é formulário; <fieldset> seria errado aqui.
		<div
			ref={shell}
			aria-busy={!ready}
			role="group"
			aria-label={label}
			// Focável só quando o conteúdo rola, para dar acesso por teclado à rolagem.
			tabIndex={scrollable ? 0 : undefined}
			style={{ height: box }}
			className={cn(
				"relative grid overflow-y-auto overscroll-contain",
				className,
			)}
		>
			<motion.div
				ref={body}
				className="col-start-1 row-start-1 min-w-0"
				initial={false}
				animate={
					reduced
						? { opacity: showSkeleton ? 0 : 1 }
						: {
								opacity: showSkeleton ? 0 : 1,
								scale: showSkeleton ? 0.99 : 1,
								filter: showSkeleton ? "blur(4px)" : "blur(0px)",
							}
				}
				transition={reduced ? { duration: 0 } : CROSSFADE}
				style={{
					transformOrigin: "top left",
					pointerEvents: showSkeleton ? "none" : undefined,
				}}
			>
				{children}
			</motion.div>

			<AnimatePresence initial={false}>
				{showSkeleton ? (
					<motion.div
						key="skeleton"
						aria-hidden
						className="pointer-events-none col-start-1 row-start-1 w-full self-start"
						initial={reduced ? { opacity: 1 } : { opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={
							reduced ? { opacity: 0 } : { opacity: 0, filter: "blur(3px)" }
						}
						transition={reduced ? { duration: 0 } : CROSSFADE}
					>
						{skeleton ?? (
							<div className="w-full">
								{Array.from({ length: lines }, (_, i) => (
									<div
										// biome-ignore lint/suspicious/noArrayIndexKey: barras fixas, sem identidade própria.
										key={i}
										className="flex items-center"
										style={{ height: lineHeight }}
									>
										<div
											className="rounded-sm bg-pressed"
											style={{
												height: barHeight,
												width: `${widthFor(i, lines)}%`,
											}}
										/>
									</div>
								))}
							</div>
						)}
					</motion.div>
				) : null}
			</AnimatePresence>

			{label ? (
				<output className="sr-only">
					{ready ? `${label}: carregado` : ""}
				</output>
			) : null}
		</div>
	);
}
