import type { Meta, StoryObj } from "@storybook/react-vite";
import { Pagina } from "./pagina";

const meta = {
	title: "Layout/Pagina",
	component: Pagina,
	tags: ["autodocs"],
	parameters: { layout: "fullscreen" },
	args: {
		descricao:
			"Ponte de receita entre dois períodos, separada em efeito preço, volume e mix.",
		className: "bg-surface-1",
	},
} satisfies Meta<typeof Pagina>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

export const ComConteudo: Story = {
	args: {
		children: (
			<div className="grid gap-3 sm:grid-cols-3">
				{["Receita", "Consumo", "Clientes"].map((titulo) => (
					<div
						key={titulo}
						className="rounded-md border border-border-strong bg-surface-2 p-3 text-small text-text-muted shadow-edge"
					>
						{titulo}
					</div>
				))}
			</div>
		),
	},
};

export const SemDescricao: Story = { args: { descricao: undefined } };
