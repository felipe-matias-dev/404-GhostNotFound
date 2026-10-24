import { DownloadSimpleIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "#/components/ui/button";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "./tooltip";

const meta = {
	title: "Componentes/Tooltip",
	component: Tooltip,
	tags: ["autodocs"],
	decorators: [
		(Story) => (
			<TooltipProvider>
				<Story />
			</TooltipProvider>
		),
	],
} satisfies Meta<typeof Tooltip>;

export default meta;
type Story = StoryObj<typeof meta>;

function Exemplo({ aberto }: { aberto?: boolean }) {
	return (
		<Tooltip defaultOpen={aberto}>
			<TooltipTrigger
				render={
					<Button variant="outline" size="icon" aria-label="Exportar CSV" />
				}
			>
				<DownloadSimpleIcon aria-hidden />
			</TooltipTrigger>
			<TooltipContent>Exportar CSV</TooltipContent>
		</Tooltip>
	);
}

// Passe o mouse ou foque o botão.
export const Padrao: Story = { render: () => <Exemplo /> };

export const Aberto: Story = { render: () => <Exemplo aberto /> };
