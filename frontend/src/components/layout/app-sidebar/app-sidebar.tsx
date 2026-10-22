// Navegação do portal sobre a Sidebar do shadcn (Componentes/Sidebar): variante `inset`,
// recolhe para ícones (Ctrl/Cmd+B, trigger do Header ou o rail) e vira Sheet no celular.
// O item ativo vem do router; rotas filhas (`/uc/0042`) mantêm a seção ativa.
import { Link, useMatchRoute } from "@tanstack/react-router";
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
	useSidebar,
} from "#/components/ui/sidebar";
import type { ItemNavegacao } from "./navegacao";

export function AppSidebar({ itens }: { itens: ItemNavegacao[] }) {
	const matchRoute = useMatchRoute();
	const { setOpenMobile } = useSidebar();

	return (
		<Sidebar variant="inset" collapsible="icon">
			<SidebarHeader>
				<div className="flex h-8 items-center px-2">
					<Logo className="text-heading group-data-[collapsible=icon]:[&>span]:hidden" />
				</div>
			</SidebarHeader>
			<SidebarContent>
				<SidebarGroup>
					<nav aria-label="Navegação principal">
						<SidebarMenu>
							{itens.map(({ to, rotulo, icone: Icone }) => {
								const ativo = Boolean(matchRoute({ to, fuzzy: to !== "/" }));
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
