import {
	BuildingsIcon,
	CurrencyCircleDollarIcon,
	GaugeIcon,
	HouseIcon,
	LightningSlashIcon,
} from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { TooltipProvider } from "#/components/ui/tooltip";
import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarGroupLabel,
	SidebarInset,
	SidebarMenu,
	SidebarMenuBadge,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarMenuSkeleton,
	SidebarProvider,
	SidebarRail,
	SidebarTrigger,
} from "./sidebar";

// Estrutura genérica do shadcn com links simples; a navegação do app (com o router) está
// em Layout/AppSidebar. Abaixo de 768px a sidebar vira um Sheet aberto pelo trigger.
const itens = [
	{ rotulo: "Visão geral", icone: HouseIcon },
	{ rotulo: "Receita", icone: CurrencyCircleDollarIcon, ativo: true },
	{ rotulo: "Unidade consumidora", icone: BuildingsIcon },
	{ rotulo: "Perdas", icone: LightningSlashIcon, badge: "12" },
	{ rotulo: "Rede", icone: GaugeIcon },
];

type Estado = "padrao" | "carregando" | "vazio";

function Exemplo({
	defaultOpen = true,
	estado = "padrao",
}: {
	defaultOpen?: boolean;
	estado?: Estado;
}) {
	return (
		<TooltipProvider>
			<SidebarProvider defaultOpen={defaultOpen} className="h-svh">
				<Sidebar variant="inset" collapsible="icon">
					<SidebarContent>
						<SidebarGroup>
							<SidebarGroupLabel>Painéis</SidebarGroupLabel>
							<SidebarMenu>
								{estado === "carregando" &&
									itens.map(({ rotulo }) => (
										<SidebarMenuItem key={rotulo}>
											<SidebarMenuSkeleton showIcon />
										</SidebarMenuItem>
									))}
								{estado === "vazio" && (
									<p className="px-1.5 text-small text-text-muted group-data-[collapsible=icon]:hidden">
										Nenhuma tela disponível para o seu perfil.
									</p>
								)}
								{estado === "padrao" &&
									itens.map(({ rotulo, icone: Icone, ativo, badge }) => (
										<SidebarMenuItem key={rotulo}>
											<SidebarMenuButton
												// biome-ignore lint/a11y/useAnchorContent: o texto entra pelo children do SidebarMenuButton.
												render={<a href="#sidebar" />}
												isActive={ativo}
												tooltip={rotulo}
											>
												<Icone
													aria-hidden
													weight={ativo ? "fill" : "regular"}
												/>
												<span>{rotulo}</span>
											</SidebarMenuButton>
											{badge && <SidebarMenuBadge>{badge}</SidebarMenuBadge>}
										</SidebarMenuItem>
									))}
							</SidebarMenu>
						</SidebarGroup>
					</SidebarContent>
					<SidebarRail />
				</Sidebar>
				<SidebarInset>
					<header className="flex h-12 items-center gap-2 border-border border-b px-3">
						<SidebarTrigger />
						<span className="font-medium text-body">Receita</span>
					</header>
				</SidebarInset>
			</SidebarProvider>
		</TooltipProvider>
	);
}

const meta = {
	title: "Componentes/Sidebar",
	component: Exemplo,
	tags: ["autodocs"],
	parameters: { layout: "fullscreen" },
} satisfies Meta<typeof Exemplo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

// Ctrl/Cmd+B ou o trigger alternam; recolhida, o rótulo aparece no tooltip.
export const Recolhida: Story = { args: { defaultOpen: false } };

export const Carregando: Story = { args: { estado: "carregando" } };

export const Vazio: Story = { args: { estado: "vazio" } };
