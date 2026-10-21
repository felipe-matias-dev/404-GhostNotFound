// Lockup do topo esquerdo: anel aberto com ponto + "VE-360" em Söhne Breit. As cores vêm
// dos tokens do tema (styles.css), então a logo acompanha escuro/claro sozinha.
// Tudo em `em`: o tamanho vem do `text-*` do className.
export function Logo({ className = "" }: { className?: string }) {
	return (
		<div
			role="img"
			aria-label="VE-360"
			className={`inline-flex items-center gap-[0.5em] font-display text-2xl font-semibold leading-none ${className}`}
		>
			<svg
				aria-hidden="true"
				viewBox="0 0 24 24"
				className="size-[1.2em] shrink-0 text-marca"
			>
				<path
					d="M21 12A9 9 0 1 1 17.24 4.68"
					fill="none"
					stroke="currentColor"
					strokeWidth="2.6"
					strokeLinecap="round"
				/>
				<circle cx="20.02" cy="7.91" r="1.4" fill="currentColor" />
			</svg>
			<span aria-hidden="true" className="text-texto">
				VE<span className="text-texto-suave">-360</span>
			</span>
		</div>
	);
}
