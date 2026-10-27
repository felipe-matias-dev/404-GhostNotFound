import { CalendarBlankIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "#/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

const meta = {
	title: "Componentes/Popover",
	component: Popover,
	tags: ["autodocs"],
} satisfies Meta<typeof Popover>;

export default meta;
type Story = StoryObj<typeof meta>;

function Exemplo({ aberto }: { aberto?: boolean }) {
	return (
		<Popover defaultOpen={aberto}>
			<PopoverTrigger render={<Button variant="outline" size="sm" />}>
				<CalendarBlankIcon aria-hidden />
				jan–dez 2025
			</PopoverTrigger>
			<PopoverContent className="w-64 p-3 text-body">
				Conteúdo livre: formulários curtos, seletores e detalhes.
			</PopoverContent>
		</Popover>
	);
}

export const Padrao: Story = { render: () => <Exemplo /> };

export const Aberto: Story = { render: () => <Exemplo aberto /> };
