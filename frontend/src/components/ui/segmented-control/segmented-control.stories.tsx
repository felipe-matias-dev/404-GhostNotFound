import { ChartLineIcon, TableIcon } from "@phosphor-icons/react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { SegmentedControl } from "./segmented-control";

const meta = {
	title: "Componentes/SegmentedControl",
	component: SegmentedControl,
	tags: ["autodocs"],
	parameters: { layout: "centered" },
	args: {
		label: "Visão do gráfico",
		value: "mes",
		onValueChange: () => {},
		options: [
			{ value: "mes", label: "Mês a mês" },
			{ value: "ano", label: "Ano a ano" },
		],
	},
	render: (args) => {
		const [value, setValue] = useState(args.value);
		return (
			<SegmentedControl {...args} value={value} onValueChange={setValue} />
		);
	},
} satisfies Meta<typeof SegmentedControl<string>>;

export default meta;
type Story = StoryObj<typeof meta>;

// Clique ou use as setas: a pílula desliza até a opção escolhida.
export const Padrao: Story = {};

export const TresOpcoes: Story = {
	args: {
		value: "12",
		options: [
			{ value: "6", label: "6 meses" },
			{ value: "12", label: "12 meses" },
			{ value: "todos", label: "Tudo" },
		],
	},
};

export const ComIcones: Story = {
	args: {
		label: "Formato",
		value: "grafico",
		options: [
			{ value: "grafico", label: <ChartLineIcon />, ariaLabel: "Gráfico" },
			{ value: "tabela", label: <TableIcon />, ariaLabel: "Tabela" },
		],
	},
};

export const Desabilitado: Story = { args: { disabled: true } };
