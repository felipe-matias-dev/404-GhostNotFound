// Hold to Confirm do interior.dev (https://www.interior.dev/docs/hold-to-confirm), instalado
// por `npx shadcn@latest add https://www.interior.dev/r/hold-to-confirm.json`. A lógica do
// hook é a original; a aparência foi trocada pelos tokens da marca VE-360:
// - face em repouso = Button `outline` (mesma altura, raio, hover e anel de foco);
// - preenchimento: `destructive` = danger/on-danger, `neutral` = cores invertidas;
// - desabilitado = surface-2 + text-disabled, sem opacidade;
// - textos para leitor de tela em português, duração via #/lib/format.
// Uso: ações destrutivas e irreversíveis (excluir, revogar). Não substitui o Button comum.
import {
	animate,
	motion,
	useMotionValue,
	useReducedMotion,
	useTransform,
} from "motion/react";
import type * as React from "react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { buttonVariants } from "#/components/ui/button";
import { formatSegundos } from "#/lib/format";
import { cn } from "#/lib/utils";

const FACE = {
	type: "spring",
	stiffness: 260,
	damping: 34,
	mass: 0.8,
} as const;

const FILL = {
	neutral: "bg-text text-bg",
	destructive: "bg-danger text-on-danger",
} as const;

export type HoldPhase = "idle" | "holding" | "releasing" | "committed";

export type UseHoldToConfirmOptions = {
	onConfirm: () => void;
	onAbort?: () => void;
	duration?: number;
	steps?: number;
	releaseRate?: number;
	moveTolerance?: number;
	haptic?: boolean;
	disabled?: boolean;
};

export function useHoldToConfirm({
	onConfirm,
	onAbort,
	duration = 1800,
	steps = 20,
	releaseRate = 2.5,
	moveTolerance = 10,
	haptic = true,
	disabled = false,
}: UseHoldToConfirmOptions) {
	const [step, setStep] = useState(0);
	const [phase, setPhase] = useState<HoldPhase>("idle");

	const phaseRef = useRef<HoldPhase>("idle");
	const down = useRef(false);
	const elapsed = useRef(0);
	const last = useRef(0);
	const raf = useRef(0);
	const origin = useRef<{ x: number; y: number } | null>(null);

	const confirm = useRef(onConfirm);
	confirm.current = onConfirm;
	const abort = useRef(onAbort);
	abort.current = onAbort;

	const move = useCallback((next: HoldPhase) => {
		phaseRef.current = next;
		setPhase(next);
	}, []);

	const reset = useCallback(() => {
		cancelAnimationFrame(raf.current);
		raf.current = 0;
		down.current = false;
		elapsed.current = 0;
		origin.current = null;
		setStep(0);
		move("idle");
	}, [move]);

	const begin = useCallback(
		(point?: { x: number; y: number }) => {
			if (disabled) return;
			if (phaseRef.current === "committed" || phaseRef.current === "holding") {
				return;
			}

			origin.current = point ?? null;
			down.current = true;
			move("holding");
			if (raf.current) return;

			last.current = performance.now();

			const loop = (now: number) => {
				// Correção sobre o original: o timestamp do rAF é o início do frame e pode ser
				// anterior ao performance.now() lido no pointerdown. dt negativo zerava o
				// progresso e o hold voltava para idle no primeiro frame.
				const dt = Math.max(0, Math.min(64, now - last.current));
				last.current = now;
				elapsed.current += down.current ? dt : -dt * releaseRate;

				if (elapsed.current >= duration) {
					raf.current = 0;
					elapsed.current = duration;
					down.current = false;
					origin.current = null;
					setStep(steps);
					move("committed");
					if (haptic) navigator.vibrate?.(14);
					confirm.current();
					return;
				}

				if (!down.current && elapsed.current <= 0) {
					raf.current = 0;
					elapsed.current = 0;
					origin.current = null;
					setStep(0);
					move("idle");
					return;
				}

				const s = Math.min(
					steps,
					Math.floor((elapsed.current / duration) * steps),
				);
				setStep((prev) => (prev === s ? prev : s));
				raf.current = requestAnimationFrame(loop);
			};

			raf.current = requestAnimationFrame(loop);
		},
		[disabled, duration, steps, releaseRate, haptic, move],
	);

	const release = useCallback(() => {
		if (phaseRef.current !== "holding") return;
		down.current = false;
		origin.current = null;
		move("releasing");
		abort.current?.();
	}, [move]);

	useEffect(() => {
		const bail = () => release();
		const onVisibility = () => {
			if (document.hidden) release();
		};
		window.addEventListener("blur", bail);
		document.addEventListener("visibilitychange", onVisibility);
		return () => {
			window.removeEventListener("blur", bail);
			document.removeEventListener("visibilitychange", onVisibility);
			cancelAnimationFrame(raf.current);
			raf.current = 0;
		};
	}, [release]);

	const bind = {
		onPointerDown: (e: React.PointerEvent) => {
			if (e.pointerType === "mouse" && e.button !== 0) return;
			e.currentTarget.setPointerCapture?.(e.pointerId);
			begin({ x: e.clientX, y: e.clientY });
		},
		onPointerMove: (e: React.PointerEvent) => {
			const from = origin.current;
			if (phaseRef.current !== "holding" || !from) return;
			if (Math.hypot(e.clientX - from.x, e.clientY - from.y) > moveTolerance) {
				release();
			}
		},
		onPointerUp: release,
		onPointerCancel: release,
		onPointerLeave: release,
		onKeyDown: (e: React.KeyboardEvent) => {
			if (e.key === "Escape") {
				if (
					phaseRef.current === "holding" ||
					phaseRef.current === "releasing"
				) {
					e.preventDefault();
					reset();
				}
				return;
			}
			if (e.repeat) return;
			if (e.key === " " || e.key === "Enter") {
				e.preventDefault();
				begin();
			}
		},
		onKeyUp: (e: React.KeyboardEvent) => {
			if (e.key === " " || e.key === "Enter") release();
		},
		onBlur: release,
		onClick: (e: React.MouseEvent) => {
			e.preventDefault();
			if (phaseRef.current === "committed") e.stopPropagation();
		},
		onContextMenu: (e: React.MouseEvent) => e.preventDefault(),
	};

	return {
		bind,
		step,
		steps,
		phase,
		progress: step / steps,
		reset,
	};
}

export type HoldToConfirmProps = {
	onConfirm: () => void;
	children: React.ReactNode;
	onAbort?: () => void;
	confirmLabel?: string;
	duration?: number;
	resetAfter?: number;
	steps?: number;
	releaseRate?: number;
	disabled?: boolean;
	tone?: "neutral" | "destructive";
	fillClassName?: string;
	className?: string;
};

export function HoldToConfirm({
	onConfirm,
	children,
	onAbort,
	confirmLabel = "Confirmado",
	duration = 1800,
	resetAfter = 1600,
	steps = 20,
	releaseRate = 2.5,
	disabled = false,
	tone = "neutral",
	fillClassName,
	className,
}: HoldToConfirmProps) {
	const { bind, phase, reset } = useHoldToConfirm({
		onConfirm,
		onAbort,
		duration,
		steps,
		releaseRate,
		disabled,
	});

	const reduced = useReducedMotion();
	const hintId = useId();

	const committed = phase === "committed";

	const swept = useMotionValue(0);
	const clipPath = useTransform(swept, (v) => `inset(0 ${(1 - v) * 100}% 0 0)`);

	useEffect(() => {
		if (phase !== "committed" || resetAfter <= 0) return;
		const back = setTimeout(reset, resetAfter);
		return () => clearTimeout(back);
	}, [phase, resetAfter, reset]);

	useEffect(() => {
		if (reduced) {
			swept.set(phase === "holding" || phase === "committed" ? 1 : 0);
			return;
		}

		if (phase === "committed") {
			const controls = animate(swept, 1, { duration: 0.12, ease: "linear" });
			return () => controls.stop();
		}

		const from = swept.get();

		if (phase === "holding") {
			const controls = animate(swept, 1, {
				duration: (duration * (1 - from)) / 1000,
				ease: "linear",
			});
			return () => controls.stop();
		}

		const controls = animate(swept, 0, {
			duration: (duration * from) / releaseRate / 1000,
			ease: [0.23, 1, 0.32, 1],
		});
		return () => controls.stop();
	}, [phase, duration, releaseRate, reduced, swept]);

	return (
		<button
			type="button"
			// aria-disabled em vez de disabled: o foco não cai para o body no meio do hold.
			aria-disabled={disabled || committed}
			aria-describedby={hintId}
			data-slot="hold-to-confirm"
			data-phase={phase}
			{...bind}
			style={{ touchAction: "manipulation", WebkitTouchCallout: "none" }}
			className={cn(
				buttonVariants({ variant: "outline" }),
				// O progresso é o próprio feedback de pressionado: sem a camada `pressed` do
				// outline, e sem hover enquanto o hold está em andamento.
				"relative isolate inline-grid select-none place-items-center overflow-hidden active:bg-transparent",
				phase !== "idle" && "hover:bg-transparent",
				disabled &&
					"cursor-not-allowed border-border bg-surface-2 text-text-disabled hover:bg-surface-2 active:bg-surface-2",
				className,
			)}
		>
			<Faces committed={committed} confirmLabel={confirmLabel}>
				{children}
			</Faces>

			<motion.span
				aria-hidden
				style={{ clipPath }}
				className={cn(
					"absolute inset-0 grid place-items-center",
					fillClassName ?? FILL[tone],
				)}
			>
				<Faces committed={committed} confirmLabel={confirmLabel}>
					{children}
				</Faces>
			</motion.span>

			<span id={hintId} className="sr-only">
				Pressione e segure por {formatSegundos(duration)} para confirmar. Soltar
				antes cancela e nada acontece.
			</span>

			<output aria-live="polite" className="sr-only">
				{committed ? confirmLabel : ""}
			</output>
		</button>
	);
}

function Faces({
	committed,
	confirmLabel,
	children,
}: {
	committed: boolean;
	confirmLabel: string;
	children: React.ReactNode;
}) {
	return (
		<span className="col-start-1 row-start-1 grid">
			<motion.span
				initial={false}
				animate={{ opacity: committed ? 0 : 1 }}
				transition={FACE}
				className="col-start-1 row-start-1 flex items-center justify-center gap-2 whitespace-nowrap"
			>
				{children}
			</motion.span>
			<motion.span
				initial={false}
				animate={{ opacity: committed ? 1 : 0 }}
				transition={FACE}
				className="col-start-1 row-start-1 flex items-center justify-center gap-1.5 whitespace-nowrap"
			>
				<svg
					width="12"
					height="12"
					viewBox="0 0 12 12"
					fill="none"
					stroke="currentColor"
					strokeWidth="1.7"
					strokeLinecap="round"
					strokeLinejoin="round"
					aria-hidden="true"
				>
					<path d="M2.5 6.4 4.7 8.6 9.5 3.5" />
				</svg>
				{confirmLabel}
			</motion.span>
		</span>
	);
}
