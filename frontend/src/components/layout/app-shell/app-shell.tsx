// Casca do app no layout `inset` da Sidebar do shadcn: navegação
// sobre `bg` e o conteúdo num painel `surface-1` com borda e raio `lg`. O trigger do Header
// recolhe a navegação para ícones (no celular, abre o Sheet).
import { useMatchRoute } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { AppSidebar, NAVEGACAO } from "#/components/layout/app-sidebar";
import { Header } from "#/components/layout/header";
import {
	SidebarInset,
	SidebarProvider,
	SidebarTrigger,
} from "#/components/ui/sidebar";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { TooltipProvider } from "#/components/ui/tooltip";

export function AppShell({ children }: { children: ReactNode }) {
	const matchRoute = useMatchRoute();
	const atual = NAVEGACAO.find(({ to }) =>
		matchRoute({ to, fuzzy: to !== "/" }),
	);

	return (
		<TooltipProvider>
			<SidebarProvider className="h-svh">
				<a
					href="#conteudo"
					className="sr-only rounded-md bg-surface-2 px-3 py-1.5 text-body text-text focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
				>
					Pular para o conteúdo
				</a>
				<AppSidebar itens={NAVEGACAO} />
				<SidebarInset className="min-h-0 overflow-hidden">
					<Header
						titulo={atual?.rotulo}
						inicio={<SidebarTrigger className="-ml-1" />}
						acoes={<ThemeToggle className="size-7" />}
					/>
					<div
						id="conteudo"
						tabIndex={-1}
						data-scroll-restoration-id="conteudo"
						className="min-h-0 flex-1 overflow-y-auto outline-none"
					>
						{children}
					</div>
				</SidebarInset>
			</SidebarProvider>
		</TooltipProvider>
	);
}
