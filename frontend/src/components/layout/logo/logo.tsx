// Lockup do topo esquerdo: anel aberto com ponto + "VE-360" em Söhne Breit. As cores vêm
// dos tokens do tema (styles.css), então a logo acompanha escuro/claro sozinha.
// Tudo em `em`: o tamanho vem do `text-*` do className.
import type { ComponentProps } from "react";
import { cn } from "#/lib/utils";

export function LogoMark({
	className,
	weight,
	...props
}: ComponentProps<"svg"> & { weight?: "regular" | "bold" | "fill" }) {
	return (
		<svg
			aria-hidden="true"
			viewBox="0 0 24 24"
			className={cn("size-4 shrink-0", className)}
			{...props}
		>
			<path
				d="M21 12A9 9 0 1 1 17.24 4.68"
				fill="none"
				stroke="currentColor"
				strokeWidth={weight === "fill" || weight === "bold" ? "2.8" : "2.4"}
				strokeLinecap="round"
			/>
			<circle
				cx="20.02"
				cy="7.91"
				r={weight === "fill" ? "1.8" : "1.4"}
				fill="currentColor"
			/>
		</svg>
	);
}

export function Logo({ className }: { className?: string }) {
	return (
		<div
			role="img"
			aria-label="VE-360"
			className={cn(
				"inline-flex items-center gap-[0.5em] font-display text-title leading-none",
				className,
			)}
		>
			<LogoMark className="size-[1.2em] text-accent-text" />
			<span aria-hidden="true" className="text-text">
				VE<span className="text-text-muted">-360</span>
			</span>
		</div>
	);
}
