import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import { Link } from "@tanstack/react-router";
import { buttonVariants } from "#/components/ui/button";

export function NaoEncontrado() {
	return (
		<div className="flex min-h-full flex-col items-center justify-center gap-3 px-3 py-10 text-center">
			<MagnifyingGlassIcon aria-hidden className="size-6 text-text-muted" />
			<h1 className="text-heading text-text">Página não encontrada</h1>
			<p className="max-w-prose text-body text-text-muted">
				O endereço não existe ou mudou. Use a navegação ao lado ou volte para a
				visão geral.
			</p>
			<Link
				to="/"
				className={buttonVariants({ variant: "outline", size: "sm" })}
			>
				Ir para a visão geral
			</Link>
		</div>
	);
}
