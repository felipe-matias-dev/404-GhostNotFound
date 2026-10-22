// Barra do topo do painel de conteúdo: 44px, título da seção em
// `text-body` e ações à direita. O título é o <h1> da página.
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
	return (
		<header
			className={cn(
				"flex h-11 shrink-0 items-center gap-1.5 border-b border-border px-3 lg:px-4",
				className,
			)}
		>
			{inicio}
			{titulo && (
				<h1 className="truncate font-medium text-body text-text">{titulo}</h1>
			)}
			{acoes && <div className="ml-auto flex items-center gap-1">{acoes}</div>}
		</header>
	);
}
