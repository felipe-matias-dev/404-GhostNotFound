// Navegação do portal sobre a Sidebar do shadcn (Componentes/Sidebar): variante `inset`,
// recolhe para ícones (Ctrl/Cmd+B, GatilhoNavegacao ou o rail) e vira Sheet no celular.
// O item ativo vem de `useItemAtivo`, o mesmo do título do Header.
import { Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Logo } from "#/components/layout/logo";
import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarRail,
	SidebarTrigger,
	useSidebar,
} from "#/components/ui/sidebar";
import { type ItemNavegacao, useItemAtivo } from "./navegacao";

export function AppSidebar({ itens }: { itens: ItemNavegacao[] }) {
	const ativoAtual = useItemAtivo(itens);
	const { setOpenMobile } = useSidebar();

	return (
		<Sidebar variant="inset" collapsible="icon">
			<SidebarHeader>
				<div className="flex h-8 items-center justify-between gap-2 px-2">
					<Logo className="text-heading group-data-[collapsible=icon]:[&>span]:hidden" />
					<GatilhoNavegacao local="sidebar" />
				</div>
			</SidebarHeader>
			<SidebarContent>
				<SidebarGroup>
					<nav aria-label="Navegação principal">
						<SidebarMenu>
							{itens.map(({ to, rotulo, icone: Icone }) => {
								const ativo = ativoAtual?.to === to;
								return (
									<SidebarMenuItem key={to}>
										<SidebarMenuButton
											render={
												<Link to={to} onClick={() => setOpenMobile(false)} />
											}
											isActive={ativo}
											tooltip={rotulo}
										>
											<Icone aria-hidden weight={ativo ? "fill" : "regular"} />
											<span>{rotulo}</span>
										</SidebarMenuButton>
									</SidebarMenuItem>
								);
							})}
						</SidebarMenu>
					</nav>
				</SidebarGroup>
			</SidebarContent>
			<SidebarRail />
		</Sidebar>
	);
}

// Com a navegação aberta o trigger fica ao lado da logo; recolhida ele
// passa para o início do Header. Só uma das duas instâncias existe por vez e o `layoutId`
// anima a troca de lugar. No celular a sidebar vira Sheet e o trigger mora sempre no
// Header, então não há o que animar.
export function GatilhoNavegacao({
	local,
	className,
}: {
	local: "sidebar" | "header";
	className?: string;
}) {
	const { isMobile, open } = useSidebar();
	const naSidebar = !isMobile && open;

	if (naSidebar !== (local === "sidebar")) return null;

	return (
		<motion.div
			layoutId={isMobile ? undefined : "gatilho-navegacao"}
			className={className}
		>
			<SidebarTrigger />
		</motion.div>
	);
}
