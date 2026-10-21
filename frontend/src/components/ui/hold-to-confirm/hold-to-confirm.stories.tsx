import { TrashIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { HoldToConfirm } from "./hold-to-confirm";

const meta = {
	title: "Componentes/HoldToConfirm",
	component: HoldToConfirm,
	tags: ["autodocs"],
	args: {
		children: "Segure para excluir",
		confirmLabel: "Excluído",
		tone: "destructive",
		onConfirm: fn(),
		onAbort: fn(),
	},
	argTypes: {
		tone: { control: "inline-radio", options: ["destructive", "neutral"] },
	},
} satisfies Meta<typeof HoldToConfirm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Padrao: Story = {};

export const Neutro: Story = {
	args: {
		tone: "neutral",
		children: "Segure para publicar",
		confirmLabel: "Publicado",
	},
};

export const Desabilitado: Story = { args: { disabled: true } };

// Enquanto a exclusão roda, a tela passa `disabled` e o botão segue focável.
export const Carregando: Story = {
	args: { disabled: true, children: "Excluindo…" },
};

export const ZonaDePerigo: Story = {
	args: {
		children: (
			<>
				<TrashIcon aria-hidden />
				Segure para excluir a carga
			</>
		),
		confirmLabel: "Carga excluída",
	},
	render: (args) => (
		<section className="w-96 rounded-lg border border-border bg-surface-1 p-4">
			<h2 className="text-heading">Excluir carga de 03/2026</h2>
			<p className="mt-1 mb-3 text-body text-text-muted">
				As 12 tabelas da competência e o histórico de ajustes saem junto. Não dá
				para desfazer.
			</p>
			<HoldToConfirm {...args} />
		</section>
	),
};
