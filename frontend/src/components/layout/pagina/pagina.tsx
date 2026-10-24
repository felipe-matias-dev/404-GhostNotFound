// Container do conteúdo de cada tela: largura máxima, respiro lateral e a descrição curta
// da tela abaixo do título (que fica no Header).
import type { ReactNode } from "react";
import { cn } from "#/lib/utils";

export function Pagina({
	descricao,
	children,
	className,
}: {
	descricao?: string;
	children?: ReactNode;
	className?: string;
}) {
	return (
		<div
			className={cn(
				"mx-auto flex w-full max-w-6xl flex-col gap-5 px-3 py-5 lg:px-5",
				className,
			)}
		>
			{descricao && (
				<p className="max-w-prose text-body text-text-muted">{descricao}</p>
			)}
			{children}
		</div>
	);
}
