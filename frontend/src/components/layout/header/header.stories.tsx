import { SidebarIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "#/components/ui/button";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { Header } from "./header";

const meta = {
	title: "Layout/Header",
	component: Header,
	tags: ["autodocs"],
	args: {
		titulo: "Receita",
		acoes: <ThemeToggle className="size-7" />,
		className: "w-[40rem] bg-surface-1",
	},
} satisfies Meta<typeof Header>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

// No app, `inicio` recebe o SidebarTrigger (recolhe a navegação; no celular abre o Sheet).
export const ComMenu: Story = {
	args: {
		className: "w-96 bg-surface-1",
		inicio: (
			<Button variant="ghost" size="icon-sm" aria-label="Recolher navegação">
				<SidebarIcon aria-hidden />
			</Button>
		),
	},
};

export const TituloLongo: Story = {
	args: {
		titulo: "Unidade consumidora 0042 · Rua das Acácias, 1200 · Bairro Centro",
		className: "w-96 bg-surface-1",
	},
};

export const SemTitulo: Story = { args: { titulo: undefined } };
