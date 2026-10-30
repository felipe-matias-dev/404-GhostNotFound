// Casca do app no layout `inset` da Sidebar do shadcn: navegação
// sobre `bg` e o conteúdo num painel `surface-1` com borda e raio `lg`. O trigger fica ao
// lado da logo com a navegação aberta e vai para o Header quando ela recolhe (no celular,
// abre o Sheet). O MotionConfig casa as animações com o `duration-200 ease-linear` da
// sidebar e respeita o "reduzir movimento" do sistema. O título do Header leva ao início da
// seção (sem recorte) e a página pode pôr a trilha do recorte ao lado dele com `HeaderTrilha`.
import { Link } from "@tanstack/react-router";
import { LayoutGroup, MotionConfig } from "motion/react";
import { type ReactNode, useState } from "react";
import {
	AppSidebar,
	GatilhoNavegacao,
	type ItemNavegacao,
	NAVEGACAO,
	useItemAtivo,
} from "#/components/layout/app-sidebar";
import { Header, HeaderTrilhaContext } from "#/components/layout/header";
import { SidebarInset, SidebarProvider } from "#/components/ui/sidebar";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { TooltipProvider } from "#/components/ui/tooltip";

export function AppShell({
	children,
	onConsultarUc,
	itens = NAVEGACAO,
	conta,
}: {
	children: ReactNode;
	onConsultarUc: () => void;
	itens?: ItemNavegacao[];
	conta?: ReactNode;
}) {
	const atual = useItemAtivo(NAVEGACAO);
	const [trilha, setTrilha] = useState<HTMLDivElement | null>(null);

	return (
		<TooltipProvider>
			<SidebarProvider className="h-svh">
				<a
					href="#conteudo"
					className="sr-only rounded-md bg-surface-2 px-3 py-1.5 text-body text-text focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
				>
					Pular para o conteúdo
				</a>
				<MotionConfig
					reducedMotion="user"
					transition={{ duration: 0.2, ease: "linear" }}
				>
					<LayoutGroup>
						<AppSidebar
							itens={itens}
							onConsultarUc={onConsultarUc}
							conta={conta}
						/>
						<SidebarInset className="min-h-0 overflow-hidden">
							<Header
								titulo={
									atual && (
										<Link
											to={atual.to}
											className="rounded-sm outline-none transition-colors hover:text-text focus-visible:text-text"
										>
											{atual.rotulo}
										</Link>
									)
								}
								inicio={<GatilhoNavegacao local="header" className="-ml-1" />}
								acoes={<ThemeToggle className="size-7" />}
								trilhaRef={setTrilha}
							/>
							<div
								id="conteudo"
								tabIndex={-1}
								data-scroll-restoration-id="conteudo"
								className="min-h-0 flex-1 overflow-y-auto outline-none"
							>
								<HeaderTrilhaContext value={trilha}>
									{children}
								</HeaderTrilhaContext>
							</div>
						</SidebarInset>
					</LayoutGroup>
				</MotionConfig>
			</SidebarProvider>
		</TooltipProvider>
	);
}
