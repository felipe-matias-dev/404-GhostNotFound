// Barra do topo do painel de conteúdo: 44px, título da seção em
// `text-body` e ações à direita. O título é o <h1> da página e desliza (layout do motion)
// quando o `inicio` aparece ou some; dentro de um LayoutGroup ele acompanha mudanças de
// outros componentes do grupo. A transição vem do MotionConfig do AppShell. Depois do título
// fica o espaço da trilha do recorte (`trilhaRef`, preenchido pela página com
// `HeaderTrilha`); com trilha, o título vira o primeiro nível, em `text-muted`.
import { motion } from "motion/react";
import type { ReactNode, Ref } from "react";
import { cn } from "#/lib/utils";

export function Header({
	titulo,
	inicio,
	acoes,
	trilhaRef,
	className,
}: {
	titulo?: ReactNode;
	inicio?: ReactNode;
	acoes?: ReactNode;
	trilhaRef?: Ref<HTMLDivElement>;
	className?: string;
}) {
	return (
		<header
			className={cn(
				"group/header flex h-11 shrink-0 items-center gap-1.5 border-b border-border px-3 lg:px-4",
				className,
			)}
		>
			{inicio}
			{titulo && (
				<motion.h1
					layout="position"
					className="shrink-0 truncate font-medium text-body text-text group-has-[[data-slot=breadcrumb]]/header:text-text-muted"
				>
					{titulo}
				</motion.h1>
			)}
			{trilhaRef && <div ref={trilhaRef} className="flex min-w-0" />}
			{acoes && <div className="ml-auto flex items-center gap-1">{acoes}</div>}
		</header>
	);
}
