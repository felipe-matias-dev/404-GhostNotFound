// Barra do topo do painel de conteúdo: 44px, título da seção em
// `text-body` e ações à direita. O título é o <h1> da página e desliza (layout do motion)
// quando o `inicio` aparece ou some; dentro de um LayoutGroup ele acompanha mudanças de
// outros componentes do grupo.
import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "#/lib/utils";

export function Header({
	titulo,
	inicio,
	acoes,
	className,
}: {
	titulo?: string;
	inicio?: ReactNode;
	acoes?: ReactNode;
	className?: string;
}) {
	const duration = useReducedMotion() ? 0 : 0.2;

	return (
		<header
			className={cn(
				"flex h-11 shrink-0 items-center gap-1.5 border-b border-border px-3 lg:px-4",
				className,
			)}
		>
			{inicio}
			{titulo && (
				<motion.h1
					layout="position"
					transition={{ duration, ease: "linear" }}
					className="truncate font-medium text-body text-text"
				>
					{titulo}
				</motion.h1>
			)}
			{acoes && <div className="ml-auto flex items-center gap-1">{acoes}</div>}
		</header>
	);
}
