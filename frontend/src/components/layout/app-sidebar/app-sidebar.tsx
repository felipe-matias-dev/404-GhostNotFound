// Navegação do portal sobre a Sidebar do shadcn (Componentes/Sidebar): variante `inset`,
// recolhe para ícones (Ctrl/Cmd+B, GatilhoNavegacao ou o rail) e vira Sheet no celular.
// O item ativo vem de `useItemAtivo`, o mesmo do título do Header.
import { Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Logo } from "#/components/layout/logo";
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarGroup,
	SidebarGroupLabel,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarRail,
	SidebarTrigger,
	useSidebar,
} from "#/components/ui/sidebar";
import type { DestinoPortal } from "#/lib/filtros";
import { type ItemNavegacao, useItemAtivo } from "./navegacao";

export function AppSidebar({
	itens,
	onConsultarUc,
	conta,
	searchPara,
}: {
	itens: ItemNavegacao[];
	onConsultarUc: () => void;
	conta?: ReactNode;
	searchPara: (destino: DestinoPortal) => Record<string, unknown>;
}) {
	const ativoAtual = useItemAtivo(itens);
	const { setOpenMobile, isMobile } = useSidebar();

	function abrirConsulta() {
		if (!isMobile) {
			onConsultarUc();
			return;
		}
		setOpenMobile(false);
		requestAnimationFrame(() => {
			document
				.querySelector<HTMLButtonElement>('[data-sidebar="trigger"]')
				?.focus();
			onConsultarUc();
		});
	}

	return (
		<Sidebar variant="inset" collapsible="icon">
			<SidebarHeader>
				<div className="flex h-8 items-center justify-between gap-2 px-2">
					<Logo className="text-heading group-data-[collapsible=icon]:[&>span]:hidden" />
					<GatilhoNavegacao local="sidebar" />
				</div>
			</SidebarHeader>
			<SidebarContent className="gap-4 pt-3">
				{[...new Set(itens.map((item) => item.grupo))].map((grupo) => (
					<SidebarGroup key={grupo}>
						<SidebarGroupLabel>{grupo}</SidebarGroupLabel>
						<nav aria-label={grupo}>
							<SidebarMenu>
								{itens
									.filter((item) => item.grupo === grupo)
									.map(({ to, rotulo, icone: Icone }) => {
										const ativo = ativoAtual?.to === to;
										const consulta = to === "/uc";
										return (
											<SidebarMenuItem key={to}>
												<SidebarMenuButton
													render={
														consulta ? undefined : (
															<Link
																to={to}
																search={
																	to === "/agente"
																		? undefined
																		: (searchPara(to) as never)
																}
																onClick={() => setOpenMobile(false)}
															/>
														)
													}
													onClick={consulta ? abrirConsulta : undefined}
													isActive={ativo}
													tooltip={rotulo}
													aria-haspopup={consulta ? "dialog" : undefined}
													aria-keyshortcuts={
														consulta ? "Control+k Meta+k" : undefined
													}
												>
													<Icone
														aria-hidden
														weight={ativo ? "fill" : "regular"}
													/>
													<span>{rotulo}</span>
												</SidebarMenuButton>
											</SidebarMenuItem>
										);
									})}
							</SidebarMenu>
						</nav>
					</SidebarGroup>
				))}
			</SidebarContent>
			{conta && <SidebarFooter>{conta}</SidebarFooter>}
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
