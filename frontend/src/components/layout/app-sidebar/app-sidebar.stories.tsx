import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { SidebarProvider } from "#/components/ui/sidebar";
import { TooltipProvider } from "#/components/ui/tooltip";
import { AppSidebar } from "./app-sidebar";
import { NAVEGACAO, organizarNavegacao } from "./navegacao";

// `parameters.rota`: rota inicial do router de memória do Storybook (.storybook/preview.tsx);
// define qual item aparece ativo.
const meta = {
	title: "Layout/AppSidebar",
	component: AppSidebar,
	tags: ["autodocs"],
	args: { itens: NAVEGACAO, onConsultarUc: fn() },
	parameters: { layout: "fullscreen", rota: "/" },
	decorators: [
		(Story, { parameters }) => (
			<TooltipProvider>
				<SidebarProvider
					defaultOpen={parameters.recolhida !== true}
					className="h-svh"
				>
					<Story />
				</SidebarProvider>
			</TooltipProvider>
		),
	],
} satisfies Meta<typeof AppSidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

export const ItemAtivo: Story = { parameters: { rota: "/receita" } };

export const MinhaAreaEConsultas: Story = {
	parameters: { rota: "/rede" },
	args: { itens: organizarNavegacao(NAVEGACAO, ["/uc"]) },
};

// Rota de detalhe (`/uc/0042`): o item da seção continua ativo.
export const RotaFilha: Story = { parameters: { rota: "/uc/0042" } };

export const Recolhida: Story = {
	parameters: { rota: "/perdas", recolhida: true },
	args: { itens: organizarNavegacao(NAVEGACAO, ["/uc"]) },
};

export const Vazio: Story = { args: { itens: [] } };
